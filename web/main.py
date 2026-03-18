#!/usr/bin/env python3
"""
DataForge — DBaaS Management Platform
Web server
"""

import asyncio
import base64
import datetime
import hashlib
import hmac
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator, Optional

import psycopg2
import psycopg2.extras
from psycopg2 import sql as pg_sql
from psycopg2 import pool as pg_pool
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent.parent   # project root
STATIC_PATH = Path(__file__).parent / "static"

DB_HOST = os.getenv("DATAFORGE_DB_HOST", "localhost")
DB_PORT = int(os.getenv("DATAFORGE_DB_PORT", "5433"))
DB_NAME = os.getenv("DATAFORGE_DB_NAME", "dataforge")
DB_USER = os.getenv("DATAFORGE_DB_USER", "dataforge")
DB_PASS = os.getenv("DATAFORGE_DB_PASS", "DataForge_Internal_2024!")

ACCESS_TTL  = 15 * 60        # 15 minutes
REFRESH_TTL = 7 * 24 * 3600  # 7 days

ACCESS_COOKIE  = "df_access"
REFRESH_COOKIE = "df_refresh"

SECRET_KEY: str = ""
_pool: Optional[pg_pool.ThreadedConnectionPool] = None


# ── Database ──────────────────────────────────────────────────────────────────

def get_db() -> Generator:
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def _cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def init_db() -> str:
    global _pool

    _pool = pg_pool.ThreadedConnectionPool(
        minconn=1, maxconn=10,
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER, password=DB_PASS,
    )

    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_config (
                    key   VARCHAR(64) PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    username   VARCHAR(64) UNIQUE NOT NULL,
                    password   TEXT        NOT NULL,
                    role       VARCHAR(16) NOT NULL DEFAULT 'user',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id          SERIAL PRIMARY KEY,
                    user_id     INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash  VARCHAR(64) UNIQUE NOT NULL,
                    expires_at  TIMESTAMPTZ NOT NULL,
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    revoked     BOOLEAN     DEFAULT FALSE
                );

                CREATE INDEX IF NOT EXISTS idx_rt_hash ON refresh_tokens(token_hash);
                CREATE INDEX IF NOT EXISTS idx_rt_user ON refresh_tokens(user_id);

                CREATE TABLE IF NOT EXISTS postgres_instances (
                    id          SERIAL PRIMARY KEY,
                    name        VARCHAR(64) UNIQUE NOT NULL,
                    db_name     VARCHAR(64) NOT NULL,
                    db_user     VARCHAR(64) NOT NULL,
                    db_password TEXT        NOT NULL,
                    host_port   INTEGER     NOT NULL,
                    status      VARCHAR(16) DEFAULT 'provisioning',
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    created_by  INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS n8n_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS groups (
                    id          SERIAL PRIMARY KEY,
                    name        VARCHAR(64) UNIQUE NOT NULL,
                    description TEXT        DEFAULT '',
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS user_groups (
                    user_id  INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
                    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    PRIMARY KEY (user_id, group_id)
                );

                CREATE TABLE IF NOT EXISTS instance_permissions (
                    id            SERIAL PRIMARY KEY,
                    group_id      INTEGER     NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    instance_type VARCHAR(16) NOT NULL,
                    instance_id   INTEGER     NOT NULL,
                    permission    VARCHAR(16) NOT NULL DEFAULT 'read',
                    UNIQUE(group_id, instance_type, instance_id)
                );
            """)

            cur.execute("SELECT value FROM app_config WHERE key = 'secret_key'")
            row = cur.fetchone()
            if row:
                secret = row["value"]
            else:
                secret = secrets.token_hex(32)
                cur.execute(
                    "INSERT INTO app_config (key, value) VALUES ('secret_key', %s)",
                    (secret,),
                )

            cur.execute("SELECT COUNT(*) AS n FROM users")
            if cur.fetchone()["n"] == 0:
                cur.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, 'admin')",
                    ("admin", _hash_password("admin123")),
                )
                print("✓ Compte admin créé  →  admin / admin123")

        conn.commit()
    finally:
        _pool.putconn(conn)

    return secret


# ── Ansible runner + helpers ──────────────────────────────────────────────────

async def _run_ansible(playbook: str, extra_vars: dict) -> tuple[int, str]:
    # Pass vars as JSON to avoid injection via special chars in values (passwords, names)
    cmd = ["ansible-playbook", playbook, "--extra-vars", json.dumps(extra_vars)]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(BASE_DIR / "ansible"),   # ansible.cfg + inventory.ini sont ici
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, (stdout + stderr).decode()


async def _docker_remove(container_name: str):
    for sub in ["stop", "rm"]:
        proc = await asyncio.create_subprocess_exec(
            "docker", sub, container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()


def _next_port(conn, base: int) -> int:
    with _cursor(conn) as cur:
        cur.execute("""
            SELECT host_port FROM postgres_instances
            UNION ALL
            SELECT host_port FROM n8n_instances
        """)
        used = {r["host_port"] for r in cur.fetchall()}
    # Also avoid the internal DataForge DB port
    used.add(DB_PORT)
    p = base
    while p in used:
        p += 1
    return p


# ── Background provisioning tasks ─────────────────────────────────────────────

async def _provision_postgres(instance_id: int, name: str, db_name: str,
                               db_user: str, db_password: str, port: int):
    code, _ = await _run_ansible("deploy_postgres.yml", {
        "instance_name": name,
        "db_name":       db_name,
        "db_user":       db_user,
        "db_password":   db_password,
        "host_port":     port,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute(
                "UPDATE postgres_instances SET status = %s WHERE id = %s",
                (status, instance_id),
            )
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_n8n(instance_id: int, name: str, port: int,
                          linked_pg: Optional[dict]):
    extra: dict = {"instance_name": name, "host_port": port}
    if linked_pg:
        extra.update({
            "target_db_host":     f"pg_{linked_pg['name']}",
            "target_db_name":     linked_pg["db_name"],
            "target_db_user":     linked_pg["db_user"],
            "target_db_password": linked_pg["db_password"],
        })
    code, _ = await _run_ansible("deploy_n8n.yml", extra)
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute(
                "UPDATE n8n_instances SET status = %s WHERE id = %s",
                (status, instance_id),
            )
        conn.commit()
    finally:
        _pool.putconn(conn)


# ── Password hashing (PBKDF2-HMAC) ────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def _check_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# ── Access token (HMAC-signed, 15 min) ────────────────────────────────────────

def _make_access_token(user_id: int, username: str, role: str) -> str:
    payload = json.dumps({
        "id": user_id, "username": username, "role": role,
        "exp": time.time() + ACCESS_TTL,
    })
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|||{sig}".encode()).decode()


def _verify_access_token(token: str) -> Optional[dict]:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        payload_str, sig = raw.rsplit("|||", 1)
        expected = hmac.new(SECRET_KEY.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(payload_str)
        if payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


# ── Refresh token (stored as SHA-256 hash in DB) ──────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _issue_refresh_token(user_id: int, conn) -> str:
    raw = secrets.token_hex(32)
    with _cursor(conn) as cur:
        cur.execute(
            """INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
               VALUES (%s, %s, NOW() + INTERVAL '%s seconds')""",
            (user_id, _hash_token(raw), REFRESH_TTL),
        )
    return raw


def _rotate_refresh_token(old_raw: str, conn) -> Optional[tuple[dict, str]]:
    old_hash = _hash_token(old_raw)
    with _cursor(conn) as cur:
        cur.execute(
            """SELECT rt.id, rt.user_id, rt.revoked, rt.expires_at,
                      u.username, u.role
               FROM   refresh_tokens rt
               JOIN   users u ON u.id = rt.user_id
               WHERE  rt.token_hash = %s""",
            (old_hash,),
        )
        row = cur.fetchone()

    if not row:
        return None

    if row["revoked"]:
        with _cursor(conn) as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = %s",
                (row["user_id"],),
            )
        return None

    if row["expires_at"] < datetime.datetime.now(datetime.timezone.utc):
        with _cursor(conn) as cur:
            cur.execute("DELETE FROM refresh_tokens WHERE id = %s", (row["id"],))
        return None

    with _cursor(conn) as cur:
        cur.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE id = %s",
            (row["id"],),
        )

    new_raw = _issue_refresh_token(row["user_id"], conn)
    return dict(row), new_raw


# ── Auth dependencies ──────────────────────────────────────────────────────────

def get_current_user(request: Request) -> dict:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    payload = _verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expirée")
    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    return user


def _set_tokens(response: Response, access: str, refresh: str):
    response.set_cookie(ACCESS_COOKIE, access, httponly=True, samesite="lax", max_age=ACCESS_TTL)
    response.set_cookie(REFRESH_COOKIE, refresh, httponly=True, samesite="lax",
                        max_age=REFRESH_TTL, path="/api/auth")


def _clear_tokens(response: Response):
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


# ── App ────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global SECRET_KEY
    SECRET_KEY = init_db()
    yield


app = FastAPI(title="DataForge", lifespan=lifespan, docs_url=None, redoc_url=None)
# Mount built Vue assets at /assets (Vite output)
app.mount("/assets", StaticFiles(directory=STATIC_PATH / "assets"), name="assets")


# ── Page routes ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return RedirectResponse("/databases")


# ── Auth API ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginRequest, response: Response, db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, username, password, role FROM users WHERE username = %s",
            (body.username,),
        )
        row = cur.fetchone()
    if not row or not _check_password(body.password, row["password"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    access  = _make_access_token(row["id"], row["username"], row["role"])
    refresh = _issue_refresh_token(row["id"], db)
    _set_tokens(response, access, refresh)
    return {"ok": True, "role": row["role"]}


@app.post("/api/auth/refresh")
def refresh_token(request: Request, response: Response, db=Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Aucun refresh token")
    result = _rotate_refresh_token(raw, db)
    if not result:
        _clear_tokens(response)
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    user, new_refresh = result
    new_access = _make_access_token(user["user_id"], user["username"], user["role"])
    _set_tokens(response, new_access, new_refresh)
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        with _cursor(db) as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = %s",
                (_hash_token(raw),),
            )
    _clear_tokens(response)
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ── Users API ──────────────────────────────────────────────────────────────────

@app.get("/api/users")
def list_users(_: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, username, role, created_at FROM users ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


@app.post("/api/users", status_code=201)
def create_user(body: CreateUserRequest, _: dict = Depends(require_admin), db=Depends(get_db)):
    if not body.username or len(body.username) > 64 or not body.username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Nom d'utilisateur invalide — lettres, chiffres, _ et - uniquement (64 car. max)")
    if body.role not in ("admin", "user"):
        raise HTTPException(400, "Rôle invalide (admin ou user)")
    if len(body.password) < 8:
        raise HTTPException(400, "Mot de passe trop court (8 car. min)")
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (body.username, _hash_password(body.password), body.role),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Nom d'utilisateur déjà utilisé")
    return {"ok": True}


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, current: dict = Depends(require_admin), db=Depends(get_db)):
    if user_id == current["id"]:
        raise HTTPException(400, "Impossible de supprimer votre propre compte")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    return {"ok": True}


# ── PostgreSQL Instances API ───────────────────────────────────────────────────

class CreatePostgresRequest(BaseModel):
    name: str
    db_name: str
    db_user: str
    db_password: str


def _valid_identifier(s: str) -> bool:
    return s.replace("_", "").replace("-", "").isalnum() and len(s) > 0


@app.get("/api/postgres")
def list_postgres(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name, db_name, db_user, host_port, status, created_at "
            "FROM postgres_instances ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/postgres/{instance_id}")
def get_postgres(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name, db_name, db_user, host_port, status, created_at "
            "FROM postgres_instances WHERE id = %s",
            (instance_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/postgres", status_code=201)
def create_postgres(body: CreatePostgresRequest, bg: BackgroundTasks,
                    user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    port = _next_port(db, 5434)
    try:
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO postgres_instances
                   (name, db_name, db_user, db_password, host_port, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (body.name, body.db_name, body.db_user, body.db_password, port, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_postgres, instance_id, body.name, body.db_name,
                body.db_user, body.db_password, port)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/postgres/{instance_id}")
def delete_postgres(instance_id: int, bg: BackgroundTasks,
                    _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM postgres_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM postgres_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"pg_{row['name']}")
    return {"ok": True}


# ── DB Management API ──────────────────────────────────────────────────────────

def _get_pg_instance(instance_id: int, db) -> dict:
    with _cursor(db) as cur:
        cur.execute("SELECT * FROM postgres_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


def _inst_conn(inst: dict, db_name: str = "postgres"):
    return psycopg2.connect(
        host="localhost", port=inst["host_port"],
        dbname=db_name, user=inst["db_user"], password=inst["db_password"],
        connect_timeout=5,
    )


@app.get("/api/postgres/{instance_id}/databases")
def list_databases(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT datname AS name,
                       pg_size_pretty(pg_database_size(datname)) AS size
                FROM   pg_database
                WHERE  datistemplate = false
                ORDER  BY datname
            """)
            result = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        raise HTTPException(503, f"Connexion impossible : {e}")
    return result


class CreateDatabaseRequest(BaseModel):
    name: str


@app.post("/api/postgres/{instance_id}/databases", status_code=201)
def create_database(instance_id: int, body: CreateDatabaseRequest,
                    _: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom de base invalide")
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(pg_sql.SQL("CREATE DATABASE {}").format(pg_sql.Identifier(body.name)))
        conn.close()
    except psycopg2.errors.DuplicateDatabase:
        raise HTTPException(409, "Base déjà existante")
    except Exception as e:
        raise HTTPException(503, str(e))
    return {"ok": True}


@app.delete("/api/postgres/{instance_id}/databases/{db_name}")
def drop_database(instance_id: int, db_name: str,
                  _: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(db_name):
        raise HTTPException(400, "Nom de base invalide")
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pg_terminate_backend(pid)
                FROM   pg_stat_activity
                WHERE  datname = %s AND pid <> pg_backend_pid()
            """, (db_name,))
            cur.execute(pg_sql.SQL("DROP DATABASE IF EXISTS {}").format(pg_sql.Identifier(db_name)))
        conn.close()
    except Exception as e:
        raise HTTPException(503, str(e))
    return {"ok": True}


@app.get("/api/postgres/{instance_id}/databases/{db_name}/tables")
def list_tables(instance_id: int, db_name: str,
                _: dict = Depends(get_current_user), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT t.table_name AS name,
                       t.table_type AS type,
                       (SELECT COUNT(*) FROM information_schema.columns c
                        WHERE c.table_schema = t.table_schema
                          AND c.table_name   = t.table_name) AS column_count
                FROM   information_schema.tables t
                WHERE  t.table_schema = 'public'
                ORDER  BY t.table_name
            """)
            result = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        raise HTTPException(503, str(e))
    return result


@app.get("/api/postgres/{instance_id}/databases/{db_name}/tables/{table_name}/stats")
def table_stats(instance_id: int, db_name: str, table_name: str,
                _: dict = Depends(get_current_user), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COALESCE(c.reltuples::bigint, 0)              AS row_count,
                    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
                    pg_size_pretty(pg_relation_size(c.oid))        AS table_size,
                    (SELECT COUNT(*) FROM pg_indexes
                     WHERE tablename = %s AND schemaname = 'public') AS index_count
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = %s AND n.nspname = 'public'
            """, (table_name, table_name))
            row = cur.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(503, str(e))
    if not row:
        raise HTTPException(404, "Table introuvable")
    return dict(row)


def _jsonify_val(v):
    if v is None:
        return None
    if isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return v
    # Decimal, UUID, datetime, etc → string
    return str(v)


@app.get("/api/postgres/{instance_id}/databases/{db_name}/tables/{table_name}/sample")
def table_sample(instance_id: int, db_name: str, table_name: str,
                 _: dict = Depends(get_current_user), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
        with conn.cursor() as cur:
            cur.execute(
                pg_sql.SQL("SELECT * FROM {} LIMIT 50").format(pg_sql.Identifier(table_name))
            )
            columns = [d[0] for d in cur.description] if cur.description else []
            rows    = [[_jsonify_val(v) for v in row] for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        raise HTTPException(503, str(e))
    return {"columns": columns, "rows": rows}


@app.get("/api/postgres/{instance_id}/databases/{db_name}/tables/{table_name}")
def describe_table(instance_id: int, db_name: str, table_name: str,
                   _: dict = Depends(get_current_user), db=Depends(get_db)):
    inst = _get_pg_instance(instance_id, db)
    try:
        conn = _inst_conn(inst, db_name)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT column_name    AS name,
                       data_type      AS type,
                       is_nullable    AS nullable,
                       column_default AS default_val
                FROM   information_schema.columns
                WHERE  table_schema = 'public' AND table_name = %s
                ORDER  BY ordinal_position
            """, (table_name,))
            result = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        raise HTTPException(503, str(e))
    return result


# ── n8n Instances API ──────────────────────────────────────────────────────────

class CreateN8nRequest(BaseModel):
    name: str
    linked_pg_id: Optional[int] = None


@app.get("/api/n8n")
def list_n8n(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("""
            SELECT n.id, n.name, n.host_port, n.status, n.created_at,
                   p.name AS linked_pg_name
            FROM   n8n_instances n
            LEFT JOIN postgres_instances p ON p.id = n.linked_pg_id
            ORDER  BY n.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/n8n/{instance_id}")
def get_n8n(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name, host_port, status, created_at FROM n8n_instances WHERE id = %s",
            (instance_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/n8n", status_code=201)
def create_n8n(body: CreateN8nRequest, bg: BackgroundTasks,
               user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    linked_pg = None
    if body.linked_pg_id:
        with _cursor(db) as cur:
            cur.execute("SELECT * FROM postgres_instances WHERE id = %s", (body.linked_pg_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Instance PostgreSQL introuvable")
        linked_pg = dict(row)
    port = _next_port(db, 5678)
    try:
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO n8n_instances (name, host_port, linked_pg_id, created_by)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (body.name, port, body.linked_pg_id, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_n8n, instance_id, body.name, port, linked_pg)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/n8n/{instance_id}")
def delete_n8n(instance_id: int, bg: BackgroundTasks,
               _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM n8n_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM n8n_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"n8n_{row['name']}")
    return {"ok": True}


# ── Groups API ─────────────────────────────────────────────────────────────────

class CreateGroupRequest(BaseModel):
    name: str
    description: str = ""


class AddMemberRequest(BaseModel):
    user_id: int


class AddPermissionRequest(BaseModel):
    instance_type: str   # 'postgres' | 'n8n'
    instance_id: int
    permission: str = "read"   # 'read' | 'write' | 'admin'


@app.get("/api/groups")
def list_groups(_: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("""
            SELECT g.id, g.name, g.description, g.created_at,
                   COUNT(DISTINCT ug.user_id) AS member_count
            FROM   groups g
            LEFT JOIN user_groups ug ON ug.group_id = g.id
            GROUP BY g.id ORDER BY g.name
        """)
        return [dict(r) for r in cur.fetchall()]


@app.post("/api/groups", status_code=201)
def create_group(body: CreateGroupRequest, _: dict = Depends(require_admin), db=Depends(get_db)):
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO groups (name, description) VALUES (%s, %s) RETURNING id",
                (body.name, body.description),
            )
            return {"id": cur.fetchone()["id"]}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Un groupe avec ce nom existe déjà")


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("DELETE FROM groups WHERE id = %s", (group_id,))
    return {"ok": True}


@app.get("/api/groups/{group_id}/members")
def list_members(group_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("""
            SELECT u.id, u.username, u.role
            FROM   user_groups ug
            JOIN   users u ON u.id = ug.user_id
            WHERE  ug.group_id = %s ORDER BY u.username
        """, (group_id,))
        return [dict(r) for r in cur.fetchall()]


@app.post("/api/groups/{group_id}/members", status_code=201)
def add_member(group_id: int, body: AddMemberRequest,
               _: dict = Depends(require_admin), db=Depends(get_db)):
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO user_groups (user_id, group_id) VALUES (%s, %s)",
                (body.user_id, group_id),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Membre déjà dans le groupe")
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(404, "Utilisateur introuvable")
    return {"ok": True}


@app.delete("/api/groups/{group_id}/members/{user_id}")
def remove_member(group_id: int, user_id: int,
                  _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "DELETE FROM user_groups WHERE group_id = %s AND user_id = %s",
            (group_id, user_id),
        )
    return {"ok": True}


@app.get("/api/groups/{group_id}/permissions")
def list_permissions(group_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, instance_type, instance_id, permission "
            "FROM instance_permissions WHERE group_id = %s",
            (group_id,),
        )
        perms = [dict(r) for r in cur.fetchall()]
    for p in perms:
        table = "postgres_instances" if p["instance_type"] == "postgres" else "n8n_instances"
        with _cursor(db) as cur:
            cur.execute(
                pg_sql.SQL("SELECT name FROM {} WHERE id = %s").format(pg_sql.Identifier(table)),
                (p["instance_id"],),
            )
            row = cur.fetchone()
            p["instance_name"] = row["name"] if row else "?"
    return perms


@app.post("/api/groups/{group_id}/permissions", status_code=201)
def add_permission(group_id: int, body: AddPermissionRequest,
                   _: dict = Depends(require_admin), db=Depends(get_db)):
    if body.instance_type not in ("postgres", "n8n"):
        raise HTTPException(400, "instance_type doit être 'postgres' ou 'n8n'")
    if body.permission not in ("read", "write", "admin"):
        raise HTTPException(400, "permission doit être 'read', 'write' ou 'admin'")
    try:
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO instance_permissions
                   (group_id, instance_type, instance_id, permission)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (group_id, body.instance_type, body.instance_id, body.permission),
            )
            return {"id": cur.fetchone()["id"]}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Permission déjà définie pour ce groupe")


@app.delete("/api/groups/{group_id}/permissions/{perm_id}")
def remove_permission(group_id: int, perm_id: int,
                      _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "DELETE FROM instance_permissions WHERE id = %s AND group_id = %s",
            (perm_id, group_id),
        )
    return {"ok": True}


# ── SPA fallback ───────────────────────────────────────────────────────────────

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str, response: Response):
    # Serve root-level static files (favicon.ico, etc.) directly
    candidate = STATIC_PATH / full_path
    if candidate.exists() and candidate.is_file() and not full_path.startswith("api/"):
        return FileResponse(candidate)
    # All other paths → serve index.html for Vue Router
    index = STATIC_PATH / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    raise HTTPException(404)


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
