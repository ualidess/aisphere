from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import User
from repositories import ChatRepository, MessageRepository
from schemas import ChatCreateRequest, ChatOut, MessageCreateRequest, MessageOut
from services import ChatService, MessageService


router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ChatCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    chat = await ChatService.create_chat(
        session=session,
        user_id=current_user.id,
        title=payload.title,
    )

    return ChatOut(
        id=chat.id,
        user_id=chat.user_id,
        title=chat.title,
    )


@router.get("", response_model=list[ChatOut])
async def list_chats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    chats = await ChatService.list_user_chats(
        session=session,
        user_id=current_user.id,
    )

    return [
        ChatOut(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
        )
        for chat in chats
    ]


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    chat = await ChatRepository.get_by_id(
        session=session,
        chat_id=chat_id,
    )

    if chat is None or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    messages = await MessageRepository.list_by_chat_id(
        session=session,
        chat_id=chat_id,
    )

    return [
        MessageOut(
            id=message.id,
            chat_id=message.chat_id,
            role=message.role,
            content=message.content,
        )
        for message in messages
    ]


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def create_message(
    chat_id: int,
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    chat = await ChatRepository.get_by_id(
        session=session,
        chat_id=chat_id,
    )

    if chat is None or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    message = await MessageService.create_message(
        session=session,
        chat_id=chat_id,
        role=payload.role,
        content=payload.content,
    )

    return MessageOut(
        id=message.id,
        chat_id=message.chat_id,
        role=message.role,
        content=message.content,
    )