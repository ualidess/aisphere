import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from auth import router as auth_router
from chats import router as chats_router
from cleanup import cleanup_expired_chats_loop
from database import get_db
from dependencies import get_current_user
from logging_config import request_id_ctx_var, setup_logging
from models import User
from rate_limit import check_rate_limit
from repositories import ChatRepository, MessageRepository
from services import ChatService, MessageService


load_dotenv()
setup_logging()

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


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx_var.set(request_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_finished",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
    finally:
        request_id_ctx_var.reset(token)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "http_exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "error": str(exc.detail),
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
                "request_id": request_id_ctx_var.get(),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "validation_error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
            "error": "Invalid request data",
        },
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Invalid request data",
                "request_id": request_id_ctx_var.get(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled_exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "error": type(exc).__name__,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "request_id": request_id_ctx_var.get(),
            }
        },
    )



class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    chat_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    chat_id: int


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@app.get("/")
async def root():
    return {"status": "ok", "message": "API is running"}

@app.get("/health")
async def healthcheck(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database healthcheck failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "database": "ok",
    }

@app.post("/stt")
async def stt(
    request: Request,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    await check_rate_limit(
        request=request,
        endpoint="stt",
        limit=10,
        window_seconds=60,
        user_id=current_user.id,
    )
    if not ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key is not configured",
        )

    audio_bytes = await audio.read()


    try:
        external_start = time.perf_counter()

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

            external_duration_ms = round((time.perf_counter() - external_start) * 1000, 2)
            logger.info(
                "external_api_finished",
                extra={
                    "external_api": "elevenlabs_stt",
                    "status_code": response.status_code,
                    "duration_ms": external_duration_ms,
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
    request_data: TTSRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    await check_rate_limit(
        request=request,
        endpoint="tts",
        limit=20,
        window_seconds=60,
        user_id=current_user.id,
    )

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
        external_start = time.perf_counter()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
                params={"output_format": ELEVENLABS_OUTPUT_FORMAT},
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "text": request_data.text,
                    "model_id": ELEVENLABS_TTS_MODEL,
                },
            )
            external_duration_ms = round((time.perf_counter() - external_start) * 1000, 2)
            logger.info(
                "external_api_finished",
                extra={
                    "external_api": "elevenlabs_tts",
                    "status_code": response.status_code,
                    "duration_ms": external_duration_ms,
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
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await check_rate_limit(
        request=http_request,
        endpoint="chat",
        limit=30,
        window_seconds=60,
        user_id=current_user.id,
    )

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
        external_start = time.perf_counter()

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        external_duration_ms = round((time.perf_counter() - external_start) * 1000, 2)
        logger.info(
            "external_api_finished",
            extra={
                "external_api": "openai_chat",
                "status_code": response.status_code,
                "duration_ms": external_duration_ms,
            },
        )

        if response.status_code >= 400:
            logger.error("OpenAI Chat error: %s", response.text)

        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

    except httpx.HTTPStatusError as exc:
        logger.exception("OpenAI Chat request failed")
        raise HTTPException(
            status_code=exc.response.status_code,
            detail="OpenAI request failed",
        ) from exc

    except httpx.RequestError as exc:
        logger.exception("OpenAI Chat connection failed")
        raise HTTPException(
            status_code=502,
            detail="OpenAI request failed",
        ) from exc

    except (KeyError, IndexError) as exc:
        logger.exception("Unexpected OpenAI API response format")
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
