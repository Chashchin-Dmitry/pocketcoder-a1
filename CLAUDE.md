# CLAUDE.md — PocketCoder-A1

## AFTER /clear — READ THIS FIRST!

```
1. Read CLAUDE.md (this file) — project overview
2. Read .a1/checkpoint.json — current state
3. Read .a1/tasks.json — task list
4. Read TODO.md — detailed phases
5. Continue work from checkpoint
```

---

## WHAT IS THIS

**PocketCoder-A1** — autonomous coding agent that:
- Works without human intervention
- Saves state between sessions (checkpoint)
- Auto-restarts when context fills up
- Validates its work (tests, lint)

---

## PROJECT STRUCTURE

```
pocketcoder-a1/
├── a1/                      # Main code
│   ├── __init__.py          # Version
│   ├── checkpoint.py        # State between sessions
│   ├── tasks.py             # Task management
│   ├── validator.py         # Validation (tests, lint)
│   ├── loop.py              # Session loop
│   ├── dashboard.py         # Web UI
│   └── cli.py               # CLI commands
│
├── .a1/                     # Data (created on init)
│   ├── checkpoint.json      # Current state
│   ├── tasks.json           # Task list
│   ├── sessions/            # Session history
│   └── checkpoints/         # Checkpoint archive
│
├── BACKLOG.md               # Full scope
├── TODO.md                  # Detailed phases
├── CLAUDE.md                # This file
└── pyproject.toml           # pip install
```

---

## CLI COMMANDS

```bash
pca init <dir>           # Initialize project
pca task add "..."       # Add task
pca think "..."          # Add raw thought
pca tasks                # Show all tasks
pca start                # Start autonomous work
pca status               # Current status
pca validate             # Run validation
pca ui                   # Web dashboard
pca log                  # Session history
```

---

## AUTONOMOUS WORK PROTOCOL

```
1. SESSION START
   └── Read checkpoint.json
   └── Read tasks.json
   └── Identify current task

2. WORK
   └── Take pending/in_progress task
   └── Execute subtasks
   └── Validate after each change

3. VALIDATION
   └── python -m py_compile (syntax)
   └── pytest (tests)
   └── ruff check (lint)
   └── If FAIL → fix
   └── If OK → commit

4. CONTEXT MONITORING
   └── Check /tokens every 10-15 min
   └── At 70%+ → save checkpoint → exit

5. CHECKPOINT FORMAT
   └── What was done
   └── Which files changed
   └── What decisions were made
   └── What to do next
```

---

## SUCCESS CRITERIA

### Per task:
- [ ] Code written
- [ ] Syntax OK (py_compile)
- [ ] Tests pass (pytest)
- [ ] Lint clean (ruff)
- [ ] Git commit done
- [ ] success_criteria from task verified

### Per project:
- [ ] `pca init` works
- [ ] `pca task add` works
- [ ] `pca start` launches agent
- [ ] Checkpoint saves correctly
- [ ] Can stop and continue
- [ ] Web UI works

---

## PROVIDERS

| Provider | Command | Requires |
|----------|---------|----------|
| claude-max | `pca start` | Max subscription |
| claude-api | `pca start --provider claude-api` | API key |
| ollama | `pca start --provider ollama` | Local model |

---

## CURRENT STATUS

**Version:** 0.1.0 (MVP)

**Done:**
- [x] Project structure
- [x] checkpoint.py
- [x] tasks.py
- [x] validator.py
- [x] loop.py (basic)
- [x] cli.py
- [x] dashboard.py (Web UI)

**In Progress:**
- See TODO.md and .a1/tasks.json
