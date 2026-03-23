"""
DataForge — Superset instances API.

Creates an internal PostgreSQL for Superset metadata storage.
"""

import secrets

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_superset
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateSupersetRequest

router = create_service_crud(ServiceConfig(
    service_type="superset",
    table="superset_instances",
    container_prefix="superset",
    prefix="/api/superset",
    list_columns="id, name, host_port, status, created_at",
    order_by="ORDER BY created_at DESC",
    internal_pg_type="superset",
    volume_prefix="superset_data",
))


@router.post("", status_code=201)
def create_superset(
    body: CreateSupersetRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    superset_port = next_port(db, 8088)
    internal_pg_port = next_port(db, 15500)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name = f"intpg_superset_{body.name}"
    superset_secret_key = secrets.token_hex(32)

    plain_admin_password = secrets.token_urlsafe(16)
    encrypted_admin_password = encrypt_secret(plain_admin_password)
    encrypted_pg_password = encrypt_secret(internal_pg_password)

    try:
        with cursor(db) as cur:
            cur.execute(
                """INSERT INTO postgres_instances
                   (name, db_name, db_user, db_password, host_port,
                    is_internal, internal_for_type, created_by)
                   VALUES (%s, %s, %s, %s, %s, TRUE, 'superset', %s)
                   RETURNING id""",
                (
                    internal_pg_name, "superset", "superset",
                    encrypted_pg_password, internal_pg_port, user["id"],
                ),
            )
            internal_pg_id = cur.fetchone()["id"]

        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO superset_instances "
                "(name, host_port, linked_pg_id, admin_password, created_by) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, superset_port, internal_pg_id,
                 encrypted_admin_password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]

        with cursor(db) as cur:
            cur.execute(
                "UPDATE postgres_instances SET internal_for_id = %s WHERE id = %s",
                (instance_id, internal_pg_id),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe deja")

    bg.add_task(
        provision_superset, instance_id, body.name, superset_port,
        internal_pg_id, internal_pg_port, encrypted_pg_password,
        encrypted_admin_password, superset_secret_key,
    )
    return {
        "id": instance_id, "port": superset_port, "status": "provisioning",
        "credentials": {
            "admin_user": "admin", "admin_password": plain_admin_password,
        },
    }
