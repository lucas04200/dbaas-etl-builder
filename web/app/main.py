"""
DataForge — Application entrypoint.

Lightweight main module that assembles all routers and middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import STATIC_PATH
from app.core.database import close_pool, init_db
from app.core.middleware import limiter, security_headers_middleware
from app.core.security import jwt_secret_key
from app.core.audit import logger

# Import routers
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.groups import router as groups_router
from app.api.services.postgres import router as postgres_router
from app.api.services.n8n import router as n8n_router
from app.api.services.metabase import router as metabase_router
from app.api.services.redis import router as redis_router
from app.api.services.postgrest import router as postgrest_router
from app.api.services.mage import router as mage_router
from app.api.services.minio import router as minio_router
from app.api.services.mariadb import router as mariadb_router
from app.api.services.qdrant import router as qdrant_router
from app.api.services.clickhouse import router as clickhouse_router
from app.api.services.ollama import router as ollama_router
from app.api.services.superset import router as superset_router
from app.api.services.airflow import router as airflow_router
from app.api.services.hasura import router as hasura_router
from app.api.services.library import router as library_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: init DB + set JWT secret. Shutdown: close pool."""
    import app.core.security as sec

    secret = init_db()
    sec.jwt_secret_key = secret
    logger.info("DataForge started")
    try:
        yield
    finally:
        close_pool()
        logger.info("DataForge stopped")


app = FastAPI(title="DataForge", lifespan=lifespan, docs_url=None, redoc_url=None)

# ── Middleware ───────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.middleware("http")(security_headers_middleware)

# ── Static files ─────────────────────────────────────────────────────────────

app.mount("/assets", StaticFiles(directory=STATIC_PATH / "assets"), name="assets")

# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(groups_router)
app.include_router(postgres_router)
app.include_router(n8n_router)
app.include_router(metabase_router)
app.include_router(redis_router)
app.include_router(postgrest_router)
app.include_router(mage_router)
app.include_router(minio_router)
app.include_router(mariadb_router)
app.include_router(qdrant_router)
app.include_router(clickhouse_router)
app.include_router(ollama_router)
app.include_router(superset_router)
app.include_router(airflow_router)
app.include_router(hasura_router)
app.include_router(library_router)


# ── Root redirect ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return RedirectResponse("/databases")


# ── SPA fallback ─────────────────────────────────────────────────────────────

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str, response: Response):
    candidate = STATIC_PATH / full_path
    if candidate.exists() and candidate.is_file() and not full_path.startswith("api/"):
        return FileResponse(candidate)
    index = STATIC_PATH / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    from fastapi import HTTPException
    raise HTTPException(404)
