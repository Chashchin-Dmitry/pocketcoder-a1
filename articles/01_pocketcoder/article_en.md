# PocketCoder-A1: How I Made My Claude Work Three Shifts

> AI doesn't replace people, people just work more. So let's at least make AI work at night.

---

It so happens that I pay 100 euros a month for Claude Code. A hefty sum that evaporates almost instantly when your account becomes a testing ground of 10+ projects, where 7-8 are mine and 2-3 are my wife's. 

Sharing a subscription is generally an expensive habit, but I don't mind. 

It so happens that I've developed a kind of addiction to building projects with Claude - I constantly want to create something in it. It's not that I have a light workload at my job - not at all. It's just that the ease of building projects on Opus 4.6 and the expensive subscription provoke my brain to load the AI 24/7. It gets absurd - before bed I try to prepare task drafts that I plan to do tomorrow, squeezing Claude as much as possible for tokens on analysis and studying the project. The kind of thing I try to avoid during the day, because I might hit the usage limit.  


It was during one of these planning sessions that I thought - damn, it would be great to set up Claude so that I could write tasks for it, and it would complete them overnight, not just plan like I'm doing now. And ideally, it would also verify its own results.  


That's how **PocketCoder-A1** was born: an autonomous coding agent with verification, a web dashboard, and multi-provider support. 7086 lines of Python, 15 modules, not a single framework.

---

## Table of Contents

1. [Why this even exists](#1-why-this-even-exists)
2. [What is PocketCoder-A1](#2-what-is-pocketcoder-a1)
3. [Architecture](#3-architecture)
4. [Case study: epotos-templates](#4-case-study-epotos-templates)
5. [Dashboard: 8 pages, no frameworks](#5-dashboard)
6. [Conclusions and what's next](#6-conclusions-and-whats-next)

---

## 1. Why this even exists

Actually, my thinking went even further, although I sat down to build the first mockups the very same evening when the idea really hit me. 

The idea is this. I'm working on one project, and thoughts about another keep spinning in my head: "need to add a DeepSeek provider", "rewrite the config", "write tests". 

And the tasks are written down. But my hands won't get to them for a week. Meanwhile the 90-euro subscription keeps ticking.

I tried OpenClaw. It didn't work, even with a good model nothing came together for me at all. Maybe I connected it wrong, maybe something else, but the result was zero. I could honestly write a separate article about those guys, because not a single project, not even a simple website parser, worked for me on it. 

So I decided to write my own. The idea is simple: wrote tasks, went for a walk or to sleep, came back to the result. The agent works in sessions, saves state, picks up the next task by itself. After each session a real check runs: pytest, py_compile, checking files on disk. A web dashboard shows what's happening in real time. Primary provider is Claude Max, plus Claude API and Ollama as experimental.

Built primarily for myself. I actually already use this, but I put it in open source, maybe someone else will find it useful too.

---

## 2. What is PocketCoder-A1

Let me decode the strange letter A in the name. It's Autonomous. And 1, as in first version. Who knows, maybe it'll take off and I'll need to write updates. 

CLI + web dashboard. Installation:

```bash
pip install pocketcoder-a1
```

Initialize on any project:

```bash
pca init /path/to/your-project
pca ui
```

Dashboard opens at `http://localhost:7331`. Add tasks, press Start Agent, the agent works autonomously.

**Requirements:** Python 3.10+, [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`npm i -g @anthropic-ai/claude-code`).

| Parameter | Value |
|-----------|-------|
| Lines of code | 7086 |
| Modules | 15 |
| Dashboard pages | 8 |
| API endpoints | 24 |
| Providers | 3 |
| E2E tests | 6/6 |

How it differs from PocketCoder v1 (my [previous project](https://habr.com/ru/articles/991022/)): v1 is a CLI agent for local models, interactive. A1 is an autonomous task manager + executor. Pressed a button, left. A completely different product. Maybe in the future I'll think about how to merge them. 

And yes, an update for the regular PocketCoder is coming soon! 

---

## 3. Architecture

The entire project is 15 Python modules. Not a single framework. HTTP server on standard `http.server`, JSON is standard `json`, files via `pathlib`. The only external dependencies are `playwright` for E2E tests and optionally `anthropic` / `ollama` for alternative providers.

### 3.1 The full picture

Here's how the entire system works, from `pca start` to completion:

![Full agent loop](1.png)

The agent starts, captures a baseline (validation snapshot BEFORE work), builds a prompt, works through Claude CLI, parses the result in real time, verifies. If everything's ok, accepts the result. If not, injects errors into the next session and tries again. Let's break down each piece.

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

Why exactly like this? Claude Code sets the variable `CLAUDECODE=1` in the environment. The subprocess inherits this, the inner `claude` sees the variable and crashes: "cannot launch inside another session". Fix is one line `env.pop`. Finding the cause took 2 hours, because the error didn't show up in stdout.

Another undocumented quirk: `--output-format stream-json` without `--verbose` just goes silent. Silence. Another 2 hours to find.

| Flag | Why |
|------|-----|
| `-p prompt` | Non-interactive mode |
| `--dangerously-skip-permissions` | Auto-approve all tool_use |
| `--no-session-persistence` | Don't pollute session history |
| `--max-turns 25` | Protection from infinite work |
| `--verbose` | Required with stream-json + -p |
| `--output-format stream-json` | NDJSON stream instead of buffering |

With `stream-json` Claude outputs NDJSON, one JSON object per line:

```json
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/src/app.py"}}]}}
{"type":"rate_limit_event","usage":{"input_tokens":12400,"output_tokens":3200}}
{"type":"result","result":"Task completed successfully."}
```

The parser classifies each event and sends it to the dashboard. `tool_use` with the name `Read` becomes type "read" (blue), `Bash` is "bash" (purple), `thinking` is yellow. 8 icon types total.

### 3.3 Verification: "Don't trust, verify"

The most important part of the system. While testing, the agent would prematurely write completed. Meaning it made 1-2 requests and that's enough for it - the AI considers it did its job. There's actually an explanation for this. When you make a request via API, it's 1 request = 1 response. But when the request comes from the web, the system under the hood automatically does minimal reasoning, and somewhere it can pull its own custom skills (instructions for working with certain modules more efficiently. Very popular for Excel/Word, but actually not only). 


![Three-tier verification](4.png)

When the agent says "COMPLETED", we don't believe it. A three-tier check kicks in.

**Tier 1, BLOCKING.** If even one check fails, the session is not accepted: `py_compile` on all .py files, `pytest`, checking that files actually exist on disk, checking `success_criteria` from the task.

**Tier 2, WARNING.** The result is only logged: `ruff`, `build`, `git diff`.

**Tier 3, ANTI-LOOP.** Protection from infinite loops. We want to burn tokens here, but still efficiently :)
Before the first session we make a baseline, a snapshot of all existing issues. Old bugs don't count. If the agent can't fix a problem in 5 attempts, the task is marked BLOCKED, the agent moves to the next one. On retry, errors are injected right into the prompt: "VERIFICATION FAILED, attempt 2/5, BLOCKING: tests 2 failed".

### 3.4 Providers

![Three providers, shared pipeline](6.png)

| Provider | How it works | Requires |
|----------|-------------|---------|
| claude-max | CLI subprocess, Stream-JSON, all native tools | Claude Max subscription |
| claude-api | Anthropic SDK, agentic loop, 6 tools | API key |
| ollama | Text streaming, no tool calling | Local Ollama |

Claude Max is the primary. And I'll be honest, the other providers are in a very raw state. I'm not used to asking for help, but if the project idea interests you - please help and get them into proper shape :) I'm not sure I can manage. 

### 3.5 Real-time data flow

![Data flow: agent, dashboard, browser](3.png)

Claude CLI outputs NDJSON, the parser in `loop.py` puts it in `AGENT_LOG_BUFFER`, AJAX `/api/log` picks it up every 2 seconds, the browser renders it. Metrics flow in parallel: `rate_limit_event` updates `_session_metrics`, `/api/status` serves them every 3 seconds to 6 cards. The timer ticks via JavaScript every second.

### 3.6 Task lifecycle

![Tasks: creation, priorities, states](5.png)

Three ways to create a task. CLI via `pca task add`. Quick Add form on the dashboard. Or AI Transform, where you type raw text and AI breaks it into structured tasks with priorities and criteria. Priorities change via drag-and-drop. States: PENDING, IN PROGRESS, DONE or BLOCKED.

---

## 4. Case study: epotos-templates

A real case. epotos-templates is an internal tool for a company - you feed it raw text, a sample presentation, or a document, and it generates reusable templates from them. The app runs on a local Ollama instance. We needed to add a second LLM provider (DeepSeek) so users could switch between models depending on the task. I wrote down my thoughts in free form and launched A1.

### Step 1: Empty page, 5 tasks in 30 seconds

I open the dashboard. The Tasks page is empty:

![Empty tasks page](01_tasks_empty.png)

Instead of manually formulating tasks, I use AI Transform. I just type raw text: "I want to clone epotos-templates, check how providers are configured, add a block for switching from llama to deepseek..."

![Typing text into AI Transform](02_transform_input.png)

I press Transform:

![Processing](03_transform_processing.png)

A few seconds later, 5 structured tasks with descriptions and success criteria:

![Preview of 5 tasks](04_transform_preview.png)

I press "Add Selected", tasks created with priorities #1-#5:

![5 tasks created](05_tasks_5_pending.png)

### Step 2: Launch

Dashboard. 0/5 tasks, IDLE. I press Start Agent:

![Dashboard before start](06_dashboard_idle.png)

Details of the first task before work begins:

![Task detail](07_task_detail_empty.png)

Settings, selecting claude-api, entering API key:

![Provider settings](09_settings_claude_api.png)

### Step 3: Agent working

Lines appear in the log in real time. THINK, BASH, READ:

![Agent working, live log](10_dashboard_running_log.png)

Task Detail: 11 tool calls, log filling up:

![Task detail, agent working](11_task_detail_live.png)

### Step 4: First result

1/5 tasks done. Green checkmark. The agent automatically moved to the next one:

![1 task done](12_dashboard_1_done.png)

The agent analyzes the codebase, reads ollama.ts, ai-client.ts, greps localhost:11434:

![Codebase analysis](13_dashboard_log_task015.png)

### Step 5: Progress

2/5 tasks done, task_016 in progress:

![2 done, 1 in progress](14_tasks_2done_3pending.png)

![Clean view](15_tasks_2done_clean.png)

The agent designs the provider architecture:

![Designing architecture](16_dashboard_log_task016.png)

### Step 6: Message to agent

While the agent works, I type in the "Message to Agent" form, I want it to write documentation too:

![Typing a message](17_dashboard_message_typed.png)

Message in queue, the agent will read it next session:

![Message sent](18_dashboard_message_sent.png)

### Step 7: All done

5/5 tasks! The agent is still working, processing my message about documentation:

![5/5 tasks, agent still working](19_dashboard_5of5_running.png)

Verification passed, the agent writes documentation:

![Verification + documentation](20_livelog_verification_docs.png)

Updates CLAUDE.md, creates MEMORY.md:

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
|------|-----|------------|
| Dashboard | `/` | 6 metric cards, Start/Stop, live log, Quick Add |
| Tasks | `/tasks` | List + drag-and-drop + bulk add + AI Transform |
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

PocketCoder-A1 works. 5 tasks on a real project in 13 minutes, autonomously. With verification, with live log, with the ability to send a message to the agent right while it's working.

Autonomous sessions work: pressed Start, left, came back to the result. Verification actually catches the lying agent on three levels: blocking, warning, anti-loop. Dashboard shows everything in real time. Queue Message lets you write to the agent while it works.

In development: auto-checkpoint at 70% context, git integration (branches + atomic commits), PyPI + uv release.


---

**PocketCoder-A1** is about open source.

**GitHub:** [github.com/Chashchin-Dmitry/pocketcoder-a1](https://github.com/Chashchin-Dmitry/pocketcoder-a1)

---

I'd appreciate a follow on LinkedIn :)
[Dmitrii Chashchin on LinkedIn](https://www.linkedin.com/in/dmitrii-chashchin-02844125b/)

Our website: [https://bvmax.ru/ai](https://bvmax.ru/ai)
