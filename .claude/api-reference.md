# API Reference — PocketCoder-A1 Dashboard

## Base URL: `http://localhost:7331`

---

## Pages (GET)

### GET /
**Dashboard** — главная страница.
- 6 карточек метрик (Tasks, Session, Tokens, Cost, Duration, Files)
- Кнопки Start/Stop Agent
- Live Log панель (обновляется каждые 2 сек)
- Queue Message форма (видна когда агент работает)

### GET /tasks
**Tasks** — список задач.
- Карточки с приоритетами (#N бейджи)
- Drag-and-drop для переупорядочивания
- Клик на задачу → раскрывается деталь (стадии, критерии, даты)
- Форма добавления задачи (title + description)

### GET /sessions
**Sessions** — история сессий.
- Таблица: номер, статус, файлы, решения, даты

### GET /log
**Activity Log** — хронология действий дашборда (не агента).
- Таймлайн событий: start, stop, add task, error

### GET /settings
**Settings** — конфигурация (read-only).
- Путь проекта, провайдер, порт

### GET /commits
**Git Commits** — история коммитов (если есть .git).
- Хеш, сообщение, автор, дата

### GET /transform
**Transform** — текст → задачи через AI.
- Textarea для свободного текста
- Кнопка "AI Transform"
- Preview с чекбоксами
- Confirm → задачи добавляются

---

## API Endpoints

### GET /api/status
Полный статус системы в JSON.

**Response:**
```json
{
  "running": false,
  "checkpoint": {
    "status": "IDLE",
    "session": 2,
    "current_task": "task_003",
    "files_modified": ["src/health.ts"],
    "decisions": ["Combined tasks 1+2"],
    "session_metrics": {
      "tokens_in": 12400,
      "tokens_out": 3200,
      "cache_read": 8000,
      "cache_creation": 1500,
      "tools_used": 58,
      "session_duration": 166
    }
  },
  "tasks": [...],
  "progress": [3, 3],
  "metrics": {
    "tokens_in": 12400,
    "tokens_out": 3200,
    "cache_read": 8000,
    "cache_creation": 1500,
    "tools_used": 58,
    "session_start": 1771763175.11,
    "session_duration": 166
  }
}
```

**Polling:** Dashboard JS вызывает каждые 3 секунды.

### GET /api/log?since=N
Записи лога агента начиная с индекса N.

**Parameters:**
- `since` (int) — индекс с которого вернуть записи (0 = все)

**Response:**
```json
{
  "entries": [
    {
      "time": "14:23:05",
      "line": "[Read] src/app/api/health/route.ts",
      "type": "read"
    },
    {
      "time": "14:23:08",
      "line": "Creating health endpoint with version field",
      "type": "text"
    }
  ],
  "total": 42
}
```

**type values:** `read`, `edit`, `write`, `bash`, `thinking`, `text`, `metric`, `verify`

**Polling:** Dashboard JS вызывает каждые 2 секунды.

---

### POST /add-task
Добавить задачу.

**Content-Type:** `application/x-www-form-urlencoded`

**Body:**
- `task` (string) — название задачи
- `description` (string, optional) — описание

**Response:** 302 redirect to `/`

**Example:**
```bash
curl -X POST http://localhost:7331/add-task \
  -d "task=Add health endpoint" \
  -d "description=Create /api/health that returns {status: ok}"
```

### POST /add-thought
Добавить сырую мысль (для transform).

**Body:** `thought` (string)
**Response:** 302 redirect to `/`

### POST /start
Запустить агента.

**Response:**
```json
{"status": "started"}
```

Агент запускается в отдельном потоке. Мониторить через `/api/status`.

### POST /stop
Остановить агента.

**Response:**
```json
{"status": "stopped"}
```

Убивает subprocess, сбрасывает `AGENT_RUNNING`.

### POST /queue-message
Отправить сообщение работающему агенту.

**Body:** `message` (string)
**Response:** 302 redirect to `/`

Сообщение сохраняется в `.a1/queue.json`. Агент прочитает его на следующей сессии (inject в prompt).

### POST /api/reorder
Переупорядочить задачи.

**Content-Type:** `application/json`

**Body:**
```json
{"order": ["task_003", "task_001", "task_002"]}
```

**Response:**
```json
{"status": "ok"}
```

Переназначает приоритеты в порядке массива.

### POST /transform
AI разбивка текста на задачи.

**Body:** `text` (string) — свободный текст
**Response:** JSON с предварительными задачами:
```json
{
  "tasks": [
    {"title": "Add login page", "description": "Create /login route..."},
    {"title": "Add auth middleware", "description": "JWT validation..."}
  ]
}
```

### POST /transform-confirm
Подтвердить задачи из transform.

**Content-Type:** `application/json`

**Body:**
```json
{
  "tasks": [
    {"title": "Add login page", "description": "..."}
  ]
}
```

**Response:**
```json
{"status": "ok", "added": 1}
```

---

## Примеры использования

### Полный цикл через API (curl)

```bash
# 1. Проверить здоровье
curl -s http://localhost:7331/api/status | python -m json.tool

# 2. Добавить задачи
curl -X POST http://localhost:7331/add-task \
  -d "task=Write tests" -d "description=pytest for all modules"
curl -X POST http://localhost:7331/add-task \
  -d "task=Create README" -d "description=With usage examples"

# 3. Запустить агента
curl -X POST http://localhost:7331/start

# 4. Мониторить (каждые 15 сек)
while true; do
  STATUS=$(curl -s http://localhost:7331/api/status)
  echo "$STATUS" | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'Running: {d[\"running\"]}, Progress: {d[\"progress\"]}')
"
  RUNNING=$(echo "$STATUS" | python -c "import json,sys; print(json.load(sys.stdin)['running'])")
  [ "$RUNNING" = "False" ] && break
  sleep 15
done

# 5. Результат
curl -s http://localhost:7331/api/status | python -m json.tool
```

### Мониторинг через Python

```python
import requests, time

base = "http://localhost:7331"

# Start agent
requests.post(f"{base}/start")

# Monitor
while True:
    status = requests.get(f"{base}/api/status").json()
    log = requests.get(f"{base}/api/log?since=0").json()

    done, total = status["progress"]
    print(f"Progress: {done}/{total}, Logs: {log['total']}")

    if not status["running"]:
        print("Agent finished!")
        break
    time.sleep(10)
```
