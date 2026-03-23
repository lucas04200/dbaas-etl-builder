"""
Tests for security module: hashing, encryption, JWT.

No database required.
"""

import pytest

from app.core.security import (
    check_password_constant_time,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    make_access_token,
    verify_access_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MySecureP@ssw0rd!"
        hashed = hash_password(password)
        assert hashed != password
        assert check_password_constant_time(password, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct-password")
        assert check_password_constant_time("wrong-password", hashed) is False

    def test_none_hash_returns_false(self):
        """Constant-time: even with no stored hash, should return False not crash."""
        assert check_password_constant_time("anything", None) is False

    def test_different_hashes_for_same_password(self):
        """Salt should make hashes unique."""
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2


class TestFernetEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "my-secret-database-password"
        encrypted = encrypt_secret(plaintext)
        assert encrypted != plaintext
        decrypted = decrypt_secret(encrypted)
        assert decrypted == plaintext

    def test_empty_string(self):
        encrypted = encrypt_secret("")
        assert decrypt_secret(encrypted) == ""

    def test_unicode(self):
        plaintext = "p@ssw0rd-àéîõü-中文"
        encrypted = encrypt_secret(plaintext)
        assert decrypt_secret(encrypted) == plaintext

    def test_decrypt_plaintext_fallback(self):
        """Pre-migration data stored in plain text should be returned as-is."""
        result = decrypt_secret("not-encrypted-at-all")
        assert result == "not-encrypted-at-all"


class TestJWT:
    def test_create_and_verify(self):
        import app.core.security as sec
        sec.jwt_secret_key = "test-secret-key-for-jwt-testing-1234"

        token = make_access_token(42, "testuser", "admin")
        payload = verify_access_token(token)
        assert payload is not None
        assert payload["id"] == 42
        assert payload["username"] == "testuser"
        assert payload["role"] == "admin"

    def test_expired_token(self):
        import time
        import jwt as pyjwt
        import app.core.security as sec
        sec.jwt_secret_key = "test-secret-key-for-jwt-testing-1234"

        expired_token = pyjwt.encode(
            {"id": 1, "username": "u", "role": "user", "exp": int(time.time()) - 10},
            sec.jwt_secret_key,
            algorithm="HS256",
        )
        assert verify_access_token(expired_token) is None

    def test_invalid_token(self):
        import app.core.security as sec
        sec.jwt_secret_key = "test-secret-key-for-jwt-testing-1234"
        assert verify_access_token("garbage.token.here") is None

    def test_tampered_token(self):
        import app.core.security as sec
        sec.jwt_secret_key = "test-secret-key-for-jwt-testing-1234"

        token = make_access_token(1, "user", "admin")
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        assert verify_access_token(tampered) is None
