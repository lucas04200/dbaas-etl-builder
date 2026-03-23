"""
DataForge - Visual Architecture Map
"""

from fastapi import APIRouter, Depends
from app.core.database import cursor, get_db
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/architecture", tags=["architecture"])

@router.get("")
def get_architecture(_: dict = Depends(get_current_user), db=Depends(get_db)):
    nodes = []
    edges = []
    
    with cursor(db) as cur:
        tables = [
            ("postgres", "postgres_instances", "#336791"),
            ("mariadb", "mariadb_instances", "#003545"),
            ("clickhouse", "clickhouse_instances", "#FFCC01"),
            ("redis", "redis_instances", "#DC382D"),
            ("qdrant", "qdrant_instances", "#E51A52"),
            ("minio", "minio_instances", "#C72E49"),
            ("mage", "mage_instances", "#8A2BE2"),
            ("airflow", "airflow_instances", "#017CEE"),
            ("n8n", "n8n_instances", "#FF6D5A"),
            ("metabase", "metabase_instances", "#509EE3"),
            ("superset", "superset_instances", "#00A699"),
            ("ollama", "ollama_instances", "#000000"),
            ("postgrest", "postgrest_instances", "#29B782"),
            ("hasura", "hasura_instances", "#1EB4D4")
        ]
        
        y_offsets = {0: 0, 1: 0, 2: 0, 3: 0}
        type_column = {
            "postgres": 0, "mariadb": 0, "clickhouse": 0,
            "redis": 1, "qdrant": 1, "minio": 1, "ollama": 1,
            "postgrest": 2, "hasura": 2, "mage": 2, "airflow": 2, "n8n": 2,
            "metabase": 3, "superset": 3
        }

        for t_type, t_name, color in tables:
            try:
                cur.execute(f"SELECT * FROM {t_name}")
                rows = cur.fetchall()
                
                for row in rows:
                    if row.get("status") == "error":
                        continue
                        
                    node_id = f"{t_type}-{row['id']}"
                    
                    if "linked_pg_id" in row and row["linked_pg_id"]:
                        parent_id = f"postgres-{row['linked_pg_id']}"
                        edges.append({
                            "id": f"e-{node_id}-{parent_id}",
                            "source": parent_id,
                            "target": node_id,
                            "animated": True,
                            "style": {"stroke": color, "strokeWidth": 2}
                        })
                    
                    if t_type == "postgres" and row.get("is_internal") and row.get("internal_for_type"):
                        parent_id = f"{row['internal_for_type']}-{row['internal_for_id']}"
                        edges.append({
                            "id": f"e-{node_id}-{parent_id}",
                            "source": node_id,
                            "target": parent_id,
                            "animated": True,
                            "style": {"strokeDasharray": "5,5", "stroke": "#888"}
                        })
                    
                    col = type_column[t_type]
                    nodes.append({
                        "id": node_id,
                        "type": "custom",
                        "position": {"x": col * 350 + 50, "y": y_offsets[col] * 100 + 50},
                        "data": {
                            "label": row["name"],
                            "type": t_type,
                            "port": row.get("host_port", ""),
                            "color": color
                        }
                    })
                    y_offsets[col] += 1
            except Exception as e:
                pass # table might not exist or columns changed

    return {"nodes": nodes, "edges": edges}
