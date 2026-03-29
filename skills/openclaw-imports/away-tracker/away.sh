#!/bin/bash
# Away Tracker - returns minutes since last user message

STATE_FILE="/var/www/html/away-state.json"

if [ -f "$STATE_FILE" ]; then
    cat "$STATE_FILE"
else
    # Fallback: calculate directly
    python3 -c "
import json, glob
from datetime import datetime, timezone

latest = 0
for f in glob.glob('/root/.openclaw/agents/main/sessions/*.jsonl'):
    try:
        with open(f) as fp:
            for line in fp:
                d = json.loads(line)
                if d.get('type') == 'message':
                    role = d.get('message', {}).get('role')
                    content = str(d.get('message', {}).get('content', ''))
                    if role == 'user' and '[cron:' not in content:
                        ts = d.get('timestamp', '')
                        if ts:
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            latest = max(latest, int(dt.timestamp()))
    except: pass

if latest:
    now = int(datetime.now(timezone.utc).timestamp())
    diff = now - latest
    mins = diff // 60
    secs = diff % 60
    away = mins >= 15
    print(json.dumps({'away': away, 'minutes': mins, 'seconds': secs}))
else:
    print(json.dumps({'away': False, 'minutes': 0, 'seconds': 0}))
"
fi
