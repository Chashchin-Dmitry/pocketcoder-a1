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
- [x] load_checkpoint()
- [x] save_checkpoint()
- [x] start_session()
- [x] end_session()
- [x] is_completed()

### 1.3 Task система [DONE]
- [x] tasks.py — TaskManager class
- [x] add_task()
- [x] add_raw_thought()
- [x] get_tasks()
- [x] get_next_task()
- [x] mark_done()

### 1.4 Validator [DONE]
- [x] validator.py — Validator class
- [x] _check_syntax()
- [x] _run_tests()
- [x] _run_lint()
- [x] _check_build()

### 1.5 Session Loop [DONE]
- [x] loop.py — SessionLoop class
- [x] build_prompt()
- [x] run_session()
- [x] _run_claude_max() (subprocess)

### 1.6 CLI [DONE]
- [x] cli.py — argparse
- [x] pca init
- [x] pca task add
- [x] pca think
- [x] pca tasks
- [x] pca start
- [x] pca status
- [x] pca validate
- [x] pca ui

### 1.7 Web Dashboard [DONE]
- [x] dashboard.py
- [x] HTML template без эмодзи
- [x] Bootstrap Icons
- [x] Авто-поиск свободного порта
- [x] Add task через форму
- [x] Start/Stop кнопки

---

## PHASE 2: АВТОНОМНОСТЬ [IN PROGRESS]

### 2.1 Улучшить Session Loop
- [ ] Мониторинг контекста (/tokens parsing)
- [ ] Авто-checkpoint при 70%
- [ ] Dual exit gate (2 условия для выхода)
- [ ] Rate limiting (защита от runaway)

**Тест:** Запустить на 5 сессий, проверить что checkpoint корректно сохраняется

### 2.2 Git Integration
- [ ] Авто-создание ветки для работы
- [ ] Атомарные коммиты после каждой задачи
- [ ] Проверка git status перед commit
- [ ] Не коммитить если тесты fail

**Тест:** Проверить что после pca start создаётся ветка и коммиты

### 2.3 Улучшить Checkpoint
- [ ] Сохранять diff файлов
- [ ] Сохранять историю решений
- [ ] Восстановление при crash
- [ ] Merge checkpoints при конфликтах

**Тест:** Прервать сессию Ctrl+C, проверить что checkpoint сохранён

---

## PHASE 3: ПРОВАЙДЕРЫ [TODO]

### 3.1 Claude API Provider
- [ ] Добавить anthropic SDK зависимость
- [ ] _run_claude_api() в loop.py
- [ ] Streaming response
- [ ] Token counting
- [ ] Error handling (rate limits, etc)

**Тест:** `pca start --provider claude-api` работает

### 3.2 Ollama Provider
- [ ] Добавить ollama зависимость
- [ ] _run_ollama() в loop.py
- [ ] Model selection
- [ ] Context size detection

**Тест:** `pca start --provider ollama --model qwen3:32b` работает

### 3.3 OpenAI-Compatible Provider
- [ ] Переиспользовать код из pocketcoder
- [ ] Presets (DeepSeek, Groq, etc)
- [ ] Auto-detect endpoint

**Тест:** `pca start --provider openai-compat --url https://api.deepseek.com` работает

---

## PHASE 4: SMART FEATURES [TODO]

### 4.1 Smart Model Router
- [ ] Классификация задач (simple/medium/complex)
- [ ] Mapping задач на модели
- [ ] Presets:
  - [ ] cost_optimizer
  - [ ] quality_first
  - [ ] speed_demon
  - [ ] custom
- [ ] UI для настройки

**Тест:** Router выбирает правильную модель для разных задач

### 4.2 Transform (мысли → задачи)
- [ ] Отправить raw_thoughts в LLM
- [ ] Получить структурированные задачи
- [ ] Разбить на подзадачи
- [ ] Оценить сложность

**Тест:** `pca transform` превращает "хочу роутер" в конкретные задачи

### 4.3 Context Management
- [ ] Авто-определение важных файлов
- [ ] Selective context loading
- [ ] Summarization при переполнении

**Тест:** При 70% контекста — корректная суммаризация

---

## PHASE 5: ТЕСТИРОВАНИЕ [TODO]

### 5.1 Unit Tests
- [ ] tests/test_checkpoint.py
- [ ] tests/test_tasks.py
- [ ] tests/test_validator.py
- [ ] tests/test_loop.py

**Метрика:** pytest coverage > 80%

### 5.2 Integration Tests
- [ ] tests/test_cli.py
- [ ] tests/test_dashboard.py
- [ ] tests/test_full_workflow.py

**Метрика:** Все интеграционные тесты проходят

### 5.3 E2E Tests
- [ ] Полный цикл: init → task → start → validate → complete
- [ ] Тест с прерыванием и восстановлением
- [ ] Тест с несколькими сессиями

**Метрика:** E2E тест проходит за < 10 минут

---

## PHASE 6: ДОКУМЕНТАЦИЯ И РЕЛИЗ [TODO]

### 6.1 Документация
- [ ] README.md с примерами
- [ ] CONTRIBUTING.md
- [ ] CHANGELOG.md
- [ ] Примеры в examples/

### 6.2 PyPI Release
- [ ] Проверить pyproject.toml
- [ ] Обновить версию
- [ ] python -m build
- [ ] twine upload

### 6.3 Дистрибутив
- [ ] PyInstaller config
- [ ] Сборка бинарника
- [ ] Тестирование на чистой системе

---

## МЕТРИКИ УСПЕХА

### Автономность
| Метрика | Цель | Как измерить |
|---------|------|--------------|
| Сессий до ручного вмешательства | > 10 | Счётчик в логе |
| Checkpoint recovery rate | 100% | Тест прерывания |
| Task completion rate | > 90% | done/total tasks |

### Качество
| Метрика | Цель | Как измерить |
|---------|------|--------------|
| Test coverage | > 80% | pytest --cov |
| Lint errors | 0 | ruff check |
| Build success | 100% | python -m build |

### Производительность
| Метрика | Цель | Как измерить |
|---------|------|--------------|
| Task per session | > 2 | tasks_done / sessions |
| Context efficiency | < 70% before exit | /tokens parsing |

---

## КАК ЗАПУСТИТЬ ТЕСТЫ

```bash
# Unit tests
pytest tests/ -v

# С coverage
pytest tests/ --cov=a1 --cov-report=html

# Lint
ruff check a1/

# Type check (если добавим)
mypy a1/

# Full validation
pca validate
```

---

## TROUBLESHOOTING

### Проблема: Claude не запускается
```bash
# Проверить что CLI установлен
which claude
claude --version

# Проверить что в PATH
echo $PATH
```

### Проблема: Порт занят
```bash
# Найти процесс
lsof -i :7331
# Убить
kill -9 <PID>
```

### Проблема: Checkpoint не сохраняется
```bash
# Проверить права
ls -la .a1/
# Проверить JSON
cat .a1/checkpoint.json | python -m json.tool
```
