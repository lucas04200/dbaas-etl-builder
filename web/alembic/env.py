"""
Alembic environment configuration for DataForge.

Reads database connection from DataForge config (env vars).
Uses raw SQL migrations (no SQLAlchemy ORM models).
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Add project root to sys.path so we can import app.core.config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct DB connection)."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
