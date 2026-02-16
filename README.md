# PocketCoder-A1 🧙

**Autonomous Coding Agent — The Autonomous Gnome**

A1 автоматически работает над задачами пока ты занят другим.

## Quick Start

```bash
# Установка
pip install -e .

# Инициализация в проекте
pca init ./my-project

# Добавить задачи
pca think "хочу сделать роутер моделей"
pca task add "Implement SmartRouter class"

# Запустить автономную работу
pca start

# Проверить статус (в другом терминале)
pca status
```

## Как это работает

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS GNOME 🧙                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. READ STATE                                              │
│     • checkpoint.json — где остановился                    │
│     • tasks.json — что делать                              │
│                                                             │
│  2. WORK                                                    │
│     • Берёт задачу                                         │
│     • Пишет код                                            │
│     • Тестирует                                            │
│                                                             │
│  3. VALIDATE (зрение)                                       │
│     • Syntax check                                         │
│     • Tests                                                │
│     • Lint                                                 │
│     • ОК? → commit → next task                             │
│     • FAIL? → fix                                          │
│                                                             │
│  4. CONTEXT CHECK                                           │
│     • /tokens > 70%? → save checkpoint → exit              │
│     • All done? → exit with COMPLETED                      │
│                                                             │
│  5. ORCHESTRATOR RESTARTS                                   │
│     • New session, fresh context                           │
│     • Read checkpoint → continue                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `pca init <dir>` | Initialize A1 in project |
| `pca think "..."` | Add raw thought |
| `pca task add "..."` | Add specific task |
| `pca tasks` | Show all tasks |
| `pca start` | Start autonomous work |
| `pca status` | Show current status |
| `pca validate` | Run validation checks |
| `pca log` | Show session history |

## Providers

| Provider | How it works | Setup |
|----------|--------------|-------|
| `claude-max` | Claude Code CLI (Max subscription) | `npm i -g @anthropic-ai/claude-code` |
| `claude-api` | Anthropic API (pay per token) | `pip install pocketcoder-a1[api]` |
| `ollama` | Local models | `pip install pocketcoder-a1[ollama]` |

```bash
# Default: Claude Max subscription
pca start

# With Ollama
pca start --provider ollama
```

## Project Structure

```
your-project/
├── .a1/
│   ├── checkpoint.json    # Current state
│   ├── tasks.json         # Task list
│   ├── sessions/          # Session history
│   └── checkpoints/       # Checkpoint archive
└── ... your code
```

## Requirements

- Python 3.10+
- Claude Code CLI (for claude-max provider)
- Git (recommended)

## License

MIT
