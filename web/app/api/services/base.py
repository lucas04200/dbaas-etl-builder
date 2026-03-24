"""
DataForge — Generic service CRUD factory.

Generates standard list / get / delete endpoints for service routers.
Each service adds its own create endpoint and any extra routes.
"""

from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db
from app.api.deps import get_current_user, require_admin
from app.api.services.provisioning import docker_remove


@dataclass
class ServiceConfig:
    """Configuration for a service's CRUD endpoints."""

    service_type: str              # e.g. "redis"
    table: str                     # e.g. "redis_instances"
    container_prefix: str          # e.g. "redis"  → container "redis_{name}"
    prefix: str                    # e.g. "/api/redis"

    # Columns for list / get queries (without secrets)
    list_columns: str              # e.g. "id, name, host_port, status, created_at"

    # Optional SQL appended after FROM clause (for JOINs)
    list_from: str = ""            # e.g. "m LEFT JOIN postgres_instances p ON ..."
    list_alias: str = ""           # table alias used in WHERE clause, e.g. "m"

    # ORDER BY clause
    order_by: str = "ORDER BY id"

    # If set, cascade-delete internal PG on service delete
    internal_pg_type: Optional[str] = None

    # Extra containers to remove on delete (relative to name)
    extra_containers: list[str] = field(default_factory=list)

    # If set, docker volume rm {volume_prefix}_{name} is called on delete
    # e.g. "redis_data" → deletes volume "redis_data_{name}"
    volume_prefix: Optional[str] = None


def create_service_crud(config: ServiceConfig) -> APIRouter:
    """
    Build an APIRouter with standard list / get / delete endpoints.

    The caller is responsible for adding create (POST) and any custom endpoints.
    """
    router = APIRouter(prefix=config.prefix, tags=[config.service_type])
    alias = config.list_alias or config.table
    from_clause = config.list_from or config.table

    # ── LIST ─────────────────────────────────────────────────────────────────

    @router.get("")
    def list_instances(_: dict = Depends(get_current_user), db=Depends(get_db)):
        with cursor(db) as cur:
            cur.execute(
                f"SELECT {config.list_columns} FROM {from_clause} {config.order_by}"
            )
            return [dict(r) for r in cur.fetchall()]

    # ── GET ──────────────────────────────────────────────────────────────────

    @router.get("/{instance_id}")
    def get_instance(instance_id: int,
                     _: dict = Depends(get_current_user),
                     db=Depends(get_db)):
        with cursor(db) as cur:
            cur.execute(
                f"SELECT {config.list_columns} FROM {from_clause} "
                f"WHERE {alias}.id = %s",
                (instance_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Instance introuvable")
        return dict(row)

    # ── DELETE ───────────────────────────────────────────────────────────────

    if config.internal_pg_type:
        # Cascade-delete: service + internal PG
        @router.delete("/{instance_id}")
        async def delete_instance_cascade(
            instance_id: int,
            _: dict = Depends(require_admin),
            db=Depends(get_db),
        ):
            with cursor(db) as cur:
                cur.execute(
                    f"SELECT name FROM {config.table} WHERE id = %s",
                    (instance_id,),
                )
                row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Instance introuvable")
            name = row["name"]

            # Find & remove internal PG
            with cursor(db) as cur:
                cur.execute(
                    "SELECT id, name FROM postgres_instances "
                    "WHERE internal_for_type = %s AND internal_for_id = %s",
                    (config.internal_pg_type, instance_id),
                )
                internal_pg = cur.fetchone()

            main_volumes = [f"{config.volume_prefix}_{name}"] if config.volume_prefix else []
            await docker_remove(f"{config.container_prefix}_{name}", volume_names=main_volumes)

            if internal_pg:
                # Internal PG container & volume names MUST match those in Ansible (internal_pg role)
                # pattern: pg_internal_{service_type}_{instance_name}
                internal_pg_container = f"pg_internal_{config.internal_pg_type}_{name}"
                internal_pg_volumes = [f"pg_internal_{config.internal_pg_type}_data_{name}"]
                await docker_remove(internal_pg_container, volume_names=internal_pg_volumes)

            for extra in config.extra_containers:
                await docker_remove(f"{extra}_{name}")

            with cursor(db) as cur:
                if internal_pg:
                    cur.execute(
                        "DELETE FROM postgres_instances WHERE id = %s",
                        (internal_pg["id"],),
                    )
                cur.execute(
                    f"DELETE FROM {config.table} WHERE id = %s",
                    (instance_id,),
                )
            return {"ok": True}
    else:
        # Simple delete: just service container
        @router.delete("/{instance_id}")
        async def delete_instance_simple(
            instance_id: int,
            _: dict = Depends(require_admin),
            db=Depends(get_db),
        ):
            with cursor(db) as cur:
                cur.execute(
                    f"SELECT name FROM {config.table} WHERE id = %s",
                    (instance_id,),
                )
                row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Instance introuvable")

            volumes = [f"{config.volume_prefix}_{row['name']}"] if config.volume_prefix else []
            await docker_remove(f"{config.container_prefix}_{row['name']}", volume_names=volumes)

            with cursor(db) as cur:
                cur.execute(
                    f"DELETE FROM {config.table} WHERE id = %s",
                    (instance_id,),
                )
            return {"ok": True}

    return router
