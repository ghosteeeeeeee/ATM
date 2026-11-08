#!/usr/bin/env python3
"""Payoff-fix CHANGE-NOW probes — CEO consult 20261108T180116Z (2026-11-08).

Runnable proof for the three live edits:
  1. STOP_TIGHTEN_SOURCES scope-widen (tuple append, 6 verdict-order names)
  2. tpsl_utils scope check exact-match -> substring membership
  3. [STOP-TIGHTEN-CAP050-SHADOW] log-only counterfactual hook
  4. constants diff = tuple + comment + 1 new flag ONLY (CEO_PROTECTED intact)

Usage: python3 brain/analysis/payoff_fix_probes_2026-11-08.py
Exit 0 iff every probe PASSes. Nothing here writes to the DB or to the logs —
the module-level `log` is monkeypatched to a capture list.
"""
import re
import subprocess
import sys

sys.path.insert(0, '/root/.hermes/scripts')
import tpsl_utils as T
import hermes_constants as hc

REPO = '/root/.hermes'
FAILURES = []


def chk(cond, name, detail=''):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ''),
          flush=True)
    if not cond:
        FAILURES.append(name)


# ── capture log lines ────────────────────────────────────────────────────────
_lines = []


def _fake_log(msg, *a, **k):
    _lines.append(str(msg))


T.log = _fake_log


def call(**kw):
    """Run the helper with a cleared dedup state; return (sl, payload, new_lines)."""
    base = dict(source='jup_yolo_mirrored', entry_price=1.0, proposed_sl=0.99,
                direction='LONG', token='PROBE', trade_id=900001, site='probe')
    base.update(kw)
    T._STOP_TIGHTEN_LOGGED.clear()
    T._STOP_TIGHTEN_CAP050_LOGGED.clear()
    before = len(_lines)
    sl, payload = T.stop_tighten_sl(**base)
    return sl, payload, _lines[before:]


def clamps(source, **kw):
    """Behavioral scope probe: dist 1.00% (> cap 0.75) — in-scope => clamped."""
    sl, payload, lg = call(source=source, proposed_sl=0.99, **kw)
    return sl, payload, lg


print("=== A. scope: substring membership (fix 2) ===")
# A1 combo source now caught (the exact-match escape)
sl, payload, lg = clamps('continuum+,jup_yolo_mirrored')
chk(abs(sl - 0.9925) < 1e-9 and payload is not None,
    "A1 combo 'continuum+,jup_yolo_mirrored' now clamps", f"sl={sl}")

# A2 near-miss: volume-buildout must NOT match volume-buildup-
names = [n for n in hc.STOP_TIGHTEN_SOURCES if n and n in 'volume-buildout']
sl, payload, lg = clamps('volume-buildout')
chk(names == [] and sl == 0.99 and payload is None,
    "A2 'volume-buildout' does NOT match 'volume-buildup-'", f"names={names}")

# A3/A4 pump-chain polarity: each matches only its own scope name
for src in ('pump-chain+', 'pump-chain-'):
    hit = [n for n in hc.STOP_TIGHTEN_SOURCES if n and n in src]
    sl, payload, lg = clamps(src)
    chk(hit == [src] and abs(sl - 0.9925) < 1e-9,
        f"A3/A4 {src!r} matches ONLY its own scope", f"hit={hit} sl={sl}")

# A5 out-of-scope sources stay identity (incl. volume-buildup+ vs scope 'volume-buildup-')
for src in ('bb_bounce', 'hl_copy_trader', 'rs_s,rs_s', 'mover+', 'volume-buildup+',
            'bb_squeeze', 'accel-300-breakout', 'r2v2-long4', 'bb-bounce-v3-long+'):
    sl, payload, lg = clamps(src)
    ok = sl == 0.99 and payload is None
    chk(ok, f"A5 out-of-scope identity {src!r}", f"sl={sl} payload={payload}")

# A6 in-scope exact names still clamp (both original entries)
for src in ('jup_yolo_mirrored', 'volume-buildup-'):
    sl, payload, lg = clamps(src)
    chk(abs(sl - 0.9925) < 1e-9 and payload is not None,
        f"A6 in-scope exact {src!r} clamps", f"sl={sl}")

# A7 the 6 appended verdict-order names all clamp, alone and in a combo
NEW6 = ['pump-chain+', 'pump-chain-', 'bb-squeeze+', 'volume-breakout-long+',
        'bb-bounce-v2-long+', 'r2v2-long3']
for src in NEW6 + ['r2-trend-long3,r2v2-long3', 'bb-squeeze+,rs-s33',
                   'STBL(1.47x)),chain(ADA(1.47x)),pump-chain+']:
    sl, payload, lg = clamps(src)
    chk(abs(sl - 0.9925) < 1e-9 and payload is not None,
        f"A7 new-scope clamp {src!r}", f"sl={sl}")

# A8 tuple = old tuple + exactly the 6 verdict-order names
OLD = ('jup_yolo_mirrored', 'volume-buildup-')
chk(hc.STOP_TIGHTEN_SOURCES[:2] == OLD
    and hc.STOP_TIGHTEN_SOURCES[2:] == tuple(NEW6)
    and len(hc.STOP_TIGHTEN_SOURCES) == 8,
    "A8 tuple = old 2 + 6 verdict-order names, order exact",
    str(hc.STOP_TIGHTEN_SOURCES))

# A9 ENFORCE=False => identity for EVERYTHING (in-scope, combo, out-of-scope)
T.STOP_TIGHTEN_ENFORCE = False
try:
    for src in ('jup_yolo_mirrored', 'continuum+,jup_yolo_mirrored',
                'pump-chain+', 'bb-squeeze+', 'volume-buildout', 'mover+'):
        sl, payload, lg = clamps(src)
        chk(sl == 0.99, f"A9 ENFORCE=False identity {src!r}", f"sl={sl}")
finally:
    T.STOP_TIGHTEN_ENFORCE = True

print("\n=== B. CAP-0.50 shadow (fix 4) ===")
# B1 dist=0.60: returns the 0.75-cap value (identity, 0.60 < 0.75) AND logs CAP050
sl, payload, lg = call(proposed_sl=0.994, trade_id=900011, site='probe_b1')
cap_lines = [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l]
chk(sl == 0.994, "B1a dist=0.60 returns 0.75-cap value (identity, under cap)", f"sl={sl}")
chk(len(cap_lines) == 1
    and 'dist=0.600% >0.50 would-clamp-to-0.50 (live cap 0.75)' in cap_lines[0]
    and 'counterfactual only' in cap_lines[0]
    and 'PROBE' in cap_lines[0] and '900011' in cap_lines[0]
    and 'probe_b1' in cap_lines[0],
    "B1b dist=0.60 logs the CAP050 line (exact format)",
    cap_lines[0].strip() if cap_lines else 'NO LINE')

# B2 dist=0.40: no CAP050 line
sl, payload, lg = call(proposed_sl=0.996, trade_id=900012, site='probe_b2')
chk(not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
    "B2 dist=0.40 logs NO CAP050 line", f"sl={sl}")

# B3 ENFORCE=False: zero CAP050 lines, identity
T.STOP_TIGHTEN_ENFORCE = False
try:
    sl, payload, lg = call(proposed_sl=0.994, trade_id=900013, site='probe_b3')
    chk(sl == 0.994 and not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
        "B3 ENFORCE=False => zero CAP050 lines + identity", f"sl={sl}")
    # and zero of ANY stop-tighten line at dist 0.60 (no clamp candidate)
    chk(not lg, "B3b ENFORCE=False dist=0.60 emits no helper lines at all")
finally:
    T.STOP_TIGHTEN_ENFORCE = True

# B4 dist=0.90: live 0.75 clamp still applies, NO CAP050 line (window <= cap)
sl, payload, lg = call(proposed_sl=0.99, trade_id=900014, site='probe_b4')
chk(abs(sl - 0.9925) < 1e-9,
    "B4a dist=0.90 clamps to 0.75-cap value (live behavior unchanged)", f"sl={sl}")
chk(not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
    "B4b dist=0.90 emits NO CAP050 line (window is 0.50 < d <= 0.75)")

# B5 profit-lock (LONG SL above entry) at dist 0.60: no CAP050 (loss-side rule)
sl, payload, lg = call(proposed_sl=1.006, direction='LONG', trade_id=900015,
                       site='probe_b5')
chk(sl == 1.006 and not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
    "B5 profit-lock LONG at dist 0.60 logs NO CAP050 line", f"sl={sl}")
# ...and unknown direction likewise
sl, payload, lg = call(proposed_sl=0.994, direction='', trade_id=900016,
                       site='probe_b5b')
chk(sl == 0.994 and not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
    "B5b direction='' logs NO CAP050 line", f"sl={sl}")

# B6 out-of-scope source at dist 0.60: no CAP050 line (scope gate first)
sl, payload, lg = call(source='mover+', proposed_sl=0.994, trade_id=900017,
                       site='probe_b6')
chk(sl == 0.994 and not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
    "B6 out-of-scope source logs NO CAP050 line", f"sl={sl}")

# B7 dedup: same (trade, site, hour) => one line; a second trade id => second line
# (direct calls — `call()` clears the dedup sets on purpose, so it can't be used here)
T._STOP_TIGHTEN_CAP050_LOGGED.clear()
_lines.clear()
for _tid in (900018, 900018, 900019):
    T.stop_tighten_sl('jup_yolo_mirrored', 1.0, 0.994, direction='LONG',
                      token='PROBE', trade_id=_tid, site='probe_b7')
n_cap = len([l for l in _lines if 'STOP-TIGHTEN-CAP050-SHADOW' in l])
chk(n_cap == 2, "B7 CAP050 dedup: 2 calls same key => 1 line, new trade => 2nd line",
    f"lines={n_cap}")

# B8 revert flag: STOP_TIGHTEN_CAP050_SHADOW=False => no lines (live SL unchanged)
T.STOP_TIGHTEN_CAP050_SHADOW = False
try:
    sl, payload, lg = call(proposed_sl=0.994, trade_id=900020, site='probe_b8')
    chk(sl == 0.994 and not [l for l in lg if 'STOP-TIGHTEN-CAP050-SHADOW' in l],
        "B8 CAP050_SHADOW=False => zero CAP050 lines (revert path)", f"sl={sl}")
finally:
    T.STOP_TIGHTEN_CAP050_SHADOW = True

# B9 CAP050 never changes the returned SL, in ANY state (loop over states)
for enf in (True, False):
    for cap050 in (True, False):
        T.STOP_TIGHTEN_ENFORCE = enf
        T.STOP_TIGHTEN_CAP050_SHADOW = cap050
        try:
            sl, payload, lg = call(proposed_sl=0.994, trade_id=900021, site='probe_b9')
            chk(sl == 0.994, f"B9 state ENFORCE={enf} CAP050={cap050}: SL untouched by CAP050",
                f"sl={sl}")
        finally:
            T.STOP_TIGHTEN_ENFORCE = True
            T.STOP_TIGHTEN_CAP050_SHADOW = True

print("\n=== C. constants diff = tuple + comment + 1 new flag ONLY ===")
head = subprocess.run(['git', '-C', REPO, 'show', 'HEAD:scripts/hermes_constants.py'],
                      capture_output=True, text=True, check=True).stdout
cur = open(f'{REPO}/scripts/hermes_constants.py', encoding='utf-8').read()


def assigns(text):
    out = {}
    for m in re.finditer(r'^([A-Z][A-Z0-9_]+)\s*=\s*(.+?)\s*$', text, re.M):
        out.setdefault(m.group(1), m.group(2))
    return out


def block(text, name):
    i = text.index(name)
    j = text.index('\n}', i)
    return text[i:j]


a_old, a_new = assigns(head), assigns(cur)
added = sorted(set(a_new) - set(a_old))
removed = sorted(set(a_old) - set(a_new))
changed = sorted(k for k in set(a_old) & set(a_new) if a_old[k] != a_new[k])
chk(added == ['STOP_TIGHTEN_CAP050_SHADOW'], "C1 exactly 1 constant ADDED",
    f"added={added}")
chk(removed == [], "C2 no constant removed", f"removed={removed}")
chk(changed == ['STOP_TIGHTEN_SOURCES'], "C3 exactly 1 value changed (the tuple)",
    f"changed={changed}")
chk(block(head, 'CEO_PROTECTED_FLAGS') == block(cur, 'CEO_PROTECTED_FLAGS'),
    "C4 CEO_PROTECTED_FLAGS byte-identical")
chk(a_new.get('STOP_TIGHTEN_CAP050_SHADOW') == 'True', "C5 new flag = True (shadow)")
# comment provenance present on the tuple line
tuple_line = next(l for l in cur.splitlines() if l.startswith('STOP_TIGHTEN_SOURCES'))
chk('20261108T180116Z' in tuple_line and 'stop_tighten_scope_cf_2026-11-08.py'
    in tuple_line and 'REVERT = remove the appended entries' in tuple_line,
    "C6 tuple comment carries consult id + walk script + revert path")
# CAP050 flag block carries polarity + bars + deadline
i = cur.index('STOP_TIGHTEN_CAP050_SHADOW = True')
pre = cur[max(0, i - 1600):i]
chk('POLARITY' in pre and 'n>=30' in pre and 'fk<=20%' in pre
    and '2026-11-14' in pre and 'NEVER changes' in pre,
    "C7 CAP050 flag comment has polarity + bars + deadline + non-flip warning")

print("\n" + "=" * 60)
if FAILURES:
    print(f"PROBES: {len(FAILURES)} FAIL -> {FAILURES}")
    sys.exit(1)
print("ALL PROBES PASS")
sys.exit(0)
