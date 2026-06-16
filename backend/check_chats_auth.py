import asyncio
import os
from datetime import datetime

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere"
)

import httpx
from app import app


async def register_and_login(client, email, password):
    await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    return login_response.json()["access_token"]


async def main():
    stamp = datetime.now().timestamp()

    user1_email = f"user1_{stamp}@example.com"
    user2_email = f"user2_{stamp}@example.com"
    password = "123456"

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        no_token_chats = await client.get("/chats")
        print("no_token_chats", no_token_chats.status_code, no_token_chats.json())

        user1_token = await register_and_login(client, user1_email, password)
        user2_token = await register_and_login(client, user2_email, password)

        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        create_chat_response = await client.post(
            "/chats",
            headers=user1_headers,
            json={"title": "User 1 private chat"},
        )
        print("create_chat_user1", create_chat_response.status_code, create_chat_response.json())

        chat_id = create_chat_response.json()["id"]

        user1_chats = await client.get("/chats", headers=user1_headers)
        print("user1_chats", user1_chats.status_code, user1_chats.json())

        user2_chats = await client.get("/chats", headers=user2_headers)
        print("user2_chats", user2_chats.status_code, user2_chats.json())

        user2_try_messages = await client.get(
            f"/chats/{chat_id}/messages",
            headers=user2_headers,
        )
        print("user2_try_user1_chat", user2_try_messages.status_code, user2_try_messages.json())


asyncio.run(main())