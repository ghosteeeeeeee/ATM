# accel_300 Audit + Stale-Bar Fix — 2026-06-23

## Trigger
User reported: "There are regularly LONG trades where the price is below the EMA300, and the reverse SHORTS when the price is above the EMA300. Both those conditions should not be allowed according to the logic the signal was designed for."

## Root Cause (P0)
File: `/root/.hermes/scripts/signals/accel_300.py` line 267
Bug: `for i in range(PERIOD + LOOKBACK, len(closes) - 1):` followed by `break` on first qualifying bar. Forward scan + break-on-first = returns OLDEST qualifying bar, not most recent.

Result: 31% of 3,537 signals emitted on 2026-06-23 had wrong direction vs current price-vs-EMA. (1,112 signals.) Signal bar was up to 5 hours stale at signal-write time.

## Fix Applied (1 line + comment)
```python
# FIX 2026-06-23: Scan BACKWARD from the latest bar so the FIRST match is
# the MOST RECENT qualifying bar. Previously scanned forward with break-on-
# first-match, which returned the OLDEST qualifying bar (could be hours old).
for i in range(len(closes) - 2, PERIOD + LOOKBACK - 1, -1):
```

Same index set as forward scan, reversed iteration order. All downstream gates (chop filter, regime slope, stale gap decay, marginal accel, gap expansion) operate on bar `i` relative values — independent of scan direction.

## Verification
- Test on TNSR LONG @ 22:30: now fires with `bars_since_cross=24`, latest_bar direction-consistent=True (vs old: bars_since_cross=24 but signal bar was hours old, latest bar direction-inconsistent)
- Syntax OK, module imports cleanly
- Verified against production DB rows for the day

## Additional Bugs Found (ai-engineer subagent + main-session verification — no false positives)

| # | Bug | Lines | Severity | Status |
|---|-----|-------|----------|--------|
| 2 | Condition 1 SHORT dead-else-branch | 330-332 | HIGH | Was_above_recently == was_ever_above_in_window (identical conditions), else:continue unreachable for SHORT |
| 4 | SHORT_BLACKLIST double-check | 675-676 | MEDIUM | First check blocks ALL signals (contradicts comment at 702-705 claiming direction-aware) |
| 5 | Confidence gap_bonus for SHORT | 716 | MEDIUM | `max(0, gap_growth - 0.05)` always 0 for SHORT (gap_growth negative) |
| 6 | MIN_GAP_EXPANSION naming | constant + 518,520 | LOW | Constant name suggests "must expand" but code allows up to 0.01 contraction |
| 7 | Dead `if cross_bar is not None: pass` | 314-315 | LOW | cross_bar init'd None at line 292, not set until line 397 |
| 8 | Comment drift | 261-264, 615, 512-514 | LOW | Stale "scanning forward" comments + duplicated comment header |

Items 2, 4, 5 awaiting T's input on which to apply. Items 6, 7, 8 are cleanups.

## Delegation Discipline Confirmed

This session used an ai-engineer delegation with a focused 8-item checklist. The subagent completed in 89.97s, 16 API calls, no timeouts. All 8 findings matched main-session verification exactly. Key working principles:

- **Focused checklist beats general audit** — 8 specific items, not "audit for all bugs"
- **Pre-load false-positive patterns** — sign-blind inequality, scope-misread, OOB protections all noted upfront
- **Verify subagent findings in main session before accepting** — both subagent and main-session traces matched, no false positives
- **Give subagent line-number precision** — exact line ranges per checklist item, not "around there"

This pattern works for any single-file audit ≤800 lines. File references are provided in the delegation context (existing skill references) so the subagent has prior session context.
