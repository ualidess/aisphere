# AI Sphere Avatar

Голосовой AI-ассистент с анимированной 3D-сферой. Пользователь задаёт вопрос голосом, сфера реагирует анимацией на каждое состояние (запись / размышление / ответ), а ответ озвучивается голосом.

Под капотом: фронтенд на чистом JavaScript + [Three.js](https://threejs.org/) (сфера на GLSL-шейдерах с шумом Симплекса), бэкенд на Flask, который связывает вместе OpenAI Whisper (распознавание речи), внешний чат-API и OpenAI TTS (синтез речи). Всё разворачивается через Docker Compose за обратным прокси Nginx.

## Как это работает

```
Браузер (Three.js сфера + запись с микрофона)
   │  /api/*  (Nginx проксирует на бэкенд)
   ▼
Flask backend (app.py)
   ├── POST /stt   → OpenAI Whisper          (аудио → текст)
   ├── POST /chat  → внешний policy_router_api (текст → ответ)
   └── POST /tts   → OpenAI TTS (tts-1, alloy) (текст → аудио)
```

Полный цикл одного вопроса (см. `sendBtn.onclick` в [frontend/script.js](frontend/script.js)):

1. Пользователь нажимает **«Задать вопрос»** — начинается запись с микрофона (автостоп через 5 секунд или по кнопке **«Закончить»**).
2. Аудио (`.webm`) отправляется на `/stt`, бэкенд распознаёт речь через Whisper и возвращает текст.
3. Текст отправляется на `/chat`, бэкенд проксирует его во внешний API (`policy_router_api`) и достаёт поле `bot_response`.
4. Ответ отправляется на `/tts`, бэкенд синтезирует речь (mp3) и возвращает аудио, которое воспроизводится в браузере.

Сфера меняет цвет, интенсивность деформации и скорость анимации в зависимости от состояния (`idle`, `recording`, `thinking`, `speaking`).

## Структура проекта

```
ai_sphere_avatar/
├── backend/
│   ├── app.py            # Flask API: /stt, /chat, /tts
│   ├── Dockerfile        # Python 3.9 + Gunicorn (4 воркера, порт 5000)
│   └── requirements.txt
├── frontend/
│   ├── index.html        # UI + стили
│   └── script.js         # Three.js сцена, шейдеры, логика записи/состояний
├── nginx/
│   └── nginx.conf        # Отдаёт фронтенд, проксирует /api/ на бэкенд
├── docker-compose.yml
└── .env                  # OPENAI_API_KEY (не коммитить)
```

## Требования

- Docker и Docker Compose
- Ключ OpenAI API (используется для Whisper STT и TTS)
- Запущенный внешний чат-API `policy_router_api`, доступный во внешней Docker-сети (см. ниже)

## Настройка и запуск

### 1. Переменные окружения

Создайте файл `.env` в корне проекта:

```env
OPENAI_API_KEY=
```

### 2. Внешняя Docker-сеть

Бэкенд подключается к двум сетям: внутренней (`avatar_front_net`) для связи с фронтендом и внешней (`existing_api_network`) для связи с чат-API. Имя внешней сети задаётся в [docker-compose.yml](docker-compose.yml):

```yaml
existing_api_network:
  external: true
  name: avatar_default   # ← замените на имя сети вашего API
```

Узнать имя сети можно командой `docker network ls`. Сеть должна существовать до запуска (её создаёт проект с `policy_router_api`).

### 3. Запуск

```bash
docker compose up --build
```

Откройте UI в браузере: **http://localhost:8078**

## Конфигурация

Параметры внешнего чат-API заданы прямо в коде ([backend/app.py](backend/app.py)):

```python
NEW_API_URL = "http://policy_router_api:8079/chat"
NEW_API_KEY = 
```

При смене адреса/ключа внешнего API обновите эти значения.

## API бэкенда

| Метод  | Endpoint | Тело запроса                       | Ответ                          |
|--------|----------|------------------------------------|--------------------------------|
| `GET`  | `/`      | —                                  | `{"status": "ok"}` (healthcheck) |
| `POST` | `/stt`   | `multipart/form-data` поле `audio` | `{"text": "..."}`              |
| `POST` | `/chat`  | `{"question": "..."}`              | `{"answer": "..."}`            |
| `POST` | `/tts`   | `{"text": "..."}`                  | `audio/mpeg` (mp3)             |

## Стек технологий

- **Фронтенд:** HTML, CSS, ванильный JS, Three.js 0.150, WebGL/GLSL-шейдеры, MediaRecorder API
- **Бэкенд:** Python 3.9, Flask, Flask-CORS, Gunicorn, OpenAI SDK (Whisper `whisper-1`, TTS `tts-1`)
- **Инфраструктура:** Docker, Docker Compose, Nginx (alpine)

## Примечания

- В репозитории присутствуют файлы `.env` с ключами — не коммитьте реальные секреты в публичный репозиторий.
- Максимальная длительность записи вопроса — 5 секунд (автостоп в `script.js`).
- Для работы микрофона браузеру нужен защищённый контекст (`localhost` подходит; для внешнего доступа потребуется HTTPS).
