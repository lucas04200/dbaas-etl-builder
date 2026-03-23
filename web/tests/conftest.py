"""
Pytest configuration & fixtures for DataForge.

Sets required environment variables before any app import.
"""

import os

# Set required env vars BEFORE importing app modules
os.environ.setdefault("DATAFORGE_DB_PASS", "test-db-pass")
os.environ.setdefault("DATAFORGE_MASTER_KEY", "dGVzdC1tYXN0ZXIta2V5LWZvcg==")  # placeholder

# Generate a valid Fernet key for tests
from cryptography.fernet import Fernet

os.environ["DATAFORGE_MASTER_KEY"] = Fernet.generate_key().decode()

import pytest


@pytest.fixture
def fernet_key():
    """Return the test Fernet key."""
    return os.environ["DATAFORGE_MASTER_KEY"]
