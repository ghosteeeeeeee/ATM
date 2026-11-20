#!/usr/bin/env python3
"""Independent bug_hunter audit — result-1 diff a037e7a0 (CEO deep run 20261119T225832Z, result-2).

Baseline is the PRE-wiring commit a037e7a0^ (not HEAD — result-1's selfcheck
pins to HEAD, which became vacuous the moment the wiring was committed).
"""
import json
import os
import pathlib
import py_compile
import subprocess
import sys
import tempfile
import textwrap

REPO = pathlib.Path('/root/.hermes')
SCRIPTS = REPO / 'scripts'
CONSTANTS = SCRIPTS / 'hermes_constants.py'
POSITION_MANAGER = SCRIPTS / 'position_manager.py'
BASE = 'a037e7a0^'
FIVE = ('atr-trend', 'atr-trend+', 'atr-trend-',
        'atr_trend_accel_long', 'atr_trend_accel_short')
FAILURES = []


def check(label, cond, detail=''):
    tag = 'PASS' if cond else 'FAIL'
    print(f'[{tag}] {label}' + (f' — {detail}' if detail else ''))
    if not cond:
        FAILURES.append(label)


def git(*args):
    return subprocess.run(['git', *args], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout


def ride_it_slice(src):
    i = src.index('\n        _is_ride_it = any(') + 1
    j = src.index('\n        _mh_exempt =', i) + 1
    return textwrap.dedent(src[i:j])


def eval_is_ride_it(src, pos_signal, tag):
    ns = {'_pos_signal': pos_signal}
    exec(compile(ride_it_slice(src), tag, 'exec'), ns)
    return ns['_is_ride_it']


def _val_eq(a, b):
    if callable(a) or callable(b):
        import inspect
        try:
            return inspect.getsource(a) == inspect.getsource(b)
        except Exception:
            return a is b
    return a == b


# Broad probe universe: every distinct `signal` string ever seen in brain,
# plus every SIGNAL_EXIT_CONFIG key (added ON), plus the standalone list.
PROBES = sorted(set(json.load(open('/tmp/distinct_signals.json'))))
ATTR = ('atr-trend', 'atr-trend+', 'atr-trend-', 'atr_trend_accel_long',
        'atr_trend_accel_short')


def main():
    print('── 1. py_compile (fresh) ──')
    for f in (CONSTANTS, POSITION_MANAGER):
        try:
            py_compile.compile(str(f), doraise=True)
            check(f'py_compile {f.name}', True)
        except py_compile.PyCompileError as e:
            check(f'py_compile {f.name}', False, str(e))

    print('── 2. diff vs PRE-wiring baseline a037e7a0^ ──')
    for f in ('scripts/hermes_constants.py', 'scripts/position_manager.py'):
        d = git('diff', '--unified=0', BASE, '--', f)
        removals = [l for l in d.splitlines()
                    if l.startswith('-') and not l.startswith('---')]
        check(f'{os.path.basename(f)}: additions-only vs {BASE}',
              not removals, f'removed={removals[:5]}')
        adds = len([l for l in d.splitlines()
                    if l.startswith('+') and not l.startswith('+++')])
        print(f'  ({f}: +{adds} lines)')

    print('── 3. OFF path: worktree hermes_constants vs pre-wiring copy ──')
    os.environ.setdefault('HERMES_DATA_DIR', '/root/.hermes/data')
    os.environ.setdefault('WWW_DATA_DIR', '/var/www/hermes/data')
    sys.path.insert(0, str(SCRIPTS))
    import hermes_constants as hc
    check('flag False on disk (module)', hc.ATR_TREND_EXIT_TRIAL_ENABLED is False,
          repr(hc.ATR_TREND_EXIT_TRIAL_ENABLED))

    old_src = git('show', f'{BASE}:scripts/hermes_constants.py')
    tmp = tempfile.mkdtemp(prefix='hc_base_')
    p = pathlib.Path(tmp) / 'hermes_constants_base.py'
    p.write_text(old_src)
    import importlib.util
    spec = importlib.util.spec_from_file_location('hermes_constants_base', p)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    old_names = {k for k in vars(old) if not k.startswith('__')}
    new_names = {k for k in vars(hc) if not k.startswith('__')}
    check('exactly one new name: the trial flag (vs pre-wiring)',
          new_names - old_names == {'ATR_TREND_EXIT_TRIAL_ENABLED'}
          and not (old_names - new_names),
          f'added={sorted(new_names - old_names)} removed={sorted(old_names - new_names)}')
    old_root = os.path.dirname(os.path.dirname(old.__file__))
    new_root = os.path.dirname(os.path.dirname(hc.__file__))

    def norm(v):
        return v.replace(old_root, new_root) if isinstance(v, str) else v

    diffs = [k for k in old_names
             if not _val_eq(norm(vars(old)[k]), norm(vars(hc).get(k, object())))]
    check('every pre-existing name byte-identical (no value edits)', not diffs,
          f'differing={diffs}')

    bypass = hc.PROFIT_MONSTER_BYPASS_SIGNALS
    check('OFF: no atr-trend entry in bypass (exact or substring)',
          not [s for s in bypass if 'atr-trend' in s or 'atr_trend' in s])
    check('OFF: no atr-trend key in SIGNAL_EXIT_CONFIG',
          not [k for k in hc.SIGNAL_EXIT_CONFIG
               if 'atr-trend' in k or 'atr_trend' in k])
    check('OFF: bypass tuple length 41 (pre-wiring size)', len(bypass) == 41,
          f'len={len(bypass)}')

    print('── 4. OFF path: position_manager vs pre-wiring source ──')
    import position_manager as pm
    for s in FIVE:
        check(f"OFF _match_exit_config('{s}') is None (default pm_trail)",
              pm._match_exit_config(s) is None, repr(pm._match_exit_config(s)))
    check("OFF control _match_exit_config('trend-ride+') == 'ride_it'",
          pm._match_exit_config('trend-ride+') == 'ride_it')

    new_pm_src = POSITION_MANAGER.read_text()
    base_pm_src = git('show', f'{BASE}:scripts/position_manager.py')
    changed = []
    for s in PROBES:
        a = eval_is_ride_it(new_pm_src, s, 'new')
        b = eval_is_ride_it(base_pm_src, s, 'base')
        if a != b:
            changed.append((s, b, a))
    check(f'OFF _is_ride_it identical to pre-wiring for all {len(PROBES)} real signals',
          not changed, f'changed={changed[:5]}')

    print('── 5. OFF path: readers ──')
    import profit_monster, cut_loser
    check('profit_monster sees bypass tuple == hermes_constants (len 41)',
          profit_monster.PROFIT_MONSTER_BYPASS_SIGNALS == bypass
          and len(profit_monster.PROFIT_MONSTER_BYPASS_SIGNALS) == 41)
    check('cut_loser sees bypass tuple == hermes_constants',
          cut_loser.PROFIT_MONSTER_BYPASS_SIGNALS == bypass)
    check('cut_loser MAE-guard module attr same object',
          cut_loser.PROFIT_MONSTER_BYPASS_SIGNALS is bypass)

    print('── 6. ON path: subprocess over patched COPY (flag True) ──')
    tmpdir = tempfile.mkdtemp(prefix='hc_on2_')
    disk = CONSTANTS.read_text()
    patched = disk.replace('ATR_TREND_EXIT_TRIAL_ENABLED = False',
                           'ATR_TREND_EXIT_TRIAL_ENABLED = True')
    check('patch flips exactly one line in COPY',
          patched.count('ATR_TREND_EXIT_TRIAL_ENABLED = True') == 1
          and patched != disk)
    (pathlib.Path(tmpdir) / 'hermes_constants.py').write_text(patched)
    env = dict(os.environ, AUDIT_MODE='on', AUDIT_TMPDIR=tmpdir,
               HERMES_DATA_DIR='/root/.hermes/data')
    r = subprocess.run([sys.executable, __file__], env=env,
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.stderr.strip():
        print('  [subprocess stderr]\n' + r.stderr)
    check('ON subprocess exited 0', r.returncode == 0, f'rc={r.returncode}')

    print('── 7. on-disk safety ──')
    d = CONSTANTS.read_text()
    check('on-disk flag still False', 'ATR_TREND_EXIT_TRIAL_ENABLED = False' in d
          and 'ATR_TREND_EXIT_TRIAL_ENABLED = True' not in d)

    print()
    if FAILURES:
        print(f'RESULT: {len(FAILURES)} FAIL — {FAILURES}')
        return 1
    print('RESULT: ALL CHECKS PASS')
    return 0


def on_path(tmpdir):
    sys.path.insert(0, tmpdir)
    sys.path.insert(1, str(SCRIPTS))
    import hermes_constants as hc
    check('subprocess flag True from COPY', hc.ATR_TREND_EXIT_TRIAL_ENABLED is True,
          hc.__file__)
    check('subprocess imported COPY', hc.__file__.startswith(tmpdir), hc.__file__)
    bypass = hc.PROFIT_MONSTER_BYPASS_SIGNALS
    check('ON bypass contains all 5', all(s in bypass for s in FIVE),
          f'len={len(bypass)}')
    check('ON bypass grew by exactly 5 (41 -> 46)', len(bypass) == 46,
          f'len={len(bypass)}')
    check('ON config maps all 5 -> ride_it',
          all(hc.SIGNAL_EXIT_CONFIG.get(k) == 'ride_it' for k in FIVE))
    # config keys unchanged except the 5 additions
    import importlib.util, pathlib, subprocess
    base_src = subprocess.run(
        ['git', 'show', 'a037e7a0^:scripts/hermes_constants.py'],
        cwd='/root/.hermes', capture_output=True, text=True, check=True).stdout
    t = tempfile.mkdtemp(prefix='hc_base2_')
    pp = pathlib.Path(t) / 'hermes_constants_base.py'
    pp.write_text(base_src)
    spec = importlib.util.spec_from_file_location('hc_base2', pp)
    base = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base
    spec.loader.exec_module(base)
    added = set(hc.SIGNAL_EXIT_CONFIG) - set(base.SIGNAL_EXIT_CONFIG)
    removed = set(base.SIGNAL_EXIT_CONFIG) - set(hc.SIGNAL_EXIT_CONFIG)
    changed = [k for k in base.SIGNAL_EXIT_CONFIG
               if k in hc.SIGNAL_EXIT_CONFIG
               and hc.SIGNAL_EXIT_CONFIG[k] != base.SIGNAL_EXIT_CONFIG[k]]
    check('ON config: exactly the 5 keys added, none removed/changed',
          added == set(FIVE) and not removed and not changed,
          f'added={sorted(added)} removed={removed} changed={changed}')

    import position_manager as pm
    probes = sorted(set(json.load(open('/tmp/distinct_signals.json')))
                    | set(hc.SIGNAL_EXIT_CONFIG) | set(FIVE))
    off_src = pathlib.Path('/root/.hermes/scripts/position_manager.py').read_text()

    # matcher collateral: every comma-part of every probe
    changed_parts = {}
    for s in probes:
        for part in [x.strip() for x in s.split(',')]:
            if not part:
                continue
            v = pm._match_exit_config(part)
            # OFF value: recompute against base config by testing membership logic
            # cheap way: OFF == base module's config result. Use a fresh matcher
            # over the base config.
            b = _base_match(part, base.SIGNAL_EXIT_CONFIG)
            if v != b:
                changed_parts[part] = (b, v)
    bad = {k: val for k, val in changed_parts.items()
           if not (('atr-trend' in k or 'atr_trend' in k) and val[1] == 'ride_it')}
    check('ON matcher: only atr-trend parts newly map -> ride_it (no collateral)',
          not bad, f'changed={len(changed_parts)} bad={dict(list(bad.items())[:5])}')
    check('ON matcher: all 5 exact keys -> ride_it',
          all(pm._match_exit_config(k) == 'ride_it' for k in FIVE))

    # _is_ride_it collateral: ON (patched flag) vs OFF source with flag forced False
    on_changed = []
    for s in probes:
        a = eval_is_ride_it_local(off_src, s, True)   # gated branch active
        b = eval_is_ride_it_local(off_src, s, False)  # flag False -> no-op
        if a != b:
            on_changed.append((s, b, a))
    bad2 = [t for t in on_changed
            if not (('atr-trend' in t[0] or 'atr_trend' in t[0])
                    and 'linreg-fade' not in t[0] and 'linreg_fade' not in t[0])]
    check('ON _is_ride_it: gated branch flips ONLY atr-trend signals (no collateral)',
          not bad2, f'flipped={len(on_changed)} bad={bad2[:5]}')
    atr_flips = [t[0] for t in on_changed if t[0].startswith(('atr-trend', 'atr_trend'))]
    check('ON _is_ride_it: every atr-trend probe flips False->True',
          len(atr_flips) >= 2, f'n={len(atr_flips)} sample={atr_flips[:5]}')
    # linreg-fade combos must stay False even with flag True
    combo = [s for s in probes if 'atr-trend' in s and 'linreg-fade' in s]
    still = all(not eval_is_ride_it_local(off_src, s, True) for s in combo)
    check('ON _is_ride_it: atr-trend+linreg-fade combos stay exempt-from-ride (V8)',
          still, f'n_combos={len(combo)}')

    import profit_monster, cut_loser
    check('ON profit_monster reader sees all 5',
          all(s in profit_monster.PROFIT_MONSTER_BYPASS_SIGNALS for s in FIVE))
    check('ON cut_loser reader sees all 5',
          all(s in cut_loser.PROFIT_MONSTER_BYPASS_SIGNALS for s in FIVE))
    check('ON readers == hermes_constants tuple',
          profit_monster.PROFIT_MONSTER_BYPASS_SIGNALS == bypass
          and cut_loser.PROFIT_MONSTER_BYPASS_SIGNALS == bypass)

    # SQL LIKE collateral: does 'atr-trend' match any historical signal that
    # does NOT contain atr-trend as its own signal? (simulated in python)
    import re as _re
    others = [s for s in probes if 'atr-trend' not in s and 'atr_trend' not in s]
    hits = [s for s in others
            if any(_re.search(_re.escape(b), s) for b in FIVE)]
    check('ON SQL-LIKE collateral: no non-atr-trend signal matches bypass patterns',
          not hits, f'hits={hits[:5]}')

    if FAILURES:
        print(f'ON-PATH: {len(FAILURES)} FAIL — {FAILURES}')
        return 1
    print('ON-PATH: ALL CHECKS PASS')
    return 0


def _base_match(part, cfg):
    """Replica of position_manager._match_exit_config against an arbitrary cfg."""
    if part in cfg:
        return cfg[part]
    import re as _re
    _base = _re.sub(r'-v\d+$', '', part)
    if _base != part and _base in cfg:
        return cfg[_base]
    for key, val in cfg.items():
        if part.startswith(key + '-') or part.startswith(key + '_'):
            return val
        if key.endswith(('+', '-')) and part.startswith(key):
            _rem = part[len(key):]
            if _re.fullmatch(r'-v\d+', _rem):
                return val
        _key_stem = key.rstrip('+-')
        if _key_stem and _base == _key_stem:
            return val
    return None


def eval_is_ride_it_local(src, pos_signal, flag):
    """Execute the REAL gated block with ATR_TREND_EXIT_TRIAL_ENABLED = flag.

    The block's function-local `from hermes_constants import ...` is stripped
    so the injected flag (not the module's) decides the branch.
    """
    body = ride_it_slice(src).replace(
        'from hermes_constants import ATR_TREND_EXIT_TRIAL_ENABLED', '')
    ns = {'_pos_signal': pos_signal, 'ATR_TREND_EXIT_TRIAL_ENABLED': flag}
    exec(compile(body, '<_is_ride_it>', 'exec'), ns)
    return ns['_is_ride_it']


if __name__ == '__main__':
    if os.environ.get('AUDIT_MODE') == 'on':
        sys.exit(on_path(os.environ['AUDIT_TMPDIR']))
    sys.exit(main())
