# AI Sphere Avatar

Голосовой AI-ассистент с анимированной 3D-сферой. Пользователь задаёт вопрос голосом или текстом, сфера реагирует на состояние приложения, AI отвечает, а ответ озвучивается голосом.

Под капотом: фронтенд на чистом JavaScript + [Three.js](https://threejs.org/), backend на FastAPI/Uvicorn, база данных PostgreSQL, OpenAI Chat Completions для ответов и ElevenLabs для распознавания и озвучивания речи. Всё разворачивается через Docker Compose за обратным прокси Nginx.

## Как это работает

```text
Браузер (Three.js сфера + UI + микрофон)
   │  /api/*  (Nginx проксирует на backend)
   ▼
FastAPI backend
   ├── Auth / JWT
   ├── Chat history CRUD
   ├── POST /chat  → OpenAI Chat Completions
   ├── POST /stt   → ElevenLabs Speech-to-Text
   ├── POST /tts   → ElevenLabs Text-to-Speech
   └── PostgreSQL
```

Полный голосовой цикл:

1. Пользователь записывает голосовой вопрос.
2. Frontend отправляет аудио на `/api/stt`.
3. Backend отправляет аудио в ElevenLabs Speech-to-Text.
4. Полученный текст отправляется на `/api/chat`.
5. Backend сохраняет сообщение пользователя в PostgreSQL.
6. Backend отправляет сообщение и контекст чата в OpenAI Chat Completions.
7. Ответ AI сохраняется в историю чата.
8. Frontend отправляет ответ на `/api/tts`.
9. Backend получает аудио от ElevenLabs Text-to-Speech.
10. Frontend воспроизводит голосовой ответ.

## Структура проекта

```text
aisphere/
├── backend/
│   ├── app.py              # FastAPI API: /chat, /stt, /tts, /health
│   ├── auth.py             # регистрация, логин, JWT
│   ├── chats.py            # CRUD чатов
│   ├── database.py         # подключение к PostgreSQL
│   ├── models.py           # SQLAlchemy модели
│   ├── repositories.py     # работа с базой данных
│   ├── services.py         # бизнес-логика
│   ├── rate_limit.py       # rate limiting
│   ├── logging_config.py   # JSON-логи и request_id
│   ├── tests/              # pytest тесты
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html          # UI
│   ├── script.js           # Three.js, запись голоса, запросы к API
│   └── styles.css          # стили
├── nginx/
│   └── nginx.conf          # frontend + proxy /api/*
├── alembic/                # миграции базы данных
├── docker-compose.yml
├── pytest.ini
├── .env.example
└── README.md
```

## Требования

* Docker Desktop
* Docker Compose
* Git
* OpenAI API key
* ElevenLabs API key

Для локального запуска тестов нужен Python и зависимости из `backend/requirements.txt`.

## Настройка и запуск

### 1. Переменные окружения

Создайте файл `.env` в корне проекта на основе `.env.example`.

Пример:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
SYSTEM_PROMPT=

ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_TTS_MODEL=eleven_multilingual_v2
ELEVENLABS_STT_MODEL=scribe_v1
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128

POSTGRES_DB=aisphere
POSTGRES_USER=aisphere
POSTGRES_PASSWORD=aisphere_password

DATABASE_URL=postgresql+asyncpg://aisphere:aisphere_password@db:5432/aisphere

JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

ALLOWED_ORIGINS=http://localhost:8078,http://127.0.0.1:8078
MAX_AUDIO_UPLOAD_BYTES=10485760
```

Файл `.env` нельзя коммитить в Git. В репозитории должен быть только `.env.example` без реальных секретов.

### 2. Docker-сеть

Backend, PostgreSQL и frontend/nginx работают в одной внутренней Docker-сети.

Наружу публикуется только frontend/nginx на порту `8078`. Backend доступен внутри Docker-сети, а API-запросы идут через Nginx по пути `/api/*`.

### 3. Запуск

```bash
docker compose up --build -d
```

Откройте UI в браузере:

```text
http://localhost:8078
```

Проверка backend:

```bash
curl http://localhost:8078/api/health
```

Ожидаемый ответ:

```json
{"status":"ok","database":"ok"}
```

## Остановка

```bash
docker compose down
```

Полный сброс с удалением базы:

```bash
docker compose down -v
docker compose up --build -d
```

## База данных

В проекте используется PostgreSQL.

Backend внутри Docker подключается к базе по адресу:

```text
db:5432
```

При локальных тестах с компьютера используется host-порт:

```text
127.0.0.1:5433
```

Применить миграции:

```bash
cd backend
alembic upgrade head
```

## API backend

| Метод    | Endpoint               | Описание                          |
| -------- | ---------------------- | --------------------------------- |
| `POST`   | `/api/auth/register`   | регистрация пользователя          |
| `POST`   | `/api/auth/login`      | логин и получение JWT             |
| `GET`    | `/api/auth/me`         | текущий пользователь              |
| `GET`    | `/api/chats`           | список чатов                      |
| `POST`   | `/api/chats`           | создать чат                       |
| `GET`    | `/api/chats/{chat_id}` | получить чат                      |
| `PATCH`  | `/api/chats/{chat_id}` | обновить чат                      |
| `DELETE` | `/api/chats/{chat_id}` | удалить чат                       |
| `POST`   | `/api/chat`            | отправить сообщение в AI          |
| `POST`   | `/api/stt`             | распознать голос через ElevenLabs |
| `POST`   | `/api/tts`             | озвучить ответ через ElevenLabs   |
| `GET`    | `/api/health`          | healthcheck backend и базы        |

## Тесты

Установить зависимости:

```bash
cd backend
python -m pip install -r requirements.txt
```

Запустить тесты:

```bash
python -m pytest
```

Тесты покрывают:

* healthcheck
* регистрацию, логин и `/auth/me`
* CRUD чатов
* мок OpenAI для `/chat`
* мок ElevenLabs для `/stt`
* мок ElevenLabs для `/tts`

Внешние API в тестах напрямую не вызываются.

## Безопасность

В проекте есть базовая защита:

* JWT-авторизация
* rate limiting для `/chat`, `/stt`, `/tts`, `/auth/login`
* CORS только для разрешённых origin
* лимит размера запроса в Nginx
* лимит размера аудио на backend
* проверка типа аудиофайла
* security headers в Nginx
* секреты только через переменные окружения
* JSON-логи с `request_id`

Для внешнего доступа нужен HTTPS/TLS. На `localhost` микрофон работает, но для публичного домена браузеру нужен защищённый контекст.

## Стек технологий

* **Frontend:** HTML, CSS, JavaScript, Three.js, WebGL/GLSL, MediaRecorder API
* **Backend:** Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy async, Alembic, httpx
* **Database:** PostgreSQL
* **AI:** OpenAI Chat Completions
* **Voice:** ElevenLabs Speech-to-Text, ElevenLabs Text-to-Speech
* **Infrastructure:** Docker, Docker Compose, Nginx
* **Tests:** pytest, pytest-asyncio, respx, httpx ASGITransport
