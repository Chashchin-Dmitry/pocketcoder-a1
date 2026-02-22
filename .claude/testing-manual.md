# Testing Manual — от нуля до результата

## Полная последовательность E2E тестирования PocketCoder-A1

Этот мануал описывает как протестировать ВСЁ: фронт, бек, синхрон данных, UX/UI, CLI.

---

## Шаг 0: Подготовка окружения

### Установка зависимостей

```bash
# PocketCoder-A1
cd pocketcoder-a1
pip install -e .

# Playwright для браузерной автоматизации
pip install playwright
playwright install chromium

# Проверка
pca --help
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### MCP Playwright (для Claude Code)

Файл `.mcp.json` уже в корне:
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

Claude Code автоматически подхватит. Проверить:
```bash
# В Claude Code:
# mcp__playwright__browser_navigate → должен быть доступен
```

---

## Шаг 1: Подготовка тестового проекта

```bash
# Вариант A: свежий проект
mkdir /tmp/test-project
cd /tmp/test-project
echo 'def hello(): return "Hello"' > hello.py
pca init .

# Вариант B: существующий проект
cd sandbox/epotos-templates
# Сбросить данные:
echo '{"tasks":[],"raw_thoughts":[],"next_id":1}' > .a1/tasks.json
echo '{"status":"IDLE","session":0}' > .a1/checkpoint.json
rm -f .a1/queue.json
```

---

## Шаг 2: Запуск дашборда

```bash
# Убить старый процесс (если есть)
lsof -ti:7331 | xargs kill -9 2>/dev/null

# Запустить
pca ui --no-browser &

# Подождать
sleep 3

# Проверить
curl -s http://localhost:7331/api/status | python -m json.tool
# Должен вернуть JSON с running=false, status=IDLE
```

---

## Шаг 3: Проверка начального состояния (скриншоты)

С Playwright или вручную:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # Главная — 6 карточек видны?
    page.goto("http://localhost:7331")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="screenshots/01_dashboard_empty.png")

    # Tasks — пустой список?
    page.goto("http://localhost:7331/tasks")
    page.screenshot(path="screenshots/02_tasks_empty.png")

    # Все 7 страниц загружаются?
    for url in ["/", "/tasks", "/sessions", "/log", "/settings", "/commits", "/transform"]:
        page.goto(f"http://localhost:7331{url}")
        page.wait_for_load_state("networkidle")
        # Проверить что нет ошибок
        assert "Error" not in page.content()

    browser.close()
```

### Что проверять на главной:
- [ ] 6 карточек видны (Tasks, Session, Tokens, Cost, Duration, Files)
- [ ] Tasks показывает 0/0
- [ ] Статус: IDLE или Stopped
- [ ] Кнопка Start Agent видна
- [ ] Log-панель пустая
- [ ] Навигация работает (sidebar)

---

## Шаг 4: Создание задач через веб-форму

```python
# На главной странице — Quick Add
page.goto("http://localhost:7331")

# Задача 1
page.locator('input[name="task"]').fill("Add health check endpoint")
page.locator('textarea[name="description"]').fill(
    "Create /api/health endpoint that returns {status: 'ok', timestamp: Date.now()}"
)
page.locator('button:has-text("Add")').click()
page.wait_for_load_state("networkidle")
page.screenshot(path="screenshots/03_task1_added.png")

# Задача 2
page.locator('input[name="task"]').fill("Add version info to health endpoint")
page.locator('textarea[name="description"]').fill(
    "Read version from package.json and return it in /api/health response"
)
page.locator('button:has-text("Add")').click()
page.wait_for_load_state("networkidle")

# Задача 3
page.locator('input[name="task"]').fill("Create API documentation file")
page.locator('textarea[name="description"]').fill(
    "Create docs/API.md listing all API endpoints with methods, paths, and response examples"
)
page.locator('button:has-text("Add")').click()
page.wait_for_load_state("networkidle")
page.screenshot(path="screenshots/04_all_tasks.png")
```

### Что проверять после добавления:
- [ ] Задачи появились на странице `/tasks`
- [ ] Приоритеты назначены (#1, #2, #3)
- [ ] API подтверждает: `curl http://localhost:7331/api/status` → progress [0, 3]
- [ ] Файл .a1/tasks.json содержит 3 задачи
- [ ] Синхрон: API progress == файл tasks.json

```python
import requests, json

# Backend verification
status = requests.get("http://localhost:7331/api/status").json()
assert status["progress"] == [0, 3], f"Expected [0,3], got {status['progress']}"

tasks_file = json.load(open(".a1/tasks.json"))
assert len(tasks_file["tasks"]) == 3
print("SYNC OK: API(3) == File(3)")
```

---

## Шаг 5: Запуск агента

```python
# Через API
response = requests.post("http://localhost:7331/start")
assert response.status_code == 200

# Или через Playwright
page.goto("http://localhost:7331")
page.locator('button:has-text("Start Agent")').click()

# Проверить что запустился
import time
time.sleep(3)
status = requests.get("http://localhost:7331/api/status").json()
assert status["running"] == True
print(f"Agent running! Checkpoint: {status['checkpoint']['status']}")

page.screenshot(path="screenshots/05_agent_started.png")
```

---

## Шаг 6: Мониторинг (каждые 15 сек, макс 5 мин)

Это самый важный шаг — проверяем синхрон данных в реальном времени.

```python
import time, requests

max_wait = 300  # 5 минут
start_time = time.time()
cycle = 0

while time.time() - start_time < max_wait:
    time.sleep(15)
    cycle += 1

    # 1. Фронт: что показывает дашборд
    status = requests.get("http://localhost:7331/api/status").json()
    done, total = status["progress"]
    running = status["running"]
    cp_status = status["checkpoint"]["status"]
    metrics = status.get("metrics", {})

    # 2. Бэк: что в файлах
    tasks_file = json.load(open(".a1/tasks.json"))
    file_done = sum(1 for t in tasks_file["tasks"] if t["status"] == "done")
    file_total = len(tasks_file["tasks"])

    # 3. Лог агента
    log = requests.get("http://localhost:7331/api/log?since=0").json()

    # 4. Проверка синхрона
    sync_ok = (done == file_done) and (total == file_total)

    elapsed = int(time.time() - start_time)
    print(f"[{elapsed:3d}s] running={running} cp={cp_status}")
    print(f"  FRONT: tasks={done}/{total} tokens={metrics.get('tokens_in',0)}/{metrics.get('tokens_out',0)}")
    print(f"  BACK:  tasks={file_done}/{file_total} tools={metrics.get('tools_used',0)} logs={log['total']}")
    print(f"  SYNC:  {'OK' if sync_ok else 'MISMATCH!'}")

    # 5. Скриншот
    page.goto("http://localhost:7331")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"screenshots/{5+cycle:02d}_monitor_{elapsed}s.png")

    # 6. Последние записи лога
    if log["entries"]:
        last = log["entries"][-1]
        print(f"  LOG: [{last['type']:8s}] {last['line'][:80]}")

    # 7. Стоп-условие
    if not running:
        print(f"\nAgent finished after {elapsed}s!")
        break

    if done == total and total > 0 and cp_status == "COMPLETED":
        print(f"\nAll {total} tasks done! Waiting for agent to stop...")
```

### Что проверять во время мониторинга:
- [ ] Карточка Tasks обновляется: 0/3 → 1/3 → 2/3 → 3/3
- [ ] Бейдж статуса: Running (зелёный)
- [ ] Лог агента заполняется (иконки: read, edit, write, bash, thinking)
- [ ] Синхрон: API progress == File progress (ВСЕГДА)
- [ ] Метрики токенов растут (если stream-json работает)
- [ ] Duration тикает (live timer)

---

## Шаг 7: Финальная верификация (5 уровней)

### Level 1: Скриншоты

```python
# Финальный дашборд
page.goto("http://localhost:7331")
page.wait_for_load_state("networkidle")
page.screenshot(path="screenshots/final_dashboard.png")

# Финальные задачи
page.goto("http://localhost:7331/tasks")
page.screenshot(path="screenshots/final_tasks.png")

# Лог
page.goto("http://localhost:7331/log")
page.screenshot(path="screenshots/final_log.png")
```

### Level 2: API

```python
status = requests.get("http://localhost:7331/api/status").json()
assert not status["running"], "Agent should be stopped"
assert status["progress"][0] == status["progress"][1], "All tasks should be done"
assert status["checkpoint"]["status"] in ["COMPLETED", "IDLE"]
```

### Level 3: Файлы

```python
import os

tasks = json.load(open(".a1/tasks.json"))
for task in tasks["tasks"]:
    assert task["status"] == "done", f"{task['id']} not done!"

# Проверить что созданные файлы существуют
checkpoint = json.load(open(".a1/checkpoint.json"))
for f in checkpoint.get("files_modified", []):
    assert os.path.exists(f), f"File {f} not found!"
```

### Level 4: Синхрон фронт-бек

```python
# API данные
api_done, api_total = status["progress"]

# Файловые данные
file_done = sum(1 for t in tasks["tasks"] if t["status"] == "done")
file_total = len(tasks["tasks"])

assert api_done == file_done, f"Sync mismatch: API({api_done}) != File({file_done})"
assert api_total == file_total, f"Sync mismatch: API({api_total}) != File({file_total})"
print(f"SYNC OK: API({api_done}/{api_total}) == File({file_done}/{file_total})")
```

### Level 5: Метрики

```python
metrics = status.get("metrics", {})
print(f"Tokens: {metrics.get('tokens_in', 0)} in / {metrics.get('tokens_out', 0)} out")
print(f"Tools: {metrics.get('tools_used', 0)}")
print(f"Duration: {metrics.get('session_duration', 0)}s")

log = requests.get("http://localhost:7331/api/log?since=0").json()
print(f"Log entries: {log['total']}")

# Типы иконок в логе
types = {}
for entry in log["entries"]:
    t = entry.get("type", "unknown")
    types[t] = types.get(t, 0) + 1
print(f"Log types: {types}")
```

---

## Шаг 8: Проверка UX/UI

### Визуальная проверка (скриншоты)

1. **6 карточек** — все видны, выровнены, с данными
2. **Прогресс-бар Tasks** — заполнен на 100% (зелёный)
3. **Бейдж статуса** — COMPLETED (синий) или Stopped
4. **Лог агента** — цветные иконки (синий=read, оранж=edit, фиолет=bash)
5. **Task detail** — кликнуть на задачу → раскрывается блок
6. **Navigation** — sidebar работает на всех страницах
7. **Responsive** — если уменьшить viewport до мобильного

### Проверка JS функций

```python
# В Playwright:
result = page.evaluate("fmtTokens(12400)")
assert result == "12.4K"

result = page.evaluate("fmtDuration(166)")
assert result == "2m 46s"

result = page.evaluate("estimateCost(12400, 3200)")
assert float(result) > 0
```

---

## Шаг 9: Проверка CLI (параллельно с дашбордом)

```bash
# Статус через CLI
pca status
# Должен показать: Session #N, COMPLETED, files_modified

# Задачи через CLI
pca tasks
# Должен показать все задачи с ✓ (done)

# Валидация
pca validate
# Должен пройти: syntax OK, tests OK (если есть)

# Лог
pca log
# Должен показать историю сессий
```

### Сравнение CLI vs Dashboard:
- [ ] Количество задач совпадает
- [ ] Статусы задач совпадают
- [ ] Номер сессии совпадает
- [ ] files_modified совпадает

---

## Troubleshooting

| Проблема | Причина | Решение |
|---------|---------|---------|
| Dashboard не стартует | Порт занят | `lsof -ti:7331 \| xargs kill -9` |
| Agent не запускается | CLAUDECODE env var | Перезапустить дашборд вне Claude Code |
| Лог пустой | Нет --verbose | Проверить loop.py subprocess args |
| Синхрон сломан | Кэш в памяти | Перезапустить дашборд |
| Tasks не обновляются | AJAX не работает | Проверить console в browser DevTools |
| Иконки все серые | Parser не классифицирует | Проверить _parse_stream_event() |
| $ shows as empty | Python Template | Escape: `$$` вместо `$` в JS |

---

## Чеклист финальный

```
□ Дашборд стартует на :7331
□ 6 карточек видны и выровнены
□ Задачи создаются через веб-форму
□ Приоритеты назначаются (#1, #2, #3)
□ Agent запускается через кнопку
□ Лог заполняется в реальном времени
□ Иконки цветные (8 типов)
□ Карточки обновляются (Tasks, Tokens, Duration)
□ Синхрон: API == File (всегда)
□ Все задачи выполнены (done)
□ Verification PASSED
□ CLI показывает то же что Dashboard
□ Скриншоты сохранены
□ Responsive работает
```
