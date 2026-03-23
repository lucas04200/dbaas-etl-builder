"""
DataForge — FastAPI dependencies for auth.
"""

from fastapi import Depends, HTTPException, Request, Response

from app.core.config import ACCESS_COOKIE, ACCESS_TTL, REFRESH_COOKIE, REFRESH_TTL
from app.core.security import make_access_token, verify_access_token


def get_current_user(request: Request) -> dict:
    """Require a valid access token in cookies."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifie")
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expiree")
    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    return user


def set_tokens(response: Response, access: str, refresh: str):
    """Set access and refresh token cookies."""
    response.set_cookie(
        ACCESS_COOKIE, access,
        httponly=True, samesite="lax", max_age=ACCESS_TTL,
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh,
        httponly=True, samesite="lax", max_age=REFRESH_TTL, path="/api/auth",
    )


def clear_tokens(response: Response):
    """Remove auth cookies."""
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
