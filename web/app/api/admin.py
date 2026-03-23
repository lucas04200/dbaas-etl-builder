"""
DataForge — Admin API.

Endpoint to reveal instance credentials (admin only, audited).
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.database import cursor, get_db
from app.core.security import decrypt_secret
from app.core.audit import audit_log
from app.api.deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Mapping of service type → (table, secret columns)
_SERVICE_SECRETS = {
    "postgres":   ("postgres_instances",   ["db_password"]),
    "redis":      ("redis_instances",      ["password"]),
    "minio":      ("minio_instances",      ["root_password"]),
    "mariadb":    ("mariadb_instances",     ["root_password"]),
    "clickhouse": ("clickhouse_instances",  ["password"]),
    "superset":   ("superset_instances",    ["admin_password"]),
    "airflow":    ("airflow_instances",     ["admin_password"]),
    "hasura":     ("hasura_instances",      ["admin_secret"]),
    "mage":       ("mage_instances",        ["access_token"]),
}


@router.get("/instances/{service_type}/{instance_id}/credentials")
def reveal_credentials(
    service_type: str,
    instance_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
    db=Depends(get_db),
):
    """
    Reveal decrypted credentials for a service instance.
    Admin only. Every call is logged in the audit trail.
    """
    svc = _SERVICE_SECRETS.get(service_type)
    if not svc:
        raise HTTPException(400, f"Type de service non supporte : {service_type}")

    table, secret_cols = svc

    # Build SELECT with the secret columns + identifiers
    cols = ", ".join(["id", "name"] + secret_cols)
    from psycopg2 import sql as pg_sql

    with cursor(db) as cur:
        cur.execute(
            pg_sql.SQL("SELECT {} FROM {} WHERE id = %s").format(
                pg_sql.SQL(", ").join(pg_sql.Identifier(c) for c in ["id", "name"] + secret_cols),
                pg_sql.Identifier(table),
            ),
            (instance_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Instance introuvable")

    # Decrypt secret columns
    credentials = {"name": row["name"]}
    for col in secret_cols:
        raw_value = row.get(col, "")
        if raw_value:
            credentials[col] = decrypt_secret(raw_value)
        else:
            credentials[col] = ""

    # Add connection info for databases
    if service_type == "postgres":
        with cursor(db) as cur:
            cur.execute(
                "SELECT db_name, db_user, host_port FROM postgres_instances WHERE id = %s",
                (instance_id,),
            )
            pg_row = cur.fetchone()
        if pg_row:
            credentials["db_name"] = pg_row["db_name"]
            credentials["db_user"] = pg_row["db_user"]
            credentials["host_port"] = pg_row["host_port"]

    elif service_type == "minio":
        with cursor(db) as cur:
            cur.execute(
                "SELECT root_user, host_port, console_port FROM minio_instances WHERE id = %s",
                (instance_id,),
            )
            minio_row = cur.fetchone()
        if minio_row:
            credentials["root_user"] = minio_row["root_user"]
            credentials["host_port"] = minio_row["host_port"]
            credentials["console_port"] = minio_row["console_port"]

    elif service_type == "mariadb":
        with cursor(db) as cur:
            cur.execute(
                "SELECT db_name, host_port FROM mariadb_instances WHERE id = %s",
                (instance_id,),
            )
            maria_row = cur.fetchone()
        if maria_row:
            credentials["db_name"] = maria_row["db_name"]
            credentials["host_port"] = maria_row["host_port"]

    # Audit trail
    audit_log(
        "reveal_credentials",
        user_id=admin["id"],
        username=admin["username"],
        ip=request.client.host,
        detail={
            "service_type": service_type,
            "instance_id": instance_id,
            "instance_name": row["name"],
        },
    )

    # Also store in DB audit table
    with cursor(db) as cur:
        cur.execute(
            """INSERT INTO audit_log (user_id, action, detail, ip)
               VALUES (%s, %s, %s, %s)""",
            (
                admin["id"],
                "reveal_credentials",
                f'{{"service_type":"{service_type}","instance_id":{instance_id},"instance_name":"{row["name"]}"}}',
                request.client.host,
            ),
        )

    return credentials
