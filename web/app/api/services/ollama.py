"""
DataForge — Ollama instances API with model management.
"""

import json
import urllib.request

import psycopg2
from fastapi import BackgroundTasks, Depends, HTTPException

from app.core.database import cursor, get_db, next_port
from app.api.deps import get_current_user, require_admin
from app.api.services.provisioning import provision_ollama
from app.api.services.base import ServiceConfig, create_service_crud
from app.models import (
    CreateOllamaRequest,
    OllamaChatRequest,
    OllamaDeleteModelRequest,
    OllamaPullRequest,
)

router = create_service_crud(ServiceConfig(
    service_type="ollama",
    table="ollama_instances",
    container_prefix="ollama",
    prefix="/api/ollama",
    list_columns="id, name, host_port, status, created_at",
    order_by="ORDER BY created_at DESC",
    volume_prefix="ollama_data",
))

# In-memory pull status: {instance_id: {model_name: "pulling"|"done"|"error"}}
_ollama_pull_status: dict[int, dict[str, str]] = {}


# ── Ollama API helpers ───────────────────────────────────────────────────────


def _ollama_url(db, instance_id: int) -> tuple[str, str]:
    with cursor(db) as cur:
        cur.execute(
            "SELECT name, host_port, status FROM ollama_instances WHERE id = %s",
            (instance_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Instance introuvable")
    if row["status"] != "running":
        raise HTTPException(409, "Instance non demarree")
    return f"http://localhost:{row['host_port']}", row["name"]


def _ollama_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read())


def _ollama_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _ollama_delete(url: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="DELETE",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


# ── Create ───────────────────────────────────────────────────────────────────


@router.post("", status_code=201)
def create_ollama(
    body: CreateOllamaRequest,
    bg: BackgroundTasks,
    user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    port = next_port(db, 11434)
    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO ollama_instances (name, host_port, created_by) "
                "VALUES (%s, %s, %s) RETURNING id",
                (body.name, port, user["id"]),
            )
            instance_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Une instance avec ce nom existe deja")

    bg.add_task(provision_ollama, instance_id, body.name, port)
    return {"id": instance_id, "port": port, "status": "provisioning"}


# ── Model management ────────────────────────────────────────────────────────


@router.get("/{instance_id}/models")
def ollama_list_models(
    instance_id: int,
    _: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    base_url, _ = _ollama_url(db, instance_id)
    try:
        data = _ollama_get(f"{base_url}/api/tags")
        return {"models": data.get("models", [])}
    except Exception:
        return {"models": []}


async def _do_ollama_pull(instance_id: int, base_url: str, model: str):
    _ollama_pull_status.setdefault(instance_id, {})[model] = "pulling"
    try:
        url = f"{base_url}/api/pull"
        payload = json.dumps({"name": model, "stream": True}).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"},
        )
        # Stream the response: Ollama sends one JSON line per progress update,
        # keeping the connection alive for the entire download (can take 30min+).
        with urllib.request.urlopen(req, timeout=1800) as r:
            for raw_line in r:
                line = raw_line.decode().strip()
                if not line:
                    continue
                chunk = json.loads(line)
                status = chunk.get("status", "")
                # Update progress info for the pull-status endpoint
                _ollama_pull_status[instance_id][model] = status or "pulling"
                if chunk.get("error"):
                    _ollama_pull_status[instance_id][model] = "error"
                    return
        _ollama_pull_status[instance_id][model] = "done"
    except Exception:
        _ollama_pull_status[instance_id][model] = "error"


@router.post("/{instance_id}/models/pull")
def ollama_pull_model(
    instance_id: int,
    body: OllamaPullRequest,
    bg: BackgroundTasks,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    base_url, _ = _ollama_url(db, instance_id)
    bg.add_task(_do_ollama_pull, instance_id, base_url, body.name)
    return {"ok": True}


@router.get("/{instance_id}/models/pull-status")
def ollama_pull_status(instance_id: int, _: dict = Depends(get_current_user)):
    return _ollama_pull_status.get(instance_id, {})


@router.delete("/{instance_id}/models")
def ollama_delete_model(
    instance_id: int,
    body: OllamaDeleteModelRequest,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    base_url, _ = _ollama_url(db, instance_id)
    try:
        _ollama_delete(f"{base_url}/api/delete", {"name": body.name})
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@router.post("/{instance_id}/chat")
def ollama_chat(
    instance_id: int,
    body: OllamaChatRequest,
    _: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    base_url, _ = _ollama_url(db, instance_id)
    try:
        result = _ollama_post(f"{base_url}/api/chat", {
            "model": body.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in body.messages
            ],
            "stream": False,
        })
        return {"message": result.get("message", {})}
    except Exception as e:
        raise HTTPException(500, f"Erreur Ollama : {e}")
