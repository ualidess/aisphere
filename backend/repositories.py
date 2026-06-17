from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chat, Message, User


class UserRepository:
    @staticmethod
    async def create(session: AsyncSession, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


class ChatRepository:
    @staticmethod
    async def create(session: AsyncSession, user_id: int, title: str = "New chat") -> Chat:
        chat = Chat(user_id=user_id, title=title)
        session.add(chat)
        await session.flush()
        await session.refresh(chat)
        return chat

    @staticmethod
    async def get_by_id(session: AsyncSession, chat_id: int) -> Chat | None:
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user_id(session: AsyncSession, user_id: int) -> list[Chat]:
        result = await session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_title(
        session: AsyncSession,
        chat: Chat,
        title: str,
    ) -> Chat:
        chat.title = title
        chat.updated_at = datetime.now(timezone.utc)

        await session.flush()
        await session.refresh(chat)
        return chat

    @staticmethod
    async def delete(
        session: AsyncSession,
        chat: Chat,
    ) -> None:
        await session.delete(chat)
        await session.flush()



class MessageRepository:
    @staticmethod
    async def create(
        session: AsyncSession,
        chat_id: int,
        role: str,
        content: str,
    ) -> Message:
        message = Message(chat_id=chat_id, role=role, content=content)
        session.add(message)

        chat = await ChatRepository.get_by_id(
            session=session,
            chat_id=chat_id,
        )

        if chat is not None:
            chat.updated_at = datetime.now(timezone.utc)

        await session.flush()
        await session.refresh(message)
        return message


    @staticmethod
    async def list_by_chat_id(session: AsyncSession, chat_id: int) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())