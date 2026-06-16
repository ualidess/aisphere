import os

import httpx
from dotenv import load_dotenv
from auth import router as auth_router
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты полезный голосовой ассистент. Отвечай кратко, ясно и по существу.",
)

app = FastAPI(title="AI Sphere Avatar API")

app.include_router(auth_router)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str


@app.get("/")
async def healthcheck():
    return {"status": "ok", "message": "API is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured",
        )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.message},
        ],
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

        return ChatResponse(answer=answer)

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail="OpenAI API returned an error",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="OpenAI API is unavailable",
        )

    except (KeyError, IndexError):
        raise HTTPException(
            status_code=502,
            detail="Unexpected OpenAI API response format",
        )