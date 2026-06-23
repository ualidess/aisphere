import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-elevenlabs-key")


@pytest.fixture
async def client():
    from app import app
    from database import engine

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
    await engine.dispose()