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
import subprocess
import time
import urllib.request
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
                    id               SERIAL PRIMARY KEY,
                    name             VARCHAR(64) UNIQUE NOT NULL,
                    db_name          VARCHAR(64) NOT NULL,
                    db_user          VARCHAR(64) NOT NULL,
                    db_password      TEXT        NOT NULL,
                    host_port        INTEGER     NOT NULL,
                    status           VARCHAR(16) DEFAULT 'provisioning',
                    is_internal      BOOLEAN     DEFAULT FALSE,
                    internal_for_type VARCHAR(32),
                    internal_for_id  INTEGER,
                    created_at       TIMESTAMPTZ DEFAULT NOW(),
                    created_by       INTEGER     REFERENCES users(id)
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

                CREATE TABLE IF NOT EXISTS metabase_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS redis_instances (
                    id         SERIAL PRIMARY KEY,
                    name       VARCHAR(64) UNIQUE NOT NULL,
                    host_port  INTEGER     NOT NULL,
                    password   TEXT        DEFAULT '',
                    status     VARCHAR(16) DEFAULT 'provisioning',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    created_by INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS postgrest_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
                    db_schema    VARCHAR(64) DEFAULT 'public',
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS mage_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS minio_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    console_port INTEGER     NOT NULL,
                    root_user    VARCHAR(64) NOT NULL,
                    root_password TEXT       NOT NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS mariadb_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    root_password TEXT       NOT NULL,
                    db_name      VARCHAR(64) DEFAULT '',
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS qdrant_instances (
                    id         SERIAL PRIMARY KEY,
                    name       VARCHAR(64) UNIQUE NOT NULL,
                    host_port  INTEGER     NOT NULL,
                    status     VARCHAR(16) DEFAULT 'provisioning',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    created_by INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS clickhouse_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    password     TEXT        DEFAULT '',
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS ollama_instances (
                    id         SERIAL PRIMARY KEY,
                    name       VARCHAR(64) UNIQUE NOT NULL,
                    host_port  INTEGER     NOT NULL,
                    status     VARCHAR(16) DEFAULT 'provisioning',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    created_by INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS superset_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
                    admin_password TEXT      NOT NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS airflow_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
                    admin_password TEXT      NOT NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS hasura_instances (
                    id           SERIAL PRIMARY KEY,
                    name         VARCHAR(64) UNIQUE NOT NULL,
                    host_port    INTEGER     NOT NULL,
                    linked_pg_id INTEGER     NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
                    admin_secret TEXT        NOT NULL,
                    status       VARCHAR(16) DEFAULT 'provisioning',
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    created_by   INTEGER     REFERENCES users(id)
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

            # Migrations for existing databases
            cur.execute("ALTER TABLE postgres_instances ADD COLUMN IF NOT EXISTS is_internal BOOLEAN DEFAULT FALSE")
            cur.execute("ALTER TABLE postgres_instances ADD COLUMN IF NOT EXISTS internal_for_type VARCHAR(32)")
            cur.execute("ALTER TABLE postgres_instances ADD COLUMN IF NOT EXISTS internal_for_id INTEGER")

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
            UNION ALL SELECT host_port FROM n8n_instances
            UNION ALL SELECT host_port FROM metabase_instances
            UNION ALL SELECT host_port FROM redis_instances
            UNION ALL SELECT host_port FROM postgrest_instances
            UNION ALL SELECT host_port FROM mage_instances
            UNION ALL SELECT host_port FROM minio_instances
            UNION ALL SELECT console_port AS host_port FROM minio_instances
            UNION ALL SELECT host_port FROM mariadb_instances
            UNION ALL SELECT host_port FROM qdrant_instances
            UNION ALL SELECT host_port FROM clickhouse_instances
            UNION ALL SELECT host_port FROM ollama_instances
            UNION ALL SELECT host_port FROM superset_instances
            UNION ALL SELECT host_port FROM airflow_instances
            UNION ALL SELECT host_port FROM hasura_instances
        """)
        used = {r["host_port"] for r in cur.fetchall()}
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
def list_postgres(internal: bool = False, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        if internal:
            cur.execute(
                "SELECT id, name, db_name, db_user, host_port, status, created_at, "
                "is_internal, internal_for_type, internal_for_id "
                "FROM postgres_instances WHERE is_internal = TRUE ORDER BY created_at DESC"
            )
        else:
            cur.execute(
                "SELECT id, name, db_name, db_user, host_port, status, created_at "
                "FROM postgres_instances WHERE is_internal IS NOT TRUE ORDER BY created_at DESC"
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


# ── Metabase provisioning ──────────────────────────────────────────────────────

async def _provision_metabase(instance_id: int, name: str, port: int,
                               internal_pg_id: int, internal_pg_port: int,
                               internal_pg_password: str):
    code, _ = await _run_ansible("deploy_metabase.yml", {
        "instance_name":        name,
        "host_port":            port,
        "internal_pg_password": internal_pg_password,
        "internal_pg_host_port": internal_pg_port,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE metabase_instances SET status = %s WHERE id = %s", (status, instance_id))
            cur.execute("UPDATE postgres_instances SET status = %s WHERE id = %s", (status, internal_pg_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_redis(instance_id: int, name: str, port: int, password: str):
    code, _ = await _run_ansible("deploy_redis.yml", {
        "instance_name": name, "host_port": port, "redis_password": password,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE redis_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_postgrest(instance_id: int, name: str, port: int, linked_pg: dict):
    code, _ = await _run_ansible("deploy_postgrest.yml", {
        "instance_name": name,
        "host_port":     port,
        "pg_host":       f"pg_{linked_pg['name']}",
        "pg_dbname":     linked_pg["db_name"],
        "pg_user":       linked_pg["db_user"],
        "pg_password":   linked_pg["db_password"],
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE postgrest_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_mage(instance_id: int, name: str, port: int,
                           linked_pg: Optional[dict]):
    extra: dict = {"instance_name": name, "host_port": port}
    if linked_pg:
        extra.update({
            "linked_pg_host":     f"pg_{linked_pg['name']}",
            "linked_pg_dbname":   linked_pg["db_name"],
            "linked_pg_user":     linked_pg["db_user"],
            "linked_pg_password": linked_pg["db_password"],
        })
    code, _ = await _run_ansible("deploy_mage.yml", extra)
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE mage_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_minio(instance_id: int, name: str, port: int, console_port: int,
                            root_user: str, root_password: str):
    code, _ = await _run_ansible("deploy_minio.yml", {
        "instance_name":      name,
        "host_port":          port,
        "console_port":       console_port,
        "minio_root_user":    root_user,
        "minio_root_password": root_password,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE minio_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_mariadb(instance_id: int, name: str, port: int,
                              root_password: str, db_name: str):
    code, _ = await _run_ansible("deploy_mariadb.yml", {
        "instance_name": name,
        "host_port":     port,
        "root_password": root_password,
        "db_name":       db_name,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE mariadb_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_qdrant(instance_id: int, name: str, port: int):
    code, _ = await _run_ansible("deploy_qdrant.yml", {
        "instance_name": name,
        "host_port":     port,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE qdrant_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_clickhouse(instance_id: int, name: str, port: int, password: str):
    code, _ = await _run_ansible("deploy_clickhouse.yml", {
        "instance_name":      name,
        "host_port":          port,
        "clickhouse_password": password,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE clickhouse_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_ollama(instance_id: int, name: str, port: int):
    code, _ = await _run_ansible("deploy_ollama.yml", {
        "instance_name": name,
        "host_port":     port,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE ollama_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_superset(instance_id: int, name: str, port: int,
                               internal_pg_id: int, internal_pg_port: int,
                               internal_pg_password: str, admin_password: str,
                               superset_secret_key: str):
    code, _ = await _run_ansible("deploy_superset.yml", {
        "instance_name":        name,
        "host_port":            port,
        "internal_pg_password": internal_pg_password,
        "internal_pg_host_port": internal_pg_port,
        "admin_password":       admin_password,
        "superset_secret_key":  superset_secret_key,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE superset_instances SET status = %s WHERE id = %s", (status, instance_id))
            cur.execute("UPDATE postgres_instances SET status = %s WHERE id = %s", (status, internal_pg_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_airflow(instance_id: int, name: str, port: int,
                              internal_pg_id: int, internal_pg_port: int,
                              internal_pg_password: str, admin_password: str):
    code, _ = await _run_ansible("deploy_airflow.yml", {
        "instance_name":        name,
        "host_port":            port,
        "internal_pg_password": internal_pg_password,
        "internal_pg_host_port": internal_pg_port,
        "admin_password":       admin_password,
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE airflow_instances SET status = %s WHERE id = %s", (status, instance_id))
            cur.execute("UPDATE postgres_instances SET status = %s WHERE id = %s", (status, internal_pg_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


async def _provision_hasura(instance_id: int, name: str, port: int,
                             linked_pg: dict, admin_secret: str):
    code, _ = await _run_ansible("deploy_hasura.yml", {
        "instance_name":      name,
        "host_port":          port,
        "admin_secret":       admin_secret,
        "linked_pg_host":     f"pg_{linked_pg['name']}",
        "linked_pg_dbname":   linked_pg["db_name"],
        "linked_pg_user":     linked_pg["db_user"],
        "linked_pg_password": linked_pg["db_password"],
    })
    status = "running" if code == 0 else "error"
    conn = _pool.getconn()
    try:
        with _cursor(conn) as cur:
            cur.execute("UPDATE hasura_instances SET status = %s WHERE id = %s", (status, instance_id))
        conn.commit()
    finally:
        _pool.putconn(conn)


# ── Metabase Instances API ─────────────────────────────────────────────────────

class CreateMetabaseRequest(BaseModel):
    name: str


@app.get("/api/metabase")
def list_metabase(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM metabase_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/metabase/{instance_id}")
def get_metabase(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM metabase_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/metabase", status_code=201)
def create_metabase(body: CreateMetabaseRequest, bg: BackgroundTasks,
                    user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")

    metabase_port   = _next_port(db, 3000)
    internal_pg_port = _next_port(db, 15000)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name = f"intpg_meta_{body.name}"

    try:
        # Enregistrement de la base interne (invisible dans la liste principale)
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO postgres_instances
                   (name, db_name, db_user, db_password, host_port,
                    is_internal, internal_for_type, created_by)
                   VALUES (%s, %s, %s, %s, %s, TRUE, 'metabase', %s) RETURNING id""",
                (internal_pg_name, "metabase", "metabase",
                 internal_pg_password, internal_pg_port, user["id"]),
            )
            internal_pg_id = cur.fetchone()["id"]

        # Enregistrement de l'instance Metabase
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO metabase_instances (name, host_port, linked_pg_id, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (body.name, metabase_port, internal_pg_id, user["id"]),
            )
            instance_id = cur.fetchone()["id"]

        # Liaison retour : internal_pg sait à quelle instance Metabase il appartient
        with _cursor(db) as cur:
            cur.execute(
                "UPDATE postgres_instances SET internal_for_id = %s WHERE id = %s",
                (instance_id, internal_pg_id),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")

    bg.add_task(_provision_metabase, instance_id, body.name, metabase_port,
                internal_pg_id, internal_pg_port, internal_pg_password)
    return {"id": instance_id, "port": metabase_port, "status": "provisioning"}


@app.delete("/api/metabase/{instance_id}")
def delete_metabase(instance_id: int, bg: BackgroundTasks,
                    _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM metabase_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")

    # Trouver et supprimer la base interne associée
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name FROM postgres_instances WHERE internal_for_type = 'metabase' AND internal_for_id = %s",
            (instance_id,),
        )
        internal_pg = cur.fetchone()

    with _cursor(db) as cur:
        cur.execute("DELETE FROM metabase_instances WHERE id = %s", (instance_id,))
    if internal_pg:
        with _cursor(db) as cur:
            cur.execute("DELETE FROM postgres_instances WHERE id = %s", (internal_pg["id"],))

    bg.add_task(_docker_remove, f"metabase_{row['name']}")
    if internal_pg:
        bg.add_task(_docker_remove, f"pg_internal_metabase_{row['name']}")
    return {"ok": True}


# ── Redis Instances API ────────────────────────────────────────────────────────

class CreateRedisRequest(BaseModel):
    name: str
    password: str = ""


@app.get("/api/redis")
def list_redis(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM redis_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/redis/{instance_id}")
def get_redis(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM redis_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/redis", status_code=201)
def create_redis(body: CreateRedisRequest, bg: BackgroundTasks,
                 user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    port = _next_port(db, 6379)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO redis_instances (name, host_port, password, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (body.name, port, body.password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_redis, instance_id, body.name, port, body.password)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/redis/{instance_id}")
def delete_redis(instance_id: int, bg: BackgroundTasks,
                 _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM redis_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM redis_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"redis_{row['name']}")
    return {"ok": True}


# ── PostgREST Instances API ────────────────────────────────────────────────────

class CreatePostgRESTRequest(BaseModel):
    name: str
    linked_pg_id: int
    db_schema: str = "public"


@app.get("/api/postgrest")
def list_postgrest(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("""
            SELECT r.id, r.name, r.host_port, r.db_schema, r.status, r.created_at,
                   p.name AS linked_pg_name
            FROM   postgrest_instances r
            JOIN   postgres_instances p ON p.id = r.linked_pg_id
            ORDER  BY r.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/postgrest/{instance_id}")
def get_postgrest(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM postgrest_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/postgrest", status_code=201)
def create_postgrest(body: CreatePostgRESTRequest, bg: BackgroundTasks,
                     user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    with _cursor(db) as cur:
        cur.execute("SELECT * FROM postgres_instances WHERE id = %s", (body.linked_pg_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance PostgreSQL introuvable")
    linked_pg = dict(row)
    port = _next_port(db, 3100)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO postgrest_instances (name, host_port, linked_pg_id, db_schema, created_by) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, port, body.linked_pg_id, body.db_schema, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_postgrest, instance_id, body.name, port, linked_pg)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/postgrest/{instance_id}")
def delete_postgrest(instance_id: int, bg: BackgroundTasks,
                     _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM postgrest_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM postgrest_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"postgrest_{row['name']}")
    return {"ok": True}


# ── Mage Instances API ─────────────────────────────────────────────────────────

class CreateMageRequest(BaseModel):
    name: str
    linked_pg_id: Optional[int] = None


@app.get("/api/mage")
def list_mage(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("""
            SELECT m.id, m.name, m.host_port, m.status, m.created_at,
                   p.name AS linked_pg_name
            FROM   mage_instances m
            LEFT JOIN postgres_instances p ON p.id = m.linked_pg_id
            ORDER  BY m.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/mage/{instance_id}")
def get_mage(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM mage_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/mage", status_code=201)
def create_mage(body: CreateMageRequest, bg: BackgroundTasks,
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
    port = _next_port(db, 6789)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO mage_instances (name, host_port, linked_pg_id, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (body.name, port, body.linked_pg_id, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_mage, instance_id, body.name, port, linked_pg)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/mage/{instance_id}")
def delete_mage(instance_id: int, bg: BackgroundTasks,
                _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM mage_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM mage_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"mage_{row['name']}")
    return {"ok": True}


# ── MinIO Instances API ────────────────────────────────────────────────────────

class CreateMinIORequest(BaseModel):
    name: str
    root_user: str = "minioadmin"
    root_password: str


@app.get("/api/minio")
def list_minio(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name, host_port, console_port, root_user, status, created_at "
            "FROM minio_instances ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/minio/{instance_id}")
def get_minio(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name, host_port, console_port, root_user, status, created_at "
            "FROM minio_instances WHERE id = %s", (instance_id,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/minio", status_code=201)
def create_minio(body: CreateMinIORequest, bg: BackgroundTasks,
                 user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    if len(body.root_password) < 8:
        raise HTTPException(400, "Mot de passe MinIO trop court (8 car. min)")
    port = _next_port(db, 9000)
    console_port = _next_port(db, port + 1)
    try:
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO minio_instances
                   (name, host_port, console_port, root_user, root_password, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (body.name, port, console_port, body.root_user, body.root_password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_minio, instance_id, body.name, port, console_port,
                body.root_user, body.root_password)
    return {"id": instance_id, "port": port, "console_port": console_port, "status": "provisioning"}


@app.delete("/api/minio/{instance_id}")
def delete_minio(instance_id: int, bg: BackgroundTasks,
                 _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM minio_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM minio_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"minio_{row['name']}")
    return {"ok": True}


# ── MariaDB Instances API ──────────────────────────────────────────────────────

class CreateMariaDBRequest(BaseModel):
    name: str
    root_password: str
    db_name: str = ""


@app.get("/api/mariadb")
def list_mariadb(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, db_name, status, created_at FROM mariadb_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/mariadb/{instance_id}")
def get_mariadb(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, db_name, status, created_at FROM mariadb_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/mariadb", status_code=201)
def create_mariadb(body: CreateMariaDBRequest, bg: BackgroundTasks,
                   user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    if not body.root_password:
        raise HTTPException(400, "Le mot de passe root est requis")
    resolved_db_name = body.db_name or body.name
    port = _next_port(db, 3310)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO mariadb_instances (name, host_port, root_password, db_name, created_by) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, port, body.root_password, resolved_db_name, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_mariadb, instance_id, body.name, port, body.root_password, resolved_db_name)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/mariadb/{instance_id}")
def delete_mariadb(instance_id: int, bg: BackgroundTasks,
                   _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM mariadb_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM mariadb_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"mariadb_{row['name']}")
    return {"ok": True}


# ── Qdrant Instances API ───────────────────────────────────────────────────────

class CreateQdrantRequest(BaseModel):
    name: str


@app.get("/api/qdrant")
def list_qdrant(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM qdrant_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/qdrant/{instance_id}")
def get_qdrant(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM qdrant_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/qdrant", status_code=201)
def create_qdrant(body: CreateQdrantRequest, bg: BackgroundTasks,
                  user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    port = _next_port(db, 6333)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO qdrant_instances (name, host_port, created_by) VALUES (%s, %s, %s) RETURNING id",
                (body.name, port, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_qdrant, instance_id, body.name, port)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/qdrant/{instance_id}")
def delete_qdrant(instance_id: int, bg: BackgroundTasks,
                  _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM qdrant_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM qdrant_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"qdrant_{row['name']}")
    return {"ok": True}


# ── ClickHouse Instances API ───────────────────────────────────────────────────

class CreateClickHouseRequest(BaseModel):
    name: str
    password: str = ""


@app.get("/api/clickhouse")
def list_clickhouse(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM clickhouse_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/clickhouse/{instance_id}")
def get_clickhouse(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM clickhouse_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/clickhouse", status_code=201)
def create_clickhouse(body: CreateClickHouseRequest, bg: BackgroundTasks,
                      user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    port = _next_port(db, 8140)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO clickhouse_instances (name, host_port, password, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (body.name, port, body.password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_clickhouse, instance_id, body.name, port, body.password)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/clickhouse/{instance_id}")
def delete_clickhouse(instance_id: int, bg: BackgroundTasks,
                      _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM clickhouse_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM clickhouse_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"clickhouse_{row['name']}")
    return {"ok": True}


# ── Ollama Instances API ───────────────────────────────────────────────────────

class CreateOllamaRequest(BaseModel):
    name: str


@app.get("/api/ollama")
def list_ollama(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM ollama_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/ollama/{instance_id}")
def get_ollama(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM ollama_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/ollama", status_code=201)
def create_ollama(body: CreateOllamaRequest, bg: BackgroundTasks,
                  user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    port = _next_port(db, 11434)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO ollama_instances (name, host_port, created_by) VALUES (%s, %s, %s) RETURNING id",
                (body.name, port, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_ollama, instance_id, body.name, port)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/ollama/{instance_id}")
def delete_ollama(instance_id: int, bg: BackgroundTasks,
                  _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM ollama_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM ollama_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"ollama_{row['name']}")
    return {"ok": True}


# ── Ollama Model Management ────────────────────────────────────────────────────

# In-memory pull status: {instance_id: {model_name: "pulling"|"done"|"error"}}
_ollama_pull_status: dict[int, dict[str, str]] = {}


def _ollama_url(db, instance_id: int) -> tuple[str, str]:
    """Returns (base_url, instance_name) or raises 404."""
    with _cursor(db) as cur:
        cur.execute("SELECT name, host_port, status FROM ollama_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    if row["status"] != "running":
        raise HTTPException(409, "Instance non démarrée")
    return f"http://localhost:{row['host_port']}", row["name"]


def _ollama_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read())


def _ollama_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _ollama_delete(url: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="DELETE")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


@app.get("/api/ollama/{instance_id}/models")
def ollama_list_models(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    base_url, _ = _ollama_url(db, instance_id)
    try:
        data = _ollama_get(f"{base_url}/api/tags")
        return {"models": data.get("models", [])}
    except Exception:
        return {"models": []}


class OllamaPullRequest(BaseModel):
    name: str


async def _do_ollama_pull(instance_id: int, base_url: str, model: str):
    _ollama_pull_status.setdefault(instance_id, {})[model] = "pulling"
    try:
        # stream=false → single JSON response when done
        _ollama_post(f"{base_url}/api/pull", {"name": model, "stream": False})
        _ollama_pull_status[instance_id][model] = "done"
    except Exception:
        _ollama_pull_status[instance_id][model] = "error"


@app.post("/api/ollama/{instance_id}/models/pull")
def ollama_pull_model(instance_id: int, body: OllamaPullRequest,
                      bg: BackgroundTasks,
                      _: dict = Depends(require_admin), db=Depends(get_db)):
    base_url, _ = _ollama_url(db, instance_id)
    bg.add_task(_do_ollama_pull, instance_id, base_url, body.name)
    return {"ok": True}


@app.get("/api/ollama/{instance_id}/models/pull-status")
def ollama_pull_status(instance_id: int, _: dict = Depends(get_current_user)):
    return _ollama_pull_status.get(instance_id, {})


class OllamaDeleteModelRequest(BaseModel):
    name: str


@app.delete("/api/ollama/{instance_id}/models")
def ollama_delete_model(instance_id: int, body: OllamaDeleteModelRequest,
                        _: dict = Depends(require_admin), db=Depends(get_db)):
    base_url, _ = _ollama_url(db, instance_id)
    try:
        _ollama_delete(f"{base_url}/api/delete", {"name": body.name})
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


class OllamaChatMessage(BaseModel):
    role: str
    content: str


class OllamaChatRequest(BaseModel):
    model: str
    messages: list[OllamaChatMessage]


@app.post("/api/ollama/{instance_id}/chat")
def ollama_chat(instance_id: int, body: OllamaChatRequest,
                _: dict = Depends(get_current_user), db=Depends(get_db)):
    base_url, _ = _ollama_url(db, instance_id)
    try:
        result = _ollama_post(f"{base_url}/api/chat", {
            "model": body.model,
            "messages": [{"role": m.role, "content": m.content} for m in body.messages],
            "stream": False,
        })
        return {"message": result.get("message", {})}
    except Exception as e:
        raise HTTPException(500, f"Erreur Ollama : {e}")


# ── Superset Instances API ─────────────────────────────────────────────────────

class CreateSupersetRequest(BaseModel):
    name: str
    admin_password: str


@app.get("/api/superset")
def list_superset(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM superset_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/superset/{instance_id}")
def get_superset(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM superset_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/superset", status_code=201)
def create_superset(body: CreateSupersetRequest, bg: BackgroundTasks,
                    user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    if not body.admin_password:
        raise HTTPException(400, "Le mot de passe administrateur est requis")

    superset_port     = _next_port(db, 8088)
    internal_pg_port  = _next_port(db, 15500)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name  = f"intpg_superset_{body.name}"
    superset_secret_key = secrets.token_hex(32)

    try:
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO postgres_instances
                   (name, db_name, db_user, db_password, host_port,
                    is_internal, internal_for_type, created_by)
                   VALUES (%s, %s, %s, %s, %s, TRUE, 'superset', %s) RETURNING id""",
                (internal_pg_name, "superset", "superset",
                 internal_pg_password, internal_pg_port, user["id"]),
            )
            internal_pg_id = cur.fetchone()["id"]

        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO superset_instances (name, host_port, linked_pg_id, admin_password, created_by) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, superset_port, internal_pg_id, body.admin_password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]

        with _cursor(db) as cur:
            cur.execute(
                "UPDATE postgres_instances SET internal_for_id = %s WHERE id = %s",
                (instance_id, internal_pg_id),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")

    bg.add_task(_provision_superset, instance_id, body.name, superset_port,
                internal_pg_id, internal_pg_port, internal_pg_password,
                body.admin_password, superset_secret_key)
    return {"id": instance_id, "port": superset_port, "status": "provisioning"}


@app.delete("/api/superset/{instance_id}")
def delete_superset(instance_id: int, bg: BackgroundTasks,
                    _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM superset_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")

    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name FROM postgres_instances WHERE internal_for_type = 'superset' AND internal_for_id = %s",
            (instance_id,),
        )
        internal_pg = cur.fetchone()

    with _cursor(db) as cur:
        cur.execute("DELETE FROM superset_instances WHERE id = %s", (instance_id,))
    if internal_pg:
        with _cursor(db) as cur:
            cur.execute("DELETE FROM postgres_instances WHERE id = %s", (internal_pg["id"],))

    bg.add_task(_docker_remove, f"superset_{row['name']}")
    if internal_pg:
        bg.add_task(_docker_remove, f"pg_internal_superset_{row['name']}")
    return {"ok": True}


# ── Airflow Instances API ──────────────────────────────────────────────────────

class CreateAirflowRequest(BaseModel):
    name: str
    admin_password: str


@app.get("/api/airflow")
def list_airflow(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM airflow_instances ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/airflow/{instance_id}")
def get_airflow(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM airflow_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/airflow", status_code=201)
def create_airflow(body: CreateAirflowRequest, bg: BackgroundTasks,
                   user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    if not body.admin_password:
        raise HTTPException(400, "Le mot de passe administrateur est requis")

    airflow_port      = _next_port(db, 8090)
    internal_pg_port  = _next_port(db, 15600)
    internal_pg_password = secrets.token_urlsafe(16)
    internal_pg_name  = f"intpg_airflow_{body.name}"

    try:
        with _cursor(db) as cur:
            cur.execute(
                """INSERT INTO postgres_instances
                   (name, db_name, db_user, db_password, host_port,
                    is_internal, internal_for_type, created_by)
                   VALUES (%s, %s, %s, %s, %s, TRUE, 'airflow', %s) RETURNING id""",
                (internal_pg_name, "airflow", "airflow",
                 internal_pg_password, internal_pg_port, user["id"]),
            )
            internal_pg_id = cur.fetchone()["id"]

        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO airflow_instances (name, host_port, linked_pg_id, admin_password, created_by) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, airflow_port, internal_pg_id, body.admin_password, user["id"]),
            )
            instance_id = cur.fetchone()["id"]

        with _cursor(db) as cur:
            cur.execute(
                "UPDATE postgres_instances SET internal_for_id = %s WHERE id = %s",
                (instance_id, internal_pg_id),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")

    bg.add_task(_provision_airflow, instance_id, body.name, airflow_port,
                internal_pg_id, internal_pg_port, internal_pg_password, body.admin_password)
    return {"id": instance_id, "port": airflow_port, "status": "provisioning"}


@app.delete("/api/airflow/{instance_id}")
def delete_airflow(instance_id: int, bg: BackgroundTasks,
                   _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM airflow_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")

    with _cursor(db) as cur:
        cur.execute(
            "SELECT id, name FROM postgres_instances WHERE internal_for_type = 'airflow' AND internal_for_id = %s",
            (instance_id,),
        )
        internal_pg = cur.fetchone()

    with _cursor(db) as cur:
        cur.execute("DELETE FROM airflow_instances WHERE id = %s", (instance_id,))
    if internal_pg:
        with _cursor(db) as cur:
            cur.execute("DELETE FROM postgres_instances WHERE id = %s", (internal_pg["id"],))

    bg.add_task(_docker_remove, f"airflow_{row['name']}")
    if internal_pg:
        bg.add_task(_docker_remove, f"pg_internal_airflow_{row['name']}")
    return {"ok": True}


# ── Hasura Instances API ───────────────────────────────────────────────────────

class CreateHasuraRequest(BaseModel):
    name: str
    linked_pg_id: int
    admin_secret: str


@app.get("/api/hasura")
def list_hasura(_: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("""
            SELECT h.id, h.name, h.host_port, h.status, h.created_at,
                   p.name AS linked_pg_name
            FROM   hasura_instances h
            JOIN   postgres_instances p ON p.id = h.linked_pg_id
            ORDER  BY h.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


@app.get("/api/hasura/{instance_id}")
def get_hasura(instance_id: int, _: dict = Depends(get_current_user), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT id, name, host_port, status, created_at FROM hasura_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    return dict(row)


@app.post("/api/hasura", status_code=201)
def create_hasura(body: CreateHasuraRequest, bg: BackgroundTasks,
                  user: dict = Depends(require_admin), db=Depends(get_db)):
    if not _valid_identifier(body.name):
        raise HTTPException(400, "Nom invalide — lettres, chiffres, _ et - uniquement")
    if not body.admin_secret:
        raise HTTPException(400, "Le secret administrateur est requis")
    with _cursor(db) as cur:
        cur.execute("SELECT * FROM postgres_instances WHERE id = %s AND is_internal = FALSE", (body.linked_pg_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance PostgreSQL introuvable")
    linked_pg = dict(row)
    port = _next_port(db, 8280)
    try:
        with _cursor(db) as cur:
            cur.execute(
                "INSERT INTO hasura_instances (name, host_port, linked_pg_id, admin_secret, created_by) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.name, port, body.linked_pg_id, body.admin_secret, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe déjà")
    bg.add_task(_provision_hasura, instance_id, body.name, port, linked_pg, body.admin_secret)
    return {"id": instance_id, "port": port, "status": "provisioning"}


@app.delete("/api/hasura/{instance_id}")
def delete_hasura(instance_id: int, bg: BackgroundTasks,
                  _: dict = Depends(require_admin), db=Depends(get_db)):
    with _cursor(db) as cur:
        cur.execute("SELECT name FROM hasura_instances WHERE id = %s", (instance_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    with _cursor(db) as cur:
        cur.execute("DELETE FROM hasura_instances WHERE id = %s", (instance_id,))
    bg.add_task(_docker_remove, f"hasura_{row['name']}")
    return {"ok": True}


# ── Service Library ────────────────────────────────────────────────────────────

# Pull status tracked in-process (resets on server restart, acceptable)
_pull_status: dict[str, str] = {}

_SERVICE_CATALOG = [
    {"id": "postgres",   "dockerImage": "postgres:16-alpine"},
    {"id": "mariadb",    "dockerImage": "mariadb:11"},
    {"id": "qdrant",     "dockerImage": "qdrant/qdrant:latest"},
    {"id": "clickhouse", "dockerImage": "clickhouse/clickhouse-server:latest"},
    {"id": "metabase",   "dockerImage": "metabase/metabase:latest"},
    {"id": "superset",   "dockerImage": "apache/superset:latest"},
    {"id": "mage",       "dockerImage": "mageai/mageai:latest"},
    {"id": "airflow",    "dockerImage": "apache/airflow:2-python3.11"},
    {"id": "postgrest",  "dockerImage": "postgrest/postgrest:latest"},
    {"id": "hasura",     "dockerImage": "hasura/graphql-engine:latest"},
    {"id": "valkey",     "dockerImage": "valkey/valkey:8-alpine"},
    {"id": "minio",      "dockerImage": "minio/minio:latest"},
    {"id": "ollama",     "dockerImage": "ollama/ollama:latest"},
]
_DEFAULT_ENABLED = {"postgres", "metabase", "valkey", "postgrest", "mage", "minio"}


def _get_enabled_services(db) -> set:
    with _cursor(db) as cur:
        cur.execute("SELECT value FROM app_config WHERE key = 'enabled_services'")
        row = cur.fetchone()
    return set(json.loads(row["value"])) if row else set(_DEFAULT_ENABLED)


def _set_enabled_services(db, enabled: set):
    with _cursor(db) as cur:
        cur.execute(
            """INSERT INTO app_config (key, value) VALUES ('enabled_services', %s)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
            (json.dumps(list(enabled)),),
        )


async def _do_pull_image(image: str):
    proc = await asyncio.create_subprocess_exec(
        "docker", "pull", image,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    _pull_status[image] = "pulled" if proc.returncode == 0 else "error"


@app.get("/api/library/enabled")
def library_enabled(_: dict = Depends(get_current_user), db=Depends(get_db)):
    return {"enabled": list(_get_enabled_services(db))}


@app.post("/api/library/{service_id}/enable")
def library_enable(service_id: str, _: dict = Depends(require_admin), db=Depends(get_db)):
    if not any(s["id"] == service_id for s in _SERVICE_CATALOG):
        raise HTTPException(404, "Service inconnu")
    enabled = _get_enabled_services(db)
    enabled.add(service_id)
    _set_enabled_services(db, enabled)
    return {"ok": True}


@app.delete("/api/library/{service_id}/enable")
def library_disable(service_id: str, _: dict = Depends(require_admin), db=Depends(get_db)):
    enabled = _get_enabled_services(db)
    enabled.discard(service_id)
    _set_enabled_services(db, enabled)
    return {"ok": True}


@app.post("/api/library/{service_id}/pull")
def library_pull(service_id: str, bg: BackgroundTasks, _: dict = Depends(require_admin)):
    svc = next((s for s in _SERVICE_CATALOG if s["id"] == service_id), None)
    if not svc:
        raise HTTPException(404, "Service inconnu")
    image = svc["dockerImage"]
    _pull_status[image] = "pulling"
    bg.add_task(_do_pull_image, image)
    return {"ok": True, "image": image}


@app.get("/api/library/pull-status")
def library_pull_status(_: dict = Depends(get_current_user)):
    # Detect images already present locally that we haven't tracked yet
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True, text=True, timeout=5,
        )
        local_images = set(result.stdout.splitlines())
        for svc in _SERVICE_CATALOG:
            img = svc["dockerImage"]
            if img not in _pull_status and img in local_images:
                _pull_status[img] = "pulled"
    except Exception:
        pass
    return _pull_status


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
