import asyncio
import os
from datetime import datetime

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere"
)

import httpx
from app import app


async def main():
    email = f"auth_me_{datetime.now().timestamp()}@example.com"
    password = "123456"

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        no_token_response = await client.get("/auth/me")
        print("no_token", no_token_response.status_code, no_token_response.json())

        await client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )

        login_response = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )

        token = login_response.json()["access_token"]

        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        print("with_token", me_response.status_code, me_response.json())


asyncio.run(main())