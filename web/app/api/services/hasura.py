"""
DataForge — Hasura instances API.

Requires a linked (non-internal) PostgreSQL instance.
"""

import secrets

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_hasura
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateHasuraRequest

router = create_service_crud(ServiceConfig(
    service_type="hasura",
    table="hasura_instances",
    container_prefix="hasura",
    prefix="/api/hasura",
    list_columns=(
        "h.id, h.name, h.host_port, h.status, h.created_at, "
        "p.name AS linked_pg_name"
    ),
    list_from=(
        "hasura_instances h "
        "JOIN postgres_instances p ON p.id = h.linked_pg_id"
    ),
    list_alias="h",
    order_by="ORDER BY h.created_at DESC",
))


@router.post("", status_code=201)
def create_hasura(
    body: CreateHasuraRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    with cursor(db) as cur:
        cur.execute(
            "SELECT * FROM postgres_instances "
            "WHERE id = %s AND is_internal = FALSE",
            (body.linked_pg_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance PostgreSQL introuvable")
    linked_pg = dict(row)

    port = next_port(db, 8280)
    plain_secret = secrets.token_urlsafe(24)
    encrypted_secret = encrypt_secret(plain_secret)

    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO hasura_instances "
                "(name, host_port, linked_pg_id, admin_secret, created_by) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, port, body.linked_pg_id, encrypted_secret, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe deja")

    bg.add_task(
        provision_hasura, instance_id, body.name, port,
        linked_pg, encrypted_secret,
    )
    return {
        "id": instance_id, "port": port, "status": "provisioning",
        "credentials": {"admin_secret": plain_secret},
    }
