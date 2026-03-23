"""
DataForge — ClickHouse instances API.
"""

import secrets

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_clickhouse
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateClickHouseRequest

router = create_service_crud(ServiceConfig(
    service_type="clickhouse",
    table="clickhouse_instances",
    container_prefix="clickhouse",
    prefix="/api/clickhouse",
    list_columns="id, name, host_port, status, created_at",
    order_by="ORDER BY created_at DESC",
    volume_prefix="clickhouse_data",
))


@router.post("", status_code=201)
def create_clickhouse(
    body: CreateClickHouseRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    port = next_port(db, 8140)
    plain_password = secrets.token_urlsafe(16)
    encrypted_password = encrypt_secret(plain_password)

    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO clickhouse_instances "
                "(name, host_port, password, created_by) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (body.name, port, encrypted_password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe deja")

    bg.add_task(provision_clickhouse, instance_id, body.name, port, encrypted_password)
    return {
        "id": instance_id, "port": port, "status": "provisioning",
        "credentials": {"password": plain_password},
    }
