from sqlalchemy.ext.asyncio import AsyncSession

from models import Chat, Message, User
from repositories import ChatRepository, MessageRepository, UserRepository


class UserService:
    @staticmethod
    async def create_user(
        session: AsyncSession,
        email: str,
        password_hash: str, 
    ) -> User:
        user = await UserRepository.create(
            session=session,
            email=email,
            password_hash=password_hash,
        )
        await session.commit()
        return user


class ChatService:
    @staticmethod
    async def create_chat(
        session: AsyncSession,
        user_id: int,
        title: str = "New chat",
    ) -> Chat:
        chat = await ChatRepository.create(
            session=session,
            user_id=user_id,
            title=title,
        )
        await session.commit()
        return chat

    @staticmethod
    async def list_user_chats(
        session: AsyncSession,
        user_id: int,
    ) -> list[Chat]:
        return await ChatRepository.list_by_user_id(
            session=session,
            user_id=user_id,
        )
    
    @staticmethod
    async def rename_chat(
        session: AsyncSession,
        chat: Chat,
        title: str,
    ) -> Chat:
        updated_chat = await ChatRepository.update_title(
            session=session,
            chat=chat,
            title=title,
        )
        await session.commit()
        return updated_chat

    @staticmethod
    async def delete_chat(
        session: AsyncSession,
        chat: Chat,
    ) -> None:
        await ChatRepository.delete(
            session=session,
            chat=chat,
        )
        await session.commit()



class MessageService:
    @staticmethod
    async def create_message(
        session: AsyncSession,
        chat_id: int,
        role: str,
        content: str,
    ) -> Message:
        message = await MessageRepository.create(
            session=session,
            chat_id=chat_id,
            role=role,
            content=content,
        )
        await session.commit()
        return message

    @staticmethod
    async def list_chat_messages(
        session: AsyncSession,
        chat_id: int,
    ) -> list[Message]:
        return await MessageRepository.list_by_chat_id(
            session=session,
            chat_id=chat_id,
        )