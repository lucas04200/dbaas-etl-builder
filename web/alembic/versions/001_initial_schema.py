"""Initial schema — captures existing DataForge tables.

Revision ID: 001
Revises: -
Create Date: 2026-03-21
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
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
        id            SERIAL PRIMARY KEY,
        name          VARCHAR(64) UNIQUE NOT NULL,
        description   TEXT        DEFAULT '',
        instance_type VARCHAR(32),
        instance_id   INTEGER,
        created_at    TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS user_groups (
        user_id  INTEGER     NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
        group_id INTEGER     NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
        role     VARCHAR(32) DEFAULT 'viewer',
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
        admin_password TEXT        NOT NULL,
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
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS audit_log CASCADE;
    DROP TABLE IF EXISTS hasura_instances CASCADE;
    DROP TABLE IF EXISTS airflow_instances CASCADE;
    DROP TABLE IF EXISTS superset_instances CASCADE;
    DROP TABLE IF EXISTS ollama_instances CASCADE;
    DROP TABLE IF EXISTS clickhouse_instances CASCADE;
    DROP TABLE IF EXISTS qdrant_instances CASCADE;
    DROP TABLE IF EXISTS mariadb_instances CASCADE;
    DROP TABLE IF EXISTS minio_instances CASCADE;
    DROP TABLE IF EXISTS mage_instances CASCADE;
    DROP TABLE IF EXISTS postgrest_instances CASCADE;
    DROP TABLE IF EXISTS redis_instances CASCADE;
    DROP TABLE IF EXISTS metabase_instances CASCADE;
    DROP TABLE IF EXISTS instance_permissions CASCADE;
    DROP TABLE IF EXISTS user_groups CASCADE;
    DROP TABLE IF EXISTS groups CASCADE;
    DROP TABLE IF EXISTS n8n_instances CASCADE;
    DROP TABLE IF EXISTS postgres_instances CASCADE;
    DROP TABLE IF EXISTS refresh_tokens CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS app_config CASCADE;
    """)
