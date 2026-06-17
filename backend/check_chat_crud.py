import asyncio
import os
from datetime import datetime

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere"
)

import httpx
from app import app


async def main():
    email = f"crud_{datetime.now().timestamp()}@example.com"
    password = "123456"

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/auth/register", json={"email": email, "password": password})

        login = await client.post("/auth/login", json={"email": email, "password": password})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/chats",
            headers=headers,
            json={"title": "Old title"},
        )
        print("create_chat", created.status_code, created.json())

        chat_id = created.json()["id"]

        get_empty = await client.get(
            f"/chats/{chat_id}",
            headers=headers,
        )
        print("get_chat_empty", get_empty.status_code, get_empty.json())

        renamed = await client.patch(
            f"/chats/{chat_id}",
            headers=headers,
            json={"title": "New title"},
        )
        print("rename_chat", renamed.status_code, renamed.json())

        message = await client.post(
            f"/chats/{chat_id}/messages",
            headers=headers,
            json={"role": "user", "content": "hello from crud test"},
        )
        print("create_message", message.status_code, message.json())

        get_with_message = await client.get(
            f"/chats/{chat_id}",
            headers=headers,
        )
        print("get_chat_with_message", get_with_message.status_code, get_with_message.json())

        deleted = await client.delete(
            f"/chats/{chat_id}",
            headers=headers,
        )
        print("delete_chat", deleted.status_code)

        get_after_delete = await client.get(
            f"/chats/{chat_id}",
            headers=headers,
        )
        print("get_after_delete", get_after_delete.status_code, get_after_delete.json())


asyncio.run(main())