"""
DataForge — Airflow instances API.

Creates an internal PostgreSQL for Airflow metadata storage.
"""

import secrets

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_airflow
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateAirflowRequest

router = create_service_crud(ServiceConfig(
    service_type="airflow",
    table="airflow_instances",
    container_prefix="airflow",
    prefix="/api/airflow",
    list_columns="id, name, host_port, status, created_at",
    order_by="ORDER BY created_at DESC",
    internal_pg_type="airflow",
    volume_prefix="airflow_data",
))


@router.post("", status_code=201)
def create_airflow(
    body: CreateAirflowRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    airflow_port = next_port(db, 8090)
    internal_pg_port = next_port(db, 15600)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name = f"intpg_airflow_{body.name}"

    plain_admin_password = secrets.token_urlsafe(16)
    encrypted_admin_password = encrypt_secret(plain_admin_password)
    encrypted_pg_password = encrypt_secret(internal_pg_password)

    try:
        with cursor(db) as cur:
            cur.execute(
                """INSERT INTO postgres_instances
                   (name, db_name, db_user, db_password, host_port,
                    is_internal, internal_for_type, created_by)
                   VALUES (%s, %s, %s, %s, %s, TRUE, 'airflow', %s)
                   RETURNING id""",
                (
                    internal_pg_name, "airflow", "airflow",
                    encrypted_pg_password, internal_pg_port, user["id"],
                ),
            )
            internal_pg_id = cur.fetchone()["id"]

        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO airflow_instances "
                "(name, host_port, linked_pg_id, admin_password, created_by) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, airflow_port, internal_pg_id,
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
        provision_airflow, instance_id, body.name, airflow_port,
        internal_pg_id, internal_pg_port, encrypted_pg_password,
        encrypted_admin_password,
    )
    return {
        "id": instance_id, "port": airflow_port, "status": "provisioning",
        "credentials": {
            "admin_user": "admin", "admin_password": plain_admin_password,
        },
    }
