# Verification discipline for signal debugging (2026-06-03)

## Key Lesson
Subagent bug claims must be verified with grep+read BEFORE passing to T. Subagents timeout at 600s and produce false positives: compare archive vs live, severity inflation, misreport function names.

T's explicit rule: "Verify all subagent bug claims with grep+py_compile."

## The pattern that caught the bug
The findings doc claimed `float(row['f'] or 0)` existed at line 1485 in signal_compactor.py — it **does not exist**. This was a false claim from a subagent.

Real verification steps:
1. `grep -n "pattern" file.py` — find actual line numbers
2. `read_file(limit=X, offset=Y)` — read actual file section
3. Compare what the report says vs reality
4. Only then report to T

## What to check when signals have price=0
1. Check signals.json pending entries — look at direction distribution and price fields
2. Check which rs.py is being called: `signals/rs.py` (signals package) vs `rs_signals.py` (top-level)
3. For the suspected file, grep: `grep -n "add_signal\|price" /root/.hermes/scripts/signals/rs.py | head -30`
4. Compare add_signal call in signals/rs.py vs rs_signals.py — find the missing price= parameter
5. Verify against signal_schema.add_signal() signature to see which params are expected

## Related
- rs-price-missing-bug.md — the actual bug this discipline caught
- T's workflow: investigate+report → plan doc → WAIT for approval → implement
- Never approve on first pass