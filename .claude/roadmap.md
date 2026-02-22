# Roadmap — Задачи перед нами

## Текущий статус: v0.1.0

**Сделано**: Core + Dashboard (12 фич) + Verification + Stream-JSON + Metrics + 6 E2E
**Код**: 4882 строк Python, 13 модулей

---

## Ближайшие задачи (приоритет)

### 1. Claude API Provider [EXPERIMENTAL]
**Файл**: `a1/loop.py` — метод `_run_claude_api()`
**Зависимости**: `anthropic` SDK
**Что даёт**: Работа через API ключ вместо Max подписки

```
Причинно-следственная связь:
  Текущее: только Claude Max (подписка, claude CLI)
    └── Ограничение: нужна подписка Max
        └── Решение: anthropic SDK → прямой API вызов
            └── Бонус: нативный подсчёт токенов (не rate_limit_event)
            └── Бонус: реальная стоимость (не estimated)
            └── Бонус: streaming через SDK
```

**Статус**: EXPERIMENTAL (нет API ключа для тестирования)

### 2. Ollama Provider [EXPERIMENTAL]
**Файл**: `a1/loop.py` — метод `_run_ollama()`
**Зависимости**: `ollama` SDK или HTTP API
**Что даёт**: Локальные модели без внешних API

```
Причинно-следственная связь:
  Текущее: только Claude (облако)
    └── Ограничение: нужен интернет + $$
        └── Решение: Ollama → локальные модели (Qwen, Llama, etc)
            └── Бонус: приватность (всё локально)
            └── Бонус: бесплатно
            └── Ограничение: качество ниже Claude
```

**Статус**: EXPERIMENTAL (Ollama не развёрнут)

### 3. Context Monitoring
**Файл**: `a1/loop.py`
**Что даёт**: Авто-checkpoint при 70% контекста

```
Причинно-следственная связь:
  Текущее: нет мониторинга контекста
    └── Риск: контекст переполнится → потеря данных
        └── Решение: парсить usage из stream-json → context_percent
            └── При 70% → автоматический checkpoint → new session
            └── Dashboard: прогресс-бар контекста
```

### 4. Git Integration
**Файл**: `a1/loop.py` + `a1/validator.py`
**Что даёт**: Автоматические ветки и коммиты

```
Причинно-следственная связь:
  Текущее: агент работает в main ветке
    └── Риск: сломает main → трудно откатить
        └── Решение: auto-branch per session
            └── git checkout -b a1/session-N
            └── Атомарные коммиты после каждой задачи
            └── Не коммитить если tests fail
            └── PR/merge после завершения
```

### 5. Unit Tests
**Файл**: `tests/`
**Что даёт**: Стабильность, рефакторинг без страха

```
Причинно-следственная связь:
  Текущее: только E2E тесты
    └── Проблема: E2E медленные (минуты), не покрывают edge cases
        └── Решение: pytest для каждого модуля
            └── test_checkpoint.py: save/load/session
            └── test_tasks.py: add/sort/reorder/criteria
            └── test_validator.py: syntax/lint/git/criteria
            └── test_loop.py: prompt building, event parsing
            └── Цель: coverage > 80%
```

---

## Долгосрочный план

| Фаза | Что | Когда |
|------|-----|-------|
| 2.x | Провайдеры (API + Ollama) | Ближайшее |
| 2.x | Context monitoring | Ближайшее |
| 2.x | Git integration | Ближайшее |
| 3.0 | Smart Model Router | Потом |
| 3.0 | Context management | Потом |
| 4.0 | Unit tests (80%+) | Потом |
| 5.0 | PyPI release | Когда стабильно |
| 5.0 | README для пользователей | Перед релизом |

---

## Критерии готовности к релизу

- [ ] Все E2E тесты проходят
- [ ] Unit tests coverage > 80%
- [ ] Минимум 2 провайдера (Claude Max + 1)
- [ ] Документация для пользователей (не dev notes)
- [ ] pip install pocketcoder-a1 работает
- [ ] 0 known bugs
