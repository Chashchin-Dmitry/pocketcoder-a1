# CURRENT STAGE — PocketCoder-A1

**Last updated**: 2026-03-05
**Version**: 0.2.4
**Status**: Phase 1 DONE, Dashboard UX DONE, Stream-JSON DONE, Verification DONE, Token Metrics DONE, Providers DONE, Config DONE
**Code**: 7086 строк Python (15 модулей)

---

## АРХИТЕКТУРА: КАК ВСЁ СВЯЗАНО

```
               Пользователь
                    │
          ┌─────────┴─────────┐
          │                   │
       CLI (pca)        Dashboard (:7331)
       a1/cli.py        a1/dashboard.py
          │                   │
          └─────────┬─────────┘
                    │
            ┌───────┴───────┐
            │               │
      TaskManager    CheckpointManager
      a1/tasks.py    a1/checkpoint.py
            │               │
            └───────┬───────┘
                    │
              SessionLoop          ◄── Главный мозг
              a1/loop.py
                    │
          ┌─────────┼─────────┐
          │         │         │
    Claude CLI   Validator   Dashboard
    (subprocess) a1/validator  (callback)
          │         .py          │
          │         │         AGENT_LOG_BUFFER
          │         │            │
    stream-json  run_all()   /api/log
    (NDJSON)     check_*()   /api/status
```

### Причинно-следственная цепочка: от задачи до результата

```
Пользователь создаёт задачу
  └── POST /add-task → tasks.py.add_task() → .a1/tasks.json
      └── Нажимает "Start Agent"
          └── POST /start → loop.start() в отдельном потоке
              └── loop._capture_baseline() → снимок ДО работы
                  └── loop.build_prompt() → собирает checkpoint + tasks + queue
                      └── subprocess: claude -p prompt --stream-json
                          └── loop._parse_stream_event() → NDJSON → тип события
                              ├── tool_use → _log_callback("Read file.py", "read")
                              │   └── dashboard._on_agent_line() → AGENT_LOG_BUFFER
                              │       └── /api/log → JS updateLog() → иконка в панели
                              ├── text → _log_callback("текст", "text")
                              ├── rate_limit_event → _update_metrics(tokens_in, tokens_out)
                              │   └── _session_metrics → /api/status → карточки Tokens/Cost
                              └── result → конец сессии
                                  └── loop._verify_session() → validator.run_all()
                                      ├── PASS → checkpoint.status = COMPLETED → stop
                                      ├── FAIL → retry (max 5) → fix prompt → повтор
                                      └── BLOCKED → mark task blocked → next task
```

---

## МОДУЛИ — КАРТА

### a1/loop.py (1219 строк) — Главный цикл

**Класс**: `SessionLoop(project_dir, provider, max_sessions, session_delay)`

**Что делает**: Запускает Claude CLI как subprocess, парсит stream-json, отправляет логи в дашборд, верифицирует результаты.

**Ключевые методы**:
| Метод | Что делает |
|-------|-----------|
| `start()` | Запуск цикла: baseline → prompt → subprocess → verify → repeat |
| `stop()` | Остановка: kill process, _running = False |
| `build_prompt()` | Собирает промпт: checkpoint + tasks + queue messages |
| `_parse_stream_event(line)` | Парсит одну строку NDJSON → определяет тип (tool_use/text/result) |
| `_capture_baseline()` | Снимок валидации ДО первой сессии (чтобы не считать старые баги) |
| `_verify_session()` | 3-уровневая верификация после каждой сессии |
| `_is_new_issue(check, report)` | Сравнение с baseline — только НОВЫЕ проблемы блокируют |
| `_get_verification_prompt()` | Инъекция ошибок верификации в следующий промпт |
| `get_session_metrics()` | Возвращает {tokens_in/out, cache, tools, cost, duration} |

**Причинно-следственные связи**:

```
loop.start()
  │
  ├── _capture_baseline()
  │     cause: агент не должен фейлиться на старых багах
  │     effect: снимок валидации ДО работы → сравнение ПОСЛЕ
  │
  ├── build_prompt()
  │     cause: агент должен знать контекст (что делать, что уже сделано)
  │     effect: prompt = checkpoint + tasks + queue + verification_prompt
  │     chain: checkpoint.load() → JSON → tasks.get_summary() → текст
  │            queue.json → messages → inject into prompt
  │
  ├── subprocess.Popen(["claude", "-p", prompt, ...])
  │     cause: нужен автономный Claude
  │     effect: Claude работает в проекте, читает/пишет файлы
  │     flags:
  │       --dangerously-skip-permissions  ← автономный режим
  │       --no-session-persistence        ← не засоряем историю
  │       --max-turns 25                  ← лимит на итерации
  │       --verbose --output-format stream-json ← real-time NDJSON
  │     env: CLAUDECODE removed ← вложенные сессии иначе crash
  │
  ├── readline() loop → _parse_stream_event()
  │     cause: нужны живые логи в дашборде
  │     effect: каждый tool_use/text/result → _log_callback → дашборд
  │     chain: JSON line → type check → extract name/text → callback
  │
  ├── _update_metrics(event)
  │     cause: нужно показывать потребление токенов
  │     effect: rate_limit_event → tokens_in/out → _session_metrics
  │     chain: _session_metrics → get_session_metrics() → /api/status → карточки
  │
  └── _verify_session()
        cause: агент может соврать ("done" без проверки)
        effect: 3 уровня проверки:
          BLOCKING: syntax + tests + files_exist + success_criteria
          WARNING:  lint + build + git
          ANTI-LOOP: baseline + max 5 retries + BLOCKED
        chain:
          retry >= MAX_VERIFY_RETRIES(5)
            └── should_block = True
                └── tasks.mark_blocked(task_id, reason)
                    ├── pca start (все задачи):
                    │   └── get_next_task() → task_002 → продолжаем
                    └── pca start --task task_001:
                        └── стоп → "task_001: BLOCKED"
```

**Константы**:
- `CONTEXT_WINDOW_SIZE = 200_000` — размер окна Claude
- `CONTEXT_THRESHOLD = 0.70` — авто-checkpoint при 70%
- `MAX_VERIFY_RETRIES = 5` — лимит ретраев верификации
- `BLOCKING_CHECKS = {"syntax", "tests"}` — то, что блокирует
- `WARNING_CHECKS = {"lint", "build", "git"}` — то, что только предупреждает

---

### a1/dashboard.py (3491 строк) — Web UI

**Функция**: `run_dashboard(project_dir, port, no_browser)`

**Что делает**: ThreadingHTTPServer на stdlib (no frameworks). 8 страниц, 24 API endpoints, live logs, AJAX.

**Страницы (8)**:
| URL | Название | Что показывает |
|-----|---------|---------------|
| `/` | Dashboard | 6 карточек метрик, кнопки Start/Stop, лог агента |
| `/tasks` | Tasks | Список задач с приоритетами, drag-drop, bulk add |
| `/task/{id}` | Task Detail | Полный вид + логи + сессии + Start/Stop/Delete |
| `/sessions` | Sessions | История сессий с метриками |
| `/log` | Activity Log | Хронология действий дашборда |
| `/settings` | Settings | Провайдер, API key, Ollama, параметры сессии |
| `/commits` | Git Commits | История коммитов с иконками типов |
| `/transform` | Transform | Текст → задачи через AI (3-step flow) |

**6 карточек метрик (главная страница)**:
| Карточка | Иконка | Данные | Источник |
|---------|--------|--------|---------|
| Tasks | `bi-check2-square` | `2/5 done` + прогресс-бар | tasks.get_progress() |
| Session | `bi-terminal` | `#3` + статус-бейдж | checkpoint.session |
| Tokens | `bi-lightning-charge` | `12.4K in / 3.2K out` + прогресс-бар | session_metrics |
| Cost | `bi-currency-dollar` | `$0.08` за сессию | session_metrics (расчёт) |
| Duration | `bi-stopwatch` | `48s` (live timer) | JS tickTimer() |
| Files | `bi-file-earmark-code` | `3 modified` | checkpoint.files_modified |

**8 типов иконок лога**:
| Тип | Иконка | Цвет | Когда |
|-----|--------|------|-------|
| read | `bi-eye` | #3b82f6 (синий) | Claude читает файл |
| edit | `bi-pencil-square` | #f97316 (оранжевый) | Claude редактирует файл |
| write | `bi-file-earmark-plus` | #10b981 (зелёный) | Claude создаёт файл |
| bash | `bi-terminal-fill` | #8b5cf6 (фиолетовый) | Claude выполняет команду |
| thinking | `bi-lightbulb` | #eab308 (жёлтый) | Claude думает |
| text | `bi-chat-left-text` | #6b7280 (серый) | Текстовый вывод |
| metric | `bi-speedometer` | #6366f1 (индиго) | Обновление метрик |
| verify | `bi-shield-check` | #10b981 (зелёный) | Результат верификации |

**Причинно-следственные связи**:

```
Карточки обновляются через AJAX:
  JS updateStatus() каждые 3 сек
    └── fetch('/api/status')
        └── DashboardHandler.handle_api_status()
            └── checkpoint.load() + tasks.get_progress() + AGENT_LOOP.get_session_metrics()
                └── JSON response → JS обновляет DOM (карточки, бейджи, прогресс-бары)

Лог обновляется через AJAX:
  JS updateLog() каждые 2 сек
    └── fetch('/api/log?since=N')
        └── AGENT_LOG_BUFFER[since:]
            └── JSON response → JS добавляет <div> с иконкой + цветом + текстом

Live Timer:
  JS tickTimer() каждые 1 сек (когда agentRunning)
    └── sessionStartTime = checkpoint.session_started_at
        └── now - start = duration → обновляет карточку Duration

Task Detail View:
  Клик на задачу → toggleTaskDetail(id)
    └── Раскрывается блок:
        ├── 3-step progress (pending → in_progress → done)
        ├── Phase, Created/Completed dates
        ├── Success Criteria
        └── Files modified (если есть)
```

**API endpoints (24 штуки)**:
| Method | Endpoint | Что делает |
|--------|----------|-----------|
| GET | `/api/status` | JSON: checkpoint + tasks + progress + running + metrics |
| GET | `/api/log?since=N` | Записи лога агента начиная с индекса N |
| GET | `/api/config` | Текущий конфиг (API key замаскирован) |
| GET | `/api/task/{id}` | Одна задача JSON |
| POST | `/add-task` | Добавить задачу (form: task, description) |
| POST | `/add-tasks-bulk` | Добавить несколько задач (textarea) |
| POST | `/add-thought` | Добавить мысль (form: thought) |
| POST | `/start` | Запустить агента (все задачи) |
| POST | `/start-task/{id}` | Запустить агента для одной задачи |
| POST | `/stop` | Остановить агента (kill subprocess) |
| POST | `/delete-task/{id}` | Удалить задачу |
| POST | `/queue-message` | Отправить сообщение агенту (form: message) |
| POST | `/api/reorder` | Переупорядочить задачи (JSON: {order: [ids]}) |
| POST | `/api/config` | Обновить конфиг (JSON) |
| POST | `/transform` | AI разбивка текста на задачи (form: text) |
| POST | `/transform-confirm` | Подтвердить задачи из transform (JSON: {tasks}) |
| POST | `/toggle-theme` | Переключить тёмную/светлую тему |

---

### a1/tasks.py (211 строк) — Управление задачами

**Класс**: `TaskManager(project_dir)`

**Хранилище**: `.a1/tasks.json`

**Ключевые методы**:
| Метод | Что делает |
|-------|-----------|
| `add_task(title, desc, priority, criteria)` | Создание задачи с auto-ID и auto-priority |
| `add_raw_thought(text)` | Сырая мысль (для transform) |
| `get_tasks()` | Все задачи |
| `get_next_task()` | Следующая pending задача (сортировка по priority ASC) |
| `mark_done(task_id)` | Отметить выполненной |
| `get_summary()` | Текст для промпта: задачи + статусы + criteria |
| `get_progress()` | `(done_count, total_count, blocked_count)` |
| `mark_blocked(task_id, reason)` | Заблокировать задачу с причиной |
| `reorder_tasks(ids)` | Переупорядочить + переназначить priorities |

**Формат задачи**:
```json
{
  "id": "task_001",
  "title": "Add health check endpoint",
  "description": "Create /api/health endpoint...",
  "status": "pending|in_progress|done|blocked",
  "priority": 1,
  "phase": "2.1",
  "success_criteria": "pytest passes, file exists",
  "blocked_reason": null,
  "created_at": "2026-02-22T12:00:00",
  "completed_at": null
}
```

---

### a1/checkpoint.py (146 строк) — Состояние между сессиями

**Класс**: `CheckpointManager(project_dir)`

**Хранилище**: `.a1/checkpoint.json`

**Ключевые методы**:
| Метод | Что делает |
|-------|-----------|
| `load()` | Загрузить checkpoint (или создать дефолтный) |
| `save(**kwargs)` | Обновить поля и сохранить |
| `start_session()` | session++ , status=WORKING, timestamps |
| `end_session()` | status=IDLE |
| `is_completed()` | status == "COMPLETED" |

**Формат checkpoint.json**:
```json
{
  "status": "IDLE|WORKING|COMPLETED",
  "session": 2,
  "current_task": "task_003",
  "context_percent": 0.45,
  "files_modified": ["src/health.ts", "docs/API.md"],
  "decisions": ["Combined tasks 1+2 into one file"],
  "next_steps": ["Run tests"],
  "last_action": "Created API docs",
  "session_metrics": {
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

**Ограничение**: `decisions` обрезается до последних 20 записей (bug #7 fix).

---

### a1/validator.py (361 строка) — Проверка результатов

**Класс**: `Validator(project_dir)`

**Что делает**: "Зрение" агента — проверяет что работа реально выполнена.

**Проверки**:
| Проверка | Тип | Что делает |
|---------|-----|-----------|
| `_check_syntax()` | BLOCKING | `python -m py_compile` на всех .py |
| `_run_tests()` | BLOCKING | `pytest -v` |
| `_run_lint()` | WARNING | `ruff check` |
| `_check_build()` | WARNING | `python -m build` или `npm run build` |
| `_check_git()` | WARNING | `git diff --stat` + `git status` (опционально) |
| `check_files_exist(paths)` | BLOCKING | Проверка что файлы из checkpoint реально на диске |
| `check_criteria(criteria)` | BLOCKING | Эвристика: "tests pass" → pytest, "file X exists" → os.path.exists |

**has_git()**: Проверяет `.git` директорию. Нет git = пропускаем git-проверки молча.

**Результат**: `Dict[str, ValidationReport]` — каждая проверка → result/message/details.

---

### a1/cli.py (289 строк) — CLI интерфейс

**Точка входа**: `pca` command (через pyproject.toml entry_points)

**Команды**:
| Команда | Что делает | Пример |
|---------|-----------|--------|
| `pca init <dir>` | Создаёт .a1/ директорию | `pca init my-project` |
| `pca task add "..."` | Добавляет задачу | `pca task add "Fix login bug"` |
| `pca think "..."` | Добавляет сырую мысль | `pca think "нужен роутер"` |
| `pca tasks` | Показывает все задачи | `pca tasks` |
| `pca start` | Запускает автономную работу | `pca start --provider claude-api` |
| `pca start --task ID` | Работа над одной задачей | `pca start --task task_001` |
| `pca status` | Текущий статус | `pca status` |
| `pca validate` | Запуск валидации | `pca validate` |
| `pca ui` | Запуск веб-дашборда | `pca ui --no-browser` |
| `pca log` | История сессий | `pca log` |
| `pca test` | Vision QA тесты | `pca test --no-vision` |

---

### a1/tester/ (1087 строк, 5 модулей) — Vision QA

**Что делает**: Автономный тестировщик — скриншот → Claude Vision → действие → скриншот.

| Модуль | Строк | Что делает |
|--------|-------|-----------|
| `runner.py` | 419 | Главный цикл: сценарий → шаги → screenshot → анализ |
| `scenarios.py` | 203 | 7 тестовых сценариев |
| `analyzer.py` | 142 | Claude Vision API анализ скриншотов |
| `browser.py` | 124 | Playwright headless обёртка |
| `report.py` | 193 | HTML/JSON отчёты со скриншотами |

**7 сценариев**:
1. Dashboard loads — страница рендерится, карточки видны
2. Add task via web — форма работает, задача появляется
3. Add thought — форма мыслей работает
4. Navigation — все 7 страниц загружаются
5. Theme toggle — переключение dark/light
6. Start/Stop agent — кнопки работают
7. API endpoint — /api/status возвращает JSON

---

## ДАННЫЕ — .a1/ директория

```
.a1/                         ← Создаётся при pca init
├── checkpoint.json          ← Текущее состояние (session, status, metrics)
├── tasks.json               ← Список задач (id, title, status, priority)
├── queue.json               ← Очередь сообщений агенту (создаётся при отправке)
├── sessions/                ← Логи сессий
│   ├── session_001.log
│   └── session_002.log
├── checkpoints/             ← Архив checkpoint-ов
│   ├── session_001.json
│   └── session_002.json
└── test-reports/            ← Отчёты Vision QA
    └── latest.html
```

---

## КОНФИГУРАЦИЯ — .claude/

```
.claude/
└── settings.local.json      ← Локальные настройки Claude Code
```

**settings.local.json**:
```json
{
  "enabledMcpjsonServers": ["playwright"],
  "enableAllProjectMcpServers": true
}
```

**Зачем**: Подключает Playwright MCP сервер для браузерной автоматизации.

Также: `.mcp.json` в корне проекта — конфигурация MCP серверов для Claude Code:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-playwright"]
    }
  }
}
```

---

## ПОЛНЫЙ МАНУАЛ: ОТ НУЛЯ ДО РЕЗУЛЬТАТА

### Шаг 0: Установка

```bash
cd pocketcoder-a1
pip install -e .

# Проверка
pca --help
```

### Шаг 1: Инициализация проекта

```bash
# На ЛЮБОМ проекте:
cd /path/to/my-project
pca init .

# Создастся .a1/ с пустыми tasks.json и checkpoint.json
```

### Шаг 2: Добавление задач

**Способ A — CLI**:
```bash
pca task add "Write pytest tests for calculator.py"
pca task add "Create README.md with usage examples"
```

**Способ B — Dashboard** (рекомендуется):
```bash
pca ui         # Открывает дашборд на :7331
# Или без браузера:
pca ui --no-browser
```
Заходишь на `http://localhost:7331`, заполняешь форму Quick Add.

**Способ C — Transform** (AI разбивка):
На странице `/transform` пишешь текст типа "нужны тесты, README, CI пайплайн" → AI разбивает на задачи → ты подтверждаешь.

### Шаг 3: Запуск агента

**Через дашборд**: Кнопка "Start Agent" на главной.

**Через CLI**: `pca start`

**Что происходит**:
1. Агент читает задачи + checkpoint
2. Берёт задачу с наименьшим приоритетом
3. Работает автономно (читает/пишет файлы, запускает команды)
4. После каждой задачи — верификация
5. Все 3 задачи done → COMPLETED → останавливается

### Шаг 4: Мониторинг (real-time)

На главной странице дашборда:
- **Карточки** обновляются каждые 3 сек (Tasks 1/3 → 2/3 → 3/3)
- **Лог агента** обновляется каждые 2 сек (иконки + действия)
- **Timer** тикает каждую секунду

**API для скриптов**:
```bash
# Статус
curl http://localhost:7331/api/status | python -m json.tool

# Лог с позиции 0
curl "http://localhost:7331/api/log?since=0" | python -m json.tool

# Прогресс
curl -s http://localhost:7331/api/status | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'Running: {d[\"running\"]}')
print(f'Progress: {d[\"progress\"]}')
print(f'Status: {d[\"checkpoint\"][\"status\"]}')
"
```

### Шаг 5: Результат

Когда все задачи выполнены:
- Карточка Tasks: `3/3 done` (зелёный прогресс-бар)
- Бейдж: `COMPLETED` (синий)
- Файлы: список в checkpoint.files_modified
- Лог: полная история действий агента

### Шаг 6: Отправка сообщения агенту (во время работы)

Если агент работает и нужно скорректировать:
1. На дашборде появляется форма "Queue message"
2. Пишешь "Focus on task_001 first" → отправляешь
3. Сообщение сохраняется в `.a1/queue.json`
4. На следующей сессии агент читает его и учитывает

---

## VERIFICATION SYSTEM — "НЕ ВЕРИМ НА СЛОВО"

### Проблема

```
БЫЛО (слабо):
  Агент пишет "COMPLETED" в checkpoint.json
    └── loop.py верит → останавливается
        └── Никакой проверки что работа реально сделана
        └── Validator существует, но НИКОГДА не вызывается
```

### Решение: 3 уровня верификации

```
СТАЛО (робастно):
  Агент пишет "COMPLETED"
    └── loop._verify_session()
        ├── TIER 1 — BLOCKING (must pass):
        │   ├── syntax: py_compile на всех .py → ошибка = блок
        │   ├── tests: pytest → failed = блок
        │   ├── files_exist: файлы из checkpoint на диске? → нет = блок
        │   └── success_criteria: "tests pass" → pytest, "file X" → os.path.exists
        │
        ├── TIER 2 — WARNING (log, don't block):
        │   ├── lint: ruff check
        │   ├── build: python -m build / npm run build
        │   └── git: diff + status (только если есть .git)
        │
        └── TIER 3 — ANTI-LOOP:
            ├── Baseline: снимок ДО первой сессии
            │   cause: старый проект может иметь failing tests
            │   effect: _is_new_issue() сравнивает с baseline → старые баги пропускаем
            ├── MAX_VERIFY_RETRIES = 3
            │   cause: агент может не справиться с фиксом
            │   effect: после 3 попыток → force_accept → остановка с предупреждением
            └── Prompt injection:
                cause: агент должен знать что сломалось
                effect: _get_verification_prompt() → текст в следующий промпт
```

### Цепочка: агент соврал

```
Агент: "COMPLETED, всё готово"
  └── _verify_session() → pytest FAIL (новый баг)
      └── _is_new_issue("tests") → True (этого не было в baseline)
          └── blocking_issues = ["tests: 2 failed"]
              └── passed = False → checkpoint.status = "WORKING"
                  └── Следующая сессия получает промпт:
                      "VERIFICATION FAILED (attempt 1/3)
                       BLOCKING: tests — 2 failed
                       FIX before marking done."
                      └── Агент чинит → COMPLETED → verify → PASS → stop
```

### Цепочка: бесконечный цикл предотвращён

```
Агент не может починить тесты:
  attempt 1: verify FAIL → retry_count=1 → reset to WORKING
  attempt 2: verify FAIL → retry_count=2 → reset to WORKING
  attempt 3: retry_count=3 >= MAX_VERIFY_RETRIES
    └── force_accept = True → loop stops
        └── Warning в логе: "FORCE ACCEPTED after 3 retries"
            └── Человек смотрит и решает
```

---

## STREAM-JSON — ЖИВЫЕ ЛОГИ

### Проблема

```
claude -p "prompt" (без stream-json)
  └── буферит ВЕСЬ stdout
      └── отдаёт ВСЕ разом после завершения
          └── log-панель пустая пока агент работает
              └── пользователь не видит прогресс
```

### Решение

```
claude -p "prompt" --verbose --output-format stream-json
  └── NDJSON: одна строка JSON = одно событие
      └── loop._parse_stream_event(line) в реальном времени
          ├── {"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}
          │   └── type="read", display="[Read] filename"
          ├── {"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}
          │   └── type="text", display="текст..."
          ├── {"type":"assistant","message":{"content":[{"type":"thinking","thinking":"..."}]}}
          │   └── type="thinking", display="thinking..."
          ├── {"type":"rate_limit_event","usage":{"input_tokens":12400,"output_tokens":3200}}
          │   └── _session_metrics updated → /api/status → карточки
          └── {"type":"result","result":"All done"}
              └── type="text", display="[Result] All done"
```

**Критический баг**: `--output-format stream-json` БЕЗ `--verbose` → ошибка. Claude CLI требует `--verbose` при использовании с `-p`.

---

## TOKEN METRICS

### Откуда берутся данные

```
Claude CLI → stream-json → rate_limit_event
  └── {"type":"rate_limit_event","usage":{
        "input_tokens": 12400,
        "output_tokens": 3200,
        "cache_read_input_tokens": 8000,
        "cache_creation_input_tokens": 1500
      }}
  └── loop._update_metrics() → _session_metrics accumulate
      └── get_session_metrics() → /api/status → JS → карточки
```

### Расчёт стоимости

```javascript
// dashboard.py → JS функция estimateCost()
cost = (tokens_in * 3 + tokens_out * 15) / 1_000_000
// $3/1M input, $15/1M output (Claude Sonnet pricing)
```

### Прогресс-бар токенов

```
tokens_in + tokens_out → percentage of CONTEXT_WINDOW_SIZE (200K)
  └── прогресс-бар: зелёный до 60%, жёлтый 60-80%, красный 80%+
```

---

## DASHBOARD FEATURES (12 штук)

### 1-6: Базовые (Phase 1)
| # | Фича | Цепочка |
|---|------|---------|
| 1 | Task forms (title+desc) | form → POST /add-task → tasks.add_task() → tasks.json |
| 2 | Priorities + Drag-Drop | DnD JS → POST /api/reorder → tasks.reorder_tasks() → priority update |
| 3 | Auto-execution by priority | prompt "LOWEST first" → get_next_task(sort=priority ASC) |
| 4 | Real-time agent logs | stream-json → _log_callback → AGENT_LOG_BUFFER → /api/log → AJAX 2s |
| 5 | Queue message | form → POST /queue-message → queue.json → loop reads → prompt inject |
| 6 | Transform (text→tasks) | textarea → POST /transform → claude -p → JSON → confirm → tasks.json |

### 7-12: UX Upgrade (Phase 2)
| # | Фича | Цепочка |
|---|------|---------|
| 7 | 6 metric cards | /api/status → metrics → JS updateStatus() → DOM update каждые 3s |
| 8 | Token metrics | rate_limit_event → _session_metrics → /api/status → Tokens/Cost cards |
| 9 | Colored log icons | event_type → icon map (8 types × 8 colors) → CSS colored <i> |
| 10 | Task detail view | click → toggleTaskDetail(id) → expand block (stages/criteria/dates) |
| 11 | Live timer | JS tickTimer() → Duration card updates every 1s when running |
| 12 | Responsive layout | CSS media queries: 3→2→1 columns, hamburger menu on mobile |

---

## BUGS FIXED (13)

| # | Файл | Баг | Причина | Фикс |
|---|------|-----|---------|------|
| 1 | loop.py | CLI args wrong | `["claude", prompt]` без `-p` | Добавлен `-p` флаг |
| 2 | loop.py | No output capture | stdout не перехватывался | `stdout=subprocess.PIPE` |
| 3 | loop.py | Nested sessions crash | `CLAUDECODE=1` в env → blocked | `env.pop("CLAUDECODE")` |
| 4 | loop.py | No auto-permissions | Каждый tool_use ждёт подтверждения | `--dangerously-skip-permissions` |
| 5 | loop.py | No max-turns | Агент мог крутиться бесконечно | `--max-turns 25` |
| 6 | loop.py | signal in thread | signal.signal() only in main thread | `threading.current_thread()` check |
| 7 | loop.py | Prompt missing format | Агент не знал формат tasks.json | HOW TO UPDATE sections в промпте |
| 8 | dashboard.py | XSS + stop button | Нет escape + stop не работал | `html.escape()` + `loop.stop()` |
| 9 | loop.py | stream-json error | `--output-format stream-json` без verbose | Добавлен `--verbose` |
| 10 | loop.py | Parser wrong format | Искал content_block_start | tool_use в assistant content[] |
| 11 | loop.py | f-string quotes | Вложенные кавычки в f-string | Extracted to variable |
| 12 | validator.py | Case-sensitive criteria | `.lower()` превращал README.md → readme.md | Re-match на оригинале |
| 13 | dashboard.py | $ in Template | `$0.00` в JS = placeholder | Escaped: `$$0.00` |

---

## E2E ТЕСТЫ — РЕЗУЛЬТАТЫ

| # | Проект | Задачи | Скриншоты | Время | Проверки | Результат |
|---|--------|--------|-----------|-------|----------|-----------|
| 1 | sandbox/test-e2e/ | 3/3 | 10 | 90s | — | PASS |
| 2 | sandbox/epotos-templates/ | 3/3 | 36 | 150s | — | PASS |
| 3 | sandbox/epotos-templates/ | 1/1 | 21 | 60s | 23 log entries | PASS |
| 4 | sandbox/test-verify/ | 4/4 | 23 | 48s | 23 pytest tests | PASS |
| 5 | Dashboard UX | — | 16 | — | 77/77 checks | PASS |
| 6 | Full Cycle | 3/3 | 14 | 165s | 22/22 checks | PASS |

### E2E #6 — Full Cycle (самый полный)

```
Шаг 0: Health check → dashboard alive, checkpoint IDLE
Шаг 1: Скриншот пустого дашборда → 6 карточек, 0/0
Шаг 2: Playwright создаёт 3 задачи через веб-форму
Шаг 3: Backend verify → API(3) == File(3)
Шаг 4: Start Agent → POST /start → Running
Шаг 5: Мониторинг каждые 15s → скриншоты + API + файлы + логи
  15s:  0/3, 7 logs (Glob, TodoWrite, text)
  30s:  0/3, 14 logs (tsc, Bash)
  45s:  0/3, 16 logs (thinking)
  60s:  2/3, 23 logs (Edit, text)
  75s:  2/3, 46 logs (Read × 20+)
  90s:  2/3, 62 logs (Read)
  120s: 2/3, 65 logs (text, mkdir)
  135s: 2/3, 66 logs (Write)
  150s: 3/3, 69 logs → COMPLETED!
  165s: stopped, 73 logs (verify PASSED)
Шаг 7: Final verify (5 levels):
  Level 1: Screenshots (dashboard, tasks, log)
  Level 2: API (agent stopped, 3/3 done)
  Level 3: Files (health/route.ts, API.md exist)
  Level 4: Sync (API tasks == File tasks)
  Level 5: Metrics (58 tools, 73 logs, 166s)
```

---

## ПОЛЕЗНЫЕ КОМАНДЫ

### Дашборд
```bash
# Запуск
pca ui                          # Открывает браузер
pca ui --no-browser             # Без браузера
pca ui -d /path/to/project      # Для конкретного проекта
pca ui --port 8080              # Другой порт

# Убить старый процесс
lsof -ti:7331 | xargs kill -9 2>/dev/null
```

### Агент
```bash
# Запуск
pca start                       # Claude Max (подписка)
pca start --provider claude-api # Claude API (ключ)
pca start --provider ollama     # Локальная модель

# Статус
pca status                      # Текущее состояние
pca tasks                       # Список задач
pca log                         # История сессий
```

### Валидация
```bash
pca validate                    # Все проверки
python -m py_compile a1/*.py    # Только синтаксис
pytest tests/ -v                # Только тесты
ruff check a1/                  # Только линт
```

### Отладка
```bash
# Посмотреть состояние
cat .a1/checkpoint.json | python -m json.tool
cat .a1/tasks.json | python -m json.tool

# Сбросить состояние
echo '{"status":"IDLE","session":0}' > .a1/checkpoint.json
echo '{"tasks":[],"next_id":1}' > .a1/tasks.json

# Посмотреть логи сессии
cat .a1/sessions/session_001.log

# API дашборда
curl -s http://localhost:7331/api/status | python -m json.tool
curl -s "http://localhost:7331/api/log?since=0" | python -m json.tool
```

### E2E тестирование (Playwright)
```bash
# Установка
pip install playwright
playwright install chromium

# Запуск тестов
source .venv/bin/activate
python sandbox/e2e_dashboard_ux/run_test.py       # 77 проверок
python sandbox/e2e_dashboard_ux/run_full_cycle.py  # Полный цикл
```

### Git
```bash
git status
git diff
git log --oneline -10
git add a1/dashboard.py a1/loop.py .a1/tasks.json
git commit -m "feat: dashboard upgrade"
git push origin main
```

---

## ФАЙЛОВЫЙ СТАТУС

| Файл | Строк | Статус | Последнее изменение |
|------|-------|--------|-------------------|
| `a1/__init__.py` | 6 | OK | v0.1.0 |
| `a1/checkpoint.py` | 146 | OK | decisions[-20:] fix |
| `a1/tasks.py` | 211 | OK | priority, reorder, criteria |
| `a1/validator.py` | 361 | OK | has_git, check_files_exist, check_criteria |
| `a1/loop.py` | 744 | OK | stream-json, verification, metrics |
| `a1/cli.py` | 289 | OK | pca test command |
| `a1/dashboard.py` | 2038 | OK | 6 cards, colors, detail view, timer, responsive |
| `a1/tester/runner.py` | 419 | OK | 7 scenarios |
| `a1/tester/scenarios.py` | 203 | OK | — |
| `a1/tester/analyzer.py` | 142 | OK | — |
| `a1/tester/browser.py` | 124 | OK | — |
| `a1/tester/report.py` | 193 | OK | — |

---

## ROADMAP

### Done
- [x] Phase 1: Core (checkpoint, tasks, validator, loop, CLI, dashboard)
- [x] Dashboard 6 features (forms, DnD, priorities, logs, queue, transform)
- [x] Dashboard UX upgrade (6 cards, colors, detail view, timer, responsive)
- [x] Stream-JSON live logs (NDJSON parsing, 8 icon types)
- [x] Post-session verification (3-tier, anti-loop)
- [x] Token metrics (rate_limit_event parsing, cost estimation)
- [x] Vision QA tester (7 scenarios, Playwright)
- [x] E2E tests (6 passed)

### In Progress
- [ ] Article 01 — Habr publication (see section below)
- [ ] Context monitoring (auto-checkpoint at 70%)
- [ ] Git integration (auto-branch, atomic commits)

### Next
- [ ] Claude API provider
- [ ] Ollama provider
- [ ] Smart Model Router
- [ ] Unit tests (coverage > 80%)
- [ ] PyPI + uv release
- [ ] epotos-templates open source release

---

## ARTICLE 01 — HABR + MEDIUM PUBLICATION

**Last updated**: 2026-03-08
**Status**: СТАТЬИ НАПИСАНЫ (RU + EN), обложки создаются, публикация в процессе

### Текущее состояние

```
DONE:
  [x] 6 mermaid диаграмм (EN, base theme, elk layout) — diagrams/01-06.mmd + 1-6.png
  [x] article_ru.md — финальная версия для Хабра
  [x] article_en.md — финальная версия для Medium
  [x] Стиль: без тире, без буллетов, без секции багов, Habr-стиль концовка с ТГ
  [x] Скрин OpenClaw добавлен (openclaw.png)
  [x] Версия с метками [photo_N] для ручной вставки картинок на Хабре
  [x] Коммит a2666c1 запушен

IN PROGRESS:
  [ ] Обложки cover_ru.html / cover_en.html — мокап дашборда (сайдбар, карточки, лог, таски)
  [ ] Публикация на Хабре — вставка текста + ручная загрузка фото
  [ ] Публикация на Medium — то же EN версия

TODO:
  [ ] Заскринить обложки 1280x640 → cover_ru.png, cover_en.png
  [ ] Загрузить 31 фото + openclaw на Хабр, заменить пути на CDN
  [ ] Проверить рендеринг markdown на Хабре (таблицы, код-блоки)
```

### Причинно-следственная цепочка

```
Проблема: 10+ проектов + 90 евро/мес подписка простаивает ночью
  └── Попытка: OpenClaw → не сработало (скрин openclaw.png)
      └── Решение: написать свой автономный агент
          └── PocketCoder-A1: CLI + Dashboard + 3 провайдера
              └── 6 диаграмм архитектуры (01-06)
                  └── Тестирование на реальном проекте epotos-templates
                      └── 26 скриншотов полного flow (01-26)
                          └── Результат: 5/5 задач за 13 минут автономно
                              └── Статьи: RU (Хабр) + EN (Medium)
                                  └── Обложки: HTML → скриншот (как в v1)
```

### Файлы статьи

| Файл | Что | Статус |
|------|-----|--------|
| `article_ru.md` | Статья RU для Хабра | DONE |
| `article_en.md` | Статья EN для Medium | DONE |
| `cover_ru.html` | Обложка RU (HTML, скринить) | IN PROGRESS |
| `cover_en.html` | Обложка EN (HTML, скринить) | IN PROGRESS |
| `openclaw.png` | Скриншот сайта OpenClaw | DONE |
| `diagrams/1-6.png` | 6 диаграмм PNG | DONE |
| `diagrams/01-06.mmd` | 6 mermaid исходников | DONE |
| `screenshots/01-26.png` | 26 скриншотов flow | DONE |
| `SCREENSHOTS_MAP.md` | Индекс скриншотов + план | DONE |

### Маппинг фото для статьи

| Метка | Файл | Откуда |
|-------|------|--------|
| [photo_openclaw] | openclaw.png | Раздел 1 — OpenClaw не сработал |
| [photo_1] | diagrams/1.png | 3.1 Общая схема |
| [photo_2] | diagrams/2.png | 3.2 Claude CLI subprocess |
| [photo_3] | diagrams/4.png | 3.3 Верификация |
| [photo_4] | diagrams/6.png | 3.4 Провайдеры |
| [photo_5] | diagrams/3.png | 3.5 Real-time поток |
| [photo_6] | diagrams/5.png | 3.6 Жизненный цикл задачи |
| [photo_7-31] | screenshots/01-26.png | Раздел 4 — Кейс epotos |

### Стиль статьи (утверждённый)

- Без длинных тире (используем запятые)
- Без буллет-листов (переводим в текст)
- Без секции багов
- Конверсационный тон, "я"/"мы"
- Технический depth: код-блоки, таблицы, диаграммы
- Концовка: ТГ канал + сайт (1:1 как в v1)
- Референс стиля: https://habr.com/ru/articles/991022/

### Обложка (текущая версия)

Левая часть:
- Бейдж OPEN SOURCE (оранжевый)
- PocketCoder-A1 (оранжевый заголовок)
- Подзаголовок (белый)
- Описание (серый)
- Теги: Python, Claude Code, Verification, Dashboard, Multi-provider

Правая часть — мокап дашборда в браузере:
- browser bar с localhost:7331
- Сайдбар: A1 логотип, навигация (Dashboard, Tasks, Sessions, Activity Log, Commits, Settings)
- 6 карточек метрик (Tasks 5/5, Session #12, Tokens 12.4K, Cost $0.08, Duration 48s, Files 23)
- Список задач (5 DONE)
- Live log (THINK, READ, EDIT, BASH, VERIFY с цветными метками)

### Habr v1 reference
- URL: https://habr.com/ru/articles/991022/
- 21K читателей, 37 upvotes, 146 bookmarks, 69 комментов
- В A1: конкурентов подробно НЕ разбираем, фокус на use case
