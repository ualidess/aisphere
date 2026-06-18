import asyncio
import os
import logging
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
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

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVENLABS_TTS_MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
ELEVENLABS_STT_MODEL = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v1")
ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")

logger = logging.getLogger(__name__)


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


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@app.get("/")
async def healthcheck():
    return {"status": "ok", "message": "API is running"}

@app.post("/stt")
async def stt(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key is not configured",
        )

    audio_bytes = await audio.read()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                data={"model_id": ELEVENLABS_STT_MODEL},
                files={
                    "file": (
                        audio.filename or "audio.webm",
                        audio_bytes,
                        audio.content_type or "audio/webm",
                    )
                },
            )
            if response.status_code >= 400:
                logger.error("ElevenLabs STT error: %s", response.text)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("ElevenLabs STT request failed")
        raise HTTPException(
            status_code=502,
            detail="Speech recognition failed. Please try again.",
        ) from exc

    data = response.json()
    text = data.get("text", "")

    if not text:
        raise HTTPException(
            status_code=502,
            detail="Speech recognition returned empty text",
        )

    return {"text": text}



@app.post("/tts")
async def tts(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key is not configured",
        )

    if not ELEVENLABS_VOICE_ID:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs voice ID is not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
                params={"output_format": ELEVENLABS_OUTPUT_FORMAT},
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "text": request.text,
                    "model_id": ELEVENLABS_TTS_MODEL,
                },
            )
            if response.status_code >= 400:
                logger.error("ElevenLabs TTS error: %s", response.text)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("ElevenLabs TTS request failed")
        raise HTTPException(
            status_code=502,
            detail="Text-to-speech failed. Please try again.",
        ) from exc

    return Response(content=response.content, media_type="audio/mpeg")

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
