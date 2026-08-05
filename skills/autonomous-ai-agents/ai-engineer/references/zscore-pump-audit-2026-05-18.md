# zscore_pump.py Audit — 2026-05-18

**File:** `/root/.hermes/scripts/signals/zscore_pump.py` (450 lines)
**Syntax:** Clean | **All 4 prior bugs:** Fixed

## Verdict: No bugs found

All bugs documented in `vvv-divergence-fix-2026-05-18.md` were already fixed prior to this audit.

## Bug Status Table

| Bug | Pattern | Status | Location |
|-----|---------|--------|----------|
| Gate needed 205 bars, only 150 fetched | Pattern 14 | Fixed | Line 267: `ZSCORE_PUMP_DIVERGENCE_LOOKBACK + BARS + 2 = 25` |
| `.index(peak_z)` finds first not last | Pattern 15 | Fixed | Line 133: `max(idx for idx, z in enumerate(recent_zs) if z == peak_z)` |
| `range(spot_lookback, len(closes))` misses last bar | Pattern 16 | Fixed | Line 119: `range(spot_lookback, len(closes) + 1)` |
| Tuner confidence overwritten by z-bonus | Pattern 17 | Fixed | Line 387: `max(confidence, confidence + conf_bonus)` |

## Verified Correct (No Bugs)

| Component | Check | Result |
|-----------|-------|--------|
| `compute_zscore` | mean/stdev, std==0 guard | ✓ |
| `_check_divergence` | peak → sustained crash detection | ✓ |
| `detect_zscore_pump` | abs(z) vs threshold, divergence gate | ✓ |
| `scan_zscore_pump_signals` | master kill-switch, direction kill-switches | ✓ |
| Blacklists | SHORT_BLACKLIST (all dirs), LONG_BLACKLIST (LONG only) | ✓ |
| Cooldown | `hours=ZSCORE_PUMP_COOLDOWN_BARS / 60.0` = 5/60 ≈ 0.083h | ✓ |
| Price staleness | 120s threshold in `_get_1m_prices` | ✓ |
| Price age check | `price_age_minutes(token) > 10` | ✓ |
| Confidence bonus | `min(15, (z_abs - threshold) * 5)` — bonus threshold = signal threshold | ✓ |
| Tuner gate | `signal_count < 15` → falls back to constants | ✓ |
| `add_signal` fields | All required fields present | ✓ |

## Minor Observations

**Stale comment (line 410):** Comment says "~10 minutes" for 5 bars on 1m data.
Actual cooldown: `5 / 60.0 = 0.083h ≈ 5 minutes`. No functional impact.

**z_score_tier=None hardcoded (line 406):** Signal always passes `z_score_tier=None`
even when z > 3.0 could infer `extreme`. Design choice, not a bug — downstream
code does not appear to consume this field currently.

## Subagent Timeout Lesson

Single-file audit (450 lines) completed in main session in minutes. Same audit
delegated to subagent with 15-min timeout → timed out at 600s. Subagent overhead
(process spawn, context serialization) dominated for this small fast task.

**Rule:** Single file ≤500 lines → always audit in main session.