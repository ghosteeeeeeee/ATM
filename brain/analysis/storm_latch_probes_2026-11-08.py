#!/usr/bin/env python3
"""Storm-latch package probes — CEO verdict 20261108T230547Z (2026-11-08).

Runnable proof for the four shipped items:
  1. registry data/shadow_disposition.json — NO-CONVERT disposition, verified
     evidence append, RSI>=45 clause correction, Q4 stale-text note, new
     linreg-fade-storm-admission-shadow entry; json.load validated; git diff
     touches ONLY this run's fields.
  2. Q4 stale log text — [STORM-CONFL-WAIVER-SHADOW] line carries the exact
     NO-CONVERT static text and no longer emits "enforcement pending".
  3. linreg-fade storm-admission shadow — helper probes against a crafted
     storm/no-storm/missing candles_1m fixture (flag, family, direction, RSI
     band, BTC limb, dedup, exception safety), a drift detector pinning
     _storm_btc_limb == waiver limb (i), and source-level assertions that the
     floor block still fires byte-identical AFTER the shadow call.
  4. auto-flip policy — pure-function packet fixtures (met/dedupe/not-met/
     no-flag/non-open), evaluator resolution, wiring + "runner never writes
     hermes_constants.py" source asserts, and registry opt-in state (none).
  Constants: ADD-only proof (git diff has zero removed lines) + polarity
  asserts (new shadow flag True, no enforce flag, STORM_MIN_RSI untouched,
  floor 45, waiver ENFORCE False).

Usage: python3 brain/analysis/storm_latch_probes_2026-11-08.py
Exit 0 iff every probe PASSes.

Side effects: NONE on the live system — hermes_log.log is patched to a
capture list BEFORE signal_compactor is imported (so even the import-time
[INIT] lines never reach logs/pipeline.log), candles fixtures live in temp
files, and no DB is written. The live candles.db is only READ when the
drift-detector waiver helper runs compute_rsi_1m('PROBE') (no rows).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, '/root/.hermes/scripts')

# ── capture log lines BEFORE any module import can emit one ──────────────────
_LINES = []


def _fake_log(msg, *a, **k):
    _LINES.append(str(msg))


import hermes_log  # noqa: E402
hermes_log.log = _fake_log

import hermes_constants as hc  # noqa: E402
import signal_compactor as sc  # noqa: E402
import shadow_disposition as sd  # noqa: E402

sc.log = _fake_log   # belt + suspenders (sc bound hermes_log.log at import)

REPO = '/root/.hermes'
FAILURES = []


def chk(cond, name, detail=''):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ''),
          flush=True)
    if not cond:
        FAILURES.append(name)


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args],
                          capture_output=True, text=True, timeout=30).stdout


# ═════════════════════════════════════════════════════════════════════════════
# Item 1 — registry
# ═════════════════════════════════════════════════════════════════════════════
try:
    reg = json.load(open(f'{REPO}/data/shadow_disposition.json'))
    chk(True, 'registry: json.load validates')
except Exception as ex:
    reg = {'entries': []}
    chk(False, f'registry: json.load validates ({type(ex).__name__}: {ex})')

entries = [e for e in reg.get('entries', []) if isinstance(e, dict)]
w = next((e for e in entries if e.get('id') == 'storm-confl-waiver'), None)
chk(w is not None, 'registry: storm-confl-waiver present')
if w:
    chk(w.get('disposition', '').startswith(
        'NO-CONVERT 2026-11-08 (CEO 20261108T230547Z)'),
        'registry: disposition flipped FLIP-PENDING -> NO-CONVERT')
    chk('the storm bottleneck is the FLOOR, not single-type confluence'
        in w.get('disposition', ''),
        'registry: disposition carries the floor-is-the-bottleneck ruling')
    for frag in ('0 true fillable storm shorts',
                 'same signal died at short-rsi-hard-floor within 1s',
                 '(SYRUP RSI26.7, SAGA RSI33.3 <45)',
                 'storm-short census = 100% floor-blocked (28/28 tokens, 435/435 block lines)',
                 'the 16.6:1 (92.5 vs 5.6 short-rescue)',
                 'ALREADY-LIVE ceiling65-75 relief (33 hits)',
                 "default 'keep shadow, NO CONVERSION'"):
        chk(frag in w.get('evidence', ''), f'registry: evidence has {frag[:52]!r}')
    chk('RSI>=45 (corrected 2026-11-08' in w.get('threshold', ''),
        'registry: waiver threshold clause corrected >=35 -> >=45')
    chk('stale-text fixed 2026-11-08: line now distinguishes pending vs bar-met-awaiting-signoff'
        in w.get('notes', ''),
        'registry: Q4 stale-text note appended to notes')

n = next((e for e in entries
          if e.get('id') == 'linreg-fade-storm-admission-shadow'), None)
chk(n is not None, 'registry: linreg-fade-storm-admission-shadow entry added')
if n:
    chk(n.get('kind') == 'shadow' and n.get('status') == 'open'
        and n.get('started') == '2026-11-08'
        and n.get('deadline') == '2026-11-12T00:00:00Z'
        and n.get('owner') == 'CEO',
        'registry: new entry kind/status/started/deadline/owner')
    th = n.get('threshold', '')
    chk('STORM_BTC_1H_MOVE_PCT' in th and 'linreg-fade- RSI in [30,45)' in th
        and 'token-day dedup n>=20' in th and 'net >= +$1.00' in th
        and '2/3 positive days' in th
        and "default_action = 'stay blocked (floor holds)'" in th,
        'registry: new entry pre-registered threshold text complete')
    chk(n.get('default_action') == 'stay blocked (floor holds)',
        'registry: new entry default_action field')
    chk('CANNOT rescue linreg-fade-' in n.get('evidence', '')
        and '489-block class' in n.get('evidence', ''),
        'registry: new entry evidence (Q3 + 489-block spring)')
    chk('floor stays 45 for everyone else' in n.get('notes', '')
        and 'RSI>=35 clause being corrected to >=45' in n.get('notes', ''),
        'registry: new entry notes')
    chk(not re.findall(r'(?:brain|data)/[\w./-]+\.(?:db|jsonl|json)',
                       n.get('stream', '')),
        'registry: new entry stream has no parseable path (no false auto-KILL)')
chk(len(entries) == 97, f'registry: 97 entries after insert (got {len(entries)})')

# Pin the diff baseline to the PRE-SHIP commit: the hourly auto-commit
# e9035a27 ("logs: hourly analysis ... no config change") swept this package
# in mid-review, so an unpinned working-tree diff goes empty the moment the
# tree is committed — its gates would then pass vacuously (adversarial review
# MED-3, verified). Pattern from the payoff-fix probes (d5f306a1). An empty
# diff now FAILS instead of passing. Note: the sweep's commit message is
# mislabeled for these files — the proper `scripts: ` package commits follow.
BASE = 'e9035a27^'

# Registry check vs the pinned base — ENTRY-LEVEL, not raw line counts: other
# actors' edits can ride the same commits (the hourly sweep carried this
# package; a parallel session's signal-zombie-purge disposition at 00:45Z rode
# this package's registry commit via git add -u). This package may change ONLY
# its own fields/entries; foreign changes are reported as INFO, not failed.
diff = git('diff', BASE, '--', 'data/shadow_disposition.json')
chk(diff.strip(),
    'registry: package diff vs pinned baseline is non-empty (wrong-base guard)')
base_reg = json.loads(git('show', f'{BASE}:data/shadow_disposition.json'))


def _emap(d):
    return {e['id']: e for e in d.get('entries', []) if isinstance(e, dict)}


bm, wm = _emap(base_reg), _emap(reg)
added_ids = set(wm) - set(bm)
removed_ids = set(bm) - set(wm)
chk(added_ids == {'linreg-fade-storm-admission-shadow'},
    f'registry: exactly one entry added (added={sorted(added_ids)})')
chk(not removed_ids, f'registry: no entries removed (removed={sorted(removed_ids)})')
changed_ids = {k for k in (set(bm) & set(wm)) if bm[k] != wm[k]}
chk('storm-confl-waiver' in changed_ids,
    'registry: storm-confl-waiver changed by this run')
wfields = {k for k in bm['storm-confl-waiver']
           if bm['storm-confl-waiver'].get(k) != wm['storm-confl-waiver'].get(k)}
chk(wfields <= {'disposition', 'evidence', 'threshold', 'notes'},
    'registry: waiver changed ONLY this run\'s fields '
    f'(changed={sorted(wfields)})')
foreign = changed_ids - {'storm-confl-waiver'}
if foreign:
    print(f'  INFO foreign registry edits riding the same commits (not this '
          f'package): {sorted(foreign)}')
chk({k for k in base_reg if k != 'entries'
     and base_reg.get(k) != reg.get(k)} <= {'updated'},
    'registry: only top-level "updated" changed outside entries')

# ═════════════════════════════════════════════════════════════════════════════
# Item 2 — Q4 stale log text (source-level; the line is emitted live at runtime)
# ═════════════════════════════════════════════════════════════════════════════
src = open(f'{REPO}/scripts/signal_compactor.py').read()
chk('confluence (storm conditions met) — enforcement pending' not in src,
    'Q4: stale "— enforcement pending" fragment gone from the log line')
# the line is one log() call split across four f-string pieces — assert each
# piece, then prove the concatenated runtime text carries the mandated string
q4_pieces = [
    'single-type confluence (storm conditions met) — shadow only ',
    '(ENFORCE=False); conversion ruling: NO-CONVERT 20261108T230547Z, ',
    'floor is the bottleneck [3/3 bar MET 2026-11-08 22:22Z, no longer pending]',
    ' [limb-ii RSI clause: STORM_MIN_RSI=35 vs registered >=45 — see registry]',
]
chk(all(p in src for p in q4_pieces),
    'Q4: all log-line f-string pieces present in source')
runtime = ''.join(q4_pieces)
q4 = ('— shadow only (ENFORCE=False); conversion ruling: '
      'NO-CONVERT 20261108T230547Z, floor is the bottleneck')
chk(q4 in runtime, 'Q4: emitted text carries the exact static NO-CONVERT string')
chk('3/3 bar MET 2026-11-08 22:22Z, no longer pending' in runtime,
    'Q4: line distinguishes pending vs bar-met (bar already met)')
chk('[STORM-CONFL-WAIVER-SHADOW]' in src, 'Q4: tag unchanged')

# ═════════════════════════════════════════════════════════════════════════════
# Constants — ADD-only + polarity
# ═════════════════════════════════════════════════════════════════════════════
cst_diff = git('diff', BASE, '--', 'scripts/hermes_constants.py')
chk(cst_diff.strip(),
    'constants: package diff vs pinned baseline is non-empty (wrong-base guard)')
cst_rem = [l for l in cst_diff.splitlines()
           if l.startswith('-') and not l.startswith('---')]
chk(not cst_rem, 'constants: git diff is ADD-only (zero removed lines)',
    f'removed={cst_rem[:3]}')
chk(hc.LINREG_FADE_STORM_SHADOW is True,
    'constants: LINREG_FADE_STORM_SHADOW = True (new flag)')
chk(not hasattr(hc, 'LINREG_FADE_STORM_ENFORCE'),
    'ENFORCE polarity assert False: no LINREG_FADE_STORM_ENFORCE flag ships')
chk(hc.STORM_MIN_RSI == 35,
    'constants: STORM_MIN_RSI untouched (value change out of ADD-only scope)')
chk(hc.STORM_CONFLUENCE_WAIVER_ENFORCE is False,
    'constants: waiver ENFORCE stays False')
chk(hc.STORM_CONFLUENCE_WAIVER_SHADOW is True,
    'constants: waiver SHADOW stays True')
chk(hc.SHORT_RSI_HARD_FLOOR == 45, 'constants: floor stays 45')

# ═════════════════════════════════════════════════════════════════════════════
# Item 3 — linreg-fade storm-admission shadow
# ═════════════════════════════════════════════════════════════════════════════
ORIG_CANDLES = sc.CANDLES_DB
TMP_DBS = []


def make_candles(move_pct=None):
    """Temp candles_1m with one BTC 60m window; move_pct=None -> no rows."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    TMP_DBS.append(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute('CREATE TABLE candles_1m (token TEXT, ts INTEGER, close REAL)')
        if move_pct is not None:
            now = int(time.time())
            p = 75000.0
            conn.execute("INSERT INTO candles_1m VALUES ('BTC', ?, ?)",
                         (now - 3600, p))
            conn.execute("INSERT INTO candles_1m VALUES ('BTC', ?, ?)",
                         (now, p * (1.0 + move_pct / 100.0)))
        conn.commit()
    finally:
        conn.close()
    return path


def shadow_case(**kw):
    """Run the helper with a cleared capture; return (emitted, lines)."""
    _LINES.clear()
    emitted = sc._linreg_fade_storm_shadow(**kw)
    return emitted, list(_LINES)


try:
    # ── storm limb fixtures ──────────────────────────────────────────────────
    sc.CANDLES_DB = make_candles(-2.0)      # storm: -2.0% <= -1.5
    ok, mv = sc._storm_btc_limb()
    chk(ok and mv is not None and abs(mv - (-2.0)) < 0.01,
        'storm limb: -2.0% fixture -> (True, -2.0)', f'got ({ok}, {mv})')

    sc.CANDLES_DB = make_candles(-1.0)      # not stormy
    ok, mv = sc._storm_btc_limb()
    chk(not ok and mv is not None and abs(mv - (-1.0)) < 0.01,
        'storm limb: -1.0% fixture -> (False, -1.0)', f'got ({ok}, {mv})')

    sc.CANDLES_DB = make_candles(None)      # missing data -> fail safe
    ok, mv = sc._storm_btc_limb()
    chk(ok is False and mv is None,
        'storm limb: missing rows -> fail-safe (False, None)')

    # ── drift detector: _storm_btc_limb == waiver limb (i) ───────────────────
    def waiver_limb_verdict():
        """Run the reviewed waiver helper; classify the stopping limb."""
        _LINES.clear()
        sc._storm_confluence_would_pass('PROBE', 'SHORT')
        txt = '\n'.join(_LINES)
        if 'FAIL(i btc-data-missing' in txt or 'not stormy enough' in txt:
            return 'i-fail', txt
        return 'i-pass', txt   # reached limb (ii)+ -> limb (i) held

    for move, expect in ((None, 'i-fail'), (-1.0, 'i-fail'), (-2.0, 'i-pass')):
        sc.CANDLES_DB = make_candles(move)
        limb_ok, _ = sc._storm_btc_limb()
        verdict, txt = waiver_limb_verdict()
        chk(verdict == expect and (limb_ok == (verdict == 'i-pass')),
            f'drift detector: limb fixture move={move} -> '
            f'waiver={verdict} limb_ok={limb_ok}',
            txt.replace('\n', ' | ')[:160])

    # ── helper probes (storm fixture live) ───────────────────────────────────
    sc.CANDLES_DB = make_candles(-2.0)

    emitted, lines = shadow_case(tkn='PROBE1', direction='SHORT',
                                 source='linreg-fade', rsi=35.0, floor=45)
    chk(emitted and len(lines) == 1, 'shadow: storm + linreg-fade + rsi35 -> line',
        f'lines={lines}')
    if lines:
        L = lines[0]
        chk('[LINREG-FADE-STORM-SHADOW]' in L
            and 'PROBE1 SHORT WOULD-ADMIT' in L
            and 'rsi=35.00' in L
            and 'storm band [30,45)' in L
            and 'floor 45' in L
            and 'ENFORCE=False' in L,
            'shadow: line text matches the registered template', L)

    emitted2, lines2 = shadow_case(tkn='PROBE1', direction='SHORT',
                                   source='linreg-fade', rsi=35.0, floor=45)
    chk(not emitted2 and not lines2,
        'shadow: (token,site,hour) dedup suppresses the repeat call')

    emitted, lines = shadow_case(tkn='PROBE2', direction='SHORT',
                                 source='linreg-fade', rsi=50.0, floor=45)
    chk(not emitted and not lines,
        'shadow: RSI50 (outside [30,45)) -> no line')

    emitted, lines = shadow_case(tkn='PROBE3', direction='SHORT',
                                 source='linreg-fade', rsi=29.9, floor=45)
    chk(not emitted and not lines, 'shadow: RSI29.9 (below band) -> no line')

    emitted, lines = shadow_case(tkn='PROBE4', direction='SHORT',
                                 source='linreg-fade', rsi=44.9, floor=45)
    chk(emitted and lines, 'shadow: RSI44.9 (band top) -> line')

    # no storm
    sc.CANDLES_DB = make_candles(-1.0)
    emitted, lines = shadow_case(tkn='PROBE5', direction='SHORT',
                                 source='linreg-fade', rsi=35.0, floor=45)
    chk(not emitted and not lines, 'shadow: no storm -> no line')

    # family / direction negatives (storm fixture)
    sc.CANDLES_DB = make_candles(-2.0)
    emitted, lines = shadow_case(tkn='PROBE6', direction='SHORT',
                                 source='pump-chain-', rsi=35.0, floor=45)
    chk(not emitted and not lines, 'shadow: non-linreg family -> no line')
    emitted, lines = shadow_case(tkn='PROBE7', direction='LONG',
                                 source='linreg-fade', rsi=35.0, floor=45)
    chk(not emitted and not lines, 'shadow: LONG direction -> no line')
    emitted, lines = shadow_case(tkn='PROBE8', direction='SHORT',
                                 source='linreg_fade', rsi=35.0, floor=45)
    chk(emitted and lines, 'shadow: dual-form source linreg_fade matches')

    # flag off
    hc.LINREG_FADE_STORM_SHADOW = False
    emitted, lines = shadow_case(tkn='PROBE9', direction='SHORT',
                                 source='linreg-fade', rsi=35.0, floor=45)
    chk(not emitted and not lines,
        'shadow: LINREG_FADE_STORM_SHADOW=False -> no lines (flag off)')
    hc.LINREG_FADE_STORM_SHADOW = True
    emitted, lines = shadow_case(tkn='PROBE9', direction='SHORT',
                                 source='linreg-fade', rsi=35.0, floor=45)
    chk(emitted and lines, 'shadow: flag restored True -> line again')

    # rsi<35 label hygiene (adversarial review MED-1): band stays [30,45) as
    # pre-registered, but the line must admit it can never actually admit
    emitted, lines = shadow_case(tkn='PROBE11', direction='SHORT',
                                 source='linreg-fade', rsi=32.0, floor=45)
    chk(emitted and lines and 'can NEVER admit' in lines[0]
        and 'WOULD-ADMIT' in lines[0] and 'ENFORCE=False' in lines[0],
        'shadow: rsi<35 line carries the knife-dead (BANANA) caveat',
        lines[0] if lines else '')

    # dry-run tagging (review LOW-4): dry lines distinguishable + independent key
    emitted, lines = shadow_case(tkn='PROBE12', direction='SHORT',
                                 source='linreg-fade', rsi=35.0, floor=45,
                                 dry=True)
    chk(emitted and lines and 'dry-run' in lines[0]
        and 'exclude from bar counts' in lines[0],
        'shadow: dry-run lines tagged (excluded from bar counts)',
        lines[0] if lines else '')
    emitted, lines = shadow_case(tkn='PROBE12', direction='SHORT',
                                 source='linreg-fade', rsi=35.0, floor=45,
                                 dry=False)
    chk(emitted and lines,
        'shadow: dry/live dedup keys independent (no cross-mode suppression)')

    # exception safety: the helper must swallow a raising storm limb
    orig_limb = sc._storm_btc_limb

    def _boom():
        raise RuntimeError('probe-forced limb failure')

    sc._storm_btc_limb = _boom
    try:
        emitted, lines = shadow_case(tkn='PROBE10', direction='SHORT',
                                     source='linreg-fade', rsi=35.0, floor=45)
        chk(emitted is False and not lines,
            'shadow: raising storm limb -> swallowed, returns False (double-guarded)')
    finally:
        sc._storm_btc_limb = orig_limb

    # ── helper scope: BTC limb ONLY (no confluence/sibling reuse) ────────────
    helper_src = src[src.index('def _linreg_fade_storm_shadow'):
                     src.index('def run_compaction')]
    chk('_storm_btc_limb(' in helper_src
        and '_storm_confluence_would_pass' not in helper_src,
        'shadow: helper reuses BTC limb only — never the confluence helper')
    limb_src = src[src.index('def _storm_btc_limb'):
                   src.index('# ── linreg-fade storm-admission SHADOW')]
    chk('STORM_MIN_RSI' not in limb_src
        and 'STORM_SIBLING_WINDOW_MIN' not in limb_src,
        'storm limb: contains no RSI (ii) / sibling (iii) conditions')

    # ── floor identity: block still fires, byte-identical, AFTER the shadow ──
    BLOCK = ('log(f"  🚫 [SHORT-RSI-HARD-FLOOR] {tkn}: SHORT blocked at approval — '
             'RSI {_rsh_rsi:.2f} < {_rsh_floor} (exec-time floor would reject anyway)")')
    TOMB = "_tombstone_pending(tkn, direction, 'short-rsi-hard-floor', dry)"
    chk(BLOCK in src, 'floor: block log line byte-identical (unchanged)')
    chk(TOMB in src, 'floor: tombstone still written')
    idx_call = src.index('_linreg_fade_storm_shadow('
                         '\n')   # call site (def is single-line)
    idx_block = src.index(BLOCK, idx_call)
    idx_tomb = src.index(TOMB, idx_block)
    chk(idx_call < idx_block < idx_tomb,
        'floor: shadow call precedes block log; tombstone follows block log')
    chk('continue' in src[idx_tomb:idx_tomb + 160],
        'floor: continue still fires after tombstone (identity outcome)')
    chk('except Exception:\n'
        '                                        pass  # shadow must never alter the block'
        in src, 'floor: call site double-guarded (own try/except)')
    chk('if _rsh_bear_override:' in src[:idx_call]
        and '✅ [SHORT-RSI-HARD-FLOOR]' in src[:idx_call],
        'floor: shadow sits inside the BLOCK (else) branch of _rsh_bear_override')
finally:
    sc.CANDLES_DB = ORIG_CANDLES
    for p in TMP_DBS:
        try:
            os.unlink(p)
        except OSError:
            pass

# ═════════════════════════════════════════════════════════════════════════════
# Item 4 — auto-flip policy (runner)
# ═════════════════════════════════════════════════════════════════════════════
sd_src = open(f'{REPO}/scripts/shadow_disposition.py').read()
sd_norm = re.sub(r'\s+', ' ', sd_src)
chk('AUTO-FLIP POLICY (CEO 20261108T230547Z): gate admissions with registered defaults'
    in sd_norm, 'runner: policy documented (docstring + packet line)')
chk('money-sizing/mults/protected flags NEVER auto-flip' in sd_src,
    'runner: protected-flag exclusion stated')
chk('[AUTO-FLIP-READY]' in sd_src and 'auto_flip_fired' in sd_src,
    'runner: packet tag + state dedupe key wired')
chk('auto_flip_flag' in sd_src and 'auto_flip_bar' in sd_src
    and 'auto_flip_packet' in sd_src,
    'runner: opt-in field + bar resolver + packet builder present')
chk("auto_flip_packet(e, st, now_iso" in sd_src,
    'runner: main loop calls the packet builder with entry state')
chk("pending_state.append((eid, 'auto_flip_fired', af_val))" in sd_src,
    'runner: state write queued append-success-only (MED-4 contract)')
chk(not re.search(r"open\([^)]*hermes_constants[^)]*,\s*['\"]w", sd_src),
    'runner: NEVER opens hermes_constants.py for write (flip stays a human edit)')

# in-process packet fixtures (same semantics the selfcheck asserts)
fx = {'id': 'probe-autoflip', 'status': 'open',
      'auto_flip_flag': 'PROBE_ADMISSION_FLAG'}
ln, sv = sd.auto_flip_packet(fx, {}, sd.NOW.isoformat(), True, 'probe bar met')
chk(ln is not None and '[AUTO-FLIP-READY]' in ln
    and 'probe-autoflip bar met' in ln and 'PROBE_ADMISSION_FLAG' in ln
    and 'one-line command' in ln,
    'auto-flip: met bar -> loud packet naming flag + one-line command')
chk(sd.auto_flip_packet(fx, {'auto_flip_fired': 'x'}, sd.NOW.isoformat(),
                        True, 'd')[0] is None,
    'auto-flip: state dedupe -> packet fires once')
chk(sd.auto_flip_packet(fx, {}, sd.NOW.isoformat(), False, 'd')[0] is None,
    'auto-flip: bar not met -> no packet')
# protected-flag denylist (bug_hunter LOW-3: enforced in code, not prose)
chk(sd.auto_flip_flag_blocked('WINNER_CELL_SIZE_MULT') is not None,
    'auto-flip: WINNER_CELL_SIZE_MULT refused (money-sizing denylist)')
chk(sd.auto_flip_flag_blocked('PM_TRAIL_ACTIVATE_PCT') is not None,
    'auto-flip: PM_TRAIL_* refused (CEO-protected denylist)')
chk(sd.auto_flip_flag_blocked('some lowercase') is not None,
    'auto-flip: non-flag-name string refused')
chk(sd.auto_flip_flag_blocked('LINREG_FADE_STORM_SHADOW') is None,
    'auto-flip: ordinary gate flag not blocked (opt-in stays possible)')
chk(sd.auto_flip_packet(dict(fx, auto_flip_flag='WINNER_CELL_SIZE_MULT'),
                        {}, sd.NOW.isoformat(), True, 'd')[0] is None,
    'auto-flip: protected flag cannot reach a packet (defense in depth)')
# polarity guard (adversarial MED-2): breach-style threshold_eval needs an
# explicit auto_flip_polarity="true=met" declaration or the bar is unknowable
sd.THRESHOLD_EVALS['_probe_breach'] = lambda e: (True, '-> BREACH: trial PnL -2.60 < -2.5')
b, d = sd.auto_flip_bar({'id': 'probe-p1', 'threshold_eval': '_probe_breach'})
chk(b is None and 'polarity' in d,
    'auto-flip: breach-style eval WITHOUT declaration -> NO packet (no inversion)',
    d)
b, d = sd.auto_flip_bar({'id': 'probe-p2', 'threshold_eval': '_probe_breach',
                         'auto_flip_polarity': 'true=met'})
chk(b is True and 'true=met' in d,
    'auto-flip: declared true=met resolves the bar with the caveat in detail')
sd.THRESHOLD_EVALS.pop('_probe_breach', None)


def _probe_boom(e):
    raise RuntimeError('must not run — preset should short-circuit')


sd.THRESHOLD_EVALS['_probe_boom'] = _probe_boom
b, d = sd.auto_flip_bar({'id': 'probe-p3', 'threshold_eval': '_probe_boom',
                         'auto_flip_polarity': 'true=met'},
                        preset=('_probe_boom', True, 'preset bar met'))
chk(b is True and 'preset bar met' in d and 'must not run' not in d,
    'auto-flip: preset short-circuits the evaluator (no double run)', d)
sd.THRESHOLD_EVALS.pop('_probe_boom', None)
chk("st.pop('auto_flip_fired', None)" in sd_src,
    'runner: auto_flip_fired re-arms when the bar clears (review LOW-7)')
b, d = sd.auto_flip_bar({'id': 'probe-no-eval'})
chk(b is None, 'auto-flip: no evaluator -> bar unknowable (no false packet)', d)
reg_af = [e.get('id') for e in entries if e.get('auto_flip_flag')]
chk(not reg_af,
    'auto-flip: no registry entry opted in yet (mechanism ships ready)',
    f'found={reg_af}')

# ═════════════════════════════════════════════════════════════════════════════
print()
if FAILURES:
    print(f'SELFCHECK FAIL — {len(FAILURES)} probe(s) failed:')
    for f in FAILURES:
        print(f'  - {f}')
    sys.exit(1)
print('SELFCHECK PASS — all storm-latch probes green')
sys.exit(0)
