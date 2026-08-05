# Same-Cycle Close — DOT + ICP (2026-05-21)

**Symptom:** Two trades closed within 3 seconds of opening. Both marked `atr_sl_hit` in PostgreSQL.

```
5/20/2026 23:22:17 ICP Close Short 2.5380  4.0 ICP  10.15 USDC  -0.01 USDC
5/20/2026 23:22:06 ICP Open Short  2.5368  4.0 ICP  10.15 USDC  -0.00 USDC

5/20/2026 22:06:11 DOT Close Short 1.2459  4.0 DOT   10.15 USDC  +0.02 USDC
5/20/2026 22:06:07 DOT Open Short  1.2465  4.0 DOT   10.15 USDC  -0.00 USDC
```

Both signals: `zscore-pump-` in source. Both have `sl_distance=0.015` (A/B test value, not real SL%).

---

## Root Cause Analysis

### DOT SHORT (trade #10226) — Impossible under current constants

**Stored SL=1.2084, entry=1.2465 → distance=3.06%**

ATR constants:
- ATR_SL_MIN_INIT = 0.7%
- ATR_SL_MAX_INIT = 0.9%

3.06% >> 0.9% → **mathematically impossible** to produce via any ATR path in tpsl_utils.py or position_manager.py.

Even with ATR_PCT_FALLBACK=3%:
- k=0.5 → sl_pct=0.015 → capped at 0.9% → SL=1.2577
- Stored SL=1.2084 ≠ 1.2577

PUMP mode (PUMP_SL_PCT=1.5%): SL would be 1.2652. Stored=1.2084. Not match.

**DOT SL=1.2084 cannot be explained by current constants.** Must be a different code path, stale data, or prior version of constants.

### ICP SHORT (trade #10234) — SL reproduced via ATR_K_NORMAL_VOL=1.25

**Stored SL=2.5175, entry=2.5368 → distance=0.76%**

ATR at trade time (from candles.db 15m, 14-period):
- ATR = 0.015768 (0.6214% of entry)
- atr_pct=0.6214% < ATR_PCT_LOW_THRESH=1% → LOW_VOL tier
- `_atr_tier()` returns k=0.5 for LOW_VOL

But reverse-engineering SL=2.5175:
- Requires eff_sl_pct = 0.782% (SL% below entry)
- k=1.25 × atr_pct=0.625% = 0.781% ✓ MATCHES

Current constants: ATR_K_NORMAL_VOL=0.75 → SL would be $2.5210 (0.85%)
**The constants were different at trade execution time (k was 1.25, not 0.75).**

### ICP Close Reason — misattribution

Pipeline log at 23:22:19: `HYPE Mirror CLOSED SHORT ICP (HL exit $2.538000)`

The close was triggered by HL mirror closing the position, NOT by SL being hit. For a SHORT, SL triggers when price FALLS below the SL level. Price path from 1m candles:
- 23:22:00 → 2.5339
- 23:22:07 (entry) → 2.53735
- 23:22:13 → 2.53735
- 23:23:00 → 2.53735

Price went UP from 2.5339 to 2.53735 — moved AGAINST the SHORT direction. SL=2.5175 is $0.02 BELOW entry. Price NEVER touched 2.5175.

`atr_sl_hit` written by position_manager is a misattribution — the HL mirror close triggered the exit, not the ATR SL mechanism.

---

## Key Constants (hermes_constants.py — verified 2026-05-21)

| Constant | Value | Notes |
|----------|-------|-------|
| ATR_SL_MIN_INIT | 0.007 (0.7%) | Initial SL floor for new trades |
| ATR_SL_MAX_INIT | 0.009 (0.9%) | Initial SL cap for new trades |
| ATR_PCT_LOW_THRESH | 0.01 (1%) | Below this → LOW_VOL, k=1.0 in `_atr_tier()` |
| ATR_K_NORMAL_VOL | 0.75 | Current value (was 1.25 before trade execution) |
| ATR_TP_K_MULT | 1.25 | TP k = k × 1.25 |
| PUMP_SL_PCT | 0.015 (1.5%) | From signal_gen.py, NOT hermes_constants |
| PUMP_TP_PCT | 0.025 (2.5%) | From signal_gen.py, NOT hermes_constants |

**PUMP_SL_PCT and PUMP_TP_PCT are NOT in hermes_constants** — they live in signal_gen.py lines 1221-1222. This is a known issue — pending migration to hermes_constants.

---

## Investigation Findings

1. **DOT SL=1.2084 is impossible under current constants** — ATR_SL_MAX_INIT=0.9%, value is 3.06%. Not reproducible via any known path.
2. **ICP SL=2.5175 REPRODUCIBLE with ATR_K_NORMAL_VOL=1.25** — reverse-engineered: k=1.25, sl_pct=1.25×0.625%=0.782% → SL=2.5175 (matches exactly). Current constant ATR_K_NORMAL_VOL=0.75 → SL would be $2.5210. **The constants were different at trade execution time (k was 1.25, not 0.75).**
3. **`sl_distance=0.015` in DB = A/B test control value, NOT real SL%** — set by decider_run's `sl_pct_val=0.015` at signal execution. Stored in `sl_distance` column, unrelated to actual computed SL.
4. **`zscore-pump-` in source → `is_pump=True` in decider_run** — pump mode SL (1.5%) doesn't match stored SL either. User confirmed: NOT pump mode. The `pump-` string is part of the signal generator name.
5. **Price never touched SL=2.5175 for ICP** — 1m candles at trade time: 2.5339→2.5339→2.5339→2.53735→2.53735 (UP, not down). HL exit=$2.538 is ABOVE entry ($2.5368) and $0.02 above the stored SL. For a SHORT, price going UP means it moved AGAINST the trade direction — SL should NOT trigger.
6. **Close reason `atr_sl_hit` is inconsistent with price path** — Pipeline log shows `HYPE Mirror CLOSED SHORT ICP (HL exit $2.538000)`. The close was triggered by mirror (HL closing), not by SL being hit. `atr_sl_hit` reason written by position_manager is a misattribution.
7. **atr_pct=0.6214% (LOW_VOL tier, k=0.5 in `_atr_tier()`)** — ATR computed from 14-period 15m candles at trade time = 0.015768. Below ATR_PCT_LOW_THRESH=1% → LOW_VOL.
8. **MIN_SL_INIT floor (0.7%) applies too aggressively** — When ATR is small (0.62%), the floor forces SL=0.7% even though computed value was 0.62%. For ICP entry=2.5368: 0.7% floor → SL=$2.5190, but stored SL=2.5175 (0.78%). The floor should not apply when the ATR itself is genuinely below MIN_INIT.

---

## Diagnostic Query

```sql
-- Find all trades that closed within 10s of opening
SELECT id, token, direction, entry_price, stop_loss, target,
       open_time, close_time,
       EXTRACT(EPOCH FROM (close_time - open_time)) as seconds_to_close,
       close_reason, pnl_usdt, source
FROM trades
WHERE status = 'closed'
  AND EXTRACT(EPOCH FROM (close_time - open_time)) < 10
ORDER BY close_time DESC;

-- Verify SL bounds at entry time
SELECT id, token, direction, entry_price, stop_loss,
       (stop_loss - entry_price) / entry_price as sl_distance_pct,
       close_reason
FROM trades
WHERE status = 'closed'
  AND ABS((stop_loss - entry_price) / entry_price) > 0.012
ORDER BY open_time DESC;
```

---

## Fix Required (pending T approval)

1. **Add guard**: If SL is outside ATR_SL_MIN_INIT/MAX_INIT bounds at entry time, log CRITICAL error before committing DB INSERT
2. **PUMP constants migration**: Move PUMP_SL_PCT/PUMP_TP_PCT from signal_gen.py to hermes_constants.py
3. **Monitor**: DOT SL=1.2084 — constants may have been different at execution; verify git history for ATR_K_* changes around May 20
4. **MIN_SL_INIT floor**: Consider not flooring when ATR × k is genuinely small (< MIN_INIT) — let the computed value stand

---

## Related Reference

- `references/brain-mirror-open-fail-db-insert-2026-05-21.md` — DOT trade #10226 phantom DB record (brain.py INSERT after mirror_open FAIL)
- `references/rapid-sl-close-not-a-bug-2026-05-21.md` — ICP + DOT 3s closes — not a bug (genuine SL hits after immediate adverse move)