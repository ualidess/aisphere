import asyncio
import os
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://aisphere:aisphere_password@127.0.0.1:5433/aisphere"
)

from sqlalchemy import select

from cleanup import delete_expired_chats
from database import AsyncSessionLocal
from models import Chat, Message, User


async def main():
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        user = User(
            email=f"cleanup_{now.timestamp()}@example.com",
            password_hash="fake_hash",
        )
        session.add(user)
        await session.flush()

        old_chat = Chat(
            user_id=user.id,
            title="Old chat",
            updated_at=now - timedelta(hours=73),
        )

        fresh_chat = Chat(
            user_id=user.id,
            title="Fresh chat",
            updated_at=now,
        )

        session.add_all([old_chat, fresh_chat])
        await session.flush()

        old_message = Message(
            chat_id=old_chat.id,
            role="user",
            content="old message",
        )

        fresh_message = Message(
            chat_id=fresh_chat.id,
            role="user",
            content="fresh message",
        )

        session.add_all([old_message, fresh_message])
        await session.commit()

        old_chat_id = old_chat.id
        fresh_chat_id = fresh_chat.id

    deleted_count = await delete_expired_chats(ttl_hours=72)
    print("deleted_count", deleted_count)

    async with AsyncSessionLocal() as session:
        old_chat_result = await session.execute(
            select(Chat).where(Chat.id == old_chat_id)
        )
        fresh_chat_result = await session.execute(
            select(Chat).where(Chat.id == fresh_chat_id)
        )

        old_messages_result = await session.execute(
            select(Message).where(Message.chat_id == old_chat_id)
        )
        fresh_messages_result = await session.execute(
            select(Message).where(Message.chat_id == fresh_chat_id)
        )

        print("old_chat_exists", old_chat_result.scalar_one_or_none() is not None)
        print("fresh_chat_exists", fresh_chat_result.scalar_one_or_none() is not None)
        print("old_messages_count", len(list(old_messages_result.scalars().all())))
        print("fresh_messages_count", len(list(fresh_messages_result.scalars().all())))


asyncio.run(main())