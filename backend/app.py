import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth import router as auth_router
from chats import router as chats_router
from cleanup import cleanup_expired_chats_loop
from database import get_db
from dependencies import get_current_user
from models import User
from repositories import ChatRepository, MessageRepository
from services import ChatService, MessageService


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты полезный голосовой ассистент. Отвечай кратко, ясно и по существу.",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(cleanup_expired_chats_loop())

    try:
        yield
    finally:
        cleanup_task.cancel()

        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="AI Sphere Avatar API",
    lifespan=lifespan,
)


app.include_router(auth_router)
app.include_router(chats_router)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    chat_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    chat_id: int


@app.get("/")
async def healthcheck():
    return {"status": "ok", "message": "API is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured",
        )

    if request.chat_id is None:
        chat_title = request.message[:60]

        chat_record = await ChatService.create_chat(
            session=session,
            user_id=current_user.id,
            title=chat_title,
        )
    else:
        chat_record = await ChatRepository.get_by_id(
            session=session,
            chat_id=request.chat_id,
        )

        if chat_record is None or chat_record.user_id != current_user.id:
            raise HTTPException(
                status_code=404,
                detail="Chat not found",
            )

    await MessageService.create_message(
        session=session,
        chat_id=chat_record.id,
        role="user",
        content=request.message,
    )

    history = await MessageRepository.list_by_chat_id(
        session=session,
        chat_id=chat_record.id,
    )

    openai_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    for message in history[-20:]:
        openai_messages.append(
            {
                "role": message.role,
                "content": message.content,
            }
        )

    payload = {
        "model": OPENAI_MODEL,
        "messages": openai_messages,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI request failed: {exc}",
        ) from exc

    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Unexpected OpenAI API response format",
        ) from exc

    await MessageService.create_message(
        session=session,
        chat_id=chat_record.id,
        role="assistant",
        content=answer,
    )

    return ChatResponse(
        answer=answer,
        chat_id=chat_record.id,
    )
