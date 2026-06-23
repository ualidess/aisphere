import pytest

from app import app
from database import get_db


class FakeDB:
    async def execute(self, statement):
        return None


async def override_get_db():
    yield FakeDB()


@pytest.mark.asyncio
async def test_healthcheck(client):
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["database"] == "ok"
    finally:
        app.dependency_overrides.clear()