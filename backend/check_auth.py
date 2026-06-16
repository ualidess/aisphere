import asyncio
import os
from datetime import datetime

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere"
)

import httpx
from app import app


async def main():
    email = f"auth_test_{datetime.now().timestamp()}@example.com"
    password = "123456"

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        register_response = await client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

        print("register", register_response.status_code, register_response.json())

        login_response = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        print("login", login_response.status_code, login_response.json())


asyncio.run(main())