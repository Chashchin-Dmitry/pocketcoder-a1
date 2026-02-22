# TODO — PocketCoder-A1

## КАК РАБОТАТЬ С ЭТИМ ФАЙЛОМ

```
1. Бери ПЕРВУЮ незавершённую задачу
2. Выполняй подзадачи по порядку
3. После каждой подзадачи — валидация
4. Отмечай [x] когда готово
5. При 70% контекста → checkpoint → exit
```

---

## PHASE 1: CORE INFRASTRUCTURE [DONE]

### 1.1 Структура проекта [DONE]
- [x] Создать папку pocketcoder-a1/
- [x] Создать a1/ модуль
- [x] Создать pyproject.toml
- [x] pip install -e . работает

### 1.2 Checkpoint система [DONE]
- [x] checkpoint.py — CheckpointManager class
- [x] load/save/start_session/end_session/is_completed
- [x] decisions[-20:] limit fix (bug #7)
- [x] session_metrics field

### 1.3 Task система [DONE]
- [x] tasks.py — TaskManager class
- [x] CRUD: add_task/get_tasks/get_next_task/mark_done
- [x] Priority field + auto-assign
- [x] reorder_tasks() for DnD
- [x] get_summary() with success_criteria
- [x] add_raw_thought() for transform

### 1.4 Validator [DONE]
- [x] validator.py — Validator class
- [x] _check_syntax / _run_tests / _run_lint / _check_build
- [x] has_git() / _check_git() — optional git support
- [x] check_files_exist(paths) — verify files on disk
- [x] check_criteria(criteria) — heuristic parser

### 1.5 Session Loop [DONE]
- [x] loop.py — SessionLoop class
- [x] build_prompt() — checkpoint + tasks + queue
- [x] subprocess: claude -p --stream-json --verbose
- [x] _parse_stream_event() — NDJSON real-time parser
- [x] _log_callback → dashboard live log
- [x] _capture_baseline / _verify_session / _is_new_issue
- [x] Anti-infinite-loop (MAX_VERIFY_RETRIES=3, force_accept)
- [x] Token metrics (rate_limit_event parsing)
- [x] env.pop("CLAUDECODE") — nested sessions fix

### 1.6 CLI [DONE]
- [x] cli.py — argparse
- [x] pca init/task add/think/tasks/start/status/validate/ui/log/test

### 1.7 Web Dashboard [DONE — MAJOR]
- [x] dashboard.py — 2038 lines, 7 pages, 17 API
- [x] 6 metric cards (Tasks/Session/Tokens/Cost/Duration/Files)
- [x] 8 colored log icon types
- [x] Task detail view (expandable, stages, criteria)
- [x] Live timer (JS tickTimer())
- [x] Drag-and-drop priorities
- [x] Queue message to agent
- [x] Transform (text → tasks via AI)
- [x] Responsive layout (hamburger, 3→2→1 columns)
- [x] XSS protection (html.escape)

### 1.8 Vision QA Tester [DONE]
- [x] tester/ — 5 modules, 1087 lines
- [x] 7 scenarios (dashboard/tasks/thoughts/nav/theme/agent/api)
- [x] Playwright headless browser
- [x] Claude Vision analysis
- [x] HTML/JSON reports

---

## PHASE 2: АВТОНОМНОСТЬ [IN PROGRESS]

### 2.1 Post-Session Verification [DONE]
- [x] 3-tier verification gate (blocking/warning/anti-loop)
- [x] Baseline comparison (pre-existing issues skipped)
- [x] Prompt injection (errors → next session)
- [x] Force accept after 3 retries

### 2.2 Stream-JSON Live Logs [DONE]
- [x] --verbose --output-format stream-json
- [x] _parse_stream_event() — NDJSON parser
- [x] 8 icon types with colors
- [x] Real-time AJAX polling (2s log, 3s status)

### 2.3 Token Metrics [DONE]
- [x] rate_limit_event parsing → _session_metrics
- [x] get_session_metrics() → /api/status
- [x] Dashboard cards (Tokens, Cost)
- [x] Cost estimation ($3/1M in, $15/1M out)

### 2.4 Context Monitoring
- [ ] Parse /tokens → context_percent
- [ ] Auto-checkpoint at 70%
- [ ] Dual exit gate (2 conditions)
- [ ] Rate limiting (runaway protection)

### 2.5 Git Integration
- [ ] Auto-branch for work
- [ ] Atomic commits after each task
- [ ] git status check before commit
- [ ] Don't commit if tests fail

### 2.6 Checkpoint Improvement
- [ ] Save diffs
- [ ] Decision history
- [ ] Crash recovery
- [ ] Merge checkpoints on conflict

---

## PHASE 3: ПРОВАЙДЕРЫ [IN PROGRESS]

### 3.1 Claude API Provider [IN PROGRESS]
- [ ] anthropic SDK dependency
- [ ] _run_claude_api() in loop.py
- [ ] Streaming response
- [ ] Token counting (native)
- [ ] Error handling (rate limits, timeouts)
- [ ] Cost tracking (real, not estimated)

### 3.2 Ollama Provider
- [ ] ollama SDK dependency
- [ ] _run_ollama() in loop.py
- [ ] Model selection (--model flag)
- [ ] Context size detection
- [ ] Streaming

### 3.3 OpenAI-Compatible Provider
- [ ] Generic endpoint support
- [ ] Presets (DeepSeek, Groq, etc)
- [ ] --url flag

---

## PHASE 4: SMART FEATURES [TODO]

### 4.1 Smart Model Router
- [ ] Task classification (simple/medium/complex)
- [ ] Model mapping
- [ ] Presets (cost_optimizer, quality_first, speed_demon)
- [ ] UI settings

### 4.2 Context Management
- [ ] Auto-detect important files
- [ ] Selective context loading
- [ ] Summarization at overflow

---

## PHASE 5: ТЕСТИРОВАНИЕ [TODO]

### 5.1 Unit Tests
- [ ] tests/test_checkpoint.py
- [ ] tests/test_tasks.py
- [ ] tests/test_validator.py
- [ ] tests/test_loop.py
- [ ] Coverage > 80%

### 5.2 E2E Tests [6/6 PASSED]
- [x] #1: Basic cycle (3/3 tasks, 90s)
- [x] #2: Real project epotos-templates (3/3, 150s)
- [x] #3: Stream-JSON verification (1/1, 60s)
- [x] #4: Verification system (4/4, 48s)
- [x] #5: Dashboard UX (77/77 checks)
- [x] #6: Full cycle web→agent→done (3/3, 22/22, 165s)

---

## PHASE 6: ДОКУМЕНТАЦИЯ И РЕЛИЗ [TODO]

### 6.1 Documentation
- [x] CLAUDE.md — project overview + module map
- [x] CURRENT_STAGE.md — full architecture + cause-effect chains + manual
- [x] TODO.md — phases roadmap (this file)
- [ ] README.md for public (clean, user-facing)
- [ ] API reference (docs/api.md)
- [ ] CONTRIBUTING.md

### 6.2 PyPI Release
- [ ] Update pyproject.toml metadata
- [ ] python -m build
- [ ] twine upload

---

## МЕТРИКИ УСПЕХА

| Метрика | Цель | Текущее |
|---------|------|---------|
| E2E tests | 6+ passed | 6/6 PASSED |
| Bugs fixed | 0 known | 13 fixed, 0 open |
| Dashboard pages | 7 | 7 |
| API endpoints | 17 | 17 |
| Log icon types | 8 | 8 |
| Code lines | — | 4882 |
