"""
Tests for Pydantic model validation.

No database required — pure input validation.
"""

import pytest
from pydantic import ValidationError

from app.models import (
    CreatePostgresRequest,
    CreateRedisRequest,
    CreateMinIORequest,
    CreateMariaDBRequest,
    CreateClickHouseRequest,
    CreateSupersetRequest,
    CreateAirflowRequest,
    CreateHasuraRequest,
    CreateN8nRequest,
    CreateMageRequest,
    CreateMetabaseRequest,
    CreateQdrantRequest,
    CreateOllamaRequest,
    LoginRequest,
    RegisterRequest,
    SetupRequest,
    CreateGroupRequest,
    AddMemberRequest,
    OllamaPullRequest,
    OllamaChatMessage,
    OllamaChatRequest,
    CreateDatabaseRequest,
)


# ── Identifier validation ───────────────────────────────────────────────────


class TestIdentifierValidation:
    """Test the _validate_identifier regex: ^[a-zA-Z][a-zA-Z0-9_-]{0,62}$"""

    @pytest.mark.parametrize("name", [
        "mydb", "prod-analytics", "test_db", "A", "a1", "my-long-name-123",
    ])
    def test_valid_names(self, name):
        req = CreatePostgresRequest(name=name)
        assert req.name == name

    @pytest.mark.parametrize("name", [
        "", "1starts-with-digit", "-starts-with-dash", "_starts-with-underscore",
        "has space", "has@special", "a" * 65,
    ])
    def test_invalid_names(self, name):
        with pytest.raises(ValidationError):
            CreatePostgresRequest(name=name)


# ── Auth models ──────────────────────────────────────────────────────────────


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(email="user@example.com", password="secret123456")
        assert req.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="secret123456")

    def test_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="a@b.com", password="")


class TestRegisterRequest:
    def test_valid(self):
        req = RegisterRequest(
            username="testuser", email="test@example.com", password="strongpass1234"
        )
        assert req.username == "testuser"

    def test_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser", email="test@example.com", password="short"
            )

    def test_invalid_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="1bad", email="test@example.com", password="strongpass1234"
            )


class TestSetupRequest:
    def test_valid_with_email(self):
        req = SetupRequest(username="admin", password="strongpass1234", email="a@b.com")
        assert req.email == "a@b.com"

    def test_valid_without_email(self):
        req = SetupRequest(username="admin", password="strongpass1234")
        assert req.email is None


# ── Instance create models (no more password fields) ─────────────────────────


class TestCreateServiceRequests:
    """All service create requests should only require a name."""

    def test_postgres_minimal(self):
        req = CreatePostgresRequest(name="mydb")
        assert req.name == "mydb"
        assert req.db_name == ""
        assert req.db_user == ""

    def test_postgres_with_options(self):
        req = CreatePostgresRequest(name="mydb", db_name="analytics", db_user="admin")
        assert req.db_name == "analytics"

    def test_redis(self):
        req = CreateRedisRequest(name="cache")
        assert req.name == "cache"

    def test_minio(self):
        req = CreateMinIORequest(name="storage")
        assert req.name == "storage"

    def test_mariadb(self):
        req = CreateMariaDBRequest(name="mydb", db_name="app")
        assert req.db_name == "app"

    def test_clickhouse(self):
        req = CreateClickHouseRequest(name="analytics")
        assert req.name == "analytics"

    def test_superset(self):
        req = CreateSupersetRequest(name="bi")
        assert req.name == "bi"

    def test_airflow(self):
        req = CreateAirflowRequest(name="orchestrator")
        assert req.name == "orchestrator"

    def test_hasura(self):
        req = CreateHasuraRequest(name="graphql", linked_pg_id=1)
        assert req.linked_pg_id == 1

    def test_n8n(self):
        req = CreateN8nRequest(name="automation")
        assert req.name == "automation"

    def test_mage(self):
        req = CreateMageRequest(name="pipeline")
        assert req.name == "pipeline"

    def test_metabase(self):
        req = CreateMetabaseRequest(name="reporting")
        assert req.name == "reporting"

    def test_qdrant(self):
        req = CreateQdrantRequest(name="vectors")
        assert req.name == "vectors"

    def test_ollama(self):
        req = CreateOllamaRequest(name="llm")
        assert req.name == "llm"


# ── Group & permission models ───────────────────────────────────────────────


class TestGroupModels:
    def test_create_group_valid(self):
        req = CreateGroupRequest(
            name="devs", instance_type="postgres", instance_id=1
        )
        assert req.name == "devs"

    def test_create_group_invalid_type(self):
        with pytest.raises(ValidationError):
            CreateGroupRequest(
                name="devs", instance_type="invalid_type", instance_id=1
            )

    def test_add_member_valid(self):
        req = AddMemberRequest(user_id=1, role="admin")
        assert req.role == "admin"

    def test_add_member_invalid_role(self):
        with pytest.raises(ValidationError):
            AddMemberRequest(user_id=1, role="superadmin")


# ── Ollama models ───────────────────────────────────────────────────────────


class TestOllamaModels:
    def test_pull_valid(self):
        req = OllamaPullRequest(name="llama3:latest")
        assert req.name == "llama3:latest"

    def test_pull_invalid_name(self):
        with pytest.raises(ValidationError):
            OllamaPullRequest(name="@invalid!")

    def test_chat_request(self):
        req = OllamaChatRequest(
            model="llama3",
            messages=[OllamaChatMessage(role="user", content="Hello")]
        )
        assert len(req.messages) == 1

    def test_chat_invalid_role(self):
        with pytest.raises(ValidationError):
            OllamaChatMessage(role="hacker", content="Hello")


# ── Database request ────────────────────────────────────────────────────────


class TestCreateDatabaseRequest:
    def test_valid(self):
        req = CreateDatabaseRequest(name="analytics")
        assert req.name == "analytics"

    def test_invalid(self):
        with pytest.raises(ValidationError):
            CreateDatabaseRequest(name="123bad")
