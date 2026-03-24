"""
DataForge — Visual Architecture Map
"""

import json
import urllib.request
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.database import cursor, get_db
from app.api.deps import get_current_user, require_admin
from app.core.security import decrypt_secret

router = APIRouter(prefix="/api/architecture", tags=["architecture"])

# ── Positions helpers ─────────────────────────────────────────────────────────

def _load_positions(db) -> dict:
    with cursor(db) as cur:
        cur.execute("SELECT value FROM app_config WHERE key = 'architecture_positions'")
        row = cur.fetchone()
    return json.loads(row["value"]) if row else {}


def _save_positions(db, positions: dict):
    with cursor(db) as cur:
        cur.execute(
            """INSERT INTO app_config (key, value) VALUES ('architecture_positions', %s)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
            (json.dumps(positions),),
        )


# ── Graph builder ─────────────────────────────────────────────────────────────

@router.get("")
def get_architecture(_: dict = Depends(get_current_user), db=Depends(get_db)):
    nodes = []
    edges = []
    saved_positions = _load_positions(db)

    with cursor(db) as cur:
        tables = [
            ("postgres",   "postgres_instances",   "#336791"),
            ("mariadb",    "mariadb_instances",    "#C0765A"),
            ("clickhouse", "clickhouse_instances", "#FACC15"),
            ("redis",      "redis_instances",      "#DC2626"),
            ("qdrant",     "qdrant_instances",     "#7B61FF"),
            ("minio",      "minio_instances",      "#C72E2B"),
            ("mage",       "mage_instances",       "#7C3AED"),
            ("airflow",    "airflow_instances",    "#017CEE"),
            ("metabase",   "metabase_instances",   "#509EE3"),
            ("superset",   "superset_instances",   "#20A7C9"),
            ("ollama",     "ollama_instances",     "#111827"),
            ("postgrest",  "postgrest_instances",  "#0D6EFD"),
            ("hasura",     "hasura_instances",     "#1EB4D4"),
        ]

        # Column layout (x position) and y offset tracker
        type_column = {
            "postgres": 0, "mariadb": 0,
            "redis": 1, "qdrant": 1, "minio": 1,
            "ollama": 1,
            "postgrest": 2, "hasura": 2, "mage": 2, "airflow": 2,
            "metabase": 3, "superset": 3, "clickhouse": 3,
        }
        y_offsets = {0: 0, 1: 0, 2: 0, 3: 0}

        for t_type, t_name, color in tables:
            try:
                cur.execute(f"SELECT * FROM {t_name}")
                rows = cur.fetchall()
            except Exception:
                continue

            for row in rows:
                if row.get("status") == "error":
                    continue

                # Skip internal postgres — show as badge on their parent instead
                if t_type == "postgres" and row.get("is_internal"):
                    # Still create the edge from the service it belongs to
                    if row.get("internal_for_type") and row.get("internal_for_id"):
                        # Edge: user PG (internal) → service that uses it
                        # We represent it as "service has a built-in DB"
                        # No node for the internal PG, just annotate the edge
                        pass
                    continue

                node_id = f"{t_type}-{row['id']}"
                col = type_column.get(t_type, 3)

                # Use saved position if available, otherwise calculate layout
                if node_id in saved_positions:
                    position = saved_positions[node_id]
                else:
                    position = {"x": col * 280 + 60, "y": y_offsets[col] * 130 + 60}

                y_offsets[col] += 1

                # Detect if this service has an internal PG linked to it
                has_internal_pg = False
                try:
                    cur.execute(
                        "SELECT COUNT(*) as n FROM postgres_instances "
                        "WHERE is_internal = TRUE AND internal_for_type = %s AND internal_for_id = %s",
                        (t_type, row["id"]),
                    )
                    r = cur.fetchone()
                    has_internal_pg = r and r["n"] > 0
                except Exception:
                    pass

                nodes.append({
                    "id": node_id,
                    "type": "custom",
                    "position": position,
                    "data": {
                        "label":          row["name"],
                        "type":           t_type,
                        "port":           row.get("host_port", ""),
                        "color":          color,
                        "status":         row.get("status", "unknown"),
                        "hasInternalPg":  has_internal_pg,
                    },
                })

                # Edge: linked_pg_id → this service
                if row.get("linked_pg_id"):
                    pg_node = f"postgres-{row['linked_pg_id']}"
                    edges.append({
                        "id":       f"e-{pg_node}-{node_id}",
                        "source":   pg_node,
                        "target":   node_id,
                        "animated": True,
                        "label":    "DB",
                        "style":    {"stroke": color, "strokeWidth": 2},
                        "labelStyle": {"fontSize": "10px", "fill": color},
                    })

    # ── Auto-detected edges from service APIs ─────────────────────────────────
    # Build port→node_id map for all postgres instances (to match detected connections)
    pg_port_map = {n["data"]["port"]: n["id"] for n in nodes if n["data"]["type"] == "postgres"}

    auto_edges = _detect_service_connections(db, nodes, pg_port_map)
    for e in auto_edges:
        if not any(ex["id"] == e["id"] for ex in edges):
            edges.append(e)

    # ── Manual edges drawn by user ────────────────────────────────────────────
    with cursor(db) as cur2:
        cur2.execute("SELECT value FROM app_config WHERE key = 'architecture_manual_edges'")
        row = cur2.fetchone()
    if row:
        for e in json.loads(row["value"]):
            if not any(ex["id"] == e["id"] for ex in edges):
                edges.append(e)

    return {"nodes": nodes, "edges": edges}


def _detect_service_connections(db, nodes: list, pg_port_map: dict) -> list:
    """
    Interroge l'API de chaque service en cours pour détecter
    les bases PostgreSQL qu'il a configurées.
    Retourne une liste d'edges à ajouter au graphe.
    """
    edges = []

    # Helper: essayer de matcher un host:port à un node postgres DataForge
    def pg_node_for_port(port: int):
        return pg_port_map.get(port)

    def http_get(url, headers=None, timeout=3):
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def http_post(url, payload, headers=None, timeout=3):
        data = json.dumps(payload).encode()
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    # ── Superset ──────────────────────────────────────────────────────────────
    with cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, admin_password FROM superset_instances WHERE status = 'running'")
        superset_rows = cur.fetchall()

    for inst in superset_rows:
        try:
            base = f"http://localhost:{inst['host_port']}"
            pwd = decrypt_secret(inst["admin_password"])
            tok = http_post(f"{base}/api/v1/security/login", {
                "username": "admin", "password": pwd,
                "provider": "db", "refresh": False,
            })["access_token"]
            dbs = http_get(f"{base}/api/v1/database/", {"Authorization": f"Bearer {tok}"})
            for db_entry in dbs.get("result", []):
                uri = db_entry.get("sqlalchemy_uri", "")
                # postgresql://user:pass@host:PORT/dbname
                try:
                    port = int(uri.split(":")[-1].split("/")[0])
                    pg_node = pg_node_for_port(port)
                    if pg_node:
                        svc_node = f"superset-{inst['id']}"
                        edges.append({
                            "id": f"auto-{pg_node}-{svc_node}-{port}",
                            "source": pg_node, "target": svc_node,
                            "animated": True, "label": db_entry.get("database_name", "DB"),
                            "style": {"stroke": "#20A7C9", "strokeWidth": 2},
                            "labelStyle": {"fontSize": "10px", "fill": "#20A7C9"},
                        })
                except Exception:
                    pass
        except Exception:
            pass

    # ── Airflow ───────────────────────────────────────────────────────────────
    with cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, admin_password FROM airflow_instances WHERE status = 'running'")
        airflow_rows = cur.fetchall()

    for inst in airflow_rows:
        try:
            base = f"http://localhost:{inst['host_port']}"
            pwd = decrypt_secret(inst["admin_password"])
            import base64 as b64
            creds = b64.b64encode(f"admin:{pwd}".encode()).decode()
            conns = http_get(f"{base}/api/v1/connections",
                             {"Authorization": f"Basic {creds}"})
            for conn in conns.get("connections", []):
                if conn.get("conn_type") != "postgres":
                    continue
                try:
                    port = int(conn.get("port", 0))
                    pg_node = pg_node_for_port(port)
                    if pg_node:
                        svc_node = f"airflow-{inst['id']}"
                        edges.append({
                            "id": f"auto-{pg_node}-{svc_node}-{port}",
                            "source": pg_node, "target": svc_node,
                            "animated": True, "label": conn.get("conn_id", "conn"),
                            "style": {"stroke": "#017CEE", "strokeWidth": 2},
                            "labelStyle": {"fontSize": "10px", "fill": "#017CEE"},
                        })
                except Exception:
                    pass
        except Exception:
            pass

    # ── Mage.ai ───────────────────────────────────────────────────────────────
    with cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, access_token FROM mage_instances WHERE status = 'running'")
        mage_rows = cur.fetchall()

    for inst in mage_rows:
        try:
            base = f"http://localhost:{inst['host_port']}"
            tok = inst.get("access_token") or ""
            headers = {"X-API-KEY": tok} if tok else {}
            result = http_get(f"{base}/api/data_sources", headers)
            for src in result.get("data_sources", []):
                if src.get("type") not in ("postgresql", "postgres"):
                    continue
                try:
                    port = int(src.get("config", {}).get("port", 0))
                    pg_node = pg_node_for_port(port)
                    if pg_node:
                        svc_node = f"mage-{inst['id']}"
                        edges.append({
                            "id": f"auto-{pg_node}-{svc_node}-{port}",
                            "source": pg_node, "target": svc_node,
                            "animated": True, "label": src.get("name", "source"),
                            "style": {"stroke": "#7C3AED", "strokeWidth": 2},
                            "labelStyle": {"fontSize": "10px", "fill": "#7C3AED"},
                        })
                except Exception:
                    pass
        except Exception:
            pass

    return edges


# ── Save positions ────────────────────────────────────────────────────────────

class PositionsPayload(BaseModel):
    positions: dict  # {node_id: {x: float, y: float}}


@router.post("/positions")
def save_positions(body: PositionsPayload,
                   _: dict = Depends(get_current_user),
                   db=Depends(get_db)):
    existing = _load_positions(db)
    existing.update(body.positions)
    _save_positions(db, existing)
    return {"ok": True}


@router.delete("/positions")
def reset_positions(_: dict = Depends(require_admin), db=Depends(get_db)):
    """Réinitialise le layout automatique."""
    with cursor(db) as cur:
        cur.execute("DELETE FROM app_config WHERE key = 'architecture_positions'")
    return {"ok": True}


# ── Manual edges ──────────────────────────────────────────────────────────────

def _load_manual_edges(db) -> list:
    with cursor(db) as cur:
        cur.execute("SELECT value FROM app_config WHERE key = 'architecture_manual_edges'")
        row = cur.fetchone()
    return json.loads(row["value"]) if row else []


def _save_manual_edges(db, edges: list):
    with cursor(db) as cur:
        cur.execute(
            """INSERT INTO app_config (key, value) VALUES ('architecture_manual_edges', %s)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
            (json.dumps(edges),),
        )


class EdgePayload(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""


@router.post("/edges")
def add_manual_edge(body: EdgePayload,
                    _: dict = Depends(get_current_user),
                    db=Depends(get_db)):
    edges = _load_manual_edges(db)
    # Avoid duplicates
    if not any(e["id"] == body.id for e in edges):
        edges.append({
            "id": body.id,
            "source": body.source,
            "target": body.target,
            "label": body.label,
            "animated": True,
            "style": {"stroke": "#6B7280", "strokeWidth": 2, "strokeDasharray": "6,3"},
            "labelStyle": {"fontSize": "10px", "fill": "#6B7280"},
        })
        _save_manual_edges(db, edges)
    return {"ok": True}


class EdgeLabelPayload(BaseModel):
    label: str


@router.patch("/edges/{edge_id}")
def update_manual_edge(edge_id: str,
                       body: EdgeLabelPayload,
                       _: dict = Depends(get_current_user),
                       db=Depends(get_db)):
    edges = _load_manual_edges(db)
    for e in edges:
        if e["id"] == edge_id:
            e["label"] = body.label
            break
    _save_manual_edges(db, edges)
    return {"ok": True}


@router.delete("/edges/{edge_id}")
def delete_manual_edge(edge_id: str,
                       _: dict = Depends(get_current_user),
                       db=Depends(get_db)):
    edges = _load_manual_edges(db)
    edges = [e for e in edges if e["id"] != edge_id]
    _save_manual_edges(db, edges)
    return {"ok": True}
