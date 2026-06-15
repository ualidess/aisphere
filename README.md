# AI Sphere Avatar

Голосовой AI-ассистент с анимированной 3D-сферой. Пользователь задаёт вопрос голосом, сфера реагирует анимацией на каждое состояние (запись / размышление / ответ), а ответ озвучивается голосом.

Под капотом: фронтенд на чистом JavaScript + [Three.js](https://threejs.org/) (сфера на GLSL-шейдерах с шумом Симплекса), бэкенд на FastAPI/Uvicorn с endpoint `/chat`, который напрямую обращается к OpenAI Chat Completions. Всё разворачивается через Docker Compose за обратным прокси Nginx.

## Как это работает

```
Браузер (Three.js сфера + запись с микрофона)
   │  /api/*  (Nginx проксирует на бэкенд)
   ▼
FastAPI backend (app.py)
   ├── GET  /      → healthcheck
   └── POST /chat  → OpenAI Chat Completions напрямую (текст → ответ)
```

Полный цикл текстового запроса в текущей версии:

1. Frontend отправляет текстовый запрос на `/api/chat`.
2. Nginx проксирует запрос в FastAPI backend.
3. Backend отправляет сообщение напрямую в OpenAI Chat Completions.
4. Ответ возвращается в формате `{"answer": "..."}`.

Голосовые функции `/stt` и `/tts` в текущей фазе не используются. Они будут добавлены позже через ElevenLabs.


## Структура проекта

```
ai_sphere_avatar/
├── backend/
│   ├── app.py            # FastAPI API: /, /chat
│   ├── Dockerfile        # Python 3.11 + Uvicorn, порт 8000
│   └── requirements.txt
├── frontend/
│   ├── index.html        # UI + стили
│   └── script.js         # Three.js сцена, шейдеры, логика записи/состояний
├── nginx/
│   └── nginx.conf        # Отдаёт фронтенд, проксирует /api/ на бэкенд
├── docker-compose.yml
└── .env.example          # пример переменных окружения, без секретов


## Требования

- Docker и Docker Compose
- Ключ OpenAI API для обращения к OpenAI Chat Completions

## Настройка и запуск

### 1. Переменные окружения

Создайте файл `.env` в корне проекта:

```env
OPENAI_API_KEY=
```

### 2. Docker-сеть

Backend и frontend работают в одной внутренней Docker-сети `avatar_front_net`.

Внешняя Docker-сеть больше не используется, так как endpoint `/chat` теперь обращается напрямую к OpenAI Chat Completions.

```yaml
networks:
  avatar_front_net:
    driver: bridge
```

В `docker-compose.yml` наружу публикуется только frontend/nginx на порту `8078`, а backend доступен только внутри Docker-сети по имени сервиса `avatar_front_backend`.


### 3. Запуск

```bash
docker compose up --build
```

Откройте UI в браузере: **http://localhost:8078**

## Конфигурация

Параметры backend задаются через переменные окружения:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
SYSTEM_PROMPT=
```

`OPENAI_API_KEY` нужен для прямого обращения к OpenAI Chat Completions.
`OPENAI_MODEL` задаёт модель, по умолчанию используется `gpt-4o-mini`.
`SYSTEM_PROMPT` задаёт системную инструкцию для ассистента.


## API бэкенда

| Метод  | Endpoint | Тело запроса                       | Ответ                          |
|--------|----------|------------------------------------|--------------------------------|
| `GET`  | `/`      | —                                  | `{"status": "ok"}` (healthcheck) |
| `POST` | `/chat`  | `{"message": "..."}`              | `{"answer": "..."}`            |


## Стек технологий

* **Фронтенд:** HTML, CSS, ванильный JS, Three.js 0.150, WebGL/GLSL-шейдеры, MediaRecorder API
* **Бэкенд:** Python 3.11, FastAPI, Uvicorn, Pydantic, httpx, python-dotenv
* **LLM:** OpenAI Chat Completions API, модель задаётся через `OPENAI_MODEL`
* **Инфраструктура:** Docker, Docker Compose, Nginx (alpine)

## Примечания

- В репозитории присутствуют файлы `.env` с ключами — не коммитьте реальные секреты в публичный репозиторий.
- Максимальная длительность записи вопроса — 5 секунд (автостоп в `script.js`).
- Для работы микрофона браузеру нужен защищённый контекст (`localhost` подходит; для внешнего доступа потребуется HTTPS).
