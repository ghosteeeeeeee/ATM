#!/usr/bin/env python3
"""brake_shadow_probe.py — probe for registry `brake-counterfactual-shadow`.

Two sections, one file (the smallest check that fails if the logic breaks):

  A. decider_run._daily_fill_cap_block + _brake_shadow_record — the block
     decision and SKIP bytes must be BYTE-IDENTICAL with/without persistence:
       A1  n=15 / net=-0.65  -> True + exact SKIP line + store row written
       A2  same call twice   -> 2 SKIP lines (log is raw), 1 store row (dedup)
       A3  store write RAISES -> still True + SKIP bytes identical
       A4  store path broken (connect fails) -> still True + SKIP identical
       A5  DAILY_FILL_CAP_ENABLED=False -> False + NO SKIP + NO store file
  B. control_tower_api._skip_events_today — parity probe: raw count must equal
     an independent line scan of the same file (both logged forms), events
     must be echo-deduped, day boundary must stop the scan, runtime bounded.

PG is stubbed (no DB touched), decider_run.log is captured (nothing written
to the real pipeline.log), and both shadow stores point at a temp dir.

Usage: python3 scripts/brake_shadow_probe.py   # exit 0 = PASS
(renamed from test_brake_shadow.py: .gitignore:95 ignores scripts/test_*.py,
so the probe ships under the committed *_probe.py house style)
"""
import importlib.util
import os
import re
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ok = True


def chk(cond, name):
    global ok
    print(('PASS  ' if cond else 'FAIL  ') + name, flush=True)
    ok = ok and bool(cond)


# ── A. block decision byte-identity + store write ────────────────────────────
import decider_run as dr            # noqa: E402  (import runs module level — it
                                    # is re-imported every pipeline minute)
import hermes_constants as hc       # noqa: E402

CAP_MAX = int(hc.DAILY_FILL_CAP_MAX)
N, NET = 15, -0.65
TOKEN, DIRECTION, SOURCE = 'BTCX', 'SHORT', 'probe-src'
EXPECTED_SKIP = (
    f'SKIP: DailyFillCap — {N} opens in last 24h (max {CAP_MAX}) '
    f'while fee-net {NET:+.2f} < 0 — brake until first green 24h '
    f'[blocked {TOKEN} {DIRECTION} {SOURCE}]'
)


class _FakeCur:
    def __init__(self, row):
        self._row = row

    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return self._row

    def close(self):
        pass


class _FakeConn:
    def __init__(self, row):
        self._row = row

    def cursor(self):
        return _FakeCur(self._row)

    def close(self):
        pass


# stub PG BEFORE any call: one SQL read -> (opens_24h, fee_net_24h)
dr.psycopg2.connect = lambda **kw: _FakeConn((N, NET))
# capture log() instead of writing the real pipeline.log
_captured = []
dr.log = lambda msg, level=None: _captured.append(str(msg))

tmp = tempfile.mkdtemp(prefix='brake_probe_')
store = os.path.join(tmp, 'brake.db')
dr._BRAKE_SHADOW_DB = store


def last_skip():
    hits = [l for l in _captured if 'SKIP: DailyFillCap' in l]
    return hits[-1] if hits else None


def reset():
    _captured.clear()


# A1 — block fires, SKIP exact, row written with brake state + dedup key
reset()
res = dr._daily_fill_cap_block(TOKEN, DIRECTION, SOURCE)
chk(res is True, 'A1 n=15/net=-0.65 -> block True')
chk(last_skip() == EXPECTED_SKIP, 'A1 SKIP line byte-exact (identity carried)')
rows = sqlite3.connect(store).execute(
    'SELECT ts, token, direction, source, fee_net_24h, opens_24h, dedup_key '
    'FROM events').fetchall()
chk(len(rows) == 1, f'A1 store row written (got {len(rows)})')
ts, tok, direc, src, fee, opens, dkey = rows[0]
chk(tok == TOKEN and direc == DIRECTION and src == SOURCE
    and fee == NET and opens == N
    and re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', ts)
    and dkey == f'{TOKEN}|{DIRECTION}|{ts[:13].replace(" ", "T")}',
    f'A1 row carries ts/token/dir/src/fee-net/opens + hour dedup key ({dkey})')

# A2 — log is raw (every call logs), store dedups per token|direction|hour
reset()
res2 = dr._daily_fill_cap_block(TOKEN, DIRECTION, SOURCE)
n_rows = sqlite3.connect(store).execute('SELECT COUNT(*) FROM events').fetchone()[0]
chk(res2 is True and last_skip() == EXPECTED_SKIP,
    'A2 second block logs the same raw SKIP again')
chk(n_rows == 1, f'A2 store deduped to 1 row for the same token|dir|hour ({n_rows})')

# A3 — store write RAISES: decision + SKIP bytes unchanged
reset()
_orig_record = dr._brake_shadow_record
dr._brake_shadow_record = lambda *a, **k: (_ for _ in ()).throw(
    RuntimeError('probe: store write exploded'))
res3 = dr._daily_fill_cap_block(TOKEN, DIRECTION, SOURCE)
chk(res3 is True, 'A3 store-write raising -> still block True')
chk(last_skip() == EXPECTED_SKIP, 'A3 SKIP bytes identical with store raising')

# A4 — store path broken (connect itself fails, caught inside the helper)
reset()
dr._brake_shadow_record = _orig_record   # restore the real helper
dr._BRAKE_SHADOW_DB = tmp  # a DIRECTORY: sqlite3.connect fails to open
res4 = dr._daily_fill_cap_block(TOKEN, DIRECTION, SOURCE)
chk(res4 is True, 'A4 broken store path -> still block True (inner guard)')
chk(last_skip() == EXPECTED_SKIP, 'A4 SKIP bytes identical with broken store')

# A5 — flag off: no block, no SKIP, no store file at all
reset()
hc.DAILY_FILL_CAP_ENABLED = False
fresh_store = os.path.join(tmp, 'off.db')
dr._BRAKE_SHADOW_DB = fresh_store
res5 = dr._daily_fill_cap_block(TOKEN, DIRECTION, SOURCE)
hc.DAILY_FILL_CAP_ENABLED = True   # restore the live value (memory only)
chk(res5 is False, 'A5 DAILY_FILL_CAP_ENABLED=False -> no block')
chk(last_skip() is None, 'A5 flag off -> no SKIP line')
chk(not os.path.exists(fresh_store), 'A5 flag off -> no store file created')

# ── B. tower parity: raw line count vs independent scan, event dedup ────────
spec = importlib.util.spec_from_file_location(
    'control_tower_api', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      'control_tower_api.py'))
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)

# synthetic log: pre-today line, one event + its stdout echo, a second event,
# a junk line — raw must count all 3 marker lines, events must dedup to 2.
syn = os.path.join(tmp, 'pipeline.log')
with open(syn, 'w') as f:
    f.write('2026-11-19 23:59:50 SKIP: DailyFillCap — yesterday\n')
    f.write('2026-11-20 01:00:00 SKIP: DailyFillCap — a [blocked AA LONG s]\n')
    f.write('2026-11-20 01:00:01   2026-11-20 01:00:00 SKIP: DailyFillCap — a '
            '[blocked AA LONG s]\n')
    f.write('2026-11-20 01:00:02 SKIP: DailyFillCap — b [blocked BB SHORT s]\n')
    f.write('2026-11-20 01:00:03 unrelated line\n')
raw, ev, last = ct._skip_events_today(syn, '2026-11-20 ')
chk((raw, ev) == (3, 2), f'B1 raw counts both forms, events dedup echoes (got {raw},{ev})')
chk(last == '2026-11-20T01:00:02Z', f'B1 last_skip_ts = newest event ({last})')

# real-log parity: tower raw count == an independent line scan of the file
real = os.path.join(ct.HERMES_LOG_DIR, 'pipeline.log')
day = datetime.now(timezone.utc).strftime('%Y-%m-%d ')
t0 = time.time()
raw_real, ev_real, _ = ct._skip_events_today(real, day)
elapsed = time.time() - t0
indep_raw = 0
indep_events = set()
with open(real, 'rb') as f:
    for bline in f:
        line = bline.decode('utf-8', 'replace')
        if not line.startswith(day):
            continue
        if 'SKIP: DailyFillCap' in line:
            indep_raw += 1
            m = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(.*)$', line.rstrip('\n'))
            if m:
                rest = m.group(2)
                me = re.match(r'^\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(.*)$', rest)
                if me:
                    indep_events.add((me.group(1), me.group(2)))
                else:
                    indep_events.add((m.group(1), rest))
chk(raw_real == indep_raw,
    f'B2 tower raw == independent scan ({raw_real} == {indep_raw})')
chk(ev_real == len(indep_events),
    f'B2 tower events == independent echo-dedup ({ev_real} == {len(indep_events)})')
chk(raw_real >= ev_real, 'B2 raw >= events (echoes only ever add lines)')
chk(elapsed < 2.0, f'B2 scan runtime {elapsed:.3f}s < 2s (60s feed)')

print('SELFCHECK ' + ('PASS' if ok else 'FAIL'), flush=True)
sys.exit(0 if ok else 1)
