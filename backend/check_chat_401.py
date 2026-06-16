import asyncio

import httpx
from app import app


async def main():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"message": "hello"},
        )

        print(response.status_code, response.json())


asyncio.run(main())