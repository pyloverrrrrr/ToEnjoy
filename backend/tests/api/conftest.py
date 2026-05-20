import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


@pytest.fixture
def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    return engine


@pytest.fixture
def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db(test_engine):
    from app.models import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(autouse=True)
def patch_external_services(test_session_factory):
    """Override FastAPI dependencies to use test services."""
    from app.main import app
    from app.db.session import get_db

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    mock_chroma = MagicMock()
    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["doc1", "doc2"],
        "documents": ["doc content 1", "doc content 2"],
        "metadatas": [{"title": "Test Doc 1", "type": "guideline"}, {"title": "Test Doc 2", "type": "education"}],
    }
    mock_col.query.return_value = {
        "ids": [["doc1"]],
        "documents": [["test content"]],
        "distances": [[1.0]],
        "metadatas": [[{"title": "Test", "type": "guideline"}]],
    }
    mock_chroma.get_collection.return_value = mock_col

    mock_redis = AsyncMock()

    mock_adapter = MagicMock()
    mock_adapter.name = "mock"
    mock_adapter.generate = AsyncMock(return_value='{"intent": "consult", "confidence": 0.95}')
    mock_adapter.embed = AsyncMock(return_value=[[0.1] * 4096])
    mock_adapter.rerank = AsyncMock(return_value=[{"index": 0, "relevance_score": 0.9}])

    async def mock_stream(messages, temperature, max_tokens):
        yield "test "
        yield "response"

    mock_adapter.generate_stream = mock_stream

    # Pre-patch session module before app's lifespan runs
    with patch("app.db.session.engine", test_engine), \
         patch("app.db.session.async_session", test_session_factory), \
         patch("app.db.chroma.get_chroma", return_value=mock_chroma), \
         patch("app.db.chroma.init_chroma", AsyncMock()), \
         patch("app.core.rag.hybrid_retriever.get_chroma", return_value=mock_chroma), \
         patch("app.db.redis.get_redis", return_value=mock_redis), \
         patch("app.db.redis.init_redis", AsyncMock()), \
         patch("app.db.redis.close_redis", AsyncMock()), \
         patch("app.core.rag.query_processor.get_adapter_registry", return_value=mock_adapter), \
         patch("app.core.agent.response_gen.get_adapter_registry", return_value=mock_adapter), \
         patch("app.core.agent.react_engine.get_adapter_registry", return_value=mock_adapter), \
         patch("app.core.rag.hybrid_retriever.get_adapter_registry", return_value=mock_adapter), \
         patch("app.core.rag.post_processor.get_adapter_registry", return_value=mock_adapter):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = override_get_db
        yield

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_token(async_client):
    """Register and login to get a valid JWT token."""
    await async_client.post("/api/auth/register", json={
        "username": "testuser", "password": "testpass", "name": "Test User", "role": "patient",
    })
    resp = await async_client.post("/api/auth/login", json={
        "username": "testuser", "password": "testpass",
    })
    data = resp.json()
    return data["token"]
