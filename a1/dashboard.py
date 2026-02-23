#!/usr/bin/env python3
"""
PocketCoder-A1 Dashboard — Full-featured Web UI
"""

import html as html_mod
import json
import socket
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, urlparse

from .checkpoint import CheckpointManager
from .tasks import TaskManager

PROJECT_DIR = None
AGENT_RUNNING = False
AGENT_LOOP = None  # Reference to SessionLoop for stop control
ACTIVITY_LOG = []  # Live activity log
AGENT_LOG_BUFFER = []  # Live agent output lines for dashboard


def esc(text: str) -> str:
    """Escape HTML to prevent XSS"""
    return html_mod.escape(str(text)) if text else ""


def log_activity(action: str, details: str = "", status: str = "info"):
    """Log activity for dashboard"""
    ACTIVITY_LOG.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "details": details,
        "status": status  # info, success, error, warning
    })
    # Keep last 100 entries
    if len(ACTIVITY_LOG) > 100:
        ACTIVITY_LOG.pop(0)


def _classify_line(line: str) -> str:
    """Classify a Claude output line into a tool type for icon display"""
    lower = line.lower().strip()
    if any(kw in lower for kw in ["read(", "reading file", "read file", "reading ", "read "]):
        return "read"
    elif any(kw in lower for kw in ["edit(", "editing file", "edit file", "editing "]):
        return "edit"
    elif any(kw in lower for kw in ["write(", "writing file", "write file", "creating file", "created "]):
        return "write"
    elif any(kw in lower for kw in ["bash(", "running:", "$ ", "command", "terminal", "pytest", "ruff "]):
        return "bash"
    elif any(kw in lower for kw in ["let me", "i'll", "i need", "thinking", "analyzing", "looking"]):
        return "thinking"
    return "text"


def _on_agent_line(line: str, event_type: str = None):
    """Parse agent output line and add to live buffer.
    event_type: pre-classified type from stream-json parser
    (read/edit/write/bash/thinking/text/metric/verify)
    If not provided, falls back to heuristic classifier."""
    stripped = line.rstrip("\n")
    if not stripped:
        return
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "line": stripped,
        "type": event_type if event_type else _classify_line(line),
    }
    AGENT_LOG_BUFFER.append(entry)
    if len(AGENT_LOG_BUFFER) > 500:
        AGENT_LOG_BUFFER.pop(0)


CSS = '''
:root {
    --bg-primary: #f8f9fa;
    --bg-secondary: #ffffff;
    --bg-tertiary: #e9ecef;
    --text-primary: #212529;
    --text-secondary: #6c757d;
    --border-color: #dee2e6;
    --accent: #6366f1;
    --accent-light: #818cf8;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}

[data-theme="dark"] {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-tertiary: #0f0f23;
    --text-primary: #f8f9fa;
    --text-secondary: #9ca3af;
    --border-color: #374151;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
}

.layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    min-height: 100vh;
}

/* Sidebar */
.sidebar {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    padding: 20px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}

.logo {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.logo-sub {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 30px;
}

.nav-section {
    margin-bottom: 24px;
}

.nav-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    margin-bottom: 12px;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    color: var(--text-primary);
    text-decoration: none;
    margin-bottom: 4px;
    transition: background 0.2s;
}

.nav-item:hover {
    background: var(--bg-tertiary);
}

.nav-item.active {
    background: var(--accent);
    color: white;
}

.nav-item i {
    width: 18px;
    text-align: center;
}

/* Main content */
.main {
    padding: 24px 32px;
    overflow-y: auto;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
}

.page-title {
    font-size: 24px;
    font-weight: 600;
}

.header-actions {
    display: flex;
    gap: 12px;
    align-items: center;
}

/* Status badge */
.status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
}

.status-running { background: var(--success); color: white; }
.status-stopped { background: var(--danger); color: white; }
.status-completed { background: var(--accent); color: white; }

/* Cards */
.cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}

.card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
}
[data-theme="dark"] .card:hover {
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
}

.card-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.card-value {
    font-size: 32px;
    font-weight: 600;
}

.card-sub {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
}

/* Progress bar */
.progress {
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    margin-top: 12px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--success));
    border-radius: 3px;
    transition: width 0.3s;
}

/* Tasks list */
.task-list {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
}

.task-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.task-header h3 {
    font-size: 16px;
    font-weight: 600;
}

.task {
    display: flex;
    align-items: center;
    padding: 14px 20px;
    border-bottom: 1px solid var(--border-color);
    transition: background 0.2s;
}

.task:last-child {
    border-bottom: none;
}

.task:hover {
    background: var(--bg-tertiary);
}

.task-check {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 2px solid var(--border-color);
    margin-right: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex-shrink: 0;
}

.task-check.done {
    background: var(--success);
    border-color: var(--success);
    color: white;
}

.task-check.progress {
    background: var(--warning);
    border-color: var(--warning);
    color: white;
}

.task-content {
    flex: 1;
}

.task-title {
    font-weight: 500;
    margin-bottom: 4px;
}

.task-meta {
    font-size: 12px;
    color: var(--text-secondary);
}

.task-phase {
    background: var(--bg-tertiary);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    color: var(--text-secondary);
}

/* Activity log */
.activity {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    margin-top: 24px;
}

.activity-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color);
    font-weight: 600;
}

.activity-list {
    max-height: 300px;
    overflow-y: auto;
}

.activity-item {
    display: flex;
    gap: 12px;
    padding: 12px 20px;
    border-bottom: 1px solid var(--border-color);
    font-size: 13px;
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-time {
    color: var(--text-secondary);
    font-family: monospace;
    flex-shrink: 0;
}

.activity-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 5px;
    flex-shrink: 0;
}

.activity-dot.info { background: var(--accent); }
.activity-dot.success { background: var(--success); }
.activity-dot.warning { background: var(--warning); }
.activity-dot.error { background: var(--danger); }

.activity-text {
    flex: 1;
}

.activity-details {
    color: var(--text-secondary);
}

/* Forms */
.form-section {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    margin-top: 24px;
}

.form-section h3 {
    font-size: 16px;
    margin-bottom: 16px;
}

.form-row {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
}

input[type="text"] {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 14px;
}

input[type="text"]:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}

input[type="text"]::placeholder {
    color: var(--text-secondary);
}

textarea {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 14px;
    font-family: inherit;
    resize: vertical;
    min-height: 60px;
    box-sizing: border-box;
}
textarea:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
textarea::placeholder {
    color: var(--text-secondary);
}

.priority-badge {
    display: inline-block;
    background: var(--accent);
    color: white;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 4px;
}

.task[draggable="true"] {
    cursor: grab;
}
.task[draggable="true"]:active {
    cursor: grabbing;
}
.task.drag-over {
    border-top: 2px solid var(--accent);
}

/* Terminal-style log panel */
.log-panel {
    background: #1e1e2e;
    border-radius: 12px;
    margin-top: 24px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    border: 1px solid #313244;
}
.log-panel-header {
    padding: 10px 16px;
    background: #181825;
    border-bottom: 1px solid #313244;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.terminal-dots {
    display: flex;
    gap: 6px;
    align-items: center;
}
.terminal-dots span {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}
.terminal-dots .dot-red { background: #f38ba8; }
.terminal-dots .dot-yellow { background: #f9e2af; }
.terminal-dots .dot-green { background: #a6e3a1; }
.terminal-title {
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #6c7086;
    letter-spacing: 0.5px;
}
.log-feed {
    max-height: 340px;
    overflow-y: auto;
    padding: 4px 0;
    scrollbar-width: thin;
    scrollbar-color: #45475a #1e1e2e;
}
.log-feed::-webkit-scrollbar { width: 6px; }
.log-feed::-webkit-scrollbar-track { background: #1e1e2e; }
.log-feed::-webkit-scrollbar-thumb { background: #45475a; border-radius: 3px; }
.log-entry {
    display: flex;
    gap: 8px;
    padding: 3px 16px;
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    font-size: 12px;
    align-items: flex-start;
    line-height: 1.5;
    transition: background 0.15s;
}
.log-entry:hover {
    background: rgba(69, 71, 90, 0.3);
}
.log-entry i {
    width: 16px;
    text-align: center;
    flex-shrink: 0;
    font-size: 11px;
    margin-top: 2px;
}
.log-time {
    color: #585b70;
    font-size: 11px;
    flex-shrink: 0;
    user-select: none;
}
.log-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #cdd6f4;
}
.log-prompt {
    color: #a6e3a1;
    flex-shrink: 0;
    user-select: none;
}
.log-cursor {
    display: inline-block;
    width: 7px;
    height: 14px;
    background: #a6e3a1;
    animation: blink 1s step-end infinite;
    margin-left: 4px;
    vertical-align: text-bottom;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
.log-empty {
    padding: 20px 16px;
    color: #585b70;
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    font-size: 12px;
    text-align: center;
}
.raw-log {
    max-height: 300px;
    overflow-y: auto;
    padding: 12px 16px;
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
    background: #11111b;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
.log-toggle {
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #89b4fa;
    cursor: pointer;
    background: none;
    border: none;
    padding: 2px 8px;
    border-radius: 4px;
    transition: background 0.15s;
}
.log-toggle:hover {
    background: rgba(137, 180, 250, 0.1);
}
/* Pixel art indicator */
.px-icon {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 1px;
    flex-shrink: 0;
    margin-top: 5px;
    image-rendering: pixelated;
    box-shadow: 1px 0 0 0 currentColor, 0 1px 0 0 currentColor;
}
.log-label {
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    min-width: 44px;
    flex-shrink: 0;
    text-transform: uppercase;
}

button {
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: transform 0.1s, opacity 0.2s;
}

button:hover { filter: brightness(1.1); }
button:active { transform: scale(0.98); }

.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover { box-shadow: 0 4px 12px rgba(99,102,241,0.3); }
.btn-success { background: var(--success); color: white; }
.btn-success:hover { box-shadow: 0 4px 12px rgba(16,185,129,0.3); }
.btn-danger { background: var(--danger); color: white; }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); }

/* Global select styling */
select {
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 14px;
    cursor: pointer;
    width: 100%;
    transition: border-color 0.2s, box-shadow 0.2s;
}
select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
input[type="number"] {
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 14px;
    width: 100%;
    transition: border-color 0.2s, box-shadow 0.2s;
}
input[type="number"]:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
input[type="password"] {
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 14px;
    font-family: monospace;
    width: 100%;
    transition: border-color 0.2s, box-shadow 0.2s;
}
input[type="password"]:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}

/* Styled scrollbars */
.activity-list::-webkit-scrollbar { width: 6px; }
.activity-list::-webkit-scrollbar-track { background: transparent; }
.activity-list::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }

/* Toast notification */
.toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    padding: 12px 20px;
    background: var(--success);
    color: white;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 1000;
    animation: toast-in 0.3s ease, toast-out 0.3s ease 2s forwards;
}
@keyframes toast-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes toast-out { from { opacity: 1; } to { opacity: 0; transform: translateY(10px); } }

/* Settings-specific styles */
.settings-label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
    display: block;
}
.settings-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 8px;
}
.settings-hint {
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 6px;
}

/* Commit styling */
.commit-hash {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
}
.commit-msg {
    font-weight: 500;
}
.commit-time {
    font-size: 12px;
    color: var(--text-secondary);
}

/* Control buttons */
.controls {
    display: flex;
    gap: 12px;
    margin-top: 24px;
}

.controls form {
    flex: 1;
}

.controls button {
    width: 100%;
    padding: 14px;
    font-size: 15px;
}

/* Theme toggle */
.theme-toggle {
    background: none;
    border: 1px solid var(--border-color);
    padding: 8px 12px;
    cursor: pointer;
    border-radius: 8px;
    color: var(--text-primary);
}

/* Session details */
.session-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}

.session-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.session-title {
    font-weight: 600;
    font-size: 16px;
}

.session-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
}

.meta-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.meta-label {
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-secondary);
}

.meta-value {
    font-weight: 500;
}

/* Empty state */
.empty {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
}

.empty i {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
}

/* Pulsing indicator for running state */
.pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #fff;
    margin: 0 2px;
    animation: pulse-anim 1.5s ease-in-out infinite;
}

@keyframes pulse-anim {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.7); }
}

/* Live timer styling */
.live-timer {
    font-family: monospace;
    font-variant-numeric: tabular-nums;
}

@media (max-width: 1200px) {
    .cards {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 768px) {
    .layout {
        grid-template-columns: 1fr;
    }
    .sidebar {
        position: fixed;
        left: -260px;
        z-index: 100;
        transition: left 0.3s;
        width: 240px;
    }
    .sidebar.open {
        left: 0;
    }
    .hamburger {
        display: block !important;
    }
    .cards {
        grid-template-columns: 1fr;
    }
    .log-feed {
        max-height: none;
    }
}

.hamburger {
    display: none;
    background: none;
    border: 1px solid var(--border-color);
    padding: 8px 12px;
    cursor: pointer;
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 18px;
}

/* Task detail expandable — slide transition */
.task-detail {
    max-height: 0;
    overflow: hidden;
    padding: 0 20px 0 56px;
    border-bottom: 1px solid var(--border-color);
    transition: max-height 0.3s ease, padding 0.3s ease;
}
.task-detail.open {
    max-height: 400px;
    padding: 12px 20px 16px 56px;
}

.task-stages {
    display: flex;
    gap: 4px;
    margin-bottom: 12px;
}

.stage-step {
    flex: 1;
    height: 6px;
    border-radius: 3px;
    background: var(--bg-tertiary);
}

.stage-step.active {
    background: var(--warning);
}

.stage-step.done {
    background: var(--success);
}

.task-detail-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
}

.task-detail-meta dt {
    font-weight: 600;
    color: var(--text-primary);
}

.task-criteria {
    margin-top: 8px;
    padding: 8px 12px;
    background: var(--bg-tertiary);
    border-radius: 8px;
    font-size: 12px;
}

.task-clickable {
    cursor: pointer;
}
'''

HTML_TEMPLATE = Template('''<!DOCTYPE html>
<html lang="en" data-theme="$theme">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PocketCoder-A1 Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>''' + CSS + '''</style>
</head>
<body>
    <div class="layout">
        <aside class="sidebar">
            <div class="logo">
                <i class="bi bi-robot"></i> PocketCoder-A1
            </div>
            <div class="logo-sub">Autonomous Gnome v0.1.0</div>

            <nav>
                <div class="nav-section">
                    <div class="nav-title">Overview</div>
                    <a href="/" class="nav-item $nav_dashboard">
                        <i class="bi bi-speedometer2"></i> Dashboard
                    </a>
                    <a href="/tasks" class="nav-item $nav_tasks">
                        <i class="bi bi-list-check"></i> Tasks
                    </a>
                    <a href="/sessions" class="nav-item $nav_sessions">
                        <i class="bi bi-terminal"></i> Sessions
                    </a>
                </div>

                <div class="nav-section">
                    <div class="nav-title">Activity</div>
                    <a href="/log" class="nav-item $nav_log">
                        <i class="bi bi-journal-text"></i> Activity Log
                    </a>
                    <a href="/commits" class="nav-item $nav_commits">
                        <i class="bi bi-git"></i> Commits
                    </a>
                    <a href="/transform" class="nav-item $nav_transform">
                        <i class="bi bi-magic"></i> Transform
                    </a>
                </div>

                <div class="nav-section">
                    <div class="nav-title">Settings</div>
                    <a href="/settings" class="nav-item $nav_settings">
                        <i class="bi bi-gear"></i> Settings
                    </a>
                </div>
            </nav>
        </aside>

        <main class="main">
            <button class="hamburger" onclick="document.querySelector('.sidebar').classList.toggle('open')">
                <i class="bi bi-list"></i>
            </button>
            $content
        </main>
    </div>

    <script>
        // Theme toggle
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }

        // Load saved theme
        const saved = localStorage.getItem('theme');
        if (saved) {
            document.documentElement.setAttribute('data-theme', saved);
        }

        // Escape HTML
        function escHtml(s) {
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        // --- AJAX polling (dashboard page only) ---
        const pageName = '$page_name';
        let logIndex = 0;

        function fmtTokens(n) {
            if (!n || n === 0) return '0';
            if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
            if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
            return n.toString();
        }

        function fmtDuration(s) {
            if (!s || s <= 0) return '0s';
            if (s < 60) return s + 's';
            const m = Math.floor(s / 60);
            const sec = s % 60;
            return m + 'm ' + sec + 's';
        }

        function estimateCost(tokensIn, tokensOut, cacheRead) {
            // Claude Opus pricing (approximate): 15/M input, 75/M output, 1.5/M cache read
            const costIn = (tokensIn - (cacheRead || 0)) * 15 / 1000000;
            const costCache = (cacheRead || 0) * 1.5 / 1000000;
            const costOut = tokensOut * 75 / 1000000;
            return Math.max(0, costIn + costCache + costOut);
        }

        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    const badge = document.getElementById('status-badge');
                    if (badge) {
                        if (data.running) {
                            badge.className = 'status status-running';
                            badge.innerHTML = '<i class="bi bi-play-circle-fill"></i> <span class="pulse-dot"></span> Running';
                        } else if (data.checkpoint && data.checkpoint.status === 'COMPLETED') {
                            badge.className = 'status status-completed';
                            badge.innerHTML = '<i class="bi bi-check-circle-fill"></i> Completed';
                        } else {
                            badge.className = 'status status-stopped';
                            badge.innerHTML = '<i class="bi bi-stop-circle-fill"></i> Stopped';
                        }
                    }
                    const tc = document.getElementById('task-count');
                    if (tc && data.progress) {
                        tc.textContent = data.progress[0] + '/' + data.progress[1];
                    }
                    const sc = document.getElementById('session-count');
                    if (sc && data.checkpoint) {
                        sc.textContent = '#' + data.checkpoint.session;
                    }
                    const fc = document.getElementById('files-count');
                    if (fc && data.checkpoint) {
                        fc.textContent = (data.checkpoint.files_modified || []).length;
                    }
                    // Token metrics
                    const m = data.metrics || {};
                    const tokC = document.getElementById('tokens-count');
                    if (tokC) {
                        tokC.textContent = fmtTokens(m.tokens_in || 0) + ' / ' + fmtTokens(m.tokens_out || 0);
                    }
                    const tokSub = document.getElementById('tokens-sub');
                    if (tokSub && m.cache_read) {
                        tokSub.textContent = 'cache: ' + fmtTokens(m.cache_read);
                    }
                    const tokBar = document.getElementById('tokens-bar');
                    if (tokBar) {
                        const pct = Math.min(100, (m.context_percent || 0) * 100);
                        tokBar.style.width = pct + '%';
                        // Change color at threshold
                        if (pct >= 70) tokBar.style.background = '#ef4444';
                        else if (pct >= 50) tokBar.style.background = '#f59e0b';
                        else tokBar.style.background = 'var(--accent)';
                    }
                    // Context percent text
                    const ctxPct = document.getElementById('context-pct');
                    if (ctxPct) {
                        const pct = Math.round((m.context_percent || 0) * 100);
                        ctxPct.textContent = pct + '%';
                    }
                    // Cost
                    const costEl = document.getElementById('cost-value');
                    if (costEl) {
                        const cost = estimateCost(m.tokens_in || 0, m.tokens_out || 0, m.cache_read || 0);
                        costEl.textContent = '$$' + cost.toFixed(3);
                    }
                    // Duration
                    const durEl = document.getElementById('duration-value');
                    if (durEl) {
                        durEl.textContent = fmtDuration(m.session_duration || 0);
                    }
                    // Queue message section
                    const qms = document.getElementById('queue-msg-section');
                    if (qms) {
                        qms.style.display = data.running ? 'block' : 'none';
                    }
                })
                .catch(() => {});
        }

        function updateLog() {
            fetch('/api/log?since=' + logIndex)
                .then(r => r.json())
                .then(data => {
                    if (data.entries && data.entries.length > 0) {
                        const feed = document.getElementById('action-feed');
                        const rawlog = document.getElementById('raw-log');
                        if (feed && rawlog) {
                            data.entries.forEach(e => {
                                const labelMap = {read:'READ', edit:'EDIT', write:'WRITE', bash:'BASH', thinking:'THINK', text:'OUT', metric:'METRIC', verify:'CHECK'};
                                const colorMap = {read:'#89b4fa', edit:'#fab387', write:'#a6e3a1', bash:'#cba6f7', thinking:'#f9e2af', text:'#6c7086', metric:'#89dceb', verify:'#a6e3a1'};
                                const label = labelMap[e.type] || 'LOG';
                                const color = colorMap[e.type] || '#6c7086';
                                const pixelIcon = '<span class="px-icon" style="background:' + color + '"></span>';
                                feed.innerHTML += '<div class="log-entry">' + pixelIcon + '<span class="log-time">' + e.time + '</span><span class="log-label" style="color:' + color + '">' + label + '</span><span class="log-text">' + escHtml(e.line.substring(0,150)) + '</span></div>';
                                rawlog.textContent += e.line + '\\n';
                            });
                            feed.scrollTop = feed.scrollHeight;
                            rawlog.scrollTop = rawlog.scrollHeight;
                        }
                        logIndex = data.total;
                    }
                })
                .catch(() => {});
        }

        function sendQueueMessage(e) {
            e.preventDefault();
            const input = document.getElementById('queue-msg-input');
            const status = document.getElementById('queue-msg-status');
            if (!input.value.trim()) return;
            fetch('/queue-message', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'message=' + encodeURIComponent(input.value)
            }).then(r => r.json()).then(data => {
                status.textContent = 'Message queued at ' + new Date().toLocaleTimeString();
                input.value = '';
            }).catch(() => { status.textContent = 'Failed to send'; });
        }

        // Live timer tick (updates every second when running)
        let sessionStartTime = 0;
        let agentRunning = false;

        function tickTimer() {
            if (!agentRunning || !sessionStartTime) return;
            const elapsed = Math.floor(Date.now() / 1000 - sessionStartTime);
            const durEl = document.getElementById('duration-value');
            if (durEl) durEl.textContent = fmtDuration(elapsed);
        }

        // Toggle task detail on tasks page
        function toggleTaskDetail(taskId) {
            const el = document.getElementById('detail-' + taskId);
            if (el) el.classList.toggle('open');
        }

        if (pageName === 'dashboard') {
            // Wrap updateStatus to also track timer state
            const _origUpdateStatus = updateStatus;
            updateStatus = function() {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        agentRunning = data.running;
                        if (data.metrics && data.metrics.session_start) {
                            sessionStartTime = data.metrics.session_start;
                        }
                    }).catch(() => {});
                _origUpdateStatus();
            };
            setInterval(updateStatus, 3000);
            setInterval(updateLog, 2000);
            setInterval(tickTimer, 1000);
            updateStatus();
        } else if (pageName === 'tasks') {
            // No auto-reload on tasks page (drag-drop needs stable DOM)
        } else {
            setTimeout(() => location.reload(), 5000);
        }

        // --- Drag and Drop (tasks page) ---
        if (pageName === 'tasks') {
            let dragSrc = null;
            document.querySelectorAll('.task[draggable]').forEach(el => {
                el.addEventListener('dragstart', e => {
                    dragSrc = el;
                    el.style.opacity = '0.4';
                    e.dataTransfer.effectAllowed = 'move';
                });
                el.addEventListener('dragover', e => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                    el.classList.add('drag-over');
                });
                el.addEventListener('dragleave', () => {
                    el.classList.remove('drag-over');
                });
                el.addEventListener('drop', e => {
                    e.preventDefault();
                    el.classList.remove('drag-over');
                    if (dragSrc && dragSrc !== el) {
                        el.parentNode.insertBefore(dragSrc, el);
                        const order = [...document.querySelectorAll('.task[data-task-id]')]
                            .map(t => t.dataset.taskId);
                        fetch('/api/reorder', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({order})
                        }).then(() => location.reload());
                    }
                });
                el.addEventListener('dragend', () => {
                    el.style.opacity = '';
                });
            });
        }
    </script>
</body>
</html>
''')


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/' or path == '/index.html':
            self.send_page('dashboard')
        elif path == '/tasks':
            self.send_page('tasks')
        elif path == '/sessions':
            self.send_page('sessions')
        elif path == '/log':
            self.send_page('log')
        elif path == '/commits':
            self.send_page('commits')
        elif path == '/settings':
            self.send_page('settings')
        elif path == '/transform':
            self.send_page('transform')
        elif path == '/api/status':
            self.send_json_status()
        elif path.startswith('/api/log'):
            self.send_json_log()
        elif path == '/api/config':
            self.send_json_config()
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)

        if self.path == '/add-task':
            task_text = params.get('task', [''])[0]
            task_desc = params.get('description', [''])[0]
            if task_text:
                tasks = TaskManager(PROJECT_DIR)
                tasks.add_task(task_text, description=task_desc)
                log_activity("Task added", task_text, "success")
            self.redirect('/')

        elif self.path == '/add-thought':
            thought = params.get('thought', [''])[0]
            if thought:
                tasks = TaskManager(PROJECT_DIR)
                tasks.add_raw_thought(thought)
                log_activity("Thought added", thought, "info")
            self.redirect('/')

        elif self.path == '/start':
            self.start_agent()
            self.redirect('/')

        elif self.path == '/stop':
            self.stop_agent()
            self.redirect('/')

        elif self.path == '/toggle-theme':
            self.redirect('/')
        elif self.path == '/transform':
            raw_text = params.get('text', [''])[0]
            if raw_text:
                result = self._transform_text(raw_text)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()

        elif self.path == '/transform-confirm':
            try:
                body = json.loads(post_data)
                tasks_list = body.get('tasks', [])
                tasks_mgr = TaskManager(PROJECT_DIR)
                added = 0
                for t in tasks_list:
                    if t.get('title'):
                        tasks_mgr.add_task(t['title'], description=t.get('description', ''))
                        added += 1
                log_activity("Transform confirmed", f"{added} tasks added", "success")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "added": added}).encode('utf-8'))
            except Exception:
                self.send_response(400)
                self.end_headers()

        elif self.path == '/queue-message':
            msg_text = params.get('message', [''])[0]
            if msg_text:
                queue_file = PROJECT_DIR / '.a1' / 'queue.json'
                queue_data = {"messages": []}
                if queue_file.exists():
                    try:
                        queue_data = json.loads(queue_file.read_text())
                    except (json.JSONDecodeError, IOError):
                        pass
                queue_data["messages"].append({
                    "text": msg_text,
                    "added_at": datetime.now().isoformat(),
                    "read": False,
                })
                queue_file.write_text(json.dumps(queue_data, indent=2, ensure_ascii=False))
                log_activity("Message queued", msg_text[:50], "info")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        elif self.path == '/api/config':
            try:
                body = json.loads(post_data)
                from .config import Config
                config = Config(PROJECT_DIR)
                for key, value in body.items():
                    config.set(key, value)
                log_activity("Config updated", ", ".join(body.keys()), "info")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif self.path == '/api/reorder':
            try:
                body = json.loads(post_data)
                task_ids = body.get('order', [])
                if task_ids:
                    tasks_mgr = TaskManager(PROJECT_DIR)
                    tasks_mgr.reorder_tasks(task_ids)
                    log_activity("Tasks reordered", f"{len(task_ids)} tasks", "info")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            except Exception:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_error(404)

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def send_page(self, page):
        theme = 'light'  # Default light theme
        content = self.build_content(page)

        nav_active = {
            'nav_dashboard': 'active' if page == 'dashboard' else '',
            'nav_tasks': 'active' if page == 'tasks' else '',
            'nav_sessions': 'active' if page == 'sessions' else '',
            'nav_log': 'active' if page == 'log' else '',
            'nav_commits': 'active' if page == 'commits' else '',
            'nav_transform': 'active' if page == 'transform' else '',
            'nav_settings': 'active' if page == 'settings' else '',
        }

        html = HTML_TEMPLATE.substitute(
            theme=theme,
            content=content,
            page_name=page,
            **nav_active
        )

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def build_content(self, page):
        if page == 'dashboard':
            return self.build_dashboard()
        elif page == 'tasks':
            return self.build_tasks_page()
        elif page == 'sessions':
            return self.build_sessions_page()
        elif page == 'log':
            return self.build_log_page()
        elif page == 'commits':
            return self.build_commits_page()
        elif page == 'settings':
            return self.build_settings_page()
        elif page == 'transform':
            return self.build_transform_page()
        return ''

    def build_dashboard(self):
        checkpoint = CheckpointManager(PROJECT_DIR)
        tasks_mgr = TaskManager(PROJECT_DIR)

        cp = checkpoint.load()
        all_tasks = tasks_mgr.get_tasks()
        done, total = tasks_mgr.get_progress()
        progress = int((done / total * 100)) if total > 0 else 0

        # Status
        if AGENT_RUNNING:
            status_class = 'status-running'
            status_text = '<i class="bi bi-play-circle-fill"></i> Running'
        elif cp.get('status') == 'COMPLETED':
            status_class = 'status-completed'
            status_text = '<i class="bi bi-check-circle-fill"></i> Completed'
        else:
            status_class = 'status-stopped'
            status_text = '<i class="bi bi-stop-circle-fill"></i> Stopped'

        # Tasks HTML (last 5, sorted by priority)
        sorted_tasks = sorted(all_tasks, key=lambda t: (t.status == 'done', t.priority))
        tasks_html = ''
        for t in sorted_tasks[:5]:
            if t.status == 'done':
                check_class = 'done'
                check_icon = '<i class="bi bi-check"></i>'
            elif t.status == 'in_progress':
                check_class = 'progress'
                check_icon = '<i class="bi bi-arrow-repeat"></i>'
            else:
                check_class = ''
                check_icon = ''

            pri = getattr(t, 'priority', 0)
            pri_badge = f'<span class="priority-badge">#{pri}</span>' if pri and t.status != 'done' else ''

            tasks_html += f'''
            <div class="task">
                <div class="task-check {check_class}">{check_icon}</div>
                <div class="task-content">
                    <div class="task-title">{esc(t.title)}</div>
                    <div class="task-meta">{esc(t.id)} {pri_badge}</div>
                </div>
            </div>
            '''

        if not tasks_html:
            tasks_html = '<div class="empty"><i class="bi bi-inbox"></i><p>No tasks yet</p></div>'

        # Activity HTML (last 5) with status icons
        status_icons = {
            'success': '<i class="bi bi-check-circle-fill" style="color:var(--success)"></i>',
            'error': '<i class="bi bi-x-circle-fill" style="color:var(--danger)"></i>',
            'warning': '<i class="bi bi-exclamation-triangle-fill" style="color:var(--warning)"></i>',
            'info': '<i class="bi bi-info-circle-fill" style="color:var(--accent)"></i>',
        }
        activity_html = ''
        for a in reversed(ACTIVITY_LOG[-5:]):
            icon = status_icons.get(a['status'], status_icons['info'])
            activity_html += f'''
            <div class="activity-item">
                <span class="activity-time">{esc(a['time'])}</span>
                <span style="flex-shrink:0">{icon}</span>
                <span class="activity-text"><strong>{esc(a['action'])}</strong> <span class="activity-details">{esc(a['details'])}</span></span>
            </div>
            '''

        if not activity_html:
            activity_html = '<div class="empty" style="padding:20px"><i class="bi bi-clock-history"></i><p>No activity yet</p></div>'

        # Control buttons
        if AGENT_RUNNING:
            control_html = '''
            <form method="POST" action="/stop">
                <button type="submit" class="btn-danger"><i class="bi bi-stop-fill"></i> Stop Agent</button>
            </form>
            '''
        else:
            control_html = '''
            <form method="POST" action="/start">
                <button type="submit" class="btn-success"><i class="bi bi-play-fill"></i> Start Agent</button>
            </form>
            '''

        return f'''
        <div class="header">
            <h1 class="page-title">Dashboard</h1>
            <div class="header-actions">
                <span class="status {status_class}" id="status-badge">{status_text}</span>
                <button class="theme-toggle" onclick="toggleTheme()">
                    <i class="bi bi-moon-stars"></i>
                </button>
            </div>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-title"><i class="bi bi-check2-square"></i> Tasks</div>
                <div class="card-value" id="task-count">{done}/{total}</div>
                <div class="card-sub">completed</div>
                <div class="progress">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-terminal"></i> Session</div>
                <div class="card-value" id="session-count">#{cp.get('session', 0)}</div>
                <div class="card-sub">{cp.get('status', 'Not started')}</div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-lightning-charge" style="color:#f59e0b"></i> Tokens</div>
                <div class="card-value" id="tokens-count" style="font-size:22px">0 / 0</div>
                <div class="card-sub" id="tokens-sub">in / out</div>
                <div class="progress">
                    <div class="progress-fill" id="tokens-bar" style="width: 0%"></div>
                </div>
                <div class="card-sub" style="margin-top:4px">Context: <strong id="context-pct">0%</strong> <span style="color:var(--muted);font-size:11px">(auto-save at 70%)</span></div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-currency-dollar" style="color:#10b981"></i> Cost</div>
                <div class="card-value" id="cost-value" style="font-size:22px">$$0.00</div>
                <div class="card-sub">this session</div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-stopwatch" style="color:#6366f1"></i> Duration</div>
                <div class="card-value" id="duration-value">0s</div>
                <div class="card-sub" id="duration-sub">current session</div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-file-earmark-code"></i> Files</div>
                <div class="card-value" id="files-count">{len(cp.get('files_modified', []))}</div>
                <div class="card-sub">modified</div>
            </div>
        </div>

        <div class="task-list">
            <div class="task-header">
                <h3>Recent Tasks</h3>
                <a href="/tasks" class="btn-secondary" style="text-decoration:none">View All</a>
            </div>
            {tasks_html}
        </div>

        <div class="form-section">
            <h3>Quick Add</h3>
            <form method="POST" action="/add-task">
                <div class="form-row">
                    <input type="text" name="task" placeholder="Task title..." required>
                    <button type="submit" class="btn-primary"><i class="bi bi-plus"></i> Add</button>
                </div>
                <textarea name="description" placeholder="Description (optional)..." rows="2"></textarea>
            </form>
        </div>

        <div class="controls">
            {control_html}
        </div>

        <div class="form-section" id="queue-msg-section" style="{'display:block' if AGENT_RUNNING else 'display:none'}">
            <h3><i class="bi bi-envelope"></i> Message to Agent</h3>
            <form onsubmit="sendQueueMessage(event)">
                <div class="form-row">
                    <input type="text" id="queue-msg-input" placeholder="Send instruction to agent (next session)..." required>
                    <button type="submit" class="btn-primary"><i class="bi bi-send"></i> Send</button>
                </div>
            </form>
            <div id="queue-msg-status" style="font-size:12px;color:var(--text-secondary);margin-top:6px"></div>
        </div>

        <div class="log-panel">
            <div class="log-panel-header">
                <div style="display:flex;align-items:center;gap:12px">
                    <div class="terminal-dots">
                        <span class="dot-red"></span>
                        <span class="dot-yellow"></span>
                        <span class="dot-green"></span>
                    </div>
                    <span class="terminal-title">agent@pocketcoder ~ live-log</span>
                </div>
                <button class="log-toggle" onclick="document.getElementById('raw-log-wrap').style.display = document.getElementById('raw-log-wrap').style.display === 'none' ? 'block' : 'none'">raw</button>
            </div>
            <div class="log-feed" id="action-feed">
                {self._render_log_entries()}
            </div>
            <div id="raw-log-wrap" style="display:none">
                <div class="raw-log" id="raw-log">{self._render_raw_log()}</div>
            </div>
        </div>

        <div class="activity">
            <div class="activity-header">Recent Activity</div>
            <div class="activity-list">
                {activity_html}
            </div>
        </div>
        '''

    def build_tasks_page(self):
        tasks_mgr = TaskManager(PROJECT_DIR)
        all_tasks = tasks_mgr.get_tasks()
        all_tasks.sort(key=lambda t: (t.status == 'done', t.priority))
        thoughts = tasks_mgr.get_raw_thoughts()

        tasks_html = ''
        for t in all_tasks:
            if t.status == 'done':
                check_class = 'done'
                check_icon = '<i class="bi bi-check"></i>'
            elif t.status == 'in_progress':
                check_class = 'progress'
                check_icon = '<i class="bi bi-arrow-repeat"></i>'
            else:
                check_class = ''
                check_icon = ''

            desc = t.description[:100] if t.description else ''
            pri = getattr(t, 'priority', 0)
            pri_badge = f'<span class="priority-badge">#{pri}</span>' if pri and t.status != 'done' else ''
            draggable = 'draggable="true"' if t.status != 'done' else ''

            # Stage progress bar
            stage_steps = ''
            if t.status == 'done':
                stage_steps = '<div class="stage-step done"></div><div class="stage-step done"></div><div class="stage-step done"></div>'
            elif t.status == 'in_progress':
                stage_steps = '<div class="stage-step done"></div><div class="stage-step active"></div><div class="stage-step"></div>'
            else:
                stage_steps = '<div class="stage-step"></div><div class="stage-step"></div><div class="stage-step"></div>'

            # Task detail metadata
            phase_text = getattr(t, 'phase', '') or ''
            criteria = getattr(t, 'success_criteria', '') or ''
            created = getattr(t, 'created_at', '') or ''
            completed = getattr(t, 'completed_at', '') or ''

            detail_html = f'''
            <div class="task-detail" id="detail-{t.id}">
                <div class="task-stages">{stage_steps}</div>
                <div class="task-detail-meta">
                    <div><dt>Status</dt><dd>{esc(t.status)}</dd></div>
                    <div><dt>Phase</dt><dd>{esc(phase_text) if phase_text else 'N/A'}</dd></div>
                    <div><dt>Created</dt><dd>{esc(created[:10]) if created else 'N/A'}</dd></div>
                    <div><dt>Completed</dt><dd>{esc(completed[:10]) if completed else '—'}</dd></div>
                </div>
                {f'<div class="task-criteria"><strong>Criteria:</strong> {esc(criteria)}</div>' if criteria else ''}
                {f'<div style="margin-top:6px;font-size:12px;color:var(--text-secondary)">{esc(desc)}</div>' if desc else ''}
            </div>
            '''

            tasks_html += f'''
            <div class="task task-clickable" {draggable} data-task-id="{t.id}" onclick="toggleTaskDetail('{t.id}')">
                <div class="task-check {check_class}">{check_icon}</div>
                <div class="task-content">
                    <div class="task-title">{esc(t.title)}</div>
                    <div class="task-meta">{esc(t.id)} {pri_badge}</div>
                </div>
                <i class="bi bi-chevron-down" style="color:var(--text-secondary);font-size:14px"></i>
            </div>
            {detail_html}
            '''

        thoughts_html = ''
        if thoughts:
            for th in thoughts:
                thoughts_html += f'''
                <div class="task">
                    <div class="task-check"><i class="bi bi-lightbulb"></i></div>
                    <div class="task-content">
                        <div class="task-title">{esc(th['text'])}</div>
                        <div class="task-meta">Raw thought</div>
                    </div>
                </div>
                '''

        return f'''
        <div class="header">
            <h1 class="page-title">Tasks</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="task-list">
            <div class="task-header">
                <h3>All Tasks ({len(all_tasks)})</h3>
            </div>
            {tasks_html if tasks_html else '<div class="empty"><i class="bi bi-inbox"></i><p>No tasks yet</p></div>'}
        </div>

        {('<div class="task-list" style="margin-top:24px"><div class="task-header"><h3>Raw Thoughts</h3></div>' + thoughts_html + '</div>') if thoughts_html else ''}

        <div class="form-section">
            <h3>Add Task</h3>
            <form method="POST" action="/add-task">
                <div class="form-row">
                    <input type="text" name="task" placeholder="Task title..." required>
                    <button type="submit" class="btn-primary"><i class="bi bi-plus"></i> Add Task</button>
                </div>
                <textarea name="description" placeholder="Description (optional)..." rows="3"></textarea>
            </form>
            <form method="POST" action="/add-thought" style="margin-top:12px">
                <div class="form-row">
                    <input type="text" name="thought" placeholder="Quick thought or idea...">
                    <button type="submit" class="btn-secondary"><i class="bi bi-lightbulb"></i> Add Thought</button>
                </div>
            </form>
        </div>
        '''

    def build_sessions_page(self):
        checkpoint = CheckpointManager(PROJECT_DIR)
        cp = checkpoint.load()

        sessions_html = ''
        checkpoints_dir = PROJECT_DIR / '.a1' / 'checkpoints'
        if checkpoints_dir.exists():
            for f in sorted(checkpoints_dir.glob('session_*.json'), reverse=True)[:10]:
                try:
                    data = json.loads(f.read_text())
                    session_num = data.get('session', '?')
                    status = data.get('status', 'Unknown')
                    files = len(data.get('files_modified', []))

                    # Status badge color
                    if status == 'COMPLETED':
                        badge_cls = 'status-completed'
                    elif status == 'WORKING':
                        badge_cls = 'status-running'
                    else:
                        badge_cls = 'status-stopped'

                    # Extract metrics from checkpoint data
                    sm = data.get('session_metrics', {})
                    tok_in = sm.get('tokens_in', 0)
                    tok_out = sm.get('tokens_out', 0)
                    duration = sm.get('session_duration', 0)
                    tools = sm.get('tools_used', 0)

                    # Format duration
                    dur_str = f'{duration // 60}m {duration % 60}s' if duration >= 60 else f'{duration}s'

                    # Format tokens
                    def _fmt_tok(n):
                        if n >= 1000000: return f'{n/1000000:.1f}M'
                        if n >= 1000: return f'{n/1000:.1f}K'
                        return str(n)

                    sessions_html += f'''
                    <div class="session-card">
                        <div class="session-header">
                            <span class="session-title">Session #{session_num}</span>
                            <span class="status {badge_cls}">{esc(status)}</span>
                        </div>
                        <div class="session-meta">
                            <div class="meta-item">
                                <span class="meta-label"><i class="bi bi-file-earmark-code"></i> Files</span>
                                <span class="meta-value">{files}</span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-label"><i class="bi bi-check2-square"></i> Task</span>
                                <span class="meta-value">{esc(data.get('current_task', 'N/A'))}</span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-label"><i class="bi bi-lightning-charge"></i> Tokens</span>
                                <span class="meta-value">{_fmt_tok(tok_in)} / {_fmt_tok(tok_out)}</span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-label"><i class="bi bi-stopwatch"></i> Duration</span>
                                <span class="meta-value">{dur_str}</span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-label"><i class="bi bi-tools"></i> Tool Calls</span>
                                <span class="meta-value">{tools}</span>
                            </div>
                        </div>
                    </div>
                    '''
                except Exception:
                    pass

        # Current session status badge
        if AGENT_RUNNING:
            cur_badge = 'status-running'
            cur_label = '<i class="bi bi-play-circle-fill"></i> Running'
        elif cp.get('status') == 'COMPLETED':
            cur_badge = 'status-completed'
            cur_label = '<i class="bi bi-check-circle-fill"></i> Completed'
        elif cp.get('status') == 'WORKING':
            cur_badge = 'status-running'
            cur_label = '<i class="bi bi-arrow-repeat"></i> Working'
        else:
            cur_badge = 'status-stopped'
            cur_label = '<i class="bi bi-stop-circle-fill"></i> Idle'

        return f'''
        <div class="header">
            <h1 class="page-title"><i class="bi bi-terminal"></i> Sessions</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="session-card" style="border-left: 3px solid var(--accent)">
            <div class="session-header">
                <span class="session-title">Current Session #{cp.get('session', 0)}</span>
                <span class="status {cur_badge}">{cur_label}</span>
            </div>
            <div class="session-meta">
                <div class="meta-item">
                    <span class="meta-label"><i class="bi bi-flag"></i> Status</span>
                    <span class="meta-value">{esc(cp.get('status', 'Not started'))}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label"><i class="bi bi-pie-chart"></i> Context</span>
                    <span class="meta-value">{cp.get('context_percent', 0)}%</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label"><i class="bi bi-check2-square"></i> Current Task</span>
                    <span class="meta-value">{esc(cp.get('current_task', 'None'))}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label"><i class="bi bi-file-earmark-code"></i> Files Modified</span>
                    <span class="meta-value">{len(cp.get('files_modified', []))}</span>
                </div>
            </div>
        </div>

        <h3 style="margin: 24px 0 16px; color: var(--text-secondary); font-size: 14px; text-transform: uppercase; letter-spacing: 1px">Previous Sessions</h3>
        {sessions_html if sessions_html else '<div class="empty"><i class="bi bi-clock-history"></i><p>No previous sessions</p></div>'}
        '''

    def build_log_page(self):
        # Icons per status type
        status_icons = {
            'success': '<i class="bi bi-check-circle-fill" style="color:var(--success)"></i>',
            'error': '<i class="bi bi-x-circle-fill" style="color:var(--danger)"></i>',
            'warning': '<i class="bi bi-exclamation-triangle-fill" style="color:var(--warning)"></i>',
            'info': '<i class="bi bi-info-circle-fill" style="color:var(--accent)"></i>',
        }

        activity_html = ''
        for a in reversed(ACTIVITY_LOG):
            icon = status_icons.get(a['status'], status_icons['info'])
            activity_html += f'''
            <div class="activity-item">
                <span class="activity-time">{esc(a['time'])}</span>
                <span style="flex-shrink:0">{icon}</span>
                <span class="activity-text">
                    <strong>{esc(a['action'])}</strong>
                    <span class="activity-details">{esc(a['details'])}</span>
                </span>
            </div>
            '''

        return f'''
        <div class="header">
            <h1 class="page-title"><i class="bi bi-journal-text"></i> Activity Log</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="activity">
            <div class="activity-header">
                All Activity
                <span style="font-weight:400;color:var(--text-secondary);font-size:13px;margin-left:8px">{len(ACTIVITY_LOG)} entries</span>
            </div>
            <div class="activity-list" style="max-height:none">
                {activity_html if activity_html else '<div class="empty"><i class="bi bi-clock-history"></i><p>No activity yet</p></div>'}
            </div>
        </div>
        '''

    def build_commits_page(self):
        # Get git log with dates and full formatting
        import subprocess
        commits_html = ''
        try:
            result = subprocess.run(
                ['git', 'log', '--format=%h|%s|%cr|%an', '-20'],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and '|' in line:
                        parts = line.split('|', 3)
                        hash_short = parts[0] if len(parts) > 0 else ''
                        msg = parts[1] if len(parts) > 1 else ''
                        rel_time = parts[2] if len(parts) > 2 else ''
                        author = parts[3] if len(parts) > 3 else ''

                        # Split commit message: first line = title, rest = body
                        msg_title = esc(msg)

                        # Icon based on conventional commit prefix
                        if msg.startswith('feat'):
                            icon_cls = 'bi-plus-circle'
                            icon_color = 'var(--success)'
                        elif msg.startswith('fix'):
                            icon_cls = 'bi-bug'
                            icon_color = 'var(--danger)'
                        elif msg.startswith('docs') or msg.startswith('doc'):
                            icon_cls = 'bi-file-text'
                            icon_color = 'var(--accent)'
                        elif msg.startswith('refactor') or msg.startswith('chore'):
                            icon_cls = 'bi-arrow-repeat'
                            icon_color = 'var(--warning)'
                        elif msg.startswith('test'):
                            icon_cls = 'bi-check2-circle'
                            icon_color = '#89dceb'
                        else:
                            icon_cls = 'bi-git'
                            icon_color = 'var(--text-secondary)'

                        commits_html += f'''
                        <div class="task">
                            <div class="task-check" style="border-color:{icon_color};color:{icon_color}"><i class="bi {icon_cls}"></i></div>
                            <div class="task-content">
                                <div class="commit-msg">{msg_title}</div>
                                <div style="display:flex;gap:12px;align-items:center;margin-top:4px">
                                    <span class="commit-hash">{esc(hash_short)}</span>
                                    <span class="commit-time">{esc(rel_time)}</span>
                                    <span class="commit-time">{esc(author)}</span>
                                </div>
                            </div>
                        </div>
                        '''
        except Exception:
            pass

        # Branch info
        branch = ''
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=PROJECT_DIR, capture_output=True, text=True
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except Exception:
            pass

        return f'''
        <div class="header">
            <h1 class="page-title"><i class="bi bi-git"></i> Git Commits</h1>
            <div class="header-actions">
                {f'<span style="font-size:13px;color:var(--text-secondary)"><i class="bi bi-diagram-2"></i> {esc(branch)}</span>' if branch else ''}
                <button class="theme-toggle" onclick="toggleTheme()">
                    <i class="bi bi-moon-stars"></i>
                </button>
            </div>
        </div>

        <div class="task-list">
            <div class="task-header">
                <h3>Recent Commits</h3>
            </div>
            {commits_html if commits_html else '<div class="empty"><i class="bi bi-git"></i><p>No commits found</p></div>'}
        </div>
        '''

    def build_settings_page(self):
        from .config import Config
        config = Config(PROJECT_DIR)
        data = config.get_all()
        provider = esc(data.get("provider", "claude-max"))
        api_key_masked = esc(config.mask_api_key(data.get("api_key")) or "")
        ollama_host = esc(data.get("ollama_host", "http://localhost:11434"))
        ollama_model = esc(data.get("ollama_model", "qwen3:30b-a3b"))
        max_sessions = data.get("max_sessions", 100)
        max_turns = data.get("max_turns", 25)
        session_delay = data.get("session_delay", 5)
        context_threshold = data.get("context_threshold", 0.70)

        # Provider options with selected state
        providers = [
            ("claude-max", "claude-max (Claude Code CLI)"),
            ("claude-api", "claude-api [EXPERIMENTAL]"),
            ("ollama", "ollama [EXPERIMENTAL]"),
        ]
        options_html = ""
        for val, label in providers:
            sel = ' selected' if val == provider else ''
            options_html += f'<option value="{val}"{sel}>{label}</option>'

        return f'''
        <div class="header">
            <h1 class="page-title"><i class="bi bi-gear"></i> Settings</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="card" style="margin-bottom:16px">
            <div class="card-title"><i class="bi bi-cpu"></i> Provider</div>
            <select id="cfg-provider" onchange="onProviderChange(this.value)" style="margin-top:8px">
                {options_html}
            </select>
            <div id="provider-badge" class="settings-hint">
                {self._provider_badge(provider)}
            </div>
        </div>

        <div class="card" id="card-apikey" style="margin-bottom:16px;{'display:none' if provider != 'claude-api' else ''}">
            <div class="card-title"><i class="bi bi-key"></i> API Key</div>
            <div style="display:flex;gap:8px;margin-top:8px">
                <input type="password" id="cfg-apikey" placeholder="sk-ant-api03-..."
                    value="{api_key_masked}" style="flex:1">
                <button onclick="saveApiKey()" class="btn-primary" style="white-space:nowrap">
                    <i class="bi bi-check-lg"></i> Save
                </button>
            </div>
            <div class="settings-hint">
                Or set <code style="background:var(--bg-tertiary);padding:2px 6px;border-radius:4px">ANTHROPIC_API_KEY</code> environment variable
            </div>
        </div>

        <div class="card" id="card-ollama" style="margin-bottom:16px;{'display:none' if provider != 'ollama' else ''}">
            <div class="card-title"><i class="bi bi-hdd-network"></i> Ollama</div>
            <div style="margin-top:8px">
                <label class="settings-label">Host URL</label>
                <input type="text" id="cfg-ollama-host" value="{ollama_host}" style="font-family:monospace;width:100%">
            </div>
            <div style="margin-top:12px">
                <label class="settings-label">Model</label>
                <input type="text" id="cfg-ollama-model" value="{ollama_model}" style="font-family:monospace;width:100%">
            </div>
            <button onclick="saveOllamaConfig()" class="btn-primary" style="margin-top:12px">
                <i class="bi bi-check-lg"></i> Save
            </button>
        </div>

        <div class="card" style="margin-bottom:16px">
            <div class="card-title"><i class="bi bi-sliders"></i> Session</div>
            <div class="settings-grid">
                <div>
                    <label class="settings-label">Max Sessions</label>
                    <input type="number" id="cfg-max-sessions" value="{max_sessions}" min="1" max="1000">
                </div>
                <div>
                    <label class="settings-label">Max Turns</label>
                    <input type="number" id="cfg-max-turns" value="{max_turns}" min="1" max="100">
                </div>
                <div>
                    <label class="settings-label">Session Delay (sec)</label>
                    <input type="number" id="cfg-delay" value="{session_delay}" min="0" max="60">
                </div>
                <div>
                    <label class="settings-label">Context Threshold</label>
                    <input type="number" id="cfg-threshold" value="{context_threshold}" min="0.1" max="0.95" step="0.05">
                </div>
            </div>
            <button onclick="saveSessionConfig()" class="btn-primary" style="margin-top:12px">
                <i class="bi bi-check-lg"></i> Save
            </button>
        </div>

        <div class="card" style="margin-bottom:16px">
            <div class="card-title"><i class="bi bi-moon-stars"></i> Theme</div>
            <button onclick="toggleTheme()" class="btn-secondary" style="margin-top:8px">
                <i class="bi bi-moon-stars"></i> Toggle Dark/Light
            </button>
        </div>

        <div class="card" style="margin-bottom:16px">
            <div class="card-title"><i class="bi bi-file-earmark-code"></i> Config File</div>
            <p style="margin-top:8px;font-family:monospace" class="commit-hash">
                {esc(str(config.path))}
            </p>
        </div>

        <script>
        function showToast(msg) {{
            const t = document.createElement('div');
            t.className = 'toast';
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 2500);
        }}

        function onProviderChange(val) {{
            document.getElementById('card-apikey').style.display = val === 'claude-api' ? 'block' : 'none';
            document.getElementById('card-ollama').style.display = val === 'ollama' ? 'block' : 'none';
            fetch('/api/config', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{provider: val}})
            }}).then(r => r.json()).then(d => {{
                if (d.ok) {{
                    let badge = document.getElementById('provider-badge');
                    if (val === 'claude-max') badge.innerHTML = '<span style="color:var(--success)">Active</span>';
                    else badge.innerHTML = '<span style="color:var(--warning)">EXPERIMENTAL</span>';
                    showToast('Provider saved: ' + val);
                }}
            }});
        }}

        function saveApiKey() {{
            let key = document.getElementById('cfg-apikey').value;
            if (!key || key.includes('...')) {{ showToast('Enter the full API key'); return; }}
            fetch('/api/config', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{api_key: key}})
            }}).then(r => r.json()).then(d => {{
                if (d.ok) showToast('API key saved');
            }});
        }}

        function saveOllamaConfig() {{
            let host = document.getElementById('cfg-ollama-host').value;
            let model = document.getElementById('cfg-ollama-model').value;
            fetch('/api/config', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ollama_host: host, ollama_model: model}})
            }}).then(r => r.json()).then(d => {{
                if (d.ok) showToast('Ollama config saved');
            }});
        }}

        function saveSessionConfig() {{
            let cfg = {{
                max_sessions: parseInt(document.getElementById('cfg-max-sessions').value),
                max_turns: parseInt(document.getElementById('cfg-max-turns').value),
                session_delay: parseInt(document.getElementById('cfg-delay').value),
                context_threshold: parseFloat(document.getElementById('cfg-threshold').value),
            }};
            fetch('/api/config', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(cfg)
            }}).then(r => r.json()).then(d => {{
                if (d.ok) showToast('Session config saved');
            }});
        }}
        </script>
        '''

    def _provider_badge(self, provider: str) -> str:
        """Generate provider status badge HTML"""
        if provider == "claude-max":
            return '<span style="color:#a6e3a1">Active</span>'
        return '<span style="color:#f9e2af">EXPERIMENTAL</span> — untested'

    def build_transform_page(self):
        return '''
        <div class="header">
            <h1 class="page-title"><i class="bi bi-magic"></i> Transform</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="cards" style="grid-template-columns:repeat(3,1fr);margin-bottom:24px">
            <div class="card" style="text-align:center;padding:16px">
                <div style="font-size:24px;margin-bottom:8px"><i class="bi bi-pencil-square" style="color:var(--accent)"></i></div>
                <div style="font-size:13px;font-weight:600">1. Write</div>
                <div style="font-size:12px;color:var(--text-secondary)">Enter raw text or ideas</div>
            </div>
            <div class="card" style="text-align:center;padding:16px">
                <div style="font-size:24px;margin-bottom:8px"><i class="bi bi-magic" style="color:var(--warning)"></i></div>
                <div style="font-size:13px;font-weight:600">2. Transform</div>
                <div style="font-size:12px;color:var(--text-secondary)">AI breaks into tasks</div>
            </div>
            <div class="card" style="text-align:center;padding:16px">
                <div style="font-size:24px;margin-bottom:8px"><i class="bi bi-check2-all" style="color:var(--success)"></i></div>
                <div style="font-size:13px;font-weight:600">3. Confirm</div>
                <div style="font-size:12px;color:var(--text-secondary)">Review and add to queue</div>
            </div>
        </div>

        <div class="form-section">
            <h3>Raw Text to Tasks</h3>
            <p style="color: var(--text-secondary); margin-bottom:16px; font-size:13px">
                Enter raw text, notes, or ideas — AI will break them into structured tasks.
            </p>
            <textarea id="transform-input" rows="6" placeholder="Example:&#10;Add login page with email/password fields&#10;Registration form with validation&#10;Password reset flow via email&#10;Write unit tests for auth module"></textarea>
            <div style="margin-top:12px;display:flex;align-items:center;gap:12px">
                <button class="btn-primary" onclick="doTransform()" id="transform-btn">
                    <i class="bi bi-magic"></i> AI Transform
                </button>
                <span id="transform-status" style="font-size:13px;color:var(--text-secondary)"></span>
            </div>
        </div>

        <div id="transform-preview" style="display:none;margin-top:24px">
            <div class="task-list">
                <div class="task-header">
                    <h3>Preview Tasks</h3>
                    <button class="btn-success" onclick="confirmTransform()">
                        <i class="bi bi-check-all"></i> Add Selected
                    </button>
                </div>
                <div id="preview-tasks"></div>
            </div>
        </div>

        <script>
        let transformedTasks = [];

        function doTransform() {
            const text = document.getElementById('transform-input').value.trim();
            if (!text) return;
            const btn = document.getElementById('transform-btn');
            const status = document.getElementById('transform-status');
            btn.disabled = true;
            status.textContent = 'Thinking...';

            fetch('/transform', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'text=' + encodeURIComponent(text)
            })
            .then(r => r.json())
            .then(data => {
                btn.disabled = false;
                if (data.tasks && data.tasks.length > 0) {
                    transformedTasks = data.tasks;
                    status.textContent = data.tasks.length + ' tasks generated';
                    renderPreview(data.tasks);
                } else {
                    status.textContent = data.error || 'No tasks generated';
                }
            })
            .catch(err => {
                btn.disabled = false;
                status.textContent = 'Error: ' + err.message;
            });
        }

        function renderPreview(tasks) {
            const container = document.getElementById('preview-tasks');
            container.innerHTML = '';
            tasks.forEach((t, i) => {
                container.innerHTML += '<div class="task"><div class="task-check"><input type="checkbox" checked data-idx="' + i + '" style="width:18px;height:18px;cursor:pointer"></div><div class="task-content"><div class="task-title">' + escHtml(t.title) + '</div><div class="task-meta">' + escHtml(t.description || '') + '</div></div></div>';
            });
            document.getElementById('transform-preview').style.display = 'block';
        }

        function confirmTransform() {
            const checks = document.querySelectorAll('#preview-tasks input[type=checkbox]');
            const selected = [];
            checks.forEach(cb => {
                if (cb.checked) selected.push(transformedTasks[parseInt(cb.dataset.idx)]);
            });
            if (selected.length === 0) return;
            fetch('/transform-confirm', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tasks: selected})
            })
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    document.getElementById('transform-status').textContent = data.added + ' tasks added!';
                    document.getElementById('transform-preview').style.display = 'none';
                    document.getElementById('transform-input').value = '';
                }
            });
        }
        </script>
        '''

    def _transform_text(self, raw_text: str) -> dict:
        """Use Claude to break raw text into structured tasks"""
        import os
        import subprocess

        prompt = f'''Break the following text into structured tasks for a software project.
Return ONLY valid JSON array, no other text. Each task object must have:
- "title": short task title (imperative, e.g. "Add login page")
- "description": 1-2 sentence description

Text to transform:
{raw_text}

Return format: [{{"title": "...", "description": "..."}}, ...]'''

        try:
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            result = subprocess.run(
                ["claude", "-p", prompt, "--max-turns", "1", "--no-session-persistence", "--dangerously-skip-permissions"],
                cwd=str(PROJECT_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout.strip()
            # Try to extract JSON from output
            start = output.find('[')
            end = output.rfind(']')
            if start >= 0 and end > start:
                tasks = json.loads(output[start:end+1])
                return {"tasks": tasks}
            return {"tasks": [], "error": "Could not parse AI response"}
        except subprocess.TimeoutExpired:
            return {"tasks": [], "error": "AI request timed out (5 min)"}
        except FileNotFoundError:
            return {"tasks": [], "error": "Claude CLI not found"}
        except Exception as e:
            return {"tasks": [], "error": str(e)}

    def send_json_status(self):
        checkpoint = CheckpointManager(PROJECT_DIR)
        tasks = TaskManager(PROJECT_DIR)

        # Get live metrics from agent loop if running
        metrics = {}
        if AGENT_LOOP and hasattr(AGENT_LOOP, 'get_session_metrics'):
            metrics = AGENT_LOOP.get_session_metrics()
        else:
            # Try to load from checkpoint
            cp = checkpoint.load()
            metrics = cp.get('session_metrics', {})

        data = {
            'checkpoint': checkpoint.load(),
            'tasks': [t.to_dict() for t in tasks.get_tasks()],
            'progress': tasks.get_progress(),
            'running': AGENT_RUNNING,
            'activity': ACTIVITY_LOG[-10:],
            'metrics': metrics,
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_json_log(self):
        """Return agent log entries since a given index"""
        query = urlparse(self.path).query
        params = parse_qs(query)
        since = int(params.get('since', ['0'])[0])

        entries = AGENT_LOG_BUFFER[since:]
        data = {
            'entries': entries,
            'total': len(AGENT_LOG_BUFFER),
            'since': since,
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_json_config(self):
        """Return current config (API key masked)"""
        from .config import Config, DEFAULTS
        config = Config(PROJECT_DIR)
        data = config.get_all()
        # Mask API key for security
        if data.get("api_key"):
            data["api_key"] = config.mask_api_key(data["api_key"])
        data["_defaults"] = DEFAULTS
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _render_log_entries(self):
        """Render existing log buffer entries as HTML (terminal style)"""
        label_map = {
            'read': 'READ', 'edit': 'EDIT', 'write': 'WRITE',
            'bash': 'BASH', 'thinking': 'THINK', 'text': 'OUT',
            'metric': 'METRIC', 'verify': 'CHECK',
        }
        color_map = {
            'read': '#89b4fa', 'edit': '#fab387', 'write': '#a6e3a1',
            'bash': '#cba6f7', 'thinking': '#f9e2af', 'text': '#6c7086',
            'metric': '#89dceb', 'verify': '#a6e3a1',
        }
        html = ''
        for e in AGENT_LOG_BUFFER[-50:]:
            etype = e.get('type', 'text')
            label = label_map.get(etype, 'LOG')
            color = color_map.get(etype, '#6c7086')
            html += f'<div class="log-entry"><span class="px-icon" style="background:{color}"></span><span class="log-time">{esc(e["time"])}</span><span class="log-label" style="color:{color}">{label}</span><span class="log-text">{esc(e["line"][:150])}</span></div>'
        if not AGENT_LOG_BUFFER:
            html = '<div class="log-empty">Waiting for agent output...<span class="log-cursor"></span></div>'
        return html

    def _render_raw_log(self):
        """Render raw log text for initial page load"""
        return esc('\n'.join(e['line'] for e in AGENT_LOG_BUFFER[-50:]))

    def start_agent(self):
        global AGENT_RUNNING, AGENT_LOOP
        if not AGENT_RUNNING:
            AGENT_LOG_BUFFER.clear()
            log_activity("Agent started", "", "success")

            def run():
                global AGENT_RUNNING, AGENT_LOOP
                AGENT_RUNNING = True
                try:
                    from .config import Config
                    from .loop import SessionLoop
                    config = Config(PROJECT_DIR)
                    resolved = config.resolve()
                    loop = SessionLoop(project_dir=PROJECT_DIR, **resolved)
                    loop._log_callback = _on_agent_line
                    AGENT_LOOP = loop
                    loop.start()
                finally:
                    AGENT_RUNNING = False
                    AGENT_LOOP = None
                    log_activity("Agent stopped", "", "warning")

            thread = threading.Thread(target=run, daemon=True)
            thread.start()

    def stop_agent(self):
        global AGENT_RUNNING, AGENT_LOOP
        if AGENT_LOOP:
            AGENT_LOOP.stop()
        AGENT_RUNNING = False
        log_activity("Agent stop requested", "", "warning")


def find_free_port(start_port: int = 7331, max_attempts: int = 20) -> int:
    for offset in range(max_attempts):
        port = start_port + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port in range {start_port}-{start_port + max_attempts}")


def run_dashboard(project_dir: Path, port: int = None, open_browser: bool = True):
    global PROJECT_DIR
    PROJECT_DIR = Path(project_dir).resolve()

    a1_dir = PROJECT_DIR / '.a1'
    if not a1_dir.exists():
        a1_dir.mkdir(parents=True)
        (a1_dir / 'sessions').mkdir()
        (a1_dir / 'checkpoints').mkdir()

    if port is None:
        port = find_free_port(7331)
    else:
        try:
            port = find_free_port(port, max_attempts=1)
        except RuntimeError:
            port = find_free_port(7331)

    server = HTTPServer(('localhost', port), DashboardHandler)

    url = f'http://localhost:{port}'
    print()
    print('  PocketCoder-A1 Dashboard')
    print('  -------------------------')
    print(f'  URL:     {url}')
    print(f'  Project: {PROJECT_DIR}')
    print()
    print('  Press Ctrl+C to stop')
    print()

    log_activity("Dashboard started", f"Port {port}", "info")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\\nDashboard stopped')
        server.shutdown()


if __name__ == '__main__':
    import sys
    project = sys.argv[1] if len(sys.argv) > 1 else '.'
    run_dashboard(project)
