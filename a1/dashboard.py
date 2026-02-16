#!/usr/bin/env python3
"""
PocketCoder-A1 Dashboard — Full-featured Web UI
"""

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
ACTIVITY_LOG = []  # Live activity log


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
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
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
}

input[type="text"]::placeholder {
    color: var(--text-secondary);
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

button:hover { opacity: 0.9; }
button:active { transform: scale(0.98); }

.btn-primary { background: var(--accent); color: white; }
.btn-success { background: var(--success); color: white; }
.btn-danger { background: var(--danger); color: white; }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); }

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

@media (max-width: 768px) {
    .layout {
        grid-template-columns: 1fr;
    }
    .sidebar {
        display: none;
    }
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

        // Auto-refresh every 5 seconds
        setTimeout(() => location.reload(), 5000);
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
        elif path == '/api/status':
            self.send_json_status()
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)

        if self.path == '/add-task':
            task_text = params.get('task', [''])[0]
            if task_text:
                tasks = TaskManager(PROJECT_DIR)
                tasks.add_task(task_text)
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
            'nav_settings': 'active' if page == 'settings' else '',
        }

        html = HTML_TEMPLATE.substitute(
            theme=theme,
            content=content,
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

        # Tasks HTML (last 5)
        tasks_html = ''
        for t in all_tasks[:5]:
            if t.status == 'done':
                check_class = 'done'
                check_icon = '<i class="bi bi-check"></i>'
            elif t.status == 'in_progress':
                check_class = 'progress'
                check_icon = '<i class="bi bi-arrow-repeat"></i>'
            else:
                check_class = ''
                check_icon = ''

            phase = getattr(t, 'phase', '') if hasattr(t, 'phase') else ''
            phase_html = f'<span class="task-phase">{phase}</span>' if phase else ''

            tasks_html += f'''
            <div class="task">
                <div class="task-check {check_class}">{check_icon}</div>
                <div class="task-content">
                    <div class="task-title">{t.title}</div>
                    <div class="task-meta">{t.id}</div>
                </div>
                {phase_html}
            </div>
            '''

        if not tasks_html:
            tasks_html = '<div class="empty"><i class="bi bi-inbox"></i><p>No tasks yet</p></div>'

        # Activity HTML (last 5)
        activity_html = ''
        for a in reversed(ACTIVITY_LOG[-5:]):
            activity_html += f'''
            <div class="activity-item">
                <span class="activity-time">{a['time']}</span>
                <span class="activity-dot {a['status']}"></span>
                <span class="activity-text">{a['action']} <span class="activity-details">{a['details']}</span></span>
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
                <span class="status {status_class}">{status_text}</span>
                <button class="theme-toggle" onclick="toggleTheme()">
                    <i class="bi bi-moon-stars"></i>
                </button>
            </div>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-title"><i class="bi bi-check2-square"></i> Tasks</div>
                <div class="card-value">{done}/{total}</div>
                <div class="card-sub">completed</div>
                <div class="progress">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-terminal"></i> Session</div>
                <div class="card-value">#{cp.get('session', 0)}</div>
                <div class="card-sub">{cp.get('status', 'Not started')}</div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-clock"></i> Context</div>
                <div class="card-value">{cp.get('context_percent', 0)}%</div>
                <div class="card-sub">used</div>
            </div>
            <div class="card">
                <div class="card-title"><i class="bi bi-file-earmark-code"></i> Files</div>
                <div class="card-value">{len(cp.get('files_modified', []))}</div>
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
                    <input type="text" name="task" placeholder="Add a new task..." required>
                    <button type="submit" class="btn-primary"><i class="bi bi-plus"></i> Add</button>
                </div>
            </form>
        </div>

        <div class="controls">
            {control_html}
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
            tasks_html += f'''
            <div class="task">
                <div class="task-check {check_class}">{check_icon}</div>
                <div class="task-content">
                    <div class="task-title">{t.title}</div>
                    <div class="task-meta">{t.id} {(' - ' + desc) if desc else ''}</div>
                </div>
            </div>
            '''

        thoughts_html = ''
        if thoughts:
            for th in thoughts:
                thoughts_html += f'''
                <div class="task">
                    <div class="task-check"><i class="bi bi-lightbulb"></i></div>
                    <div class="task-content">
                        <div class="task-title">{th['text']}</div>
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
                    <input type="text" name="task" placeholder="Task description..." required>
                    <button type="submit" class="btn-primary"><i class="bi bi-plus"></i> Add Task</button>
                </div>
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
                    sessions_html += f'''
                    <div class="session-card">
                        <div class="session-header">
                            <span class="session-title">Session #{session_num}</span>
                            <span class="status status-{'completed' if status == 'COMPLETED' else 'stopped'}">{status}</span>
                        </div>
                        <div class="session-meta">
                            <div class="meta-item">
                                <span class="meta-label">Files Modified</span>
                                <span class="meta-value">{files}</span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-label">Current Task</span>
                                <span class="meta-value">{data.get('current_task', 'N/A')}</span>
                            </div>
                        </div>
                    </div>
                    '''
                except Exception:
                    pass

        return f'''
        <div class="header">
            <h1 class="page-title">Sessions</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="session-card">
            <div class="session-header">
                <span class="session-title">Current Session #{cp.get('session', 0)}</span>
                <span class="status status-{'running' if AGENT_RUNNING else 'stopped'}">{'Running' if AGENT_RUNNING else 'Stopped'}</span>
            </div>
            <div class="session-meta">
                <div class="meta-item">
                    <span class="meta-label">Status</span>
                    <span class="meta-value">{cp.get('status', 'Not started')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Context</span>
                    <span class="meta-value">{cp.get('context_percent', 0)}%</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Current Task</span>
                    <span class="meta-value">{cp.get('current_task', 'None')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Files Modified</span>
                    <span class="meta-value">{len(cp.get('files_modified', []))}</span>
                </div>
            </div>
        </div>

        <h3 style="margin: 24px 0 16px">Previous Sessions</h3>
        {sessions_html if sessions_html else '<div class="empty"><i class="bi bi-clock-history"></i><p>No previous sessions</p></div>'}
        '''

    def build_log_page(self):
        activity_html = ''
        for a in reversed(ACTIVITY_LOG):
            activity_html += f'''
            <div class="activity-item">
                <span class="activity-time">{a['time']}</span>
                <span class="activity-dot {a['status']}"></span>
                <span class="activity-text">{a['action']} <span class="activity-details">{a['details']}</span></span>
            </div>
            '''

        return f'''
        <div class="header">
            <h1 class="page-title">Activity Log</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="activity">
            <div class="activity-header">All Activity ({len(ACTIVITY_LOG)} entries)</div>
            <div class="activity-list" style="max-height:none">
                {activity_html if activity_html else '<div class="empty"><i class="bi bi-clock-history"></i><p>No activity yet</p></div>'}
            </div>
        </div>
        '''

    def build_commits_page(self):
        # Get git log
        import subprocess
        commits_html = ''
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-20'],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\\n'):
                    if line:
                        parts = line.split(' ', 1)
                        hash_short = parts[0]
                        msg = parts[1] if len(parts) > 1 else ''
                        commits_html += f'''
                        <div class="task">
                            <div class="task-check"><i class="bi bi-git"></i></div>
                            <div class="task-content">
                                <div class="task-title">{msg}</div>
                                <div class="task-meta">{hash_short}</div>
                            </div>
                        </div>
                        '''
        except Exception:
            pass

        return f'''
        <div class="header">
            <h1 class="page-title">Git Commits</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="task-list">
            <div class="task-header">
                <h3>Recent Commits</h3>
            </div>
            {commits_html if commits_html else '<div class="empty"><i class="bi bi-git"></i><p>No commits found</p></div>'}
        </div>
        '''

    def build_settings_page(self):
        return '''
        <div class="header">
            <h1 class="page-title">Settings</h1>
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="bi bi-moon-stars"></i>
            </button>
        </div>

        <div class="card" style="margin-bottom:16px">
            <div class="card-title">Theme</div>
            <button onclick="toggleTheme()" class="btn-secondary">
                <i class="bi bi-moon-stars"></i> Toggle Dark/Light
            </button>
        </div>

        <div class="card">
            <div class="card-title">Provider</div>
            <p style="color: var(--text-secondary); margin-top: 8px">
                Current: <strong>claude-max</strong> (Claude Code CLI)
            </p>
        </div>
        '''

    def send_json_status(self):
        checkpoint = CheckpointManager(PROJECT_DIR)
        tasks = TaskManager(PROJECT_DIR)

        data = {
            'checkpoint': checkpoint.load(),
            'tasks': [t.to_dict() for t in tasks.get_tasks()],
            'progress': tasks.get_progress(),
            'running': AGENT_RUNNING,
            'activity': ACTIVITY_LOG[-10:],
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def start_agent(self):
        global AGENT_RUNNING
        if not AGENT_RUNNING:
            log_activity("Agent started", "", "success")

            def run():
                global AGENT_RUNNING
                AGENT_RUNNING = True
                try:
                    from .loop import SessionLoop
                    loop = SessionLoop(PROJECT_DIR)
                    loop.start()
                finally:
                    AGENT_RUNNING = False
                    log_activity("Agent stopped", "", "warning")

            thread = threading.Thread(target=run, daemon=True)
            thread.start()

    def stop_agent(self):
        global AGENT_RUNNING
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
