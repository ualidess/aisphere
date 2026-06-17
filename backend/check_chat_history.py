import asyncio
import os
from datetime import datetime

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere"
)

import httpx
from app import app


async def main():
    email = f"history_{datetime.now().timestamp()}@example.com"
    password = "123456"

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        no_token = await client.post("/chat", json={"message": "Hello"})
        print("no_token_chat", no_token.status_code, no_token.json())

        await client.post("/auth/register", json={"email": email, "password": password})

        login = await client.post("/auth/login", json={"email": email, "password": password})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        first = await client.post(
            "/chat",
            headers=headers,
            json={"message": "Say only: test answer"},
        )
        print("first_chat", first.status_code, first.json())

        chat_id = first.json()["chat_id"]

        messages = await client.get(
            f"/chats/{chat_id}/messages",
            headers=headers,
        )
        print("messages", messages.status_code, messages.json())


asyncio.run(main())