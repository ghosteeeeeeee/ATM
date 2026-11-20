#!/usr/bin/env python3
"""Selfcheck — atr-trend ride_it exit trial wiring (CEO deep run 20261119T225832Z, result-1).

OFF path (flag False, on-disk file): behavior must be identical to the
PRE-wiring commit a037e7a0^ (result-2 bug_hunter fix: the original pinned to
HEAD, which became the wiring commit itself once a037e7a0 landed — that made
the identity checks vacuous and the "only new name" check FAIL after commit).
ON path (flag True in a SUBPROCESS over a patched COPY of hermes_constants):
all five atr-trend variants bypass PM trail, map to ride_it, and join the
universal-hold exemption. The on-disk file must remain False.

NOTE (test-harness trap, found by result-2): position_manager.py:17 inserts
scripts/ at sys.path[0] during ITS import — so any patched-copy test must
import hermes_constants BEFORE position_manager, or the on-disk copy shadows
the patched one. Production is unaffected (one file on disk is the config).

Run: python3 automation/ceo/checkpoints/selfcheck_20261119T225832Z_result1.py
"""
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import textwrap
import pathlib

REPO = pathlib.Path('/root/.hermes')
SCRIPTS = REPO / 'scripts'
CONSTANTS = SCRIPTS / 'hermes_constants.py'
POSITION_MANAGER = SCRIPTS / 'position_manager.py'
BASE = 'a037e7a0^'  # pre-wiring commit; HEAD moves, this must not
FIVE = ('atr-trend', 'atr-trend+', 'atr-trend-',
        'atr_trend_accel_long', 'atr_trend_accel_short')
SIGNALS = ('atr-trend', 'atr-trend+', 'atr-trend-',
           'atr_trend_accel_long', 'atr_trend_accel_short',
           'trend-ride+', 'btc-wave', 'linreg-fade', 'volume-breakout', 'mover-')

FAILURES = []


def check(label, cond, detail=''):
    tag = 'PASS' if cond else 'FAIL'
    print(f'[{tag}] {label}' + (f' — {detail}' if detail else ''))
    if not cond:
        FAILURES.append(label)


def ride_it_slice(src):
    """Extract the real _is_ride_it block (assignment through the gated if)."""
    i = src.index('\n        _is_ride_it = any(') + 1
    j = src.index('\n        _mh_exempt =', i) + 1
    return textwrap.dedent(src[i:j])


def eval_is_ride_it(src, pos_signal):
    ns = {'_pos_signal': pos_signal}
    exec(compile(ride_it_slice(src), '<_is_ride_it>', 'exec'), ns)
    return ns['_is_ride_it']


def _val_eq(a, b):
    """Values equal; for functions compare source (object identity differs)."""
    if callable(a) or callable(b):
        import inspect
        try:
            return inspect.getsource(a) == inspect.getsource(b)
        except Exception:
            return a is b
    return a == b


def off_path():
    # Pin path-derived constants so the baseline copy (loaded from /tmp) resolves
    # the same values as the on-disk module (resolved from scripts/).
    os.environ.setdefault('HERMES_DATA_DIR', '/root/.hermes/data')
    os.environ.setdefault('WWW_DATA_DIR', '/var/www/hermes/data')
    print('── py_compile ──')
    for f in (CONSTANTS, POSITION_MANAGER):
        try:
            py_compile.compile(str(f), doraise=True)
            check(f'py_compile {f.name}', True)
        except py_compile.PyCompileError as e:
            check(f'py_compile {f.name}', False, str(e))

    print('── OFF path: hermes_constants (flag False) ──')
    sys.path.insert(0, str(SCRIPTS))
    import hermes_constants as hc
    check('flag is False on disk', hc.ATR_TREND_EXIT_TRIAL_ENABLED is False,
          repr(hc.ATR_TREND_EXIT_TRIAL_ENABLED))

    # Byte-identical values for every pre-existing name vs PRE-wiring baseline.
    old_src = subprocess.run(
        ['git', 'show', f'{BASE}:scripts/hermes_constants.py'],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    tmp = tempfile.mkdtemp(prefix='hc_old_')
    old_path = pathlib.Path(tmp) / 'hermes_constants_head.py'
    old_path.write_text(old_src)
    import importlib.util
    spec = importlib.util.spec_from_file_location('hermes_constants_head', old_path)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old  # register so inspect.getsource works
    spec.loader.exec_module(old)
    old_names = {k for k in vars(old) if not k.startswith('__')}
    new_names = {k for k in vars(hc) if not k.startswith('__')}
    check('only new name is the trial flag',
          new_names - old_names == {'ATR_TREND_EXIT_TRIAL_ENABLED'}
          and not (old_names - new_names),
          f'added={sorted(new_names - old_names)} removed={sorted(old_names - new_names)}')
    # REP_DB_PATH & friends are __file__-derived: the baseline copy loads from
    # /tmp, so normalize each module's own repo-root prefix before comparing.
    old_root = os.path.dirname(os.path.dirname(old.__file__))
    new_root = os.path.dirname(os.path.dirname(hc.__file__))

    def norm(v):
        return v.replace(old_root, new_root) if isinstance(v, str) else v

    diffs = [k for k in old_names
             if not _val_eq(norm(vars(old)[k]), norm(vars(hc).get(k, object())))]
    check('every existing name byte-identical to pre-wiring baseline', not diffs, f'differing={diffs}')
    d = subprocess.run(['git', 'diff', '--unified=0', BASE, '--', 'scripts/hermes_constants.py'],
                       cwd=REPO, capture_output=True, text=True, check=True).stdout
    removals = [l for l in d.splitlines() if l.startswith('-') and not l.startswith('---')]
    check('git diff of hermes_constants: additions only (no line removed/edited)',
          not removals, f'removed={removals[:5]}')
    shutil.rmtree(tmp, ignore_errors=True)

    bypass = hc.PROFIT_MONSTER_BYPASS_SIGNALS
    hit = [s for s in FIVE if s in bypass]
    hit_sub = [s for s in bypass if 'atr-trend' in s or 'atr_trend' in s]
    check('bypass contains none of the 5 atr-trend variants',
          not hit and not hit_sub, f'exact={hit} substring={hit_sub}')
    bad_keys = [k for k in hc.SIGNAL_EXIT_CONFIG if 'atr-trend' in k or 'atr_trend' in k]
    check('SIGNAL_EXIT_CONFIG has no atr-trend key', not bad_keys, f'keys={bad_keys}')

    print('── OFF path: position_manager ──')
    import position_manager as pm
    for s in ('atr-trend', 'atr-trend+', 'atr_trend_accel_long'):
        v = pm._match_exit_config(s)
        # Code deviation note: matcher default is None (callers treat None as
        # the default engine, pm_trail) — mandate said "returns pm_trail".
        check(f"_match_exit_config('{s}') returns default (None => pm_trail)",
              v is None, repr(v))
    check("control: _match_exit_config('trend-ride+') == 'ride_it'",
          pm._match_exit_config('trend-ride+') == 'ride_it')

    new_pm_src = POSITION_MANAGER.read_text()
    old_pm_src = subprocess.run(
        ['git', 'show', f'{BASE}:scripts/position_manager.py'],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    same = []
    for s in SIGNALS:
        a = eval_is_ride_it(new_pm_src, s)
        b = eval_is_ride_it(old_pm_src, s)
        same.append((s, a, b, a == b))
    check('_is_ride_it OFF-path identical to pre-wiring for all probes',
          all(x[3] for x in same), '; '.join(f'{s}:new={a},old={b}' for s, a, b, _ in same))
    atr = [x for x in same if x[0].startswith('atr-') or x[0].startswith('atr_')]
    check('_is_ride_it False for atr-trend strings (same as today)',
          all(x[1] is False and x[2] is False for x in atr))
    check("fidelity control: 'trend-ride+' still True / 'btc-wave' False",
          dict((x[0], x[1]) for x in same)['trend-ride+'] is True
          and dict((x[0], x[1]) for x in same)['btc-wave'] is False)

    print('── OFF path: readers see identical values ──')
    import profit_monster, cut_loser
    check('profit_monster sees hermes_constants bypass tuple',
          profit_monster.PROFIT_MONSTER_BYPASS_SIGNALS == bypass
          and len(bypass) == 41, f'len={len(bypass)}')
    check('cut_loser sees hermes_constants bypass tuple',
          cut_loser.PROFIT_MONSTER_BYPASS_SIGNALS == bypass)

    # ── ON path in a subprocess over a patched COPY ──
    print('── ON path: subprocess with patched copy (flag True) ──')
    tmpdir = tempfile.mkdtemp(prefix='hc_on_')
    patched = (CONSTANTS.read_text()
               .replace('ATR_TREND_EXIT_TRIAL_ENABLED = False',
                        'ATR_TREND_EXIT_TRIAL_ENABLED = True'))
    check('patch applied to COPY (count=1)',
          patched != CONSTANTS.read_text()
          and patched.count('ATR_TREND_EXIT_TRIAL_ENABLED = True') == 1)
    (pathlib.Path(tmpdir) / 'hermes_constants.py').write_text(patched)
    env = dict(os.environ, SELFCHECK_MODE='on', SELFCHECK_TMPDIR=tmpdir,
               HERMES_DATA_DIR='/root/.hermes/data')
    r = subprocess.run([sys.executable, __file__], env=env,
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.stderr.strip():
        sys.stdout.write('  [subprocess stderr]\n' + r.stderr)
    check('ON-path subprocess exited 0', r.returncode == 0, f'rc={r.returncode}')
    shutil.rmtree(tmpdir, ignore_errors=True)

    print('── On-disk file safety ──')
    disk = CONSTANTS.read_text()
    check('on-disk hermes_constants still has flag = False',
          'ATR_TREND_EXIT_TRIAL_ENABLED = False' in disk
          and 'ATR_TREND_EXIT_TRIAL_ENABLED = True' not in disk)

    print()
    if FAILURES:
        print(f'RESULT: {len(FAILURES)} FAIL — {FAILURES}')
        return 1
    print('RESULT: ALL CHECKS PASS')
    return 0


def on_path(tmpdir):
    """Runs inside the subprocess: patched constants FIRST on sys.path."""
    sys.path.insert(0, tmpdir)
    sys.path.insert(1, str(SCRIPTS))
    import hermes_constants as hc
    check('subprocess flag is True (from patched COPY)',
          hc.ATR_TREND_EXIT_TRIAL_ENABLED is True, hc.__file__)
    check('subprocess imported the COPY, not the on-disk file',
          hc.__file__.startswith(tmpdir), hc.__file__)
    missing = [s for s in FIVE if s not in hc.PROFIT_MONSTER_BYPASS_SIGNALS]
    check('bypass contains all 5 variants', not missing, f'missing={missing}')
    mapped = {k: hc.SIGNAL_EXIT_CONFIG.get(k) for k in FIVE}
    check('config maps all 5 -> ride_it',
          all(v == 'ride_it' for v in mapped.values()), repr(mapped))
    check('no collateral: existing config keys unchanged',
          hc.SIGNAL_EXIT_CONFIG.get('trend-ride+') == 'ride_it'
          and hc.SIGNAL_EXIT_CONFIG.get('ai-trader+') == 'rr_engine'
          and 'confluence' not in hc.SIGNAL_EXIT_CONFIG
          and hc.SIGNAL_EXIT_CONFIG.get('atr-spike+') == 'atr')

    import position_manager as pm
    got = {s: pm._match_exit_config(s) for s in FIVE}
    check('matcher returns ride_it for all 5', all(v == 'ride_it' for v in got.values()),
          repr(got))
    check("matcher control: 'btc-wave' still default", pm._match_exit_config('btc-wave') is None)

    src = POSITION_MANAGER.read_text()
    res = {s: eval_is_ride_it(src, s) for s in
           ('atr-trend', 'atr-trend+', 'atr-trend-',
            'atr_trend_accel_long', 'atr_trend_accel_short',
            'btc-wave', 'linreg-fade')}
    atr = [v for k, v in res.items() if k.startswith('atr')]
    check('_is_ride_it True for all 5 atr-trend variants (flag True)',
          len(atr) == 5 and all(atr), repr(res))
    check('controls stay False: btc-wave, linreg-fade',
          res['btc-wave'] is False and res['linreg-fade'] is False)

    import profit_monster, cut_loser
    pm_byp = profit_monster.PROFIT_MONSTER_BYPASS_SIGNALS
    cl_byp = cut_loser.PROFIT_MONSTER_BYPASS_SIGNALS
    check('profit_monster (reader) sees all 5 under flag True',
          all(s in pm_byp for s in FIVE), f'len={len(pm_byp)}')
    check('cut_loser (reader) sees all 5 under flag True',
          all(s in cl_byp for s in FIVE), f'len={len(cl_byp)}')
    check('readers see same tuple as hermes_constants',
          pm_byp == cl_byp == hc.PROFIT_MONSTER_BYPASS_SIGNALS)
    if FAILURES:
        print(f'ON-PATH: {len(FAILURES)} FAIL — {FAILURES}')
        return 1
    print('ON-PATH: ALL CHECKS PASS')
    return 0


if __name__ == '__main__':
    if os.environ.get('SELFCHECK_MODE') == 'on':
        sys.exit(on_path(os.environ['SELFCHECK_TMPDIR']))
    sys.exit(off_path())
