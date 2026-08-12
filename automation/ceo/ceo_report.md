## CEO Report — 2026-08-13 Hebbian Gate Decision

### Diagnosis
Hebbian gate doing nothing useful:
- **75 AUTO-APPROVEs**: ALL n=1-2 (rubber stamps, zero statistical power)
- **22 AUTO-REJECTs**: ALL already-blacklisted tokens (CELO, MEGA) + ETH
- **Zero actual outcomes tracked** — gate never learns
- **Root bug**: Composite scoring (Path B) bypassed `HEBBIAN_AUTO_MIN_N=5` entirely. Path A (n-based) correctly required n>=5 but never fired because Path B returned first.

### Fix Applied
**Deleted composite scoring path** from `decider_run.py:1308-1322`. Now only Path A (n-based) handles auto-decisions, enforcing `HEBBIAN_AUTO_MIN_N=5`. Soft advisories (boost/penalty WARN returns) still fire for confidence adjustments — those are fine at low n.

Trade impact: trades with n<5 history now flow to LLM context gate instead of getting rubber-stamped. This is the correct behavior — unknown token+signal combos should be evaluated by the LLM, not auto-approved by a graph weight from 1-2 historical trades.

### Verification
- Syntax check: OK
- No dangling references to `composite_score` in decider_run.py
- `HEBBIAN_AUTO_MIN_N=5` now actually enforced (was dead code before)
