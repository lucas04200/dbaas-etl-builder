"""
DataForge — MariaDB instances API.
"""

import secrets

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret, decrypt_secret
from app.api.deps import require_admin
from app.api.services.provisioning import provision_mariadb
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import CreateMariaDBRequest

router = create_service_crud(ServiceConfig(
    service_type="mariadb",
    table="mariadb_instances",
    container_prefix="mariadb",
    prefix="/api/mariadb",
    list_columns="id, name, host_port, db_name, status, created_at",
    order_by="ORDER BY created_at DESC",
))


@router.post("", status_code=201)
def create_mariadb(
    body: CreateMariaDBRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    resolved_db_name = body.db_name or body.name
    port = next_port(db, 3310)
    plain_password = secrets.token_urlsafe(16)
    encrypted_password = encrypt_secret(plain_password)

    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO mariadb_instances "
                "(name, host_port, root_password, db_name, created_by) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, port, encrypted_password, resolved_db_name, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe deja")

    bg.add_task(
        provision_mariadb, instance_id, body.name, port,
        encrypted_password, resolved_db_name,
    )
    return {
        "id": instance_id, "port": port, "status": "provisioning",
        "credentials": {
            "root_password": plain_password, "db_name": resolved_db_name,
        },
    }

from fastapi.responses import StreamingResponse
import subprocess
import datetime

@router.get("/{instance_id}/backup")
def backup_mariadb(instance_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("SELECT * FROM mariadb_instances WHERE id = %s", (instance_id,))
        inst = cur.fetchone()
    if not inst:
        raise HTTPException(404, "Instance introuvable")
    if inst["status"] != "running":
        raise HTTPException(400, "L'instance n'est pas active.")
        
    container_name = f"mariadb_{inst['name']}"
    
    cmd = [
        "docker", "exec", "-i", container_name,
        "mysqldump", "-u", "root", f"-p{decrypt_secret(inst['root_password'])}", 
        inst['db_name'] if inst['db_name'] else inst['name']
    ]
    
    def stream_backup():
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            while True:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    break
                yield chunk
        finally:
            proc.stdout.close()
            proc.stderr.close()
            proc.wait()
            
    db_name = inst['db_name'] if inst['db_name'] else inst['name']
    filename = f"mariadb_{inst['name']}_{db_name}_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    return StreamingResponse(
        stream_backup(), 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
