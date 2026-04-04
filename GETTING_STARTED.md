# Getting Started with PocketCoder-A1

Step-by-step guide from zero to running agent.

---

## Step 1: Install

```bash
# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install PocketCoder-A1
pip install pocketcoder-a1

# Check it works
pca --version
# Expected: pca 0.2.4
```

## Step 2: Install Claude Code CLI

PocketCoder-A1 uses Claude Code CLI as the main engine.

```bash
npm i -g @anthropic-ai/claude-code
claude --version
```

If you don't have Node.js: https://nodejs.org/

If you use the `claude-api` provider instead of `claude-max`, Claude Code CLI is still needed for the default provider but not strictly required. See Step 5 for provider setup.

## Step 3: Initialize on your project

```bash
# Go to the project you want the agent to work on
cd /path/to/your-project

# Initialize A1
pca init .
```

This creates a `.a1/` directory with:
- `checkpoint.json` — agent state
- `tasks.json` — task list
- `config.json` — settings

## Step 4: Launch the dashboard

```bash
pca ui
```

Browser opens at `http://localhost:7331`. You should see the Dashboard page with empty metric cards and "Start Agent" button.

If you want to launch without opening the browser:
```bash
pca ui --no-browser
```

If your project is in a different directory:
```bash
pca ui -d /path/to/your-project
```

## Step 5: Configure the provider

In the dashboard, click **Settings** in the left menu.

### Option A: Claude Max (recommended)

If you have a Claude Max subscription ($100/month):

1. Select provider: **claude-max**
2. Click **Save**
3. That's it — works through Claude Code CLI, no API key needed

Make sure `claude` CLI is logged in. Run `claude` in terminal once to verify.

### Option B: Claude API

If you have an Anthropic API key:

1. Select provider: **claude-api**
2. Paste your API key in the **API Key** field
3. Click **Save**

Get an API key at https://console.anthropic.com/

### Option C: Ollama (local models)

If you want to use local models:

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3.1`
3. In Settings, select provider: **ollama**
4. Set model name (e.g. `llama3.1`)
5. URL defaults to `http://localhost:11434`
6. Click **Save**

Note: Ollama provider is experimental. Best results with claude-max.

## Step 6: Add tasks

Three ways to add tasks:

### Way 1: Quick Add (on Dashboard)

On the main Dashboard page, scroll to **Quick Add**. Type a title and optional description, click **Add**.

### Way 2: AI Transform (recommended for multiple tasks)

1. Go to **Tasks** page
2. Scroll to **AI Transform** section
3. Write your thoughts in free form, e.g.:
   ```
   I want to add a health endpoint, write tests for auth module,
   refactor the config to use environment variables
   ```
4. Click **Transform**
5. AI breaks your text into structured tasks with descriptions and success criteria
6. Review and click **Add Selected**

### Way 3: CLI

```bash
pca task add "Add /api/health endpoint"
pca task add "Write unit tests for auth"
pca tasks  # verify
```

## Step 7: Start the agent

Click the green **Start Agent** button on the Dashboard.

Or from CLI:
```bash
pca start                      # all tasks
pca start --task task_001      # single task only
```

## Step 8: Monitor

Once started, the dashboard shows:

- **Status badge**: WORKING (red) in the top right
- **Metric cards**: session number, tokens used, cost, duration, files modified
- **Live Log**: real-time feed of what the agent does — file reads (blue), edits (orange), bash commands (purple), thinking (yellow)
- **Recent Tasks**: progress updates with green checkmarks

The log updates every 2 seconds. Metrics update every 3 seconds. The timer ticks every second.

### Send a message to the agent

While the agent is running, a **Message to Agent** form appears. Type instructions like "also write documentation" or "use pytest, not unittest". The agent reads it at the start of the next session.

### Stop the agent

Click the red **Stop Agent** button. Or from CLI:
```bash
# Ctrl+C in the terminal where pca start is running
```

## Step 9: Check results

When the agent finishes:

- Status changes to **COMPLETED** (green badge)
- All tasks show green checkmarks
- Check the actual code changes in your project directory
- Agent log shows verification results (pytest, syntax checks)

The agent verifies its own work after each task:
- Runs `py_compile` on all .py files
- Runs `pytest` if tests exist
- Checks that files it claims to have created actually exist
- Checks success criteria from the task

If verification fails, the agent retries (up to 5 times).

---

## Troubleshooting

### "pca: command not found"

Make sure your venv is activated:
```bash
source .venv/bin/activate
```

### Dashboard won't start

Check if port 7331 is in use:
```bash
lsof -i :7331
```

### Agent doesn't start

Check that Claude Code CLI works:
```bash
claude --version
```

For `claude-api` provider, check your API key is set correctly in Settings.

### Agent finishes too quickly without doing anything

This can happen if `--max-turns` is too low or the prompt is unclear. Check the live log for details.

---

## CLI Reference

```bash
pca init .                           # Initialize project
pca task add "title"                 # Add task
pca task delete task_001             # Delete task
pca tasks                            # List all tasks
pca think "raw idea"                 # Add raw thought
pca start                            # Start agent (all tasks)
pca start --task task_001            # Single task
pca start --provider claude-api      # Use API provider
pca status                           # Current status
pca validate                         # Run validation
pca ui                               # Launch dashboard
pca ui --no-browser                  # Without opening browser
pca config                           # Show config
pca config set provider ollama       # Change setting
pca log                              # Session history
pca test                             # Run E2E tests
```
