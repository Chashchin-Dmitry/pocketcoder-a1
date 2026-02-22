# Module Reference — PocketCoder-A1

## Карта модулей (кто кого вызывает)

```
Пользователь
  │
  ├── CLI (pca) ─────────────────┐
  │   a1/cli.py (289 строк)     │
  │                              │
  └── Dashboard (:7331) ────────┐│
      a1/dashboard.py (2038)    ││
                                ││
        ┌───────────────────────┘│
        │                       │
        ▼                       ▼
   TaskManager            SessionLoop
   a1/tasks.py (211)      a1/loop.py (744)
        │                       │
        │              ┌────────┼────────┐
        │              │        │        │
        │         Validator  Checkpoint  Claude CLI
        │         (361)      (146)       (subprocess)
        │              │        │            │
        └──────────────┴────────┘      stream-json
                  .a1/                  (NDJSON)
           (tasks.json,                     │
            checkpoint.json)           _log_callback
                                           │
                                     AGENT_LOG_BUFFER
                                           │
                                      /api/log → JS
```

---

## a1/loop.py — SessionLoop (744 строк)

**Роль**: Мозг системы. Запускает Claude, парсит вывод, верифицирует, управляет метриками.

### Публичные методы

| Метод | Сигнатура | Что |
|-------|-----------|-----|
| `__init__` | `(project_dir, provider="claude-max", max_sessions=100, session_delay=5)` | Инициализация: загрузка checkpoint, tasks, validator |
| `start()` | `→ None` | Главный цикл: baseline → [build_prompt → subprocess → verify]* |
| `stop()` | `→ None` | Убить процесс, _running = False |
| `build_prompt()` | `→ str` | Собрать промпт из checkpoint + tasks + queue |
| `get_session_metrics()` | `→ dict` | Текущие метрики: tokens, tools, duration |

### Приватные методы

| Метод | Что |
|-------|-----|
| `_run_claude_max(prompt)` | Subprocess: claude -p --stream-json |
| `_parse_stream_event(line)` | JSON → тип события (tool_use/text/result/rate_limit) |
| `_update_metrics(event)` | rate_limit_event → _session_metrics |
| `_capture_baseline()` | Снимок валидации ДО работы |
| `_verify_session()` | 3-tier верификация ПОСЛЕ работы |
| `_is_new_issue(check, report)` | Сравнение с baseline |
| `_get_verification_prompt()` | Ошибки → текст для следующего промпта |
| `_read_queue_messages()` | Прочитать .a1/queue.json |
| `_log_callback(text, type)` | Колбэк для отправки в дашборд |

### Атрибуты

| Атрибут | Тип | Что |
|---------|-----|-----|
| `_running` | bool | Флаг работы |
| `_current_process` | Popen | Текущий subprocess |
| `_log_callback` | callable | Колбэк для live log |
| `_session_metrics` | dict | Накопительные метрики сессии |
| `_last_verification` | dict | Результат последней верификации |
| `_context_percent` | float | Процент использования контекста (0.0-1.0) |

### Константы

| Константа | Значение | Зачем |
|-----------|----------|-------|
| `CONTEXT_WINDOW_SIZE` | 200,000 | Размер окна Claude в токенах |
| `CONTEXT_THRESHOLD` | 0.70 | Авто-checkpoint при 70% |
| `MAX_VERIFY_RETRIES` | 3 | Лимит ретраев верификации |
| `BLOCKING_CHECKS` | {syntax, tests} | Что блокирует |
| `WARNING_CHECKS` | {lint, build, git} | Что только предупреждает |

---

## a1/dashboard.py — Web UI (2038 строк)

**Роль**: Полноценный веб-дашборд. HTTP-сервер на stdlib без фреймворков.

### Глобальные переменные

| Переменная | Тип | Что |
|-----------|-----|-----|
| `PROJECT_DIR` | Path | Путь к проекту |
| `AGENT_RUNNING` | bool | Агент работает? |
| `AGENT_LOOP` | SessionLoop | Ссылка на цикл (для stop) |
| `ACTIVITY_LOG` | list | Лог действий дашборда (max 100) |
| `AGENT_LOG_BUFFER` | list | Лог агента для live-панели (max 500) |

### Функции

| Функция | Что |
|---------|-----|
| `run_dashboard(project_dir, port, no_browser)` | Запуск HTTP-сервера |
| `esc(text)` | HTML escape для XSS защиты |
| `log_activity(action, details, status)` | Добавить в ACTIVITY_LOG |
| `_classify_line(line)` | Эвристическая классификация строки → тип иконки |
| `_on_agent_line(line, event_type)` | Парсинг + добавление в AGENT_LOG_BUFFER |

### DashboardHandler (HTTPRequestHandler)

Обрабатывает GET/POST запросы. Маршрутизация через `do_GET()` и `do_POST()`.

### JavaScript функции (встроены в HTML)

| Функция | Что |
|---------|-----|
| `updateStatus()` | AJAX: /api/status → обновление карточек (3s) |
| `updateLog()` | AJAX: /api/log → обновление лог-панели (2s) |
| `tickTimer()` | Обновление карточки Duration (1s) |
| `fmtTokens(n)` | Форматирование: 12400 → "12.4K" |
| `fmtDuration(s)` | Форматирование: 166 → "2m 46s" |
| `estimateCost(in, out)` | Расчёт: ($3/1M in + $15/1M out) |
| `toggleTaskDetail(id)` | Раскрытие/скрытие деталей задачи |

### CSS

Bootstrap Icons (CDN) + кастомный CSS. Тёмная/светлая тема (CSS variables).

---

## a1/tasks.py — TaskManager (211 строк)

**Роль**: CRUD для задач. Приоритеты, сортировка, критерии.

### Методы

| Метод | Сигнатура | Что |
|-------|-----------|-----|
| `add_task` | `(title, desc=None, priority=None, criteria=None) → dict` | Создать задачу. Auto-ID, auto-priority |
| `add_raw_thought` | `(text) → None` | Сырая мысль для transform |
| `get_tasks` | `() → list[dict]` | Все задачи |
| `get_next_task` | `() → dict or None` | Следующая pending (sort by priority ASC) |
| `mark_done` | `(task_id) → None` | Статус → "done" + completed_at |
| `mark_in_progress` | `(task_id) → None` | Статус → "in_progress" |
| `get_summary` | `() → str` | Текст для промпта: все задачи + criteria |
| `get_progress` | `() → tuple(int, int)` | (done_count, total_count) |
| `reorder_tasks` | `(ids: list) → None` | Переупорядочить + переназначить priorities |

### Формат .a1/tasks.json

```json
{
  "tasks": [
    {
      "id": "task_001",
      "title": "Add health endpoint",
      "description": "Create /api/health...",
      "status": "pending",
      "priority": 1,
      "phase": "2.1",
      "success_criteria": "pytest passes",
      "created_at": "2026-02-22T12:00:00",
      "completed_at": null,
      "raw_thought": null
    }
  ],
  "raw_thoughts": [],
  "next_id": 2
}
```

---

## a1/checkpoint.py — CheckpointManager (146 строк)

**Роль**: Состояние между сессиями. Load/save, session tracking.

### Методы

| Метод | Что |
|-------|-----|
| `load() → dict` | Загрузить или создать дефолтный checkpoint |
| `save(**kwargs) → None` | Обновить поля и записать на диск |
| `start_session() → None` | session++, status=WORKING, timestamps |
| `end_session() → None` | status=IDLE |
| `is_completed() → bool` | status == "COMPLETED" |

### Лимит decisions

```python
# Bug #7 fix: decisions array limited to last 20
self.data["decisions"] = self.data["decisions"][-20:]
```

---

## a1/validator.py — Validator (361 строка)

**Роль**: "Зрение" агента. Проверяет что работа реально выполнена.

### Методы

| Метод | Тип | Что |
|-------|-----|-----|
| `run_all() → Dict[str, ValidationReport]` | ALL | Все проверки разом |
| `_check_syntax() → ValidationReport` | BLOCKING | py_compile на всех .py |
| `_run_tests() → ValidationReport` | BLOCKING | pytest -v |
| `_run_lint() → ValidationReport` | WARNING | ruff check |
| `_check_build() → ValidationReport` | WARNING | python -m build / npm build |
| `_check_git() → ValidationReport or None` | WARNING | diff + status (None если нет git) |
| `has_git() → bool` | UTIL | Есть ли .git директория |
| `check_files_exist(paths) → ValidationReport` | BLOCKING | Файлы на диске? |
| `check_criteria(criteria) → ValidationReport` | BLOCKING | Эвристика success_criteria |

### ValidationReport

```python
@dataclass
class ValidationReport:
    result: ValidationResult  # OK, FAIL, SKIP, ERROR
    message: str
    details: Optional[str] = None
    command: Optional[str] = None
```

### check_criteria — эвристический парсер

```
"tests pass"          → запускает pytest
"lint clean"          → запускает ruff
"file X exists"       → os.path.exists(X)
"README.md exists"    → os.path.exists("README.md")
всё остальное         → SKIP (не можем проверить)
```

**Bug #12**: `.lower()` превращал "README.md" в "readme.md" → FAIL на Linux. Fix: re-match на оригинальной строке.

---

## a1/cli.py — CLI Interface (289 строк)

**Роль**: Точка входа. `pca` command через pyproject.toml entry_points.

### Команды

| Команда | Функция | Что |
|---------|---------|-----|
| `pca init <dir>` | `cmd_init()` | Создать .a1/ |
| `pca task add "..."` | `cmd_task_add()` | Добавить задачу |
| `pca think "..."` | `cmd_think()` | Сырая мысль |
| `pca tasks` | `cmd_tasks()` | Показать задачи |
| `pca start` | `cmd_start()` | Запустить работу |
| `pca status` | `cmd_status()` | Текущий статус |
| `pca validate` | `cmd_validate()` | Валидация |
| `pca ui` | `cmd_ui()` | Дашборд |
| `pca log` | `cmd_log()` | История |
| `pca test` | `cmd_test()` | Vision QA |

---

## a1/tester/ — Vision QA (1087 строк)

**Роль**: Автономный тестировщик. Screenshot → Claude Vision → действие.

| Модуль | Строк | Что |
|--------|-------|-----|
| `runner.py` | 419 | Главный цикл: сценарий → шаги → screenshot |
| `scenarios.py` | 203 | 7 сценариев |
| `analyzer.py` | 142 | Claude Vision API |
| `browser.py` | 124 | Playwright headless |
| `report.py` | 193 | HTML/JSON отчёты |

### 7 сценариев

1. **Dashboard loads** — рендер, карточки видны
2. **Add task via web** — форма, задача появляется
3. **Add thought** — форма мыслей
4. **Navigation** — все 7 страниц
5. **Theme toggle** — dark/light
6. **Start/Stop agent** — кнопки
7. **API endpoint** — /api/status JSON
