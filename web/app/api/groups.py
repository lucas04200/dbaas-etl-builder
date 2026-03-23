"""
DataForge — Groups & Permissions API.
"""

import psycopg2
from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import sql as pg_sql

from app.core.database import cursor, get_db
from app.api.deps import require_admin
from app.models import AddMemberRequest, AddPermissionRequest, CreateGroupRequest

router = APIRouter(prefix="/api", tags=["groups"])

_INSTANCE_TABLES = {
    "postgres":   "postgres_instances",
    "n8n":        "n8n_instances",
    "metabase":   "metabase_instances",
    "redis":      "redis_instances",
    "postgrest":  "postgrest_instances",
    "mage":       "mage_instances",
    "minio":      "minio_instances",
    "mariadb":    "mariadb_instances",
    "qdrant":     "qdrant_instances",
    "clickhouse": "clickhouse_instances",
    "ollama":     "ollama_instances",
    "superset":   "superset_instances",
    "airflow":    "airflow_instances",
    "hasura":     "hasura_instances",
}


def _resolve_instance_name(db, instance_type: str, instance_id: int) -> str:
    table = _INSTANCE_TABLES.get(instance_type)
    if not table:
        return "?"
    with cursor(db) as cur:
        cur.execute(
            pg_sql.SQL("SELECT name FROM {} WHERE id = %s").format(
                pg_sql.Identifier(table)
            ),
            (instance_id,),
        )
        row = cur.fetchone()
        return row["name"] if row else "?"


# ── All instances (for group creation dropdown) ──────────────────────────────

@router.get("/instances")
def list_all_instances(_: dict = Depends(require_admin), db=Depends(get_db)):
    result = []
    for itype, table in _INSTANCE_TABLES.items():
        extra_filter = " AND is_internal = FALSE" if itype == "postgres" else ""
        with cursor(db) as cur:
            cur.execute(
                pg_sql.SQL("SELECT id, name FROM {} WHERE status = 'running'{}").format(
                    pg_sql.Identifier(table),
                    pg_sql.SQL(extra_filter),
                )
            )
            for row in cur.fetchall():
                result.append({"type": itype, "id": row["id"], "name": row["name"]})
    return result


# ── Groups CRUD ──────────────────────────────────────────────────────────────

@router.get("/groups")
def list_groups(_: dict = Depends(require_admin), db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("""
            SELECT g.id, g.name, g.description, g.instance_type, g.instance_id,
                   COUNT(DISTINCT ug.user_id) AS member_count
            FROM   groups g
            LEFT JOIN user_groups ug ON ug.group_id = g.id
            GROUP BY g.id ORDER BY g.name
        """)
        groups = [dict(r) for r in cur.fetchall()]
    for g in groups:
        if g["instance_type"] and g["instance_id"]:
            g["instance_name"] = _resolve_instance_name(
                db, g["instance_type"], g["instance_id"]
            )
        else:
            g["instance_name"] = None
    return groups


@router.post("/groups", status_code=201)
def create_group(
    body: CreateGroupRequest,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO groups (name, description, instance_type, instance_id) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (body.name, body.description, body.instance_type, body.instance_id),
            )
            return {"id": cur.fetchone()["id"]}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Un groupe avec ce nom existe deja")


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute("DELETE FROM groups WHERE id = %s", (group_id,))
    return {"ok": True}


# ── Members ──────────────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/members")
def list_members(group_id: int, _: dict = Depends(require_admin), db=Depends(get_db)):
    with cursor(db) as cur:
        cur.execute(
            """SELECT u.id, u.username, u.email, ug.role
               FROM   user_groups ug
               JOIN   users u ON u.id = ug.user_id
               WHERE  ug.group_id = %s ORDER BY u.username""",
            (group_id,),
        )
        return [dict(r) for r in cur.fetchall()]


@router.post("/groups/{group_id}/members", status_code=201)
def add_member(
    group_id: int,
    body: AddMemberRequest,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    try:
        with cursor(db) as cur:
            cur.execute(
                "INSERT INTO user_groups (user_id, group_id, role) VALUES (%s, %s, %s)",
                (body.user_id, group_id, body.role),
            )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Membre deja dans le groupe")
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(404, "Utilisateur introuvable")
    return {"ok": True}


@router.delete("/groups/{group_id}/members/{user_id}")
def remove_member(
    group_id: int,
    user_id: int,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    with cursor(db) as cur:
        cur.execute(
            "DELETE FROM user_groups WHERE group_id = %s AND user_id = %s",
            (group_id, user_id),
        )
    return {"ok": True}


# ── Permissions ──────────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/permissions")
def list_permissions(
    group_id: int, _: dict = Depends(require_admin), db=Depends(get_db)
):
    with cursor(db) as cur:
        cur.execute(
            "SELECT id, instance_type, instance_id, permission "
            "FROM instance_permissions WHERE group_id = %s",
            (group_id,),
        )
        perms = [dict(r) for r in cur.fetchall()]
    for p in perms:
        p["instance_name"] = _resolve_instance_name(
            db, p["instance_type"], p["instance_id"]
        )
    return perms


@router.post("/groups/{group_id}/permissions", status_code=201)
def add_permission(
    group_id: int,
    body: AddPermissionRequest,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    try:
        with cursor(db) as cur:
            cur.execute(
                """INSERT INTO instance_permissions
                   (group_id, instance_type, instance_id, permission)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (group_id, body.instance_type, body.instance_id, body.permission),
            )
            return {"id": cur.fetchone()["id"]}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Permission deja definie pour ce groupe")


@router.delete("/groups/{group_id}/permissions/{perm_id}")
def remove_permission(
    group_id: int,
    perm_id: int,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    with cursor(db) as cur:
        cur.execute(
            "DELETE FROM instance_permissions WHERE id = %s AND group_id = %s",
            (perm_id, group_id),
        )
    return {"ok": True}
