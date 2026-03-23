"""
DataForge — PostgreSQL instance router.
"""

import secrets
import datetime
import subprocess

import psycopg2
import psycopg2.sql as pg_sql
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.core.security import encrypt_secret
from app.api.deps import get_current_user, require_admin
from app.api.services.provisioning import docker_remove, provision_postgres
from app.models import CreatePostgresRequest, CreateDatabaseRequest

router = APIRouter(prefix="/api/postgres", tags=["postgres"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_pg_instance(instance_id: int, db) -> dict:
    with cursor(db) as cur:
        cur.execute("SELECT * FROM postgres_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


def _inst_conn(inst: dict, db_name: str = "postgres"):
    from app.core.security import decrypt_secret
    return psycopg2.connect(
        host="localhost", port=inst["host_port"],
        dbname=db_name, user=inst["db_user"],
        password=decrypt_secret(inst["db_password"]),
        connect_timeout=5,
    )


def _jsonify_val(v):
    if v is None:
        return None
    if isinstance(v, (bool, int, str, float)):
        return v
    return str(v)


# ── Instance CRUD ────────────────────────────────────────────────────────────


@router.get("")
def list_postgres(internal: bool = False,
                  _: dict = Depends(get_current_user),
                  db=Depends(get_db)):
    with cursor(db) as cur:
        if internal:
            cur.execute(
                "SELECT id, name, db_name, db_user, host_port, status, created_at, "
                "is_internal, internal_for_type, internal_for_id "
                "FROM postgres_instances ORDER BY id"
            )
        else:
            cur.execute(
                "SELECT id, name, db_name, db_user, host_port, status, created_at "
                "FROM postgres_instances WHERE is_internal IS NOT TRUE ORDER BY id"
            )
        return [dict(r) for r in cur.fetchall()]


@router.get("/{instance_id}")
def get_postgres(instance_id: int,
                 _: dict = Depends(get_current_user),
                 db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute(
            "SELECT id, name, db_name, db_user, host_port, status, created_at "
            "FROM postgres_instances WHERE id = %s",
            (instance_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@router.post("")
def create_postgres(body: CreatePostgresRequest,
                    bg: BackgroundTasks,
                    user: dict = Depends(require_admin),
                    db=Depends(get_db)):
    port = next_port(db, 5434)
    db_name = body.db_name or body.name
    db_user = body.db_user or "admin"
    plain_password = secrets.token_urlsafe(16)
    enc_password = encrypt_secret(plain_password)
    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO postgres_instances (name, db_name, db_user, db_password, host_port, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (body.name, db_name, db_user, enc_password, port, user["id"]),
        )
        instance_id = cur.fetchone()["id"]
    bg.add_task(provision_postgres, instance_id, body.name, db_name,
                db_user, enc_password, port)
    return {
        "id": instance_id, "port": port,
        "credentials": {
            "db_name": db_name, "db_user": db_user,
            "db_password": plain_password,
        },
    }


@router.delete("/{instance_id}")
async def delete_postgres(instance_id: int,
                          _: dict = Depends(require_admin),
                          db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("SELECT name FROM postgres_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    await docker_remove(f"pg_{row['name']}", volume_names=[f"pg_data_{row['name']}"])
    with cursor(db) as cur:
        cur.execute("DELETE FROM postgres_instances WHERE id = %s", (instance_id,))
    return {"ok": True}


# ── Database management endpoints ────────────────────────────────────────────


@router.get("/{instance_id}/databases")
def list_databases(instance_id: int,
                   _: dict = Depends(get_current_user),
                   db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
            )
            return [r[0] for r in cur.fetchall()]
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()


@router.post("/{instance_id}/databases")
def create_database(instance_id: int,
                    body: CreateDatabaseRequest,
                    _: dict = Depends(require_admin),
                    db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                pg_sql.SQL("CREATE DATABASE {}").format(pg_sql.Identifier(body.name))
            )
        return {"ok": True}
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()


@router.delete("/{instance_id}/databases/{db_name}")
def drop_database(instance_id: int, db_name: str,
                  _: dict = Depends(require_admin),
                  db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                pg_sql.SQL("DROP DATABASE {}").format(pg_sql.Identifier(db_name))
            )
        return {"ok": True}
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()


@router.get("/{instance_id}/databases/{db_name}/tables")
def list_tables(instance_id: int, db_name: str,
                _: dict = Depends(get_current_user),
                db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                "ORDER BY table_schema, table_name"
            )
            return [{"schema": r[0], "table": r[1]} for r in cur.fetchall()]
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()


@router.get("/{instance_id}/databases/{db_name}/tables/{table_name}")
def describe_table(instance_id: int, db_name: str, table_name: str,
                   _: dict = Depends(get_current_user),
                   db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = %s "
                "ORDER BY ordinal_position",
                (table_name,),
            )
            return [
                {"column": r[0], "type": r[1], "nullable": r[2], "default": r[3]}
                for r in cur.fetchall()
            ]
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()


@router.get("/{instance_id}/databases/{db_name}/tables/{table_name}/stats")
def table_stats(instance_id: int, db_name: str, table_name: str,
                _: dict = Depends(get_current_user),
                db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        with conn.cursor() as cur:
            cur.execute(
                pg_sql.SQL("SELECT COUNT(*) FROM {}").format(
                    pg_sql.Identifier(table_name)
                )
            )
            count = cur.fetchone()[0]
            cur.execute(
                "SELECT pg_total_relation_size(%s)",
                (table_name,),
            )
            size = cur.fetchone()[0]
        return {"row_count": count, "total_size": size}
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()


@router.get("/{instance_id}/databases/{db_name}/tables/{table_name}/sample")
def sample_rows(instance_id: int, db_name: str, table_name: str,
                _: dict = Depends(get_current_user),
                db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
    except Exception:
        raise HTTPException(502, "Connexion impossible")
    try:
        with conn.cursor() as cur:
            cur.execute(
                pg_sql.SQL("SELECT * FROM {} LIMIT 50").format(
                    pg_sql.Identifier(table_name)
                )
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return {
            "columns": cols,
            "rows": [
                [_jsonify_val(v) for v in row]
                for row in rows
            ],
        }
    except Exception:
        raise HTTPException(500, "Erreur serveur")
    finally:
        conn.close()

import os
from pathlib import Path
from fastapi.responses import FileResponse
from pydantic import BaseModel
from minio import Minio

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/app/backups"))


# ── Backup / Restore ─────────────────────────────────────────────────────────


class BackupRequest(BaseModel):
    database: str = "postgres"


@router.post("/{instance_id}/backup")
def backup_postgres(instance_id: int, body: BackupRequest,
                    _: dict = Depends(require_admin), db=Depends(get_db)):
    """pg_dump vers un fichier local — téléchargeable depuis l'UI."""
    inst = _get_pg_instance(instance_id, db)
    if inst["status"] != "running":
        raise HTTPException(400, "Instance non démarrée")

    backup_dir = BACKUP_DIR / inst["name"]
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{body.database}_{timestamp}.dump"
    filepath = backup_dir / filename

    container = f"pg_{inst['name']}"
    cmd = [
        "docker", "exec", container,
        "pg_dump", "-U", inst["db_user"], "--format=custom", body.database,
    ]
    try:
        with open(filepath, "wb") as f:
            res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=300)
        if res.returncode != 0:
            filepath.unlink(missing_ok=True)
            raise HTTPException(500, f"pg_dump échoué : {res.stderr.decode()}")
    except subprocess.TimeoutExpired:
        filepath.unlink(missing_ok=True)
        raise HTTPException(504, "Timeout lors du backup")

    size = filepath.stat().st_size
    return {"ok": True, "filename": filename, "size": size}


@router.get("/{instance_id}/backups")
def list_backups(instance_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    backup_dir = BACKUP_DIR / inst["name"]
    if not backup_dir.exists():
        return []
    files = sorted(backup_dir.glob("*.dump"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {"filename": f.name, "size": f.stat().st_size,
         "created_at": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
        for f in files
    ]


@router.get("/{instance_id}/backups/{filename}")
def download_backup(instance_id: int, filename: str,
                    _: dict = Depends(require_admin), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    # Sécurité : pas de path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Nom de fichier invalide")
    filepath = BACKUP_DIR / inst["name"] / filename
    if not filepath.exists():
        raise HTTPException(404, "Fichier introuvable")
    return FileResponse(str(filepath), filename=filename,
                        media_type="application/octet-stream")


@router.delete("/{instance_id}/backups/{filename}")
def delete_backup(instance_id: int, filename: str,
                  _: dict = Depends(require_admin), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Nom de fichier invalide")
    filepath = BACKUP_DIR / inst["name"] / filename
    if not filepath.exists():
        raise HTTPException(404, "Fichier introuvable")
    filepath.unlink()
    return {"ok": True}

class BackupMinioRequest(BaseModel):
    minio_id: int

@router.post("/{instance_id}/databases/{db_name}/backup-minio")
def backup_database_minio(instance_id: int, db_name: str, body: BackupMinioRequest, _: dict = Depends(require_admin), db=Depends(get_db)):
    from app.core.security import decrypt_secret
    inst = _get_pg_instance(instance_id, db)
    if inst["status"] != "running":
        raise HTTPException(400, "L'instance PostgreSQL n'est pas active.")
        
    with cursor(db) as cur:
        cur.execute("SELECT * FROM minio_instances WHERE id = %s", (body.minio_id,))
        minio_inst = cur.fetchone()
        
    if not minio_inst or minio_inst["status"] != "running":
        raise HTTPException(400, "L'instance MinIO sélectionnée n'est pas active.")

    container_name = f"pg_{inst['name']}"
    if inst["is_internal"]:
        container_name = f"pg_internal_{inst['internal_for_type']}_{inst['name']}"
        
    cmd = [
        "docker", "exec", container_name,
        "pg_dump", "-U", inst["db_user"], "--format=custom", db_name
    ]
    
    try:
        client = Minio(
            f"localhost:{minio_inst['host_port']}",
            access_key=minio_inst["root_user"],
            secret_key=decrypt_secret(minio_inst["root_password"]),
            secure=False
        )
        
        bucket_name = "dataforge-backups"
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except Exception as e:
        raise HTTPException(502, f"Erreur de connexion MinIO : {e}")
        
    filename = f"postgres/{inst['name']}/{db_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        client.put_object(
            bucket_name, 
            filename, 
            proc.stdout, 
            length=-1, 
            part_size=10*1024*1024
        )
    except Exception as e:
        proc.kill()
        raise HTTPException(500, f"Erreur MinIO: {str(e)}")
    finally:
        proc.stdout.close()
        proc.stderr.close()
        proc.wait()
        
    if proc.returncode != 0:
        raise HTTPException(500, "Le processus pg_dump a échoué.")
        
    return {"ok": True, "filename": filename, "bucket": bucket_name, "minio": minio_inst["name"]}
