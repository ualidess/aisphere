import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import AsyncSessionLocal
from models import Chat


CHAT_TTL_HOURS = 72
CLEANUP_INTERVAL_SECONDS = 60 * 60


async def delete_expired_chats(ttl_hours: int = CHAT_TTL_HOURS) -> int:
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chat).where(Chat.updated_at < cutoff_time)
        )
        expired_chats = list(result.scalars().all())

        for chat in expired_chats:
            await session.delete(chat)

        await session.commit()

        return len(expired_chats)


async def cleanup_expired_chats_loop() -> None:
    while True:
        try:
            deleted_count = await delete_expired_chats()

            if deleted_count:
                print(f"Deleted expired chats: {deleted_count}")

        except Exception as exc:
            print(f"Chat cleanup failed: {exc}")

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)