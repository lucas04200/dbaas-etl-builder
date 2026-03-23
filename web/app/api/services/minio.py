"""
DataForge — MinIO instance router.
"""

import secrets

from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_minio
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateMinIORequest

router = create_service_crud(ServiceConfig(
    service_type="minio",
    table="minio_instances",
    container_prefix="minio",
    prefix="/api/minio",
    list_columns="id, name, host_port, console_port, root_user, status, created_at",
    volume_prefix="minio_data",
))


@router.post("")
def create_minio(body: CreateMinIORequest,
                 bg: BackgroundTasks,
                 user: dict = Depends(require_admin),
                 db=Depends(get_db)):
    port = next_port(db, 9000)
    console_port = next_port(db, port + 1)
    root_user = "minioadmin"
    plain_password = secrets.token_urlsafe(16)
    enc_password = encrypt_secret(plain_password)
    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO minio_instances "
            "(name, host_port, console_port, root_user, root_password, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (body.name, port, console_port, root_user, enc_password, user["id"]),
        )
        instance_id = cur.fetchone()["id"]
    bg.add_task(provision_minio, instance_id, body.name, port,
                console_port, root_user, enc_password)
    return {
        "id": instance_id, "port": port, "console_port": console_port,
        "credentials": {
            "root_user": root_user, "root_password": plain_password,
        },
    }
