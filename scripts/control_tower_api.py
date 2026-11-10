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
from paths import HERMES_DATA, WWW_DATA, HERMES_LOG_DIR  # noqa: E402

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


# ── fill_cap (DailyFillCap / Cap D visibility, CEO consult 20261110T184624Z) ──
# Bounded backward scan of pipeline.log for DailyFillCap SKIP events dated
# today (UTC). ONLY single-timestamp lines count as events: pipeline
# double-logs every log() line as a stdout echo ('TS   TS SKIP: ...'), so
# counting both would double the event count (registry evidence: 12 events =
# 24 lines). The Cap D skip path is stateless by design (no PG/SQLite record),
# so the log is the only source for last_skip_ts / blocked_candidates_today.
_FC_SCAN_CHUNK = 4 * 1024 * 1024    # per-iteration backward read
_FC_SCAN_MAX = 64 * 1024 * 1024     # hard cap (~2.4 days at the current ~27MB/day)
_FC_TS_RE = re.compile(r'^\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
_FC_SKIP_RE = re.compile(r'^\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) SKIP: DailyFillCap')


def _skip_events_today(path, day_prefix):
    """(events_today_utc, last_event_ts_iso_or_None) from pipeline.log.

    Scans backward from EOF (bounded to _FC_SCAN_MAX bytes) and stops at the
    first line dated before day_prefix (the log is chronological). Never
    raises: any read failure returns what was counted so far.
    """
    count = 0
    last = None
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0, None
    pos = size
    scanned = 0
    carry = b''
    try:
        with open(path, 'rb') as f:
            while pos > 0 and scanned < _FC_SCAN_MAX:
                n = min(_FC_SCAN_CHUNK, pos)
                pos -= n
                scanned += n
                f.seek(pos)
                buf = f.read(n) + carry
                parts = buf.split(b'\n')
                if pos > 0:
                    carry = parts.pop(0)   # this line's start lives in older bytes
                else:
                    carry = b''
                # decode only lines whose first non-space bytes are a date
                txts = []
                for raw in parts:
                    s = raw.lstrip()
                    txts.append(s.decode('utf-8', 'replace') if s[:4].isdigit() else None)
                j = -1                      # last index of a pre-today line
                for i, txt in enumerate(txts):
                    if txt is None:
                        continue
                    m = _FC_TS_RE.match(txt)
                    if m and m.group(1) < day_prefix:
                        j = i
                chunk_last = None
                for txt in txts[j + 1:]:    # today's region of this chunk
                    if txt is None:
                        continue
                    m = _FC_SKIP_RE.match(txt)
                    if m:
                        count += 1
                        chunk_last = m.group(1)
                if last is None and chunk_last is not None:
                    last = chunk_last       # chunks arrive newest-first
                if j >= 0:
                    break                   # boundary hit: older bytes are pre-today
    except Exception:
        pass
    return count, (last.replace(' ', 'T') + 'Z' if last else None)


def _fill_cap():
    """DailyFillCap (Cap D) state for the tower feed — never raises.

    engaged/opens_24h/fee_net_24h come from ONE cheap PG read (same SQL as
    decider_run._daily_fill_cap_block); max from DAILY_FILL_CAP_MAX.
    last_skip_ts / blocked_candidates_today come from a bounded scan of
    pipeline.log (see _skip_events_today). Any failure degrades that field
    to null — a broken feed must never break the tower.
    """
    out = {'engaged': None, 'opens_24h': None, 'max': None,
           'fee_net_24h': None, 'last_skip_ts': None,
           'blocked_candidates_today': None}
    cap_max = None
    try:
        from hermes_constants import DAILY_FILL_CAP_MAX
        cap_max = int(DAILY_FILL_CAP_MAX)
        out['max'] = cap_max
    except Exception as e:
        log(f'WARN: fill_cap DAILY_FILL_CAP_MAX unreadable: {e}')
    try:
        import psycopg2
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
            cur = conn.cursor()
            # SAME SQL as decider_run._daily_fill_cap_block: live opens (paper=false)
            # + fee-net of JSON-fee closed fills over the rolling 24h (ONE read).
            cur.execute("""
                SELECT COUNT(*) FILTER (WHERE paper = false
                                        AND open_time > NOW() - INTERVAL '24 hours'),
                       COALESCE(SUM(pnl_usdt) FILTER (WHERE status = 'closed'
                                AND close_time > NOW() - INTERVAL '24 hours'
                                AND fees LIKE '{%'), 0)
                     - COALESCE(SUM(COALESCE((fees::json->>'fee_total')::numeric, 0))
                           FILTER (WHERE status = 'closed'
                                AND close_time > NOW() - INTERVAL '24 hours'
                                AND fees LIKE '{%'), 0)
                FROM trades
            """)
            row = cur.fetchone()
        finally:
            try:
                if cur is not None:
                    cur.close()
            finally:
                if conn is not None:
                    conn.close()
        n = int(row[0] or 0)
        net = float(row[1] or 0)
        out['opens_24h'] = n
        out['fee_net_24h'] = net
        if cap_max is not None:
            # mirror the helper's AND exactly (raw net, pre-rounding)
            out['engaged'] = bool(n >= cap_max and net < 0)
    except Exception as e:
        log(f'WARN: fill_cap PG read failed: {e}')
    try:
        cnt, last = _skip_events_today(os.path.join(HERMES_LOG_DIR, 'pipeline.log'),
                                       datetime.now(timezone.utc).strftime('%Y-%m-%d '))
        out['blocked_candidates_today'] = cnt
        out['last_skip_ts'] = last
    except Exception as e:
        log(f'WARN: fill_cap log scan failed: {e}')
    return out


def main():
    # F1 fix (bug_hunter 20261110, MEDIUM): the RELEASED transition is invisible
    # to decider_run — it respawns every pipeline minute with an empty state set,
    # so a cross-process release is never logged there (the real release at
    # 19:42Z left no trace anywhere durable). The tower feed runs every 60s and
    # owns the previous payload, so the engaged flip is durable HERE:
    # prev engaged=true -> current false = release. Stateless (reads the file it
    # is about to overwrite); Cap D's stateless contract untouched.
    _prev_engaged = None
    try:
        with open(OUTPUT) as f:
            _prev_engaged = (json.load(f).get('fill_cap') or {}).get('engaged')
    except Exception:
        _prev_engaged = None
    fill_cap = _fill_cap()
    try:
        if _prev_engaged is True and fill_cap.get('engaged') is False:
            _now = datetime.now(timezone.utc)
            log(f'DailyFillCap RELEASED {_now.strftime("%H:%M")}Z (tower) — '
                f'opens {fill_cap.get("opens_24h")} < {fill_cap.get("max")} (roll-off) '
                f'or fee-net {float(fill_cap.get("fee_net_24h") or 0):+.2f} >= 0 — '
                f'{fill_cap.get("blocked_candidates_today")} candidates held today')
    except Exception:
        pass  # visibility only — a log failure must never break the feed
    reg = _load(REGISTRY, None)
    if not reg or not isinstance(reg.get('entries'), list):
        log('ERROR: registry missing/empty — writing error feed')
        payload = {'generated_at': NOW.isoformat(), 'error': 'registry unreadable',
                   'counts': {}, 'sections': {}, 'trials': [], 'calendar': [],
                   'done': [], 'packets': [], 'fill_cap': fill_cap}
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
            'fill_cap': fill_cap,
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
