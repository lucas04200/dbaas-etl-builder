"""
DataForge — Metabase instance router.
"""

import secrets

from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_metabase
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateMetabaseRequest

router = create_service_crud(ServiceConfig(
    service_type="metabase",
    table="metabase_instances",
    container_prefix="metabase",
    prefix="/api/metabase",
    list_columns="id, name, host_port, linked_pg_id, status, created_at",
    internal_pg_type="metabase",
))


@router.post("")
def create_metabase(body: CreateMetabaseRequest,
                    bg: BackgroundTasks,
                    user: dict = Depends(require_admin),
                    db=Depends(get_db)):
    metabase_port = next_port(db, 3000)
    internal_pg_port = next_port(db, 15000)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name = f"intpg_meta_{body.name}"
    enc_pg_password = encrypt_secret(internal_pg_password)

    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO postgres_instances "
            "(name, db_name, db_user, db_password, host_port, is_internal, internal_for_type, created_by) "
            "VALUES (%s, 'metabase', 'metabase', %s, %s, TRUE, 'metabase', %s) RETURNING id",
            (internal_pg_name, enc_pg_password, internal_pg_port, user["id"]),
        )
        internal_pg_id = cur.fetchone()["id"]

        cur.execute(
            "INSERT INTO metabase_instances (name, host_port, linked_pg_id, created_by) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (body.name, metabase_port, internal_pg_id, user["id"]),
        )
        instance_id = cur.fetchone()["id"]

        cur.execute(
            "UPDATE postgres_instances SET internal_for_id = %s WHERE id = %s",
            (instance_id, internal_pg_id),
        )

    bg.add_task(provision_metabase, instance_id, body.name, metabase_port,
                internal_pg_id, internal_pg_port, enc_pg_password)
    return {"id": instance_id, "port": metabase_port}
