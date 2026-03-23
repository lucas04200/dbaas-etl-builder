"""
DataForge — Qdrant instances API.
"""

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.api.deps import require_admin
from app.api.services.provisioning import provision_qdrant
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateQdrantRequest

router = create_service_crud(ServiceConfig(
    service_type="qdrant",
    table="qdrant_instances",
    container_prefix="qdrant",
    prefix="/api/qdrant",
    list_columns="id, name, host_port, status, created_at",
    order_by="ORDER BY created_at DESC",
    volume_prefix="qdrant_data",
))


@router.post("", status_code=201)
def create_qdrant(
    body: CreateQdrantRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    port = next_port(db, 6333)
    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO qdrant_instances (name, host_port, created_by) "
                "VALUES (%s, %s, %s) RETURNING id",
                (body.name, port, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe deja")

    bg.add_task(provision_qdrant, instance_id, body.name, port)
    return {"id": instance_id, "port": port, "status": "provisioning"}
