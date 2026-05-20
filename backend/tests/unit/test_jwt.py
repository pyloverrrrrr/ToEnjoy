from datetime import timedelta, timezone, datetime

import pytest
from jwt import InvalidTokenError

from app.middleware.auth import create_access_token, decode_token
from app.config import Settings


@pytest.fixture
def jwt_settings():
    return Settings(
        jwt_secret="test-jwt-secret",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
        database_url="sqlite+aiosqlite:///:memory:",
    )


class TestJWT:
    def test_roundtrip(self, jwt_settings, monkeypatch):
        monkeypatch.setattr("app.middleware.auth.settings", jwt_settings)

        token = create_access_token(user_id=42, username="testuser", role="patient")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["username"] == "testuser"
        assert payload["role"] == "patient"
        assert "exp" in payload

    def test_decode_with_wrong_secret(self, jwt_settings, monkeypatch):
        monkeypatch.setattr("app.middleware.auth.settings", jwt_settings)

        token = create_access_token(user_id=1, username="u", role="patient")
        wrong_settings = Settings(
            jwt_secret="wrong-secret",
            jwt_algorithm="HS256",
            jwt_expire_minutes=60,
            database_url="sqlite+aiosqlite:///:memory:",
        )
        monkeypatch.setattr("app.middleware.auth.settings", wrong_settings)

        with pytest.raises(InvalidTokenError):
            decode_token(token)

    def test_decode_expired_token(self, jwt_settings, monkeypatch):
        monkeypatch.setattr("app.middleware.auth.settings", jwt_settings)

        import jwt as pyjwt
        expire = datetime.now(timezone.utc) - timedelta(minutes=1)
        payload = {"sub": "1", "username": "u", "role": "patient", "exp": expire}
        expired_token = pyjwt.encode(payload, jwt_settings.jwt_secret, algorithm=jwt_settings.jwt_algorithm)

        with pytest.raises(InvalidTokenError):
            decode_token(expired_token)

    def test_decode_malformed_token(self, jwt_settings, monkeypatch):
        monkeypatch.setattr("app.middleware.auth.settings", jwt_settings)

        with pytest.raises(InvalidTokenError):
            decode_token("not.a.valid.token")
