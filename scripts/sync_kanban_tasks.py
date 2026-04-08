#!/usr/bin/env python3
"""
sync_kanban_tasks.py — Bidirectional sync between TASKS.md and kanban.json.

TASKS.md status → kanban.json column mapping:
  [🚨] → blocked
  [!] / [ ] / [⬜] → todo
  [P] → in_progress
  [x] / [✅] → done

kanban.json → TASKS.md status mapping:
  blocked → [🚨]
  todo → [ ]
  in_progress → [P]
  done → [✅]

Uses hermes_write_with_lock.py for all file writes.
Direction 1: python3 sync_kanban_tasks.py tasks→kanban
Direction 2: python3 sync_kanban_tasks.py kanban→tasks
Both:       python3 sync_kanban_tasks.py both

Lock files: /root/.hermes/locks/tasks.md.lock and /root/.hermes/locks/kanban.lock
"""
import sys, os, re, json, time, subprocess
sys.path.insert(0, '/root/.hermes/scripts')

TASKS_FILE  = '/root/.hermes/brain/TASKS.md'
KANBAN_FILE = '/var/www/hermes/data/kanban.json'
LOCK_WRITER = '/root/.hermes/scripts/hermes_write_with_lock.py'
MAX_WAIT    = 30

def log(msg):
    print(f"[sync_kanban_tasks] {msg}", file=sys.stderr)

def write_with_lock(lockname, target, content):
    """Use hermes_write_with_lock.py to atomically write a file."""
    try:
        proc = subprocess.run(
            [sys.executable, LOCK_WRITER, lockname, target],
            input=content,
            capture_output=True,
            text=True,
            timeout=MAX_WAIT + 5
        )
        if proc.returncode == 0:
            log(f"Wrote {len(content)} bytes to {target}")
            return True
        else:
            log(f"SKIPPED: {target} locked ({proc.stderr.strip()})")
            return False
    except Exception as e:
        log(f"ERROR writing {target}: {e}")
        return False

# ── TASKS.md parsing ──────────────────────────────────────────────────────────

TASK_STATUS_RE = re.compile(r'^(\s*)-\s*\[([^\]]*)\]\s+(.+?)(?:\s*\(([^)]+)\))?(?:\s*—.*)?$')

def parse_tasks_md(content):
    """Parse TASKS.md, return list of (lineno, status_marker, text, project)."""
    tasks = []
    for i, line in enumerate(content.splitlines(), 1):
        # Skip comment/quote lines
        stripped = line.strip()
        if stripped.startswith('>') or stripped.startswith('#'):
            continue
        m = TASK_STATUS_RE.match(line)
        if m:
            indent, marker, text, project = m.groups()
            tasks.append({
                'lineno': i,
                'marker': marker.strip(),
                'text': text.strip(),
                'project': (project or '').strip(),
                'raw': line
            })
    return tasks

def tasks_status_to_kanban_col(marker):
    """Map TASKS.md marker to kanban column."""
    if marker == '🚨': return 'blocked'
    if marker in ('!', ' ', '⬜', ''): return 'todo'
    if marker == 'P': return 'in_progress'
    if marker in ('x', '✅'): return 'done'
    return 'todo'

# ── kanban.json parsing ───────────────────────────────────────────────────────

def load_kanban():
    try:
        with open(KANBAN_FILE) as f:
            return json.load(f)
    except:
        return {'updated': time.time(), 'columns': {'todo': [], 'in_progress': [], 'done': [], 'blocked': []}}

def save_kanban(data):
    write_with_lock('kanban', KANBAN_FILE, json.dumps(data, indent=2))

# ── Direction 1: TASKS.md → kanban.json ──────────────────────────────────────

KANBAN_ID_RE = re.compile(r'[^a-z0-9]+')

def make_kanban_id(text):
    """Make a stable ID from task text."""
    return KANBAN_ID_RE.sub('-', text.lower())[:50]

def sync_tasks_to_kanban():
    """Read TASKS.md, update kanban.json to match task statuses."""
    if not os.path.exists(TASKS_FILE):
        log(f"TASKS.md not found at {TASKS_FILE}, skipping")
        return

    with open(TASKS_FILE) as f:
        content = f.read()

    tasks = parse_tasks_md(content)
    kanban = load_kanban()
    columns = kanban.setdefault('columns', {'todo': [], 'in_progress': [], 'done': [], 'blocked': []})

    # Clear existing columns and rebuild from TASKS.md
    for col in columns:
        columns[col] = []

    task_id_map = {}  # kanban_id -> task data (for updating existing items)

    for task in tasks:
        col = tasks_status_to_kanban_col(task['marker'])
        item = {
            'id': make_kanban_id(task['text']),
            'name': task['text'],
            'description': task['project'],
            'project': task['project'],
            'priority': 3,
            'status': col,
            'marker': task['marker']
        }
        columns[col].append(item)

    kanban['updated'] = time.time()
    save_kanban(kanban)
    log(f"Synced {len(tasks)} tasks → kanban.json")

# ── Direction 2: kanban.json → TASKS.md ──────────────────────────────────────

KANBAN_TO_TASKS = {
    'blocked': '🚨',
    'todo': ' ',
    'in_progress': 'P',
    'done': '✅'
}

def sync_kanban_to_tasks():
    """Read kanban.json, FULL REWRITE of TASKS.md from parsed state (not in-place patch)."""
    if not os.path.exists(KANBAN_FILE):
        log(f"kanban.json not found, skipping")
        return

    kanban = load_kanban()
    columns = kanban.get('columns', {})

    # Build a map of task text → new kanban status
    task_status_map = {}
    for col_name, items in columns.items():
        marker = KANBAN_TO_TASKS.get(col_name, ' ')
        for item in items:
            task_status_map[item['name']] = (marker, col_name)

    with open(TASKS_FILE) as f:
        content = f.read()

    # Parse all lines preserving structure
    all_lines = content.splitlines(keepends=True)
    # Rebuild: collect non-task lines as-is, update task lines from kanban map
    changed = 0
    new_lines = []
    for line in all_lines:
        m = TASK_STATUS_RE.match(line.rstrip('\n'))
        if m:
            indent, old_marker, text, project = m.groups()
            new_text = text.strip()
            if new_text in task_status_map:
                new_marker, new_col = task_status_map[new_text]
                if new_marker != old_marker.strip():
                    # SAFE rewrite: one task per line, no concatenation risk
                    marker_char = new_marker
                    line_content = text.strip()
                    if project and project.strip():
                        line_content += f" ({project.strip()})"
                    # Preserve trailing content after the full task line match
                    trailing = line[len(m.group(0)):].rstrip('\n')
                    new_line = f"{indent}- [{marker_char}] {line_content}{trailing}\n"
                    new_lines.append(new_line)
                    changed += 1
                    continue
        new_lines.append(line)

    if changed:
        new_content = ''.join(new_lines)
        # Validate: check no line has more than one '- [' pattern (garble detection)
        for nl in new_lines:
            if nl.strip().startswith('- ['):
                count = nl.count('- [')
                if count > 1:
                    log(f"VALIDATION FAILED: garbled line after rewrite: {nl[:80]}")
                    log("ABORTING write to prevent corruption")
                    return
        write_with_lock('tasks.md', TASKS_FILE, new_content)
        log(f"Synced {changed} task statuses ← kanban.json")
    else:
        log("No task status changes needed from kanban.json")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    direction = sys.argv[1] if len(sys.argv) > 1 else 'both'
    log(f"Starting sync ({direction})...")

    if direction in ('tasks→kanban', 'tasks-to-kanban', 'tasks2kanban', '1'):
        sync_tasks_to_kanban()
    elif direction in ('kanban→tasks', 'kanban-to-tasks', 'kanban2tasks', '2'):
        sync_kanban_to_tasks()
    elif direction == 'both':
        sync_tasks_to_kanban()
        sync_kanban_to_tasks()
    else:
        log(f"Unknown direction: {direction}")
        log("Usage: sync_kanban_tasks.py [tasks→kanban|kanban→tasks|both]")
        sys.exit(1)

if __name__ == '__main__':
    main()
