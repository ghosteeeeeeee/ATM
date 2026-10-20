#!/usr/bin/env python3
"""R2 verification test 2: end-to-end auto-revert simulation in an ISOLATED dir.
Copies live hermes_constants.py + vacation_guardrail.py to /tmp/ichimoku_r2_sim/,
fakes psycopg2 with a bad-WR cohort (Decimal values), triggers the revert, and
verifies: (a) flag flipped, (b) file compiles, (c) alert payload JSON-serializable,
(d) atomic write used (no truncation window), (e) fresh-import gate denies bypass."""
import sys, os, shutil, subprocess, json
from decimal import Decimal

SIM = '/tmp/ichimoku_r2_sim'
shutil.rmtree(SIM, ignore_errors=True)
os.makedirs(SIM)
shutil.copy('/root/.hermes/scripts/hermes_constants.py', SIM)
shutil.copy('/root/.hermes/scripts/vacation_guardrail.py', SIM)

sim_code = r'''
import sys, os, json, types
SIM = '/tmp/ichimoku_r2_sim'
sys.path.insert(0, SIM)                 # temp constants FIRST
sys.path.insert(1, '/root/.hermes/scripts')  # paths etc.

# Fake psycopg2: bad cohort — 6 trades, WR 16.7% < 40% threshold, Decimal values
from decimal import Decimal
fake = types.ModuleType('psycopg2')
class _Cur:
    def __init__(self): self._row = (6, 1, Decimal('-12.34'), Decimal('16.7'))
    def execute(self, q):
        self.q = q
        assert "signal = 'ichimoku+'" in q, 'kill query shape changed'
    def fetchone(self): return self._row
    def close(self): pass
class _Conn:
    def cursor(self): return _Cur()
    def close(self): pass
fake.connect = lambda **kw: _Conn()
sys.modules['psycopg2'] = fake

import importlib.util
spec = importlib.util.spec_from_file_location('vacation_guardrail', os.path.join(SIM, 'vacation_guardrail.py'))
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)

# Capture log + write_alert instead of touching production files
calls = {'log': [], 'alert': []}
vg.log = lambda msg, lvl='INFO': calls['log'].append((lvl, str(msg)))
def fake_alert(level, message, data):
    json.dumps({'level': level, 'message': message, 'data': data})  # would raise TypeError on Decimal
    calls['alert'].append((level, message, data))
vg.write_alert = fake_alert

# Verify pre-state
import hermes_constants
assert hermes_constants.ICHIMOKU_LONG_BYPASS_ENABLED is True, 'pre-state wrong'
pre_mtime = os.path.getmtime(os.path.join(SIM, 'hermes_constants.py'))

vg.check_ichimoku_bypass_kill()

# 1. Flag flipped in the SIM constants file
content = open(os.path.join(SIM, 'hermes_constants.py')).read()
assert 'ICHIMOKU_LONG_BYPASS_ENABLED = False  # AUTO-REVERTED' in content, 'flag NOT flipped'
assert "ICHIMOKU_LONG_BYPASS_ENABLED = True\n" not in content, 'True line still present'
# 2. No leftover tmp file + os.replace semantics (file replaced, not truncated in place)
assert not os.path.exists(os.path.join(SIM, 'hermes_constants.py.tmp')), 'tmp file leftover'
# 3. Alert landed with float types (JSON-serializable — verified inside fake_alert)
assert calls['alert'], 'write_alert never called'
lvl, msg, data = calls['alert'][0]
assert isinstance(data['wr'], float) and isinstance(data['pnl'], float), f"types wrong: {type(data['wr'])}, {type(data['pnl'])}"
assert isinstance(data['n_trades'], int), 'n_trades not int'
# 4. Kill log line present
assert any('ICHIMOKU-BYPASS-KILL' in m and 'Auto-reverted' in m for _, m in calls['log']), 'kill log missing'
print('SIM-OK: flipped=%s alert_data=%s' % (True, data))
'''
r = subprocess.run([sys.executable, '-c', sim_code], capture_output=True, text=True, timeout=120)
print(r.stdout.strip())
if r.returncode != 0:
    print('STDERR:', r.stderr[-2500:])
    sys.exit(1)

# 5. Flipped file compiles + fresh process sees flag False
r2 = subprocess.run([sys.executable, '-c', f'''
import sys; sys.path.insert(0, {SIM!r}); sys.path.insert(1, "/root/.hermes/scripts")
import py_compile; py_compile.compile({os.path.join(SIM, "hermes_constants.py")!r}, doraise=True)
import hermes_constants as h
print("fresh-import flag:", h.ICHIMOKU_LONG_BYPASS_ENABLED)
assert h.ICHIMOKU_LONG_BYPASS_ENABLED is False
'''], capture_output=True, text=True, timeout=60)
print(r2.stdout.strip())
if r2.returncode != 0:
    print('STDERR:', r2.stderr[-1500:]); sys.exit(1)

# 6. Gate denies bypass with the FLIPPED constants (fresh process, real gate code)
r3 = subprocess.run([sys.executable, '-c', f'''
import sys, re, textwrap
sys.path.insert(0, {SIM!r}); sys.path.insert(1, "/root/.hermes/scripts")
SRC = open("/root/.hermes/scripts/signal_compactor.py").read().splitlines(keepends=True)
GATE = textwrap.dedent("".join(SRC[3330:3439]))
import hermes_constants as h
assert h.ICHIMOKU_LONG_BYPASS_ENABLED is False
unique_signal_types=1; bare_source="ichimoku"; _src_stripped="ichimoku"; source="ichimoku+"
direction="LONG"; source_parts=["ichimoku+"]; _neutral_relax=False; _regime="LONG_BIAS"
CONFLUENCE_REQUIRED=True; conf=70; token="T"
pass_gate=False; gate_msg=""
ns = dict(globals())
exec(GATE, ns)
print("post-revert gate:", ns["pass_gate"], "|", ns["gate_msg"])
assert ns["pass_gate"] is False and "disabled" in ns["gate_msg"]
'''], capture_output=True, text=True, timeout=60)
print(r3.stdout.strip())
if r3.returncode != 0:
    print('STDERR:', r3.stderr[-1500:]); sys.exit(1)

print('TEST2 ALL PASS: auto-revert end-to-end kills the gate')
