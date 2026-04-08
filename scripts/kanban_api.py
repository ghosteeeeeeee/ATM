#!/usr/bin/env python3
"""
kanban_api.py — Hermes Kanban Board API Server.
Serves the projects.html kanban board at /projects and persists to kanban.json.

Run: python3 /root/.hermes/scripts/kanban_api.py
Daemon: supervised by systemd or run in background.
"""
import os, sys, json, time, subprocess
from flask import Flask, request, jsonify, send_file, Response

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = '/var/www/hermes/data'
KANBAN_FILE = os.path.join(DATA_DIR, 'kanban.json')
HTML_FILE = '/var/www/hermes/projects.html'

# Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ── JSON helpers ──────────────────────────────────────────────────────────────

def load_kanban():
    """Load kanban data from JSON file. Seed with defaults if missing."""
    if not os.path.exists(KANBAN_FILE):
        return _seed_default()
    try:
        with open(KANBAN_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return _seed_default()

def save_kanban(data):
    """Atomically write kanban data to JSON file."""
    tmp = KANBAN_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, KANBAN_FILE)

def _seed_default():
    """Seed kanban.json with current TASKS.md / PROJECTS.md data."""
    # Import brain files to parse them
    data = {
        'updated': time.time(),
        'columns': {
            'todo': [],
            'in_progress': [],
            'done': [],
            'blocked': []
        }
    }
    # Try to seed from existing tasks — if file is empty/invalid, return empty structure
    return data

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/projects', methods=['GET'])
def serve_html():
    """Serve the kanban HTML page."""
    return send_file(HTML_FILE)

@app.route('/api/config/projects', methods=['GET'])
def get_projects():
    """Return full kanban state as { columns: {todo, in_progress, done, blocked} }"""
    data = load_kanban()
    return jsonify({
        'my_projects': data.get('columns', {}).get('todo', []) + \
                       data.get('columns', {}).get('in_progress', []) + \
                       data.get('columns', {}).get('done', []) + \
                       data.get('columns', {}).get('blocked', []),
        'columns': data.get('columns', {}),
        'updated': data.get('updated', 0)
    })

@app.route('/api/config/projects/save', methods=['POST'])
def save_projects():
    """Save full kanban state. Expects { my_projects: [...] }"""
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    projects = body.get('my_projects', [])

    # Reorganize by column
    columns = {'todo': [], 'in_progress': [], 'done': [], 'blocked': []}
    for p in projects:
        status = p.get('status', 'todo')
        col = 'todo'
        if status in ('in_progress', 'blocked', 'done'):
            col = status
        elif status in ('pending', 'todo'):
            col = 'todo'
        # Strip status to avoid confusion on reload
        p_clean = {k: v for k, v in p.items() if k != 'status'}
        columns[col].append(p_clean)

    data = {
        'updated': time.time(),
        'columns': columns
    }
    save_kanban(data)
    subprocess.run([sys.executable, '/root/.hermes/scripts/sync_kanban_tasks.py', 'kanban→tasks'], timeout=30)
    return jsonify({'ok': True, 'saved': len(projects)})

@app.route('/api/config/projects/<task_id>', methods=['DELETE'])
def delete_project(task_id):
    """Delete a task by id."""
    data = load_kanban()
    changed = False
    for col in data.get('columns', {}):
        data['columns'][col] = [p for p in data['columns'][col]
                                  if str(p.get('id', p.get('_id', ''))) != str(task_id)]
    save_kanban(data)
    return jsonify({'ok': True})

# ── Health ─────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'kanban-api'})

# ── Standalone runner ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3461
    print(f'Kanban API starting on port {port}...')
    app.run(host='127.0.0.1', port=port, debug=False)
