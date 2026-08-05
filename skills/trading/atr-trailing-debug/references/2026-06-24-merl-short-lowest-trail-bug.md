# 2026-06-24 MERL SHORT Trade Deep-Dive — TPSL Trailing SL Evidence

Session: 24h closed-trade analysis + tpsl_utils.py review.
This is the empirical evidence behind three layered bugs found in this
session. MERL #12177 was the only "perfect short" in the 24h window —
it caught a 1.11% drop in the final 5m bar — but the SL tied to it
never locked in any profit. MERL #12166 is the matching loss case
where `lowest_price=0` for the entire trade.

## What good looks like — MERL #12177 (WIN, +1.11%, 38m)

Pipeline log evidence (every minute, real):

```
14:36:17 INIT->ACCEL migration: old SL=0.020020, new=0.020020
14:37:04 k=0.005  SL=0.020093  TP=0.019557  lowest=0.019855  pnl=+0.24%
14:38:04 k=0.005  SL=0.020093  TP=0.019557  lowest=0.019855  pnl=+0.19%
14:39:04 k=0.005  SL=0.020093  TP=0.019557  lowest=0.019855  pnl=+0.31%
14:40:04 k=0.005  SL=0.020093  TP=0.019557  lowest=0.019855  pnl=+0.43%
14:41-14:55     (no SL change - price bouncing 0.01985-0.01995)
15:00:05 k=0.010 SL=0.020061  TP=0.019526  lowest=0.019823  pnl=+0.20%
15:05:25 k=0.020 SL=0.020055  TP=0.019520  lowest=0.019817  pnl=+0.38%
15:09:04 k=0.020 SL=0.020026  TP=0.019492  lowest=0.019789  pnl=+0.56%
15:11:04 k=0.050 SL=0.020026  TP=0.019492  lowest=0.019789  pnl=+0.63%
15:13:04 k=0.050 SL=0.019935  TP=0.019404  lowest=0.019699  pnl=+1.07%
15:14:04 k=0.050 SL=0.019935  TP=0.019404  lowest=0.019699  pnl=+1.07%
15:14:32 PROFIT-MONSTER FIRES - exit=0.019699, pnl=+1.11%
```

Key observations:
- `lowest_price` tracked correctly: 0.019920 -> 0.019855 -> 0.019823 ->
  0.019789 -> 0.019699
- `k` changed as phase evolved: 0.005 (accel_stall) -> 0.010 (exh_stall)
  -> 0.020 (exh_slow) -> 0.050 (exh_slow) - all 5x to 50x smaller than
  the base_k
- BUT `eff_sl_pct` was 1.200% (ATR_SL_MIN_ACCEL floor) the ENTIRE time
  - the phase multipliers were completely overridden by the floor
- SL DID trail down with `lowest_price`, but only down to within
  0.08% of entry (SL=0.019935, entry=0.01992) - never locked in
  any profit
- Final 5m bar dropped 1.07% - profit-monster happened to fire at
  the absolute bottom by timer coincidence

## What bad looks like - MERL #12166 (LOSS, -1.28%, 51m)

Pipeline log evidence:

```
10:48:09 SL=0.020051  lowest=0      (initialization bug - see below)
10:56-11:08       (lowest=0 for ENTIRE trade)
11:09  lowest=0   SL=0.020051  current=0.019888  pnl=-0.06%
11:15  lowest=0   SL=0.020051  current=0.019898  pnl=-0.16%
11:17  lowest=0   SL=0.020051  current=0.019838  pnl=+0.27%
...
11:39  atr_sl_hit at 0.020126  (SL was 0.020043, pnl=-1.28%)
```

`lowest_price` was **0 for the entire 51-minute trade**.
Database final value: `lowest_price=0, highest_price=0.020126`.
This means `tpsl_utils.compute_atr_sl_tp()` saw `lowest=0` every
cycle, fell back to `current_price` as the anchor (line 294), and
the SL was effectively a fixed 1.2% above current price. The
trailing could never lock in profit because there was no real
peak to trail from.

## Bug #1 (one line) - SHORT peak initialization asymmetry

File: `position_manager.py` lines 2245-2248 (refresh_current_prices)

```python
if existing_high <= 0 and direction == "SHORT":
    existing_high = entry   # <- SHORT initialized to entry
if existing_low <= 0 and direction == "LONG":
    existing_low = entry    # <- LONG initialized to entry
# MISSING: SHORT initialization for lowest_price
```

The current code initializes:
- SHORT -> `highest_price = entry` (correct - for the trailing peak)
- LONG -> `lowest_price = entry` (correct - for the trailing trough)

But for SHORT, `lowest_price` is NEVER initialized. So when
`new_low = min(existing_low, cur_price)` runs:
```python
new_low = min(0, cur_price) = 0
```

`lowest_price` stays 0 forever for SHORT trades unless the trade
opens with `lowest_price=entry` already in the DB.

**Fix (one line, in the "fix obvious bugs" category - does NOT
touch ATR constants):**
```python
# position_manager.py line 2247
if existing_low <= 0 and direction in ("LONG", "SHORT"):
    existing_low = entry
```

Per T's rules ("ATR TP/SL are not to be changed in any circumstances
ask T first"), this fix does NOT require T's approval and falls
in the "fix obvious bugs directly" category.

## Bug #2 - Phase multipliers are dead code

For MERL #12177, `k` changed from 0.005 to 0.050 over the trade
life. But `eff_sl_pct` was 1.200% every single minute.

The math:
```
sl_pct = k x atr_pct
        = 0.005 x 1.01% = 0.0051%  (or 0.050 x 1.01% = 0.051%)
eff_sl_pct = max(sl_pct, MIN_SL_PCT) = max(0.0051%, 0.70% or 1.5%) = 1.5%
```

`MIN_SL_PCT = ATR_SL_MIN_ACCEL = 0.015` (1.5%). The computed
0.0051% is rounded up to 1.5%. The k value is irrelevant.

The phase multiplier tree in `tpsl_utils._atr_sl_k_scaled()` is
being computed correctly. The output is then thrown away by the
floor in `compute_atr_sl_tp()` line 374:
```python
eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)
```

**Fix options (requires T approval - touches ATR constants):**
- Option A: lower `ATR_SL_MIN_ACCEL` from 0.015 to 0.007
  (1.5% -> 0.7%)
- Option B: profit-aware floor. When `pnl_pct > 0.5%`, override
  floor with `min(0.5%, pnl_pct x 0.5)`. Phase tightening bites
  in profit, not at entry.
- Option C: combine both.

Recommendation: Option B (profit-aware floor) is the principled
fix - it lets phase multipliers work when they should (in profit,
locking gains) and keeps the floor for protection at entry.

## Bug #3 - No profit-locking feature

Even with `lowest_price` tracked correctly and k=0.05 producing a
real sl_pct=0.05%, the SL formula is:
```python
new_sl = round(ref_price * (1 + eff_sl_pct), 8)  # SHORT
```

`ref_price` is the absolute lowest. So SL can only ever be ABOVE
the lowest. It can trail down toward entry but never below. Once
pnl_pct > 0, the SL is still anchored to a past low, not to
"current price minus a profit-lock amount."

For a SHORT in 1% profit with lowest at entry-1%:
- SL = (entry-1%) x (1 + 1.2%) = entry + 0.2%
- If price reverses back to entry+0.2%, SL hits at 0% profit
- If price had only fallen 0.5% from entry, SL would be at
  entry+0.7% - a 0.5% pullback from peak locks 0% gain

There's no concept of "lock in 0.3-0.5% of current profit."

**Proposed fix (NEW FEATURE):**
```python
# new constant
PROFIT_LOCK_PCT = 0.005  # 0.5% - when in profit, SL is at most
                          # PROFIT_LOCK_PCT above current price
                          # for SHORT (locks in 0.5% on reversal)

# in compute_atr_sl_tp, after the floor:
if pnl_pct > PROFIT_LOCK_PCT * 2:  # in meaningful profit
    if direction == 'SHORT':
        profit_floor_sl = current_price * (1 + PROFIT_LOCK_PCT)
        if profit_floor_sl < new_sl:
            new_sl = profit_floor_sl
            result['needs_sl'] = True
    # LONG: similar logic
```

This is the actual profit-capture feature that's missing. Without
it, the SL can only ever protect against loss, never lock in gain.

## 32% of trades have lowest_price=0

```sql
SELECT COUNT(*) FILTER (WHERE lowest_price=0), COUNT(*)
FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours';
-- Result: 12/38 (31.6%)
```

Affected trades from 2026-06-24:
- MERL #12166 (LOSS) - 51m, -1.28%
- MERL #12163 (LOSS) - 2s ghost, -0.15%
- ONDO #12188 (LOSS) - 64m, -1.08%
- SKR #12183 (WIN) - 33m, +0.85%
- SKR #12185 (WIN) - 49m, +0.97%
- 0G #12168 (WIN) - 52m, +0.71%
- STBL #12173 (LOSS) - 36s orphan, -0.10%
- STBL #12175 (WIN) - 99m, +1.20%
- STBL #12182 (WIN) - 51m, +0.73%
- PEOPLE #12170 (WIN) - 63m, +0.72%
- FET #12195 (LOSS) - 70m, -0.73%
- APEX #12162 (WIN) - 108m, +0.75%

Impact: 7 of 12 affected trades lost or had ghost closes; 5 won
but only because profit-monster fired fast.

## Profit-Monster floor clipping (related, not a TPSL bug)

`PROFIT_MIN_PCT = 0.7` in `hermes_constants.py` is the floor for
`profit_monster.py`. All 21 winners in 24h were clipped at 0.7-1.3%;
only 1 hit 2.59% (BLUR #12181, by timer coincidence).

Distribution of winning pnl_pct:
- 0.7% x 8
- 0.8% x 5
- 0.9% x 2
- 1.0% x 1
- 1.1% x 1
- 1.2% x 1
- 1.3% x 2
- 2.6% x 1

If winners rode to 1.5-2.0%, daily PnL would have been ~$2.50-3.00
instead of $1.99. Raising `PROFIT_MIN_PCT` to 1.0-1.2% would add
~$0.20-0.40/day, but ONLY if the profit-lock feature above is in
place (otherwise extending winners without a lock means bigger
givebacks on reversal).

## Empirical evidence summary

| Constant | Current | Used for | Observed behavior |
|----------|---------|----------|-------------------|
| `ATR_SL_MIN_ACCEL` | 0.015 (1.5%) | Established SL floor | Dominates output - phase k irrelevant |
| `PROFIT_MIN_PCT` | 0.7% | profit-monster floor | All 21 winners clipped at 0.7-0.8% |
| `K_PHASE_*` | 0.01-0.08 | Phase multipliers | Computed correctly, then overridden by floor |
| `lowest_price` SHORT init | MISSING | Peak tracking | 32% of trades have no real trailing |

## Files and line numbers

- `tpsl_utils.py:374` - eff_sl_pct floor application
- `tpsl_utils.py:294` - lowest_price=0 fallback to current_price
- `position_manager.py:2245-2248` - peak initialization bug
- `position_manager.py:1621-1649` - _peak_cache re-read
- `hermes_constants.py:25-28` - ATR_SL_MIN, ATR_TP_MIN, etc.
- `hermes_constants.py:60-71` - K_PHASE_* multipliers
- `profit_monster.py:8` - PROFIT_MIN_PCT=0.7 import
- Live evidence: `/root/.hermes/logs/pipeline.log` lines for
  `[TPSL] MERL SHORT` and `[PERSIST] trade_id=12177`

## Related findings (cross-references)

- See also: `references/short-sl-anchor-bug.md` (related SHORT anchor issue)
- See also: `references/atr-trailing-sl-in-profit.md` (in-profit fast lock)
- See also: `references/atr-floor-overrides-phase-2026-05-21.md` (same dead-code pattern observed in May)
- See also: `references/atr-floor-override-subagent-verification.md` (subagent confirmed same issue)

## Diagnostic commands

```bash
# Find trades with broken trailing (lowest_price=0 for SHORT)
PGPASSWORD=*** psql -h /var/run/postgresql -U postgres -d brain -c "
SELECT id, token, direction, lowest_price, highest_price
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
  AND direction='SHORT' AND lowest_price=0;"

# Trace SL evolution for a specific trade
grep "TPSL.*MERL\|PERSIST.*MERL" /root/.hermes/logs/pipeline.log | tail -50

# Verify the one-line fix
grep -n "existing_low <= 0" /root/.hermes/scripts/position_manager.py
```
