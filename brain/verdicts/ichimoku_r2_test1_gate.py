#!/usr/bin/env python3
"""R2 verification test 1: extract REAL gate + final-guard code from live
signal_compactor.py by exact line ranges and execute it under test scenarios."""
import sys, re, textwrap, json
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import (STANDALONE_BYPASS_SIGNALS, ACCEL_300_STANDALONE_BYPASS_ENABLED,
                              ACCEL_300_STANDALONE_BYPASS_CONFIDENCE, CONFLUENCE_REQUIRED,
                              CONFLUENCE_NEUTRAL_RELAX)

SRC = open('/root/.hermes/scripts/signal_compactor.py').read().splitlines(keepends=True)

def grab(a, b):  # 1-based inclusive
    code = ''.join(SRC[a-1:b])
    assert 'ichimoku' in code or 'STANDALONE_BYPASS' in code, f'range {a}-{b} looks wrong'
    return textwrap.dedent(code)

# ── Gate chain: lines 3331-3439 (if not CONFLUENCE_REQUIRED ... else: gate_msg) ──
GATE = grab(3331, 3439)
assert 'ichimoku LONG standalone bypass' in GATE
assert 'only {unique_signal_types} unique types' in GATE

def run_gate(flag_val, source, direction, regime_4h='LONG_BIAS'):
    unique_signal_types = len(set(re.sub(r'\d+$', '', p.rstrip('+-')) or p for p in source.split(',')))
    bare_source = re.sub(r'\d+$', '', source.rstrip('+-')) if source else ''
    _src_stripped = source.rstrip('+-') if source else ''
    source_parts = [p.strip() for p in source.split(',') if p.strip()]
    _neutral_relax = CONFLUENCE_NEUTRAL_RELAX and regime_4h == 'NEUTRAL'
    pass_gate = False
    gate_msg = ''
    ns = dict(CONFLUENCE_REQUIRED=CONFLUENCE_REQUIRED, unique_signal_types=unique_signal_types,
              bare_source=bare_source, _src_stripped=_src_stripped, source=source,
              direction=direction, token='TEST',
              source_parts=source_parts, _neutral_relax=_neutral_relax, _regime='LONG_BIAS',
              STANDALONE_BYPASS_SIGNALS=STANDALONE_BYPASS_SIGNALS,
              ACCEL_300_STANDALONE_BYPASS_ENABLED=ACCEL_300_STANDALONE_BYPASS_ENABLED,
              ACCEL_300_STANDALONE_BYPASS_CONFIDENCE=ACCEL_300_STANDALONE_BYPASS_CONFIDENCE,
              conf=70, re=re, _temporal_confluence_count=lambda *a: 0,
              pass_gate=pass_gate, gate_msg=gate_msg, log=lambda *a, **k: None)
    # stub the flag: hermes_constants import inside the gate reads the REAL module.
    # To flip it we monkeypatch sys.modules['hermes_constants'] attribute.
    import hermes_constants
    old = hermes_constants.ICHIMOKU_LONG_BYPASS_ENABLED
    hermes_constants.ICHIMOKU_LONG_BYPASS_ENABLED = flag_val
    try:
        exec(GATE, ns)
    finally:
        hermes_constants.ICHIMOKU_LONG_BYPASS_ENABLED = old
    return ns['pass_gate'], ns['gate_msg']

results = []
def T(name, got, want_gate, want_substr=''):
    ok = (got[0] == want_gate) and (want_substr in got[1])
    results.append((name, ok, got))
    print(f"{'PASS' if ok else 'FAIL'} | {name}: pass_gate={got[0]} msg='{got[1]}'")

T('flag=TRUE  LONG single ichimoku+', run_gate(True, 'ichimoku+', 'LONG'), True, 'ichimoku LONG bypass')
T('flag=FALSE LONG single ichimoku+', run_gate(False, 'ichimoku+', 'LONG'), False, 'ichimoku bypass disabled')
T('flag=TRUE  SHORT single ichimoku-', run_gate(True, 'ichimoku-', 'SHORT'), False)
T('flag=FALSE SHORT single ichimoku-', run_gate(False, 'ichimoku-', 'SHORT'), False)
T('flag=TRUE  LONG confluence ichimoku+,rs_s (2 types)', run_gate(True, 'ichimoku+,rs_s', 'LONG'), True, '2 unique types')
T('flag=TRUE  LONG ichimoku+ in 4h NEUTRAL (gate branch)', run_gate(True, 'ichimoku+', 'LONG', 'NEUTRAL'), True, 'ichimoku LONG bypass')
T('flag=TRUE  LONG non-ichimoku single (rs+)', run_gate(True, 'rs+', 'LONG'), False)

# ── HOTSET-FINAL guard: lines 4906-4939 ──
FINAL = grab(4906, 4939)
assert 'HOTSET-FINAL' in FINAL

def run_final_guard(src):
    tkn = 'TEST'; direction = 'LONG'
    entry = {}
    blocked = []
    def _log(*a, **k):
        blocked.append(a[0] if a else '')
    def _get_regime_4h(t):
        return 'NORMAL', 0.0
    src_parts = [p.strip() for p in (src or '').split(',') if p.strip()]
    ns = dict(CONFLUENCE_REQUIRED=CONFLUENCE_REQUIRED, src=tkn and src, tkn=tkn,
              src_parts=src_parts, direction=direction, entry=entry, re=re,
              STANDALONE_BYPASS_SIGNALS=STANDALONE_BYPASS_SIGNALS,
              ACCEL_300_STANDALONE_BYPASS_ENABLED=ACCEL_300_STANDALONE_BYPASS_ENABLED,
              CONFLUENCE_NEUTRAL_RELAX=CONFLUENCE_NEUTRAL_RELAX,
              get_regime_4h=_get_regime_4h, log=_log)
    passed = []
    code = 'for _one in [1]:\n' + textwrap.indent(FINAL, '    ') + '\n    passed.append(True)\n'
    ns['passed'] = passed
    exec(code, ns)
    return bool(ns['passed']), blocked

for src_case in ['ichimoku+', 'pump-chain+', 'ai-trader+']:
    passed, logs = run_final_guard(src_case)
    tag = 'ALLOWED at final guard' if passed else 'BLOCKED at final guard'
    results.append((f'final-guard {src_case}', (passed == (src_case in ('pump-chain+','ai-trader+'))), (passed, logs)))
    print(f"{'PASS' if results[-1][1] else 'FAIL'} | final guard src='{src_case}': {tag} | log: {logs[-1][:110] if logs else '-'}")

print()
print('ALL PASS' if all(r[1] for r in results) else 'SOME TESTS FAILED')
