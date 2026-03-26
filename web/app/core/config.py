"""
DataForge — Centralised configuration.

Every secret MUST come from environment variables.
No hardcoded default passwords — if a required var is missing, the app refuses to start.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # project root
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "web" / ".env")  # Fallback for some setups
WEB_DIR = BASE_DIR / "web"
STATIC_PATH = WEB_DIR / "static"

# ── Internal database ────────────────────────────────────────────────────────

DB_HOST = os.getenv("DATAFORGE_DB_HOST", "localhost")
DB_PORT = int(os.getenv("DATAFORGE_DB_PORT", "5433"))
DB_NAME = os.getenv("DATAFORGE_DB_NAME", "dataforge")
DB_USER = os.getenv("DATAFORGE_DB_USER", "dataforge")

# CRITICAL: no hardcoded default — must be provided
DB_PASS = os.getenv("DATAFORGE_DB_PASS", "")
if not DB_PASS:
    print(
        "FATAL: DATAFORGE_DB_PASS environment variable is required.\n"
        "  export DATAFORGE_DB_PASS='your-strong-password-here'",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Master encryption key (Fernet) ───────────────────────────────────────────
# Used to encrypt service credentials at rest in the database.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MASTER_KEY = os.getenv("DATAFORGE_MASTER_KEY", "")
if not MASTER_KEY:
    print(
        "FATAL: DATAFORGE_MASTER_KEY environment variable is required.\n"
        "  Generate one with:\n"
        "    python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
        file=sys.stderr,
    )
    sys.exit(1)

# ── JWT ──────────────────────────────────────────────────────────────────────
# If not set, a random key is generated at startup and stored in app_config.
# For multi-instance deployments, set a shared key via env.
JWT_SECRET_KEY = os.getenv("DATAFORGE_JWT_SECRET", "")

JWT_ALGORITHM = "HS256"
ACCESS_TTL = 15 * 60       # 15 minutes
REFRESH_TTL = 7 * 24 * 3600  # 7 days

ACCESS_COOKIE = "df_access"
REFRESH_COOKIE = "df_refresh"

# ── Rate limiting ────────────────────────────────────────────────────────────

RATE_LIMIT_LOGIN = os.getenv("DATAFORGE_RATE_LIMIT_LOGIN", "5/minute")
RATE_LIMIT_REGISTER = os.getenv("DATAFORGE_RATE_LIMIT_REGISTER", "3/minute")
RATE_LIMIT_SETUP = os.getenv("DATAFORGE_RATE_LIMIT_SETUP", "3/minute")

# ── Password policy ─────────────────────────────────────────────────────────

PASSWORD_MIN_LENGTH = 12
