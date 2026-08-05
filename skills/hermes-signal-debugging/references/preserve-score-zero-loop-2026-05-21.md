# Preserve Score-Zero Loop — 2026-05-21

## Symptom

Tokens appear in `hotset.json` with `final_score=0.0`, `compact_rounds=0`, high base confidence, but no live trades open. Example (2026-05-21 02:13-02:14):
```
DASH: conf=79.52 final_conf=MISSING score=0.0 regime=SHORT_BIAS ...
BLUR: conf=88.0 final_conf=MISSING score=0.0 ...
AAVE: conf=88.0 final_conf=MISSING score=0.0 ...
```

These entries are **preserved from the previous hot-set** but have **no fresh DB signal** this cycle. They are not APPROVED — they bypassed the approval path because they came through `_filter_safe_prev_hotset()` (preservation), not the main DB scoring path.

## Root Cause Chain

1. **Confluence gate blocks single-source signals** — `zscore-pump-` alone doesn't pass the 2-source requirement. Log: `🔒 [PENDING-APPROVE-BLOCK] DASH:SHORT single-source blocked from APPROVE`
2. **DB signals expire** — the last multi-source signals for DASH/BLUR/AAVE expired (>5 min old) and were marked EXPIRED
3. **No fresh signal replaces them** — the confluence gate keeps blocking single-source replacements
4. **Preservation path active** — `_filter_safe_prev_hotset()` preserves the old entry because it passes all safety checks (2+ sources, not in cooldown, no open position, staleness OK)
5. **Score computed as 0.0** — `_score_signal()` with `compact_rounds=0` and `age_m` from DB created_at gives `final_score=0.0` (or very low)
6. **decider_run skips** — `final_score=0.0` entries may still be in hotset.json but are not APPROVED in the DB because the preservation path bypasses the APPROVAL step

## Key Diagnostic Markers in hotset.json

| Field | Normal | Preserve-score-zero |
|-------|--------|---------------------|
| `compact_rounds` | 1+ (survived cycles) | 0 |
| `final_score` | > 0 | 0.0 |
| `survival_round` | 1+ | 1 (preserved, not incremented) |
| `entry_origin_ts` | first entry time | old (carried forward) |

## Key Log Signatures

```
🔄 [PRESERVE-ADD] DASH:SHORT ... score=0.00 (preserved, no DB entry)
✅ [PRESERVE-PASS] DASH:SHORT ... passed all filters -> preserved
💾 [HOTSET-WRITE] DASH:SHORT ... score=0.00
🔒 [PENDING-APPROVE-BLOCK] DASH:SHORT single-source blocked from APPROVE — need 2+ for confluence
```

## Why decider_run Won't Execute These

`decider_run` reads from the `approved` signals in the DB. Preservation adds entries to `hotset.json` but does NOT write any `decision=APPROVED` row to the DB. The token is in `hotset.json` but has no DB row with `decision=APPROVED` — so decider_run skips it.

## Fix Options

1. **Reduce preservation window** — entries with `compact_rounds=0` (never survived a cycle) should NOT be preserved across cycles. Only entries with `rounds >= 2` should survive a full cycle without a fresh signal.

2. **Require minimum score to preserve** — if `final_score < 1.0`, don't preserve regardless of sources.

3. **Force re-approval on preserve** — when preserving an entry, trigger a new PENDING→APPROVED pass so it enters the DB properly.

## Differential vs. Other Hot-Set Starvation Causes

| Cause | Hot-set has entries? | Entries have score>0? | Solution |
|-------|---------------------|----------------------|----------|
| WR filter blind | No (0 entries) | N/A | Fix WR data source |
| Confluence gate too tight | Yes but wrong ones | 0.0 | Tune source requirements |
| Preserve-score-zero loop | Yes | 0.0 | Cap preservation to rounds>=2 |
| Regime filter too tight | Yes | >0 but blocked at decider | Check regime data age |
| Timer dead | Yes but stale | >0 | Restart compactor timer |