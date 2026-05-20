import pytest
from app.config import Settings


@pytest.fixture
def test_settings():
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        dashscope_api_key="test-key",
        jwt_secret="test-secret",
        debug=True,
    )
