# Screenshots Map — Article 01 (PocketCoder-A1) REWRITE

## AFTER /clear — READ THIS FIRST

```
1. Read THIS file: articles/01_pocketcoder/SCREENSHOTS_MAP.md
2. Read the OLD article for style reference: articles/01_pocketcoder/article_ru.md
3. Continue from "Reading progress" section below
4. Task: rewrite article 01 with fresh screenshots, updated diagrams, RU + EN
```

## What we're doing

REWRITING the first article (`articles/01_pocketcoder/`) — NOT creating a 4th article.
- Fresh screenshots (22 pcs) showing full flow from empty dashboard to completed tasks
- Updated mermaid diagrams with cause-effect chains, CLI flags, internal logic
- Article text RU + EN in the same style as the original
- Rename screenshots from "Снимок экрана..." to descriptive English names
- Commit everything to git (png as-is, no quality loss)

## Style reference (from article_ru.md)

- Provocative title + quote subtitle
- Opens with personal story / problem
- "we" not "I", conversational tone
- Technical depth with code blocks and diagrams
- Bug tables / comparison tables
- Screenshots of dashboard
- Table of contents with anchors
- Current stats: 7086 lines, 15 modules, 8 pages, 24 API, 16 bugs, 6 E2E tests

## Screenshot Index

| # | Original time | New name | What's on screen | Article section |
|---|--------------|----------|-----------------|-----------------|
| 01 | 20.29.43 | 01_tasks_empty.png | Tasks page, 0 tasks, "No tasks yet". Forms: Add Task, Think, Bulk Import, AI Transform — all empty. Dark theme. Sidebar: A1 logo v0.2.4 | Empty state |
| 02 | 20.32.22 | 02_transform_input.png | Tasks page, AI Transform textarea filled: "I want to make a git clone of epotos-templates, then check how it is configured, and finally add block where you can switch from llama to deepseek. The settings should be easy to understand..." | Transform — user input |
| 03 | 20.32.34 | 03_transform_processing.png | Same page, TRANSFORM button clicked, "> processing..." visible | Transform — AI processing |
| 04 | 20.33.08 | 04_transform_preview.png | Transform done: "> 5 tasks generated". PREVIEW section: 5 green task cards (Clone epotos-templates / Analyze config / Design provider settings / Implement UI block / Verify E2E). All checked. "+ ADD SELECTED" button | Transform — preview |
| 05 | 20.33.19 | 05_tasks_5_pending.png | Tasks page: "[ 5 TASKS ]", all 5 cards visible with priorities #1-#5, all PENDING. Transform textarea reset to example | Tasks — 5 tasks created |
| 06 | 20.33.31 | 06_dashboard_idle.png | Dashboard page. 6 cards: Tasks 0/5, Session #2 IDLE, Tokens 0/0 (0%), Cost $0.000, Duration 16s, Files 0. Task list (5). Quick Add form. GREEN "START AGENT" button. Live-log: "Waiting for agent output..." Red STOPPED badge top-right | Dashboard — before start |
| 07 | 20.33.48 | 07_task_detail_empty.png | Task Detail page: "Clone epotos-templates repository". Pending, Priority #1. Description, Success Criteria, Phase N/A, Created 2026-03-05 20:33. 4 metric cards: 0 Tool Calls, 0 Sessions, 0 Tokens In, 0 Tokens Out. Execution Log: "No log entries for this task yet". Buttons: START TASK, DELETE | Task Detail — empty |
| 08 | 20.39.01 | DUPLICATE of 07? | Same as 07 — Task Detail "Clone epotos-templates", all zeros, empty log. ASK USER if different | QUESTION |
| 09 | 20.41.04 | 09_settings_claude_api.png | Settings page. Provider: "claude-api [EXPERIMENTAL]", yellow EXPERIMENTAL badge. API Key: "sk-ant-api03-..." masked. Session: Max Sessions=100, Max Turns=25, Session Delay=5, Context Threshold=0.7. Theme toggle. Config file path shown | Settings page |
| 10 | 20.42.05 | 10_dashboard_running_log.png | Dashboard scrolled down. Recent Tasks visible. RED "STOP AGENT" button. "MESSAGE TO AGENT" form with Send button. Live-log: agent working on task_014 — THINK, BASH (ToolSearch), OUT, READ (checkpoint.json, tasks.json), THINK, READ (Grep epotos-templates), BASH (ls, find). Timestamps 20:41-20:42 | Dashboard — agent working, live log |
| 11 | 20.42.17 | 11_task_detail_live.png | Task Detail "Clone epotos-templates" — now LIVE (green dot). Pending, Priority #1. Metrics: 11 Tool Calls, 8 Sessions. Execution Log: 16 entries — LIVE. Shows READ, THINK, OUT, BASH, READ entries. Session History: Session #2 (IDLE), Sessions #3-#8 (WORKING, 0/0 tokens, 0 tools each) | Task Detail — agent working on it |
| 12 | 20.42.52 | 12_dashboard_1_done.png | Dashboard. Tasks 1/5, Session #9 WORKING, Tokens 0/0, Cost $0.000, Duration 1m 18s, Files 0. GREEN RUNNING badge. Task list: task_014 "Clone epotos-templates" has green checkmark (done), moved to bottom. STOP AGENT button (red). MESSAGE TO AGENT form | Dashboard — 1 task completed |

| 13 | 20.43.24 | 13_dashboard_log_task015.png | Dashboard scrolled down. Live-log: agent analyzing epotos-templates on task_015 — BASH (find, Glob), READ (ollama.ts, ai-client.ts, ai-assistant.ts, status/route.ts, next.config.ts), THINK, Grep localhost:11434, EDIT tasks.json. "I now have a complete picture of the LLM provider setup." RECENT ACTIVITY: Agent started task_014 20:41:23, Config updated provider 20:41:07, Agent stopped/stop requested 20:40 | Dashboard — agent analyzing codebase |
| 14 | 20.43.42 | 14_tasks_2done_3pending.png | Tasks page. 5 tasks: task_016 "Design extensible provider settings architecture" IN PROGRESS #3 (orange gear). task_017 "Implement provider switching UI block" PENDING #4. task_018 "Verify provider switching works end-to-end" PENDING #5. task_014 "Clone epotos-templates" DONE (green check). task_015 "Analyze epotos-templates config" DONE (green check). Below: Add Task, Think, Bulk Import (example text), AI Transform forms | Tasks — 2 done, 1 in progress, 2 pending |
| 15 | 20.43.51 | 15_tasks_2done_clean.png | Same Tasks page moments later, cleaner shot. Same state: task_016 IN PROGRESS, task_017+018 PENDING, task_014+015 DONE. Slightly different scroll position | Tasks — clean view (may be duplicate of 14) |
| 16 | 20.46.00 | 16_dashboard_log_task016.png | Dashboard scrolled down. Agent on task_016 (Design provider settings). Live-log: WRITE/EDIT/READ status/route.ts, CHECK [Verification] PASSED. THINK "I'm in session #10, working on task_016". BASH [ToolSearch], READ checkpoint.json + tasks.json, READ provider-config.ts + provider-client.ts. THINK "Session #9 already created the provider architecture files". RECENT ACTIVITY same | Dashboard — agent designing provider architecture |
| 17 | 20.52.05 | 17_dashboard_message_typed.png | Dashboard scrolled down. Agent on task_016. Live-log: migrating files from ollama to provider-client — THINK, READ, EDIT ai-assistant.ts + chat/route.ts. **KEY DETAIL: Message to Agent field has typed text: "I want tp also make documentation and update memory about this case"** — user about to send instruction to running agent | Dashboard — user typing message to agent |
| 18 | 20.52.14 | 18_dashboard_message_sent.png | Dashboard moments after 17. Same live-log continuing: more EDITs on ai-assistant.ts, chat/route.ts, parse-input/route.ts, bulk-parse/route.ts. OUT "Now update the OllamaMessage reference..." **"Message queued at 20:52:07"** visible below message field — confirms message was sent to agent | Dashboard — message queued confirmation |
| 19 | 20.54.19 | 19_dashboard_5of5_running.png | Dashboard top. **5/5 tasks completed!** Session #11 WORKING. Tokens 0/0, Cost $0.000, Duration 4m 24s, Files 18 modified. GREEN RUNNING badge. All 5 tasks green checkmarks. STOP AGENT button. Agent still running (processing user message about documentation) | Dashboard — all 5 tasks done, agent still working |
| 20 | 20.54.45 | 20_livelog_verification_docs.png | Live-log close-up (dark terminal). task_016: "Only pre-existing errors remain (DocumentBlock type mismatch...)". CHECK [Verification] PASSED. THINK "The user wants me to: 1. Create documentation about the epotos-templates provider switching work 2." BASH [ToolSearch], READ checkpoint.json + tasks.json + MEMORY.md, Glob *.md | Live-log — verification passed, starting documentation per user request |
| 21 | 20.58.21 | 21_livelog_memory_write.png | Live-log close-up. task_016: EDIT epotos-templates/CLAUDE.md ×2, OUT "Documentation done. Now create the PocketCoder memory files." WRITE MEMORY.md, WRITE epotos-provider-switching.md. OUT "Now update checkpoint and mark complete." EDIT checkpoint.json ×2. CHECK [Verification] PASSED | Live-log — writing docs + memory files + final checkpoint |
| 22 | 21.22.35 | 22_dashboard_completed.png | Dashboard FINAL. **5/5 completed. Session #12 COMPLETED.** Duration 2m 59s. Files 23 modified. GREEN "COMPLETED" badge top-right. GREEN "START AGENT" button (agent stopped). All 5 tasks green checkmarks. Live-log shows last entries from documentation phase. **This is the end state — full cycle complete** | Dashboard — COMPLETED, all done |

### Light theme screenshots (23-26)

| # | Original time | New name | What's on screen | Article section |
|---|--------------|----------|-----------------|-----------------|
| 23 | 21.55.19 | 23_tasks_light.png | Tasks page LIGHT theme. 7 tasks total: task_019 "Clone reclamation project repository" PENDING #6, task_020 "Add DeepSeek provider integration" PENDING #7, task_014-018 all DONE. Add Task, Think, Bulk Import, AI Transform forms. Shows the UI works beautifully in both themes | Light theme — Tasks |
| 24 | 21.55.27 | 24_dashboard_light.png | Dashboard LIGHT theme. 5/7 completed, Session #12 COMPLETED. Tokens 0/0, Cost $0.000, Duration 2m 59s, Files 23. GREEN COMPLETED badge. Task list: task_019+020 pending (orange badges), task_014-016 done (green). Quick Add form. GREEN START AGENT button | Light theme — Dashboard |
| 25 | 21.55.33 | 25_dashboard_log_light.png | Dashboard scrolled down LIGHT theme. Live-log with dark terminal: EDIT CLAUDE.md, WRITE MEMORY.md + epotos-provider-switching.md, EDIT checkpoint.json, CHECK [Verification] PASSED. RECENT ACTIVITY: Transform confirmed 2 tasks added (21:53:10), Agent stopped (20:57:30), Message queued "I want to also make documentation..." (20:52:07), Agent started task_014 (20:41:23), Config updated provider (20:41:07) | Light theme — Live-log + Activity |
| 26 | 21.55.53 | 26_task_detail_done_light.png | Task Detail LIGHT theme: "Clone epotos-templates repository" DONE, Priority #1. Description + Success Criteria. 4 metric cards: 17 Tool Calls, 7 Sessions, 0 Tokens In, 0 Tokens Out. Execution Log 25 entries: BASH (ls, find, gh search repos), READ, THINK, OUT "Repository cloned successfully", EDIT tasks.json + checkpoint.json, CHECK [Verification] PASSED. Session History: Session #2 IDLE, Sessions #3-#8 WORKING | Light theme — Task Detail completed |

## Questions for user (ANSWER THESE — edit directly below each question)

### Q1: Screenshot 08 — duplicate?
Screenshot 08 (20.39.01) looks identical to 07 (20.33.48) — Task Detail "Clone epotos-templates", all zeros, empty execution log. Is this a duplicate or is there a difference I'm missing? Should I drop it from the article?
> **Answer:**

### Q2: Screenshot 15 — duplicate?
Screenshot 15 (20.43.51) looks nearly identical to 14 (20.43.42) — same Tasks page with 2 done + 3 pending, 9 seconds apart. Keep both or drop one?
> **Answer:**

### Q3: Light theme screenshots 23-26 — where in the article?
The 4 light theme screenshots (23-26) show the same state as dark theme (completed, tasks, etc.) but in light mode. Options:
- a) Separate section "Light theme" at the end
- b) Side-by-side pairs (dark+light) throughout the article
- c) Just a few as "bonus" / "theme toggle" demo
> **Answer:**

### Q4: Article scope — just epotos-templates case study, or full PocketCoder overview?
The 22 screenshots tell the story of one specific case (epotos-templates provider switching). Should the article:
- a) Focus ONLY on this case study (like a "watch me work" walkthrough)
- b) Mix case study with PocketCoder architecture explanation (like the original article_ru.md)
- c) Something else?
> **Answer:**

### Q5: Diagrams — what to include?
Which mermaid diagrams do you want?
- a) Cause-effect chain (text → tasks → agent → done) — matches the screenshot flow
- b) Architecture diagram (loop.py → validator → checkpoint → dashboard)
- c) CLI flags / subprocess (how claude is called)
- d) All of the above
- e) Something else?
> **Answer:**

## Reading progress
- [x] Screenshots 01-06 read and described
- [x] Screenshots 07-12 read and described
- [x] Screenshots 13-18 read and described
- [x] Screenshots 19-22 read and described
- [ ] All renamed on disk
- [ ] Mermaid diagrams created (cause-effect, CLI flags, internal logic)
- [ ] Article RU written
- [ ] Article EN written
- [ ] Committed to git

## Flow so far (cause-effect chain from screenshots)

```
01: Empty Tasks page — no tasks exist yet
 |
02: User types raw text into AI Transform textarea (epotos-templates provider switching)
 |
03: Clicks TRANSFORM → "processing..." — AI breaks text into tasks
 |
04: AI generates 5 structured tasks with titles + descriptions → PREVIEW with checkboxes
 |
05: User clicks ADD SELECTED → 5 tasks created with auto-priorities #1-#5
 |
06: User goes to Dashboard → sees 0/5 tasks, Session #2 IDLE → clicks START AGENT
 |
07: User clicks task_014 → Task Detail page (empty, before agent touches it)
 |
08: (duplicate? or user revisited task detail later)
 |
09: User goes to Settings → shows claude-api provider, API key, session params
 |
10: Dashboard scrolled down — agent is RUNNING, live-log shows THINK/BASH/READ on task_014
 |
11: Task Detail for task_014 — now LIVE, 11 tool calls, 8 sessions, execution log filling
 |
12: Dashboard — 1/5 tasks done (task_014 checked), Session #9, Duration 1m18s, still RUNNING
 |
13: Agent analyzes epotos-templates codebase — reads ollama.ts, ai-client.ts, next.config.ts, greps localhost:11434
 |
14: Tasks page — 2/5 done (014+015), task_016 IN PROGRESS, 017+018 PENDING
 |
15: (same as 14, cleaner shot)
 |
16: Agent designs provider architecture — reads provider-config.ts, provider-client.ts from session #9
 |
17: User types message to agent: "I want to also make documentation and update memory about this case"
 |
18: Message queued at 20:52:07 — agent continues migrating files from ollama to provider-client
 |
19: Dashboard — 5/5 tasks DONE! Session #11, Duration 4m24s, 18 files. Agent still running (processing user message)
 |
20: Verification PASSED — agent reads user message, starts documentation work
 |
21: Agent writes docs: CLAUDE.md updates, MEMORY.md, epotos-provider-switching.md, checkpoint update
 |
22: FINAL — Dashboard COMPLETED. Session #12, 23 files modified. Green COMPLETED badge. Full cycle done.
```

## Key narrative moments for the article

1. **Empty → Tasks via AI Transform** (01-05): raw text → 5 structured tasks in 30 seconds
2. **Start Agent** (06): one click, autonomous work begins
3. **Live monitoring** (10-13): real-time log with typed entries (BASH/READ/EDIT/THINK)
4. **Progress tracking** (12, 14): tasks completing one by one, green checkmarks appearing
5. **User → Agent communication** (17-18): message queued while agent works, picked up next session
6. **Verification system** (16, 20): CHECK [Verification] PASSED after each session
7. **Documentation on demand** (20-21): user asks agent to document, it writes CLAUDE.md + memory files
8. **Full completion** (19, 22): 5/5 tasks done, 23 files modified, green COMPLETED badge
