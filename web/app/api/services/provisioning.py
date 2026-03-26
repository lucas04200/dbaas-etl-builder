"""
DataForge — Ansible provisioning and Docker helpers.
"""

import asyncio
import json
from typing import Optional

from app.core.config import BASE_DIR
from app.core.database import cursor, get_pool
from app.core.security import decrypt_secret
from app.core.audit import logger


async def run_ansible(playbook: str, extra_vars: dict) -> tuple[int, str]:
    """Run an Ansible playbook. Secrets in extra_vars are decrypted before passing."""
    cmd = ["ansible-playbook", playbook, "--extra-vars", json.dumps(extra_vars)]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(BASE_DIR / "ansible"),
    )
    stdout, stderr = await proc.communicate()
    output = (stdout + stderr).decode()
    if proc.returncode != 0:
        logger.error("Ansible playbook %s failed (rc: %d): %s", playbook, proc.returncode, output)
    return proc.returncode, output


async def docker_remove(container_name: str, volume_names: list[str] | None = None):
    """
    Kills and force-removes a Docker container and its volumes on the remote host(s)
    using the dedicated remove_container.yml Ansible playbook.
    """
    logger.info("Removing container %s and volumes %s via Ansible", container_name, volume_names)
    code, output = await run_ansible("remove_container.yml", {
        "container_name": container_name,
        "volume_names": volume_names or [],
    })
    if code != 0:
        logger.error("Ansible removal failed for container %s (rc: %d): %s",
                     container_name, code, output)
    else:
        logger.info("Successfully removed container %s and volumes %s",
                    container_name, volume_names)


def _update_status(table: str, instance_id: int, status: str,
                   extra_updates: Optional[list[tuple]] = None):
    """Update instance status after provisioning."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with cursor(conn) as cur:
            cur.execute(
                f"UPDATE {table} SET status = %s WHERE id = %s",
                (status, instance_id),
            )
            if extra_updates:
                for sql, params in extra_updates:
                    cur.execute(sql, params)
        conn.commit()
    finally:
        pool.putconn(conn)


# ── Provisioning functions ───────────────────────────────────────────────────

async def provision_postgres(instance_id: int, name: str, db_name: str,
                              db_user: str, db_password: str, port: int):
    code, _ = await run_ansible("deploy_postgres.yml", {
        "instance_name": name, "db_name": db_name,
        "db_user": db_user, "db_password": decrypt_secret(db_password),
        "host_port": port,
    })
    _update_status("postgres_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_n8n(instance_id: int, name: str, port: int,
                         linked_pg: Optional[dict]):
    extra: dict = {"instance_name": name, "host_port": port}
    if linked_pg:
        extra.update({
            "target_db_host": f"pg_{linked_pg['name']}",
            "target_db_name": linked_pg["db_name"],
            "target_db_user": linked_pg["db_user"],
            "target_db_password": decrypt_secret(linked_pg["db_password"]),
        })
    code, _ = await run_ansible("deploy_n8n.yml", extra)
    _update_status("n8n_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_metabase(instance_id: int, name: str, port: int,
                              internal_pg_id: int, internal_pg_port: int,
                              internal_pg_password: str):
    code, _ = await run_ansible("deploy_metabase.yml", {
        "instance_name": name, "host_port": port,
        "internal_pg_password": decrypt_secret(internal_pg_password),
        "internal_pg_host_port": internal_pg_port,
    })
    status = "running" if code == 0 else "error"
    _update_status("metabase_instances", instance_id, status,
                   [("UPDATE postgres_instances SET status = %s WHERE id = %s",
                     (status, internal_pg_id))])


async def provision_redis(instance_id: int, name: str, port: int, password: str):
    code, _ = await run_ansible("deploy_redis.yml", {
        "instance_name": name, "host_port": port,
        "redis_password": decrypt_secret(password) if password else "",
    })
    _update_status("redis_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_postgrest(instance_id: int, name: str, port: int,
                               linked_pg: dict):
    code, _ = await run_ansible("deploy_postgrest.yml", {
        "instance_name": name, "host_port": port,
        "pg_host": f"pg_{linked_pg['name']}",
        "pg_dbname": linked_pg["db_name"],
        "pg_user": linked_pg["db_user"],
        "pg_password": decrypt_secret(linked_pg["db_password"]),
    })
    _update_status("postgrest_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_mage(instance_id: int, name: str, port: int,
                          internal_pg_id: int, internal_pg_port: int,
                          internal_pg_password: str):
    code, _ = await run_ansible("deploy_mage.yml", {
        "instance_name": name, "host_port": port,
        "internal_pg_password": decrypt_secret(internal_pg_password),
        "internal_pg_host_port": internal_pg_port,
    })
    status = "running" if code == 0 else "error"
    _update_status("mage_instances", instance_id, status,
                   [("UPDATE postgres_instances SET status = %s WHERE id = %s",
                     (status, internal_pg_id))])


async def provision_minio(instance_id: int, name: str, port: int,
                           console_port: int, root_user: str, root_password: str):
    code, _ = await run_ansible("deploy_minio.yml", {
        "instance_name": name, "host_port": port,
        "console_port": console_port,
        "minio_root_user": root_user,
        "minio_root_password": decrypt_secret(root_password),
    })
    _update_status("minio_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_mariadb(instance_id: int, name: str, port: int,
                             root_password: str, db_name: str):
    code, _ = await run_ansible("deploy_mariadb.yml", {
        "instance_name": name, "host_port": port,
        "root_password": decrypt_secret(root_password),
        "db_name": db_name,
    })
    _update_status("mariadb_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_qdrant(instance_id: int, name: str, port: int):
    code, _ = await run_ansible("deploy_qdrant.yml", {
        "instance_name": name, "host_port": port,
    })
    _update_status("qdrant_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_clickhouse(instance_id: int, name: str, port: int,
                                password: str):
    code, _ = await run_ansible("deploy_clickhouse.yml", {
        "instance_name": name, "host_port": port,
        "clickhouse_password": decrypt_secret(password) if password else "",
    })
    _update_status("clickhouse_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_ollama(instance_id: int, name: str, port: int):
    code, _ = await run_ansible("deploy_ollama.yml", {
        "instance_name": name, "host_port": port,
    })
    _update_status("ollama_instances", instance_id,
                   "running" if code == 0 else "error")


async def provision_superset(instance_id: int, name: str, port: int,
                              internal_pg_id: int, internal_pg_port: int,
                              internal_pg_password: str, admin_password: str,
                              superset_secret_key: str):
    code, _ = await run_ansible("deploy_superset.yml", {
        "instance_name": name, "host_port": port,
        "internal_pg_password": decrypt_secret(internal_pg_password),
        "internal_pg_host_port": internal_pg_port,
        "admin_password": decrypt_secret(admin_password),
        "superset_secret_key": superset_secret_key,
    })
    status = "running" if code == 0 else "error"
    _update_status("superset_instances", instance_id, status,
                   [("UPDATE postgres_instances SET status = %s WHERE id = %s",
                     (status, internal_pg_id))])


async def provision_airflow(instance_id: int, name: str, port: int,
                             internal_pg_id: int, internal_pg_port: int,
                             internal_pg_password: str, admin_password: str):
    code, _ = await run_ansible("deploy_airflow.yml", {
        "instance_name": name, "host_port": port,
        "internal_pg_password": decrypt_secret(internal_pg_password),
        "internal_pg_host_port": internal_pg_port,
        "admin_password": decrypt_secret(admin_password),
    })
    status = "running" if code == 0 else "error"
    _update_status("airflow_instances", instance_id, status,
                   [("UPDATE postgres_instances SET status = %s WHERE id = %s",
                     (status, internal_pg_id))])


async def provision_hasura(instance_id: int, name: str, port: int,
                            linked_pg: dict, admin_secret: str):
    code, _ = await run_ansible("deploy_hasura.yml", {
        "instance_name": name, "host_port": port,
        "admin_secret": decrypt_secret(admin_secret),
        "linked_pg_host": f"pg_{linked_pg['name']}",
        "linked_pg_dbname": linked_pg["db_name"],
        "linked_pg_user": linked_pg["db_user"],
        "linked_pg_password": decrypt_secret(linked_pg["db_password"]),
    })
    _update_status("hasura_instances", instance_id,
                   "running" if code == 0 else "error")
