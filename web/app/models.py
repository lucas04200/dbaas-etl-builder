"""
DataForge — Pydantic models with strong validation.

All user input is validated with regex, length constraints, and type checks.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# ── Validation patterns ──────────────────────────────────────────────────────

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,62}$")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _validate_identifier(v: str, field_name: str = "Nom") -> str:
    if not _IDENTIFIER_RE.match(v):
        raise ValueError(
            f"{field_name} invalide — doit commencer par une lettre, "
            "contenir uniquement lettres, chiffres, _ et - (64 car. max)"
        )
    return v


def _validate_email(v: str) -> str:
    if not _EMAIL_RE.match(v):
        raise ValueError("Adresse e-mail invalide")
    return v


def _validate_password(v: str) -> str:
    from app.core.config import PASSWORD_MIN_LENGTH

    if len(v) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Mot de passe trop court ({PASSWORD_MIN_LENGTH} car. min)")
    return v


# ── Auth models ──────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=128)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return _validate_email(v)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    email: str = Field(..., max_length=128)
    password: str = Field(..., max_length=256)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        return _validate_identifier(v, "Nom d'utilisateur")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)


class SetupRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., max_length=256)
    email: Optional[str] = Field(None, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        return _validate_identifier(v, "Nom d'utilisateur")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v:
            return _validate_email(v)
        return v


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., max_length=256)
    role: str = Field("user", pattern=r"^(admin|user)$")
    email: Optional[str] = Field(None, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        return _validate_identifier(v, "Nom d'utilisateur")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)


# ── Instance models ──────────────────────────────────────────────────────────


class CreatePostgresRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    db_name: str = Field("", max_length=64)
    db_user: str = Field("", max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)

    @field_validator("db_name", "db_user")
    @classmethod
    def validate_identifiers(cls, v):
        if v and not _IDENTIFIER_RE.match(v):
            raise ValueError("Identifiant invalide")
        return v


class CreateN8nRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    linked_pg_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateMetabaseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateRedisRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreatePostgRESTRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    linked_pg_id: int
    db_schema: str = Field("public", min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateMageRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateMinIORequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateMariaDBRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    db_name: str = Field("", max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateQdrantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateClickHouseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateOllamaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateSupersetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateAirflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


class CreateHasuraRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    linked_pg_id: int

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v)


# ── Groups & permissions models ──────────────────────────────────────────────

INSTANCE_TYPES = {
    "postgres", "n8n", "metabase", "redis", "postgrest", "mage",
    "minio", "mariadb", "qdrant", "clickhouse", "ollama", "superset",
    "airflow", "hasura",
}


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field("", max_length=256)
    instance_type: str = Field(..., min_length=1)
    instance_id: int

    @field_validator("instance_type")
    @classmethod
    def validate_instance_type(cls, v):
        if v not in INSTANCE_TYPES:
            raise ValueError(f"Type d'instance invalide : {v}")
        return v


class AddMemberRequest(BaseModel):
    user_id: int
    role: str = Field("viewer", pattern=r"^(admin|viewer|read_write|read_only)$")


class AddPermissionRequest(BaseModel):
    instance_type: str
    instance_id: int
    permission: str = Field("read", pattern=r"^(read|write|admin)$")

    @field_validator("instance_type")
    @classmethod
    def validate_instance_type(cls, v):
        if v not in INSTANCE_TYPES:
            raise ValueError(f"Type d'instance invalide : {v}")
        return v


# ── Ollama models ────────────────────────────────────────────────────────────

_MODEL_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$")


class OllamaPullRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_model_name(cls, v):
        if not _MODEL_NAME_RE.match(v):
            raise ValueError("Nom de modele invalide")
        return v


class OllamaDeleteModelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_model_name(cls, v):
        if not _MODEL_NAME_RE.match(v):
            raise ValueError("Nom de modele invalide")
        return v


class OllamaChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(system|user|assistant)$")
    content: str = Field(..., min_length=1, max_length=32000)


class OllamaChatRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=128)
    messages: list[OllamaChatMessage] = Field(..., min_length=1, max_length=100)


class CreateDatabaseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return _validate_identifier(v, "Nom de base")
