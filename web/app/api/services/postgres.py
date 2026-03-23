"""
DataForge — PostgreSQL instance router.
"""

import secrets

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
    await docker_remove(f"pg_{row['name']}")
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

from fastapi.responses import StreamingResponse
import subprocess
import datetime

@router.get("/{instance_id}/databases/{db_name}/backup")
def backup_database(instance_id: int, db_name: str, _: dict = Depends(require_admin), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    if inst["status"] != "running":
        raise HTTPException(400, "L'instance n'est pas active.")
        
    container_name = f"pg_{inst['name']}"
    if inst["is_internal"]:
        container_name = f"pg_internal_{inst['internal_for_type']}_{inst['name']}"
        
    cmd = [
        "docker", "exec", "-i", container_name,
        "pg_dump", "-U", inst["db_user"], "--format=custom", db_name
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
            
    filename = f"{inst['name']}_{db_name}_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"
    return StreamingResponse(
        stream_backup(), 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
