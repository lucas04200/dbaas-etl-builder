"""
DataForge — Database module.

Connection pool management, cursor helpers, and schema migrations.
"""

import json
import secrets
from typing import Generator, Optional

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool

from app.core.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER, JWT_SECRET_KEY
from app.core.audit import logger

_pool: Optional[pg_pool.ThreadedConnectionPool] = None


def get_pool() -> pg_pool.ThreadedConnectionPool:
    """Return the global connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialised — call init_db() first")
    return _pool


def get_db() -> Generator:
    """FastAPI dependency: borrow a connection, auto-commit/rollback."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def cursor(conn):
    """Shortcut for a RealDictCursor."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def close_pool():
    """Gracefully close all connections."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Database pool closed")


# ── Schema initialisation & migrations ──────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_config (
    key   VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(64) UNIQUE NOT NULL,
    password   TEXT        NOT NULL,
    role       VARCHAR(16) NOT NULL DEFAULT 'user',
    email      VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(128);

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
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(64) UNIQUE NOT NULL,
    db_name           VARCHAR(64) NOT NULL,
    db_user           VARCHAR(64) NOT NULL,
    db_password       TEXT        NOT NULL,
    host_port         INTEGER     NOT NULL,
    status            VARCHAR(16) DEFAULT 'provisioning',
    is_internal       BOOLEAN     DEFAULT FALSE,
    internal_for_type VARCHAR(32),
    internal_for_id   INTEGER,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    created_by        INTEGER     REFERENCES users(id)
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
    mage_email   VARCHAR(128),
    access_token TEXT,
    status       VARCHAR(16) DEFAULT 'provisioning',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    created_by   INTEGER     REFERENCES users(id)
);
ALTER TABLE mage_instances ADD COLUMN IF NOT EXISTS mage_email VARCHAR(128);
ALTER TABLE mage_instances ADD COLUMN IF NOT EXISTS access_token TEXT;

CREATE TABLE IF NOT EXISTS minio_instances (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(64) UNIQUE NOT NULL,
    host_port     INTEGER     NOT NULL,
    console_port  INTEGER     NOT NULL,
    root_user     VARCHAR(64) NOT NULL,
    root_password TEXT        NOT NULL,
    status        VARCHAR(16) DEFAULT 'provisioning',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    created_by    INTEGER     REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mariadb_instances (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(64) UNIQUE NOT NULL,
    host_port     INTEGER     NOT NULL,
    root_password TEXT        NOT NULL,
    db_name       VARCHAR(64) DEFAULT '',
    status        VARCHAR(16) DEFAULT 'provisioning',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    created_by    INTEGER     REFERENCES users(id)
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
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(64) UNIQUE NOT NULL,
    host_port      INTEGER     NOT NULL,
    linked_pg_id   INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
    admin_password TEXT        NOT NULL,
    status         VARCHAR(16) DEFAULT 'provisioning',
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    created_by     INTEGER     REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS airflow_instances (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(64) UNIQUE NOT NULL,
    host_port      INTEGER     NOT NULL,
    linked_pg_id   INTEGER     REFERENCES postgres_instances(id) ON DELETE SET NULL,
    admin_password TEXT         NOT NULL,
    status         VARCHAR(16) DEFAULT 'provisioning',
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    created_by     INTEGER     REFERENCES users(id)
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

CREATE TABLE IF NOT EXISTS audit_log (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER,
    action     VARCHAR(64) NOT NULL,
    detail     JSONB,
    ip         VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

CREATE TABLE IF NOT EXISTS metabase_connections (
    metabase_id INTEGER NOT NULL REFERENCES metabase_instances(id) ON DELETE CASCADE,
    pg_id       INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (metabase_id, pg_id)
);

CREATE TABLE IF NOT EXISTS n8n_connections (
    n8n_id     INTEGER NOT NULL REFERENCES n8n_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (n8n_id, pg_id)
);

CREATE TABLE IF NOT EXISTS mage_connections (
    mage_id    INTEGER NOT NULL REFERENCES mage_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (mage_id, pg_id)
);

CREATE TABLE IF NOT EXISTS superset_connections (
    superset_id INTEGER NOT NULL REFERENCES superset_instances(id) ON DELETE CASCADE,
    pg_id       INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (superset_id, pg_id)
);

CREATE TABLE IF NOT EXISTS airflow_connections (
    airflow_id INTEGER NOT NULL REFERENCES airflow_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (airflow_id, pg_id)
);
"""

_MIGRATIONS_SQL = """
ALTER TABLE groups ADD COLUMN IF NOT EXISTS instance_type VARCHAR(32);
ALTER TABLE groups ADD COLUMN IF NOT EXISTS instance_id INTEGER;
ALTER TABLE user_groups ADD COLUMN IF NOT EXISTS role VARCHAR(32) DEFAULT 'viewer';
ALTER TABLE postgres_instances ADD COLUMN IF NOT EXISTS is_internal BOOLEAN DEFAULT FALSE;
ALTER TABLE postgres_instances ADD COLUMN IF NOT EXISTS internal_for_type VARCHAR(32);
ALTER TABLE postgres_instances ADD COLUMN IF NOT EXISTS internal_for_id INTEGER;

DELETE FROM groups WHERE instance_type IS NULL AND name IN (
    'mage','metabase','n8n','minio','postgrest','redis',
    'airflow','clickhouse','ollama','superset','hasura','mariadb','qdrant'
);

CREATE TABLE IF NOT EXISTS metabase_connections (
    metabase_id INTEGER NOT NULL REFERENCES metabase_instances(id) ON DELETE CASCADE,
    pg_id       INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (metabase_id, pg_id)
);

CREATE TABLE IF NOT EXISTS n8n_connections (
    n8n_id     INTEGER NOT NULL REFERENCES n8n_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (n8n_id, pg_id)
);

CREATE TABLE IF NOT EXISTS mage_connections (
    mage_id    INTEGER NOT NULL REFERENCES mage_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (mage_id, pg_id)
);

CREATE TABLE IF NOT EXISTS superset_connections (
    superset_id INTEGER NOT NULL REFERENCES superset_instances(id) ON DELETE CASCADE,
    pg_id       INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (superset_id, pg_id)
);

CREATE TABLE IF NOT EXISTS airflow_connections (
    airflow_id INTEGER NOT NULL REFERENCES airflow_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (airflow_id, pg_id)
);
"""


def _run_alembic_migrations() -> None:
    """Run Alembic migrations to bring the schema up to date."""
    try:
        from alembic.config import Config
        from alembic import command
        import os

        ini_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "alembic.ini",
        )
        if os.path.exists(ini_path):
            alembic_cfg = Config(ini_path)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations applied")
        else:
            logger.warning("alembic.ini not found, falling back to raw SQL")
            raise FileNotFoundError
    except Exception as exc:
        logger.warning("Alembic unavailable (%s), using raw SQL schema", exc)
        conn = _pool.getconn()
        try:
            with cursor(conn) as cur:
                cur.execute(_SCHEMA_SQL)
                cur.execute(_MIGRATIONS_SQL)
            conn.commit()
        finally:
            _pool.putconn(conn)


def init_db() -> str:
    """Initialise connection pool, run schema + migrations, return JWT secret."""
    global _pool

    _pool = pg_pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )

    # Apply schema via Alembic (with raw SQL fallback)
    _run_alembic_migrations()

    # Ensure connection tables exist (Alembic might not have them yet)
    conn = _pool.getconn()
    try:
        with cursor(conn) as cur:
            cur.execute(_SCHEMA_SQL)
            cur.execute(_MIGRATIONS_SQL)
        conn.commit()
    except Exception as exc:
        logger.error("Failed to ensure connection tables: %s", exc)
    finally:
        _pool.putconn(conn)

    # JWT secret management
    conn = _pool.getconn()
    try:
        with cursor(conn) as cur:
            if JWT_SECRET_KEY:
                secret = JWT_SECRET_KEY
            else:
                cur.execute(
                    "SELECT value FROM app_config WHERE key = 'secret_key'"
                )
                row = cur.fetchone()
                if row:
                    secret = row["value"]
                else:
                    secret = secrets.token_hex(32)
                    cur.execute(
                        "INSERT INTO app_config (key, value) VALUES ('secret_key', %s)",
                        (secret,),
                    )

        conn.commit()
        logger.info("Database initialised")
    finally:
        _pool.putconn(conn)

    return secret


def next_port(conn, base: int) -> int:
    """Find the next available host port starting from `base`."""
    with cursor(conn) as cur:
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
