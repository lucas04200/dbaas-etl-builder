"""
DataForge — Monitoring Docker (Live Stats + Status Sync + Logs)
"""

import json
import subprocess
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_current_user, require_admin
from app.core.database import cursor, get_db

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Tables de service avec leur préfixe de container
_SERVICE_TABLES = [
    ("postgres_instances",    "pg"),
    ("mariadb_instances",     "mariadb"),
    ("qdrant_instances",      "qdrant"),
    ("clickhouse_instances",  "clickhouse"),
    ("metabase_instances",    "metabase"),
    ("superset_instances",    "superset"),
    ("mage_instances",        "mage"),
    ("airflow_instances",     "airflow"),
    ("postgrest_instances",   "postgrest"),
    ("hasura_instances",      "hasura"),
    ("redis_instances",       "redis"),
    ("minio_instances",       "minio"),
    ("ollama_instances",      "ollama"),
]


@router.get("")
def get_docker_stats(_: dict = Depends(require_admin)):
    """CPU/RAM/IO en live via docker stats."""
    try:
        res = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=15,
        )
        containers = []
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                name = data.get("Name", "").lstrip("/")
                containers.append({
                    "id":       data.get("ID"),
                    "name":     name,
                    "cpu":      data.get("CPUPerc", "0.00%"),
                    "mem":      data.get("MemUsage", "0B / 0B"),
                    "mem_perc": data.get("MemPerc", "0.00%"),
                    "net":      data.get("NetIO", "0B / 0B"),
                    "block":    data.get("BlockIO", "0B / 0B"),
                })
            except json.JSONDecodeError:
                pass
        return sorted(containers, key=lambda c: c["name"])
    except Exception as e:
        return {"error": str(e)}


@router.post("/sync")
def sync_statuses(_: dict = Depends(require_admin), db=Depends(get_db)):
    """
    Compare le statut réel de chaque container Docker avec ce qui est en DB.
    Met à jour les instances dont le statut a changé.
    Retourne la liste des changements effectués.
    """
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception as e:
        raise HTTPException(500, f"Docker inaccessible : {e}")

    # Construire un dict {container_name: state}
    docker_states: dict[str, str] = {}
    for line in res.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            d = json.loads(line)
            name = d.get("Names", "").lstrip("/")
            state = d.get("State", "unknown")  # running / exited / paused / ...
            docker_states[name] = state
        except json.JSONDecodeError:
            pass

    changes = []

    for table, prefix in _SERVICE_TABLES:
        try:
            with cursor(db) as cur:
                cur.execute(f"SELECT id, name, status FROM {table}")
                rows = cur.fetchall()
        except Exception:
            continue  # table peut ne pas exister encore

        for row in rows:
            container_name = f"{prefix}_{row['name']}"
            docker_state = docker_states.get(container_name)

            if docker_state is None:
                # Container introuvable → erreur si la DB pense qu'il tourne
                if row["status"] == "running":
                    new_status = "error"
                else:
                    continue
            elif docker_state == "running":
                new_status = "running"
            else:
                # exited, paused, dead, etc.
                new_status = "stopped"

            if new_status != row["status"]:
                with cursor(db) as cur:
                    cur.execute(
                        f"UPDATE {table} SET status = %s WHERE id = %s",
                        (new_status, row["id"]),
                    )
                changes.append({
                    "table":     table,
                    "name":      row["name"],
                    "container": container_name,
                    "old":       row["status"],
                    "new":       new_status,
                })

    return {"synced": len(changes), "changes": changes}


@router.get("/logs/{container_name}")
def get_container_logs(
    container_name: str,
    tail: int = Query(default=200, ge=10, le=2000),
    _: dict = Depends(get_current_user),
):
    """Retourne les N dernières lignes de logs d'un container Docker."""
    # Sécurité basique : pas de caractères spéciaux dans le nom
    if not container_name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Nom de container invalide")

    try:
        res = subprocess.run(
            ["docker", "logs", "--tail", str(tail), "--timestamps", container_name],
            capture_output=True, text=True, timeout=10,
        )
        # docker logs écrit sur stderr par défaut
        output = res.stderr or res.stdout
        lines = output.strip().split("\n") if output.strip() else []
        return {"container": container_name, "lines": lines, "count": len(lines)}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Timeout lors de la récupération des logs")
    except Exception as e:
        raise HTTPException(500, str(e))
