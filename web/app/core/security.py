"""
DataForge — Security module.

- Fernet (AES-128-CBC + HMAC-SHA256) for encrypting service credentials at rest
- PyJWT (HS256) for access tokens
- PBKDF2-HMAC-SHA256 for user password hashing
- Refresh token management
"""

import datetime
import hashlib
import hmac as _hmac
import secrets
import time
from typing import Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import (
    ACCESS_TTL,
    JWT_ALGORITHM,
    MASTER_KEY,
    REFRESH_TTL,
)
from app.core.audit import logger

# ── Fernet cipher (for service credentials at rest) ─────────────────────────

_fernet = Fernet(MASTER_KEY.encode())


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret for storage in database. Returns base64 string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret from database. Returns plaintext."""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Fallback: value may still be stored in plaintext (pre-migration)
        logger.warning("Failed to decrypt secret — may be plaintext (pre-migration)")
        return ciphertext


# ── Password hashing (PBKDF2-HMAC-SHA256, 600k iterations) ──────────────────

_PBKDF2_ITERATIONS = 600_000  # OWASP 2024 recommendation


def hash_password(password: str) -> str:
    """Hash a password with a random salt. Returns 'salt$hash'."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    )
    return f"{salt}${dk.hex()}"


def check_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash. Constant-time comparison."""
    try:
        salt, dk_hex = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
        )
        return _hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# Dummy hash to prevent timing attacks on non-existent users
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def check_password_constant_time(password: str, stored: Optional[str]) -> bool:
    """Always runs PBKDF2 to prevent user enumeration via timing."""
    if stored is None:
        check_password(password, _DUMMY_HASH)
        return False
    return check_password(password, stored)


# ── JWT access tokens ────────────────────────────────────────────────────────

# Set at startup by init_db() or from env
jwt_secret_key: str = ""


def make_access_token(user_id: int, username: str, role: str) -> str:
    """Create a signed JWT access token."""
    payload = {
        "id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=ACCESS_TTL),
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, jwt_secret_key, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(
            token,
            jwt_secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "id", "username", "role"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Refresh tokens (stored as SHA-256 hash in DB) ───────────────────────────


def hash_token(raw: str) -> str:
    """SHA-256 hash of a raw refresh token."""
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_refresh_token(user_id: int, cursor_fn, conn) -> str:
    """Create a new refresh token, store hash in DB, return raw value."""
    raw = secrets.token_hex(32)
    with cursor_fn(conn) as cur:
        cur.execute(
            """INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
               VALUES (%s, %s, NOW() + INTERVAL '%s seconds')""",
            (user_id, hash_token(raw), REFRESH_TTL),
        )
    return raw


def rotate_refresh_token(old_raw: str, cursor_fn, conn) -> Optional[tuple[dict, str]]:
    """Rotate a refresh token: revoke old, issue new. Returns (user_info, new_raw) or None."""
    old_hash = hash_token(old_raw)
    with cursor_fn(conn) as cur:
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

    # Compromised token reuse detection
    if row["revoked"]:
        with cursor_fn(conn) as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = %s",
                (row["user_id"],),
            )
        return None

    if row["expires_at"] < datetime.datetime.now(datetime.timezone.utc):
        with cursor_fn(conn) as cur:
            cur.execute("DELETE FROM refresh_tokens WHERE id = %s", (row["id"],))
        return None

    # Revoke old token
    with cursor_fn(conn) as cur:
        cur.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE id = %s",
            (row["id"],),
        )

    new_raw = issue_refresh_token(row["user_id"], cursor_fn, conn)
    return dict(row), new_raw
