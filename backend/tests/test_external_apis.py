from uuid import uuid4

import pytest
from httpx import Request, Response


async def create_auth_headers(client):
    email = f"external-test-{uuid4()}@example.com"
    password = "StrongPassword123!"

    await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_uses_mocked_openai(client, monkeypatch):
    headers = await create_auth_headers(client)
    called_urls = []

    async def fake_external_post(self, url, *args, **kwargs):
        called_urls.append(str(url))

        return Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Mocked AI response"
                        }
                    }
                ]
            },
            request=Request("POST", url),
        )

    monkeypatch.setattr(
        "httpx.AsyncClient.post",
        fake_external_post,
    )

    response = await client.request(
        "POST",
        "/chat",
        json={"message": "Hello from test"},
        headers=headers,
    )

    data = response.json()

    assert response.status_code == 200
    assert "https://api.openai.com/v1/chat/completions" in called_urls
    assert "Mocked AI response" in str(data)