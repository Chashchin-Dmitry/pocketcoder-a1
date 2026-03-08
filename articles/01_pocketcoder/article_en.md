# I Built an Agent That Codes While I Sleep. It Lies.

> AI doesn't replace people, people just work more. So let's at least make AI work while we sleep.

---

I have 10+ projects. All through Claude Code. A subscription at 90 euros a month. And every evening the same thing: I close the laptop, the subscription sits idle. Next morning, context reset, explain everything again.

I thought: what if I write tasks before bed, press Start, and wake up to results? Not just "the agent wrote something", but with real verification. Because, as it turns out, the agent can write `"status": "COMPLETED"` in the checkpoint while tests are failing. Files it "created" don't exist on disk.

We caught the agent lying. And spent a week teaching it not to.

That's how **PocketCoder-A1** was born: an autonomous coding agent with verification, a web dashboard, and multi-provider support. 7086 lines of Python, 15 modules, zero frameworks.

---

## Table of Contents

1. [Why this exists](#1-why-this-exists)
2. [What is PocketCoder-A1](#2-what-is-pocketcoder-a1)
3. [Architecture](#3-architecture)
4. [Case study: epotos-templates](#4-case-study-epotos-templates)
5. [Dashboard: 8 pages, no frameworks](#5-dashboard)
6. [Conclusions and what's next](#6-conclusions-and-whats-next)

---

## 1. Why this exists

You know that feeling when AI tools don't replace your work but add to it? I started doing things more efficiently and ended up with more projects. Now there are 10+. All code-based. All through Claude Code.

The problem is simple. I'm working on one project while thoughts about another keep spinning: "need to add a DeepSeek provider", "rewrite the config", "write tests". I write them down somewhere. But my hands won't get to it for a week. Meanwhile the 90-euro subscription keeps ticking.

I tried OpenClaw. It didn't work, even with a good model nothing came together for me. Maybe I connected it wrong, maybe something else, but the result was zero.

So I decided to build my own. The idea is simple: write tasks, go for a walk or sleep, come back to results. The agent works in sessions, saves state, picks up the next task automatically. After each session it runs real verification: pytest, py_compile, file checks on disk. A web dashboard shows what's happening in real time. Primary provider is Claude Max, plus Claude API and Ollama as experimental.

Built primarily for myself. I'll actually use this product. But I put it in open source, maybe someone else will find it useful too.

---

## 2. What is PocketCoder-A1

CLI + web dashboard. Installation:

```bash
git clone https://github.com/Chashchin-Dmitry/pocketcoder-a1.git
cd pocketcoder-a1
pip install -e .
```

Initialize on any project:

```bash
pca init /path/to/your-project
pca ui -d /path/to/your-project
```

Dashboard opens at `http://localhost:7331`. Add tasks, press Start Agent, the agent works autonomously.

**Requirements:** Python 3.10+, [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`npm i -g @anthropic-ai/claude-code`).

| Attribute | Value |
|-----------|-------|
| Lines of code | 7086 |
| Modules | 15 |
| Dashboard pages | 8 |
| API endpoints | 24 |
| Providers | 3 |
| E2E tests | 6/6 |

How it differs from PocketCoder v1 (my previous project): v1 is a CLI agent for local models, interactive. A1 is an autonomous task manager + executor. Press a button, leave. A completely different product.

---

## 3. Architecture

The entire project is 15 Python modules. Zero frameworks. HTTP server on standard `http.server`, JSON via standard `json`, files via `pathlib`. The only external dependencies are `playwright` for E2E tests and optionally `anthropic` / `ollama` for alternative providers.

### 3.1 Full picture

Here's how the system works end-to-end, from `pca start` to completion:

![Full agent loop](1.png)

The agent starts, captures a baseline (validation snapshot BEFORE work), builds a prompt, works through Claude CLI, parses results in real time, verifies. If everything passes, it accepts the result. If not, it injects errors into the next session and tries again. Let's break down each piece.

### 3.2 Claude CLI as subprocess

The core of the system is launching Claude CLI as a subprocess. Sounds simple, but this is where the sneakiest problems were hiding.

![Claude CLI subprocess: flags, parsing, callback](2.png)

The final launch code:

```python
import os, subprocess

env = os.environ.copy()
env.pop("CLAUDECODE", None)  # without this, nested sessions crash

proc = subprocess.Popen(
    ["claude", "-p", prompt,
     "--dangerously-skip-permissions",
     "--no-session-persistence",
     "--max-turns", "25",
     "--verbose",
     "--output-format", "stream-json"],
    cwd=str(project_dir),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
```

Why exactly like this? Claude Code sets `CLAUDECODE=1` in the environment. The subprocess inherits this, the inner `claude` sees the variable and crashes: "cannot launch inside another session". Fix is one line, `env.pop`. Finding the cause took 2 hours because the error didn't show up in stdout.

Another undocumented quirk: `--output-format stream-json` without `--verbose` just goes silent. Nothing. Another 2 hours.

| Flag | Why |
|------|-----|
| `-p prompt` | Non-interactive mode |
| `--dangerously-skip-permissions` | Auto-approve all tool_use |
| `--no-session-persistence` | Don't pollute session history |
| `--max-turns 25` | Prevents infinite execution |
| `--verbose` | Required with stream-json + -p |
| `--output-format stream-json` | NDJSON stream instead of buffering |

With `stream-json`, Claude outputs NDJSON, one JSON object per line:

```json
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/src/app.py"}}]}}
{"type":"rate_limit_event","usage":{"input_tokens":12400,"output_tokens":3200}}
{"type":"result","result":"Task completed successfully."}
```

The parser classifies each event and sends it to the dashboard. `tool_use` named `Read` becomes type "read" (blue), `Bash` becomes "bash" (purple), `thinking` becomes yellow. 8 icon types total.

### 3.3 Verification: "Don't trust, verify"

The most important part of the system.

![Three-tier verification](4.png)

When the agent says "COMPLETED", we don't believe it. A three-tier check kicks in.

**Tier 1, BLOCKING.** If any check fails, the session is rejected: `py_compile` on all .py files, `pytest`, check that files actually exist on disk, check `success_criteria` from the task.

**Tier 2, WARNING.** Results are only logged: `ruff`, `build`, `git diff`.

**Tier 3, ANTI-LOOP.** Protection against infinite cycles. Before the first session we capture a baseline, a snapshot of all pre-existing issues. Old bugs don't count. If the agent can't fix a problem in 5 attempts, the task is marked BLOCKED and the agent moves to the next one. On retry, errors are injected directly into the prompt: "VERIFICATION FAILED, attempt 2/5, BLOCKING: tests 2 failed".

### 3.4 Providers

![Three providers, shared pipeline](6.png)

| Provider | How it works | Requires |
|----------|-------------|----------|
| claude-max | CLI subprocess, Stream-JSON, all native tools | Claude Max subscription |
| claude-api | Anthropic SDK, agentic loop, 6 tools | API key |
| ollama | Text streaming, no tool calling | Local Ollama |

Claude Max is the primary provider. Claude API and Ollama are **EXPERIMENTAL**. If you want to help, GitHub PRs welcome. I'm one person, can't physically polish everything. Built it for myself, if someone wants to adapt it, I'll gladly accept contributions.

### 3.5 Real-time data flow

![Data flow: agent, dashboard, browser](3.png)

Claude CLI outputs NDJSON, the parser in `loop.py` puts it in `AGENT_LOG_BUFFER`, AJAX `/api/log` picks it up every 2 seconds, browser renders it. Metrics flow in parallel: `rate_limit_event` updates `_session_metrics`, `/api/status` serves them every 3 seconds to 6 cards. Timer ticks via JavaScript every second.

### 3.6 Task lifecycle

![Tasks: creation, priorities, states](5.png)

Three ways to create a task. CLI via `pca task add`. Quick Add form on the dashboard. Or AI Transform, where you type raw text and AI breaks it into structured tasks with priorities and criteria. Priorities change via drag-and-drop. States: PENDING, IN PROGRESS, DONE or BLOCKED.

---

## 4. Case study: epotos-templates

A real case. epotos-templates is a project for a company, document processing + template generation. I needed to add provider switching (from Ollama to DeepSeek). I wrote down my thoughts in free form and launched A1.

### Step 1: Empty page, 5 tasks in 30 seconds

I open the dashboard. Tasks page is empty:

![Empty tasks page](01_tasks_empty.png)

Instead of manually formulating tasks, I use AI Transform. I just type raw text: "I want to clone epotos-templates, check how providers are configured, add a block for switching from llama to deepseek..."

![Typing text into AI Transform](02_transform_input.png)

I press Transform:

![Processing](03_transform_processing.png)

A few seconds later, 5 structured tasks with descriptions and success criteria:

![Preview of 5 tasks](04_transform_preview.png)

I click "Add Selected", tasks created with priorities #1-#5:

![5 tasks created](05_tasks_5_pending.png)

### Step 2: Launch

Dashboard. 0/5 tasks, IDLE. I press Start Agent:

![Dashboard before start](06_dashboard_idle.png)

First task details before work begins:

![Task detail](07_task_detail_empty.png)

Settings, selecting claude-api, entering API key:

![Provider settings](09_settings_claude_api.png)

### Step 3: Agent working

Log lines appear in real time. THINK, BASH, READ:

![Agent working, live log](10_dashboard_running_log.png)

Task Detail: 11 tool calls, log filling up:

![Task detail, agent working](11_task_detail_live.png)

### Step 4: First result

1/5 tasks done. Green checkmark. Agent automatically moved to the next one:

![1 task done](12_dashboard_1_done.png)

Agent analyzing the codebase, reading ollama.ts, ai-client.ts, grepping localhost:11434:

![Codebase analysis](13_dashboard_log_task015.png)

### Step 5: Progress

2/5 tasks done, task_016 in progress:

![2 done, 1 in progress](14_tasks_2done_3pending.png)

![Clean view](15_tasks_2done_clean.png)

Agent designing provider architecture:

![Designing architecture](16_dashboard_log_task016.png)

### Step 6: Message to agent

While the agent works, I type in the "Message to Agent" form, I want it to write documentation too:

![Typing a message](17_dashboard_message_typed.png)

Message queued, the agent will read it next session:

![Message sent](18_dashboard_message_sent.png)

### Step 7: All done

5/5 tasks! Agent still working, processing my documentation request:

![5/5 tasks, agent still working](19_dashboard_5of5_running.png)

Verification passed, agent writing documentation:

![Verification + documentation](20_livelog_verification_docs.png)

Updating CLAUDE.md, creating MEMORY.md:

![Writing documentation](21_livelog_memory_write.png)

### Final

COMPLETED. 5/5 tasks, 12 sessions, 23 files modified:

![COMPLETED](22_dashboard_completed.png)

### Light theme

The dashboard works in both themes:

![Tasks, light](23_tasks_light.png)

![Dashboard, light](24_dashboard_light.png)

![Log, light](25_dashboard_log_light.png)

![Task detail, light](26_task_detail_done_light.png)

---

## 5. Dashboard

3491 lines of pure Python. No React, no Vue, no Flask. Standard `http.server` + `string.Template`. All CSS, JavaScript and HTML in one file.

### 8 pages

| Page | URL | What it does |
|------|-----|-------------|
| Dashboard | `/` | 6 metric cards, Start/Stop, live log, Quick Add |
| Tasks | `/tasks` | Task list + drag-and-drop + bulk add + AI Transform |
| Task Detail | `/task/{id}` | Full view + logs + metrics + Start/Stop/Delete |
| Sessions | `/sessions` | Session history with metrics |
| Activity Log | `/log` | Action timeline |
| Settings | `/settings` | Provider, API key, parameters |
| Commits | `/commits` | Git history with type icons |
| Transform | `/transform` | Raw text, AI, tasks |

### 6 metric cards

| Card | Data |
|------|------|
| Tasks | `2/5 done` + progress bar |
| Session | `#3` + WORKING/IDLE/COMPLETED |
| Tokens | `12.4K in / 3.2K out` + context progress |
| Cost | `$0.08` per session |
| Duration | `48s` (live timer, ticks every second) |
| Files | `3 modified` |

The log is styled like macOS Terminal. Dark background, monospace font, 8 icon types (read/edit/write/bash/thinking/text/metric/verify). Updates via AJAX every 2 seconds.

Full REST API with 24 endpoints. You can monitor from scripts:

```bash
curl http://localhost:7331/api/status | python -m json.tool
curl "http://localhost:7331/api/log?since=0" | python -m json.tool
```

---

## 6. Conclusions and what's next

PocketCoder-A1 works. 5 tasks on a real project in 13 minutes, autonomously. With verification, with live logging, with the ability to send the agent a message while it's working.

Autonomous sessions work: press Start, leave, come back to results. Verification actually catches the lying agent on three levels: blocking, warning, anti-loop. Dashboard shows everything in real time. Queue Message lets you write to the agent while it works.

In progress: auto-checkpoint at 70% context, git integration (branches + atomic commits), PyPI + uv release.

We're in the middle of a vibe-coding boom right now. It would be cool to have more tools that optimize your workflow. Not replacing humans, extending capabilities. You sleep, your subscription works.

---

**PocketCoder-A1** is about open source.

**GitHub:** [github.com/Chashchin-Dmitry/pocketcoder-a1](https://github.com/Chashchin-Dmitry/pocketcoder-a1)

---

I'd appreciate a like and a subscribe to the channel :)
[https://t.me/notes_from_cto](https://t.me/notes_from_cto)

Our website: [https://bvmax.ru/ai](https://bvmax.ru/ai)
