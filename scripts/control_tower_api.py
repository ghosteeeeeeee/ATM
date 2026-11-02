#!/usr/bin/env python3
"""
control_tower_api.py — JSON feed for the Control Tower web dashboard.

Reads the canonical registry (data/shadow_disposition.json) + the daily tower
render (automation/ceo/control_tower.md) + recent shadow-disposition kanban
packets, and writes /var/www/hermes/data/control_tower.json for
web/control_tower.html (page polls every 30s; this timer runs every 60s).

Design (CEO build 2026-10-31, v2 = T's "live updates as the calendar is
updated" request): the CALENDAR is registry-derived, so any registry edit
(shows up within one timer tick) — the page never waits for the 08:15 run.
Progress n-vs-bar comes from shadow_disposition.PROGRESS_EVALS (memoized,
subprocess hooks ~1s) and degrades to '—' on any failure: a broken hook must
never break the feed.

Zero trading behavior; read-only everywhere except its own output file.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, WWW_DATA  # noqa: E402

REGISTRY = os.path.join(HERMES_DATA, 'shadow_disposition.json')
TOWER = '/root/.hermes/automation/ceo/control_tower.md'
KANBAN = '/root/.hermes/automation/ceo/ceo_kanban.md'
OUTPUT = os.path.join(WWW_DATA, 'control_tower.json')

NOW = datetime.now(timezone.utc)
# staleness thresholds (mirror shadow_disposition: tower regenerates daily)
TOWER_STALE_H = 26
FEED_STALE_MIN = 10


def log(msg):
    print(f'[control-tower-api] {msg}', flush=True)


def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log(f'WARN: cannot load {path}: {e}')
        return default


def _parse_deadline(dl):
    try:
        dt = datetime.fromisoformat(str(dl).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _tag(days):
    if days < 0:
        return f'OVERDUE {-days}d'
    if days == 0:
        return 'TODAY'
    return f'T-{days}'


def _entry(e, dl_dt):
    days = (dl_dt.date() - NOW.date()).days if dl_dt else None
    bar = str(e.get('bar') or e.get('threshold') or '')
    bar = re.sub(r'^bar:\s*', '', bar)
    return {
        'id': e.get('id', '?'),
        'kind': e.get('kind', ''),
        'owner': str(e.get('owner', '')),
        'deadline': str(e.get('deadline') or ''),
        'days_left': days,
        'tag': _tag(days) if days is not None else 'UNDATED',
        'bar': bar,
        'default_action': str(e.get('default_action') or ''),
        'started': str(e.get('started') or ''),
    }


def _progress(e):
    """Live n-vs-bar via shadow_disposition's hooks; never raises."""
    name = e.get('progress_eval')
    if not name:
        return None
    try:
        import shadow_disposition as sd
        fn = sd.PROGRESS_EVALS.get(name)
        if fn is None:
            return {'text': f'UNKNOWN eval {name}', 'met': None}
        d = fn(e)
        if not isinstance(d, dict):
            return {'text': 'malformed evaluator output', 'met': None}
        if 'error' in d:
            return {'text': f"unavailable ({d['error']})", 'met': None}
        mark = 'OK' if d.get('met') else 'NOT MET'
        return {'text': f"{d['now']} vs >={d['target']} {d.get('unit', '')} — {mark}",
                'met': bool(d.get('met'))}
    except Exception as ex:
        return {'text': f'unavailable ({type(ex).__name__}: {ex})', 'met': None}


def _recent_packets(limit=8):
    """Last shadow-disposition kanban lines (what just fired)."""
    try:
        with open(KANBAN, errors='replace') as f:
            # tail only — kanban is huge and append-only
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 200_000))
            tail = f.read()
    except Exception as e:
        return [f'(kanban unreadable: {e})']
    hits = [ln.strip() for ln in tail.splitlines() if 'shadow-disposition:' in ln]
    return hits[-limit:][::-1]


def main():
    reg = _load(REGISTRY, None)
    if not reg or not isinstance(reg.get('entries'), list):
        log('ERROR: registry missing/empty — writing error feed')
        payload = {'generated_at': NOW.isoformat(), 'error': 'registry unreadable',
                   'counts': {}, 'sections': {}, 'trials': [], 'calendar': [],
                   'done': [], 'packets': []}
    else:
        entries = [e for e in reg['entries'] if isinstance(e, dict)]
        opens = [e for e in entries if e.get('status') == 'open']
        dones = [e for e in entries if e.get('status') == 'done']

        dated, undated = [], []
        for e in opens:
            dt = _parse_deadline(e.get('deadline'))
            (dated if dt else undated).append((dt, e))
        dated.sort(key=lambda x: x[0])

        def bucket(lo, hi):
            return [_entry(e, dt) for dt, e in dated if lo < dt <= hi]

        sections = {
            'overdue': [_entry(e, dt) for dt, e in dated if dt <= NOW],
            'due24': bucket(NOW, NOW + timedelta(hours=24)),
            'due7': bucket(NOW + timedelta(hours=24), NOW + timedelta(days=7)),
            'due14': bucket(NOW + timedelta(days=7), NOW + timedelta(days=14)),
            'later': [_entry(e, dt) for dt, e in dated if dt > NOW + timedelta(days=14)],
            'undated': [_entry(e, None) for e in undated],
        }

        trials = []
        for e in opens:
            if e.get('kind') in ('trial', 'watch'):
                ent = _entry(e, _parse_deadline(e.get('deadline')))
                ent['progress'] = _progress(e)
                trials.append(ent)
        trials.sort(key=lambda x: x['deadline'] or '9999')
        # attach progress to their section copies too (same id)
        prog_by_id = {t['id']: t.get('progress') for t in trials}
        for sec in sections.values():
            for ent in sec:
                if ent['id'] in prog_by_id:
                    ent['progress'] = prog_by_id[ent['id']]

        cal_map = {}
        for dt, e in dated:
            cal_map.setdefault(dt.date().isoformat(), []).append(e.get('id', '?'))
        from datetime import date as _date
        calendar = [{'date': d, 'tag': _tag((_date.fromisoformat(d) - NOW.date()).days),
                     'days_left': (_date.fromisoformat(d) - NOW.date()).days,
                     'ids': cal_map[d]} for d in sorted(cal_map)]

        tower_mtime = None
        try:
            tower_mtime = os.path.getmtime(TOWER)
        except OSError:
            pass
        reg_mtime = None
        try:
            reg_mtime = os.path.getmtime(REGISTRY)
        except OSError:
            pass

        payload = {
            'generated_at': NOW.isoformat(),
            'registry_mtime': (datetime.fromtimestamp(reg_mtime, timezone.utc)
                               .isoformat() if reg_mtime else None),
            'tower_mtime': (datetime.fromtimestamp(tower_mtime, timezone.utc)
                            .isoformat() if tower_mtime else None),
            'tower_stale': bool(tower_mtime is None
                                or NOW.timestamp() - tower_mtime > TOWER_STALE_H * 3600),
            'counts': {'open': len(opens), 'done': len(dones),
                       'total': len(entries)},
            'sections': sections,
            'trials': trials,
            'calendar': calendar,
            'done': [e.get('id', '?') for e in dones],
            'packets': _recent_packets(),
        }

    tmp = f'{OUTPUT}.{os.getpid()}.tmp'
    with open(tmp, 'w') as f:
        json.dump(payload, f, indent=1)
    os.replace(tmp, OUTPUT)
    counts = payload.get('counts', {})
    log(f'feed -> {OUTPUT} (open={counts.get("open")}, done={counts.get("done")}, '
        f'trials={len(payload.get("trials", []))}, '
        f'calendar_days={len(payload.get("calendar", []))})')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'[control-tower-api] FATAL: {e}', flush=True)
        sys.exit(1)
