"""
DataForge — PostgREST instance router.
"""

from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.api.deps import require_admin
from app.api.services.provisioning import provision_postgrest
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreatePostgRESTRequest

router = create_service_crud(ServiceConfig(
    service_type="postgrest",
    table="postgrest_instances",
    container_prefix="postgrest",
    prefix="/api/postgrest",
    list_columns=(
        "pr.id, pr.name, pr.host_port, pr.linked_pg_id, pr.db_schema, "
        "pr.status, pr.created_at, p.name AS linked_pg_name"
    ),
    list_from=(
        "postgrest_instances pr "
        "LEFT JOIN postgres_instances p ON p.id = pr.linked_pg_id"
    ),
    list_alias="pr",
))


@router.post("")
def create_postgrest(body: CreatePostgRESTRequest,
                     bg: BackgroundTasks,
                     user: dict = Depends(require_admin),
                     db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute(
            "SELECT * FROM postgres_instances WHERE id = %s",
            (body.linked_pg_id,),
        )
        linked_pg = cur.fetchone()
    if not linked_pg:
        raise HTTPException(404, "Instance PostgreSQL introuvable")
    linked_pg = dict(linked_pg)

    port = next_port(db, 3100)
    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO postgrest_instances (name, host_port, linked_pg_id, db_schema, created_by) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (body.name, port, body.linked_pg_id, body.db_schema, user["id"]),
        )
        instance_id = cur.fetchone()["id"]
    bg.add_task(provision_postgrest, instance_id, body.name, port, linked_pg)
    return {"id": instance_id, "port": port}
