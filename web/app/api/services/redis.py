"""
DataForge — Redis instance router.
"""

import secrets

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_redis
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateRedisRequest

router = create_service_crud(ServiceConfig(
    service_type="redis",
    table="redis_instances",
    container_prefix="redis",
    prefix="/api/redis",
    list_columns="id, name, host_port, status, created_at",
))


@router.post("")
def create_redis(body: CreateRedisRequest,
                 bg: BackgroundTasks,
                 user: dict = Depends(require_admin),
                 db=Depends(get_db)):
    port = next_port(db, 6379)
    plain_password = secrets.token_urlsafe(16)
    enc_password = encrypt_secret(plain_password)
    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO redis_instances (name, host_port, password, created_by) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (body.name, port, enc_password, user["id"]),
        )
        instance_id = cur.fetchone()["id"]
    bg.add_task(provision_redis, instance_id, body.name, port, enc_password)
    return {
        "id": instance_id, "port": port,
        "credentials": {"password": plain_password},
    }
