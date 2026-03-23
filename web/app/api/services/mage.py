"""
DataForge — Mage instance router.
"""

import secrets

from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_mage
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateMageRequest

router = create_service_crud(ServiceConfig(
    service_type="mage",
    table="mage_instances",
    container_prefix="mage",
    prefix="/api/mage",
    list_columns=(
        "m.id, m.name, m.host_port, m.status, m.created_at, "
        "p.name AS linked_pg_name"
    ),
    list_from=(
        "mage_instances m "
        "LEFT JOIN postgres_instances p ON p.id = m.linked_pg_id"
    ),
    list_alias="m",
    internal_pg_type="mage",
))


@router.post("")
def create_mage(body: CreateMageRequest,
                bg: BackgroundTasks,
                user: dict = Depends(require_admin),
                db=Depends(get_db)):
    port = next_port(db, 6789)
    internal_pg_port = next_port(db, 15200)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name = f"intpg_mage_{body.name}"
    enc_pg_password = encrypt_secret(internal_pg_password)

    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO postgres_instances "
            "(name, db_name, db_user, db_password, host_port, is_internal, internal_for_type, created_by) "
            "VALUES (%s, 'mage', 'mage', %s, %s, TRUE, 'mage', %s) RETURNING id",
            (internal_pg_name, enc_pg_password, internal_pg_port, user["id"]),
        )
        internal_pg_id = cur.fetchone()["id"]

        cur.execute(
            "INSERT INTO mage_instances (name, host_port, linked_pg_id, created_by) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (body.name, port, internal_pg_id, user["id"]),
        )
        instance_id = cur.fetchone()["id"]

        cur.execute(
            "UPDATE postgres_instances SET internal_for_id = %s WHERE id = %s",
            (instance_id, internal_pg_id),
        )

    bg.add_task(provision_mage, instance_id, body.name, port,
                internal_pg_id, internal_pg_port, enc_pg_password)
    return {"id": instance_id, "port": port}
