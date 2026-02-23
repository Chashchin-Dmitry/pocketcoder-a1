# PocketCoder-A1

**Autonomous Coding Agent with Web Dashboard**

A1 works on your tasks autonomously — you add tasks, start the agent, watch progress in the dashboard.

---

## Quick Start (5 steps)

```bash
# 1. Clone and install
git clone https://github.com/Chashchin-Dmitry/pocketcoder-a1.git
cd pocketcoder-a1
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Install browser for E2E tests (optional)
pip install playwright requests
playwright install chromium

# 3. Initialize in any project
pca init /path/to/your-project

# 4. Add tasks
pca task add "Add login page" -d /path/to/your-project
pca task add "Write unit tests" -d /path/to/your-project

# 5. Launch dashboard
pca ui -d /path/to/your-project
# Opens http://localhost:7331
```

**Requirements:** Python 3.10+, [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed (`npm i -g @anthropic-ai/claude-code`)

---

## Web Dashboard

Open `http://localhost:7331` after running `pca ui`. 7 pages:

| Page | What it does |
|------|-------------|
| **Dashboard** | Status cards, task list, Quick Add form, Start/Stop agent, Live Log |
| **Tasks** | All tasks with priority badges (#1 #2 #3), drag-and-drop reorder, Add Task + Add Thought forms |
| **Sessions** | Current and previous session details |
| **Activity Log** | Timeline of all actions (started, stopped, task added) |
| **Commits** | Git commit history |
| **Transform** | Paste raw text -> AI breaks it into structured tasks |
| **Settings** | Theme toggle (dark/light), provider info |

### Key features:
- **Live Agent Log** — see what Claude is doing in real-time (action icons + raw log)
- **Queue Message** — send instructions to running agent (appears when agent is Running)
- **Drag-and-Drop** — reorder task priorities on Tasks page
- **Dark Theme** — click moon icon top-right
- **Transform** — paste messy notes, AI creates structured tasks with checkboxes

---

## How to Test (step by step)

### Option A: Use the dashboard (recommended)

```bash
source .venv/bin/activate

# Start dashboard on any project
pca ui -d /path/to/your-project
```

Then in browser at `http://localhost:7331`:

1. **Add tasks** — Quick Add form on Dashboard, or Tasks page
2. **Start Agent** — green button, watch status change to "Running"
3. **Watch Live Log** — "Agent Live Log" panel shows what Claude does
4. **Send message** — "Message to Agent" form appears when running
5. **Stop** — red "Stop Agent" button
6. **Transform** — go to Transform page, paste text, click "AI Transform"
7. **Check results** — Tasks page shows green checkmarks for completed tasks

### Option B: CLI only

```bash
source .venv/bin/activate

pca init ./my-project
pca task add "Create hello.py with greet function" -d ./my-project
pca start -d ./my-project          # Runs agent in terminal
pca status -d ./my-project         # Check progress
pca tasks -d ./my-project          # See task list
```

### Option C: Run E2E tests

```bash
source .venv/bin/activate

# Start dashboard in background
pca ui -d ./my-project --no-browser &

# Run vision-based tests (7 scenarios)
pca test -d ./my-project --no-vision

# Reports saved to .a1/test-reports/
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `pca init <dir>` | Initialize .a1/ in project |
| `pca task add "..."` | Add task with optional description |
| `pca think "..."` | Add raw thought/idea |
| `pca tasks` | Show all tasks |
| `pca start` | Start autonomous agent (CLI mode) |
| `pca status` | Show current status |
| `pca validate` | Run validation (syntax, tests, lint) |
| `pca ui` | Launch web dashboard on :7331 |
| `pca test` | Run E2E vision tests |
| `pca log` | Show session history |

Add `-d /path/to/project` to any command to specify project directory.

---

## Dashboard API (17 endpoints)

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | `/` | Dashboard page |
| GET | `/tasks` | Tasks page |
| GET | `/sessions` | Sessions page |
| GET | `/log` | Activity log page |
| GET | `/commits` | Git commits page |
| GET | `/transform` | Transform page |
| GET | `/settings` | Settings page |
| GET | `/api/status` | JSON: checkpoint + tasks + progress + running |
| GET | `/api/log?since=N` | JSON: agent log entries since index N |
| POST | `/add-task` | Add task (form: task, description) |
| POST | `/add-thought` | Add thought (form: thought) |
| POST | `/start` | Start agent |
| POST | `/stop` | Stop agent |
| POST | `/queue-message` | Message to agent (form: message) |
| POST | `/api/reorder` | Reorder tasks (JSON: {order: [ids]}) |
| POST | `/transform` | AI transform text to tasks (form: text) |
| POST | `/transform-confirm` | Confirm transformed tasks (JSON: {tasks}) |

---

## Project Structure

```
pocketcoder-a1/
├── a1/                      # Main code
│   ├── checkpoint.py        # State between sessions
│   ├── tasks.py             # Task management (priorities, reorder)
│   ├── validator.py         # Validation (syntax, tests, lint)
│   ├── loop.py              # Agent session loop (Claude CLI subprocess)
│   ├── dashboard.py         # Web UI (17 endpoints, inline HTML/CSS/JS)
│   ├── cli.py               # CLI commands (pca)
│   └── tester/              # Vision-based QA agent
├── .a1/                     # Data (created on pca init)
│   ├── checkpoint.json      # Current state
│   ├── tasks.json           # Task list with priorities
│   ├── queue.json           # Message queue for agent
│   ├── sessions/            # Session logs
│   └── checkpoints/         # Checkpoint archive
├── sandbox/                 # Test projects
│   ├── test-e2e/            # E2E test (3/3 tasks passed)
│   └── epotos-templates/    # Real project test (3/3 tasks passed)
├── CLAUDE.md                # Agent instructions
├── CURRENT_STAGE.md         # Status with cause-effect chains
└── pyproject.toml           # pip install -e .
```

---

## Providers

| Provider | Command | Requires |
|----------|---------|----------|
| claude-max | `pca start` | Claude Code CLI + Max subscription |
| claude-api | `pca start --provider claude-api` | ANTHROPIC_API_KEY |
| ollama | `pca start --provider ollama` | Local Ollama server |

---

## License

MIT
