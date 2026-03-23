"""
DataForge — Service library management.

Pull Docker images, enable/disable services in the catalog.
"""

import asyncio
import json
import subprocess

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/library", tags=["library"])

# In-memory pull status (resets on server restart, acceptable)
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


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_enabled_services(db) -> set:
    with cursor(db) as cur:
        cur.execute("SELECT value FROM app_config WHERE key = 'enabled_services'")
        row = cur.fetchone()
    return set(json.loads(row["value"])) if row else set(_DEFAULT_ENABLED)


def _set_enabled_services(db, enabled: set):
    with cursor(db) as cur:
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


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/enabled")
def library_enabled(_: dict = Depends(get_current_user), db=Depends(get_db)):
    return {"enabled": list(_get_enabled_services(db))}


@router.post("/{service_id}/enable")
def library_enable(
    service_id: str,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    if not any(s["id"] == service_id for s in _SERVICE_CATALOG):
        raise HTTPException(404, "Service inconnu")
    enabled = _get_enabled_services(db)
    enabled.add(service_id)
    _set_enabled_services(db, enabled)
    return {"ok": True}


@router.delete("/{service_id}/enable")
def library_disable(
    service_id: str,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    enabled = _get_enabled_services(db)
    enabled.discard(service_id)
    _set_enabled_services(db, enabled)
    return {"ok": True}


@router.post("/{service_id}/pull")
def library_pull(
    service_id: str,
    bg: BackgroundTasks,
    _: dict = Depends(require_admin),
):
    svc = next((s for s in _SERVICE_CATALOG if s["id"] == service_id), None)
    if not svc:
        raise HTTPException(404, "Service inconnu")
    image = svc["dockerImage"]
    _pull_status[image] = "pulling"
    bg.add_task(_do_pull_image, image)
    return {"ok": True, "image": image}


@router.get("/pull-status")
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
