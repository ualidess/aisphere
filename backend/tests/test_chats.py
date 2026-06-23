from uuid import uuid4

import pytest


async def create_auth_headers(client):
    email = f"chat-test-{uuid4()}@example.com"
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
async def test_chat_crud(client):
    headers = await create_auth_headers(client)

    create_response = await client.post(
        "/chats",
        json={"title": "Test chat"},
        headers=headers,
    )

    assert create_response.status_code == 201

    created_chat = create_response.json()
    chat_id = created_chat.get("id") or created_chat.get("chat_id")

    assert chat_id is not None

    list_response = await client.get(
        "/chats",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)

    get_response = await client.get(
        f"/chats/{chat_id}",
        headers=headers,
    )

    assert get_response.status_code == 200

    update_response = await client.patch(
        f"/chats/{chat_id}",
        json={"title": "Updated test chat"},
        headers=headers,
    )

    assert update_response.status_code == 200

    delete_response = await client.delete(
        f"/chats/{chat_id}",
        headers=headers,
    )

    assert delete_response.status_code in (200, 204)

    get_deleted_response = await client.get(
        f"/chats/{chat_id}",
        headers=headers,
    )

    assert get_deleted_response.status_code == 404