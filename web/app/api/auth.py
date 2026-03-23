"""
DataForge — Authentication API.

Endpoints: login, register, setup, refresh, logout, me.
All auth endpoints are rate-limited.
"""

from typing import Optional

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import REFRESH_COOKIE
from app.core.database import cursor, get_db
from app.core.middleware import limiter
from app.core.security import (
    check_password_constant_time,
    hash_password,
    hash_token,
    issue_refresh_token,
    make_access_token,
    rotate_refresh_token,
)
from app.core.audit import audit_log
from app.api.deps import clear_tokens, get_current_user, require_admin, set_tokens
from app.models import (
    CreateUserRequest,
    LoginRequest,
    RegisterRequest,
    SetupRequest,
)

router = APIRouter(prefix="/api", tags=["auth"])


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/auth/register", status_code=201)
@limiter.limit("3/minute")
def register(body: RegisterRequest, request: Request, db=Depends(get_db)):
    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO users (username, password, role, email) VALUES (%s, %s, 'user', %s)",
                (body.username, hash_password(body.password), body.email),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Nom d'utilisateur deja utilise")
    audit_log("register", username=body.username, ip=request.client.host)
    return {"ok": True}


# ── Login ────────────────────────────────────────────────────────────────────

@router.post("/auth/login")
@limiter.limit("5/minute")
def login(body: LoginRequest, request: Request, response: Response, db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute(
            "SELECT id, username, password, role FROM users WHERE email = %s",
            (body.email,),
        )
        row = cur.fetchone()

    stored_hash = row["password"] if row else None
    if not check_password_constant_time(body.password, stored_hash):
        audit_log("login_failed", ip=request.client.host, detail={"email": body.email}, success=False)
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    access = make_access_token(row["id"], row["username"], row["role"])
    refresh = issue_refresh_token(row["id"], cursor, db)
    set_tokens(response, access, refresh)

    audit_log("login", user_id=row["id"], username=row["username"], ip=request.client.host)
    return {"ok": True, "role": row["role"]}


# ── Refresh ──────────────────────────────────────────────────────────────────

@router.post("/auth/refresh")
def refresh_token(request: Request, response: Response, db=Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Aucun refresh token")
    result = rotate_refresh_token(raw, cursor, db)
    if not result:
        clear_tokens(response)
        raise HTTPException(status_code=401, detail="Session invalide ou expiree")
    user, new_refresh = result
    new_access = make_access_token(user["user_id"], user["username"], user["role"])
    set_tokens(response, new_access, new_refresh)
    return {"ok": True}


# ── Logout ───────────────────────────────────────────────────────────────────

@router.post("/auth/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        with cursor(db) as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = %s",
                (hash_token(raw),),
            )
    clear_tokens(response)
    return {"ok": True}


# ── Setup (first-run) ────────────────────────────────────────────────────────

@router.get("/setup/status")
def setup_status(db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users")
        n = cur.fetchone()["n"]
    return {"needs_setup": n == 0}


@router.post("/setup", status_code=201)
@limiter.limit("3/minute")
def setup(body: SetupRequest, request: Request, db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users")
        if cur.fetchone()["n"] > 0:
            raise HTTPException(403, "Le compte initial a deja ete cree")
    with cursor(db) as cur:
        cur.execute(
            "INSERT INTO users (username, password, role, email) VALUES (%s, %s, 'admin', %s)",
            (body.username, hash_password(body.password), body.email),
        )
    audit_log("setup", username=body.username, ip=request.client.host)
    return {"ok": True}


# ── Me ───────────────────────────────────────────────────────────────────────

@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ── Users (admin) ────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(_: dict = Depends(require_admin), db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("SELECT id, username, role, email, created_at FROM users ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, request: Request,
                _: dict = Depends(require_admin), db=Depends(get_db)):
    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s)",
                (body.username, hash_password(body.password), body.role, body.email),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Nom d'utilisateur deja utilise")
    audit_log("create_user", username=body.username, ip=request.client.host,
              detail={"role": body.role})
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request,
                current: dict = Depends(require_admin), db=Depends(get_db)):
    if user_id == current["id"]:
        raise HTTPException(400, "Impossible de supprimer votre propre compte")
    with cursor(db) as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    audit_log("delete_user", user_id=current["id"], ip=request.client.host,
              detail={"deleted_user_id": user_id})
    return {"ok": True}
