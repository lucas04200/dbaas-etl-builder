"""
DataForge — n8n instance router.
"""

from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.api.deps import require_admin
from app.api.services.provisioning import provision_n8n
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateN8nRequest

router = create_service_crud(ServiceConfig(
    service_type="n8n",
    table="n8n_instances",
    container_prefix="n8n",
    prefix="/api/n8n",
    list_columns="id, name, host_port, linked_pg_id, status, created_at",
))


@router.post("")
def create_n8n(body: CreateN8nRequest,
               bg: BackgroundTasks,
               user: dict = Depends(require_admin),
               db=Depends(get_db)):
    linked_pg = None
    if body.linked_pg_id:
        with cursor(db) as cur:
            cur.execute(
                "SELECT * FROM postgres_instances WHERE id = %s",
                (body.linked_pg_id,),
            )
            linked_pg = cur.fetchone()
        if not linked_pg:
            raise HTTPException(404, "Instance PostgreSQL introuvable")
        linked_pg = dict(linked_pg)

    port = next_port(db, 5678)
    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO n8n_instances (name, host_port, linked_pg_id, created_by) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (body.name, port, body.linked_pg_id, user["id"]),
        )
        instance_id = cur.fetchone()["id"]
    bg.add_task(provision_n8n, instance_id, body.name, port, linked_pg)
    return {"id": instance_id, "port": port}
