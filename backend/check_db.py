import asyncio
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services import ChatService, MessageService, UserService


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv("ALEMBIC_DATABASE_URL")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def main():
    email = f"test_{datetime.now().timestamp()}@example.com"

    async with AsyncSessionLocal() as session:
        user = await UserService.create_user(
            session=session,
            email=email,
            password_hash="fake_hash",
        )

    async with AsyncSessionLocal() as session:
        chat = await ChatService.create_chat(
            session=session,
            user_id=user.id,
            title="Test chat",
        )

    async with AsyncSessionLocal() as session:
        await MessageService.create_message(
            session=session,
            chat_id=chat.id,
            role="user",
            content="Hello",
        )
        await MessageService.create_message(
            session=session,
            chat_id=chat.id,
            role="assistant",
            content="Hi",
        )

    async with AsyncSessionLocal() as session:
        messages = await MessageService.list_chat_messages(
            session=session,
            chat_id=chat.id,
        )

    print(f"user_id={user.id}")
    print(f"chat_id={chat.id}")
    print(f"messages_count={len(messages)}")

    await engine.dispose()


asyncio.run(main())