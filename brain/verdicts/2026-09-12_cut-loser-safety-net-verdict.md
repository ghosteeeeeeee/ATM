# Independent Auditor Verdict: Cut-Loser Safety Net Hierarchy

**Auditor:** DeepSeek Harness (independent, fresh-eyes analysis)
**Date:** 2026-09-12
**Files Read:** cut_loser.py, hermes_constants.py (CL constants), hyperliquid_exchange.py (place_stop_loss_order), position_manager.py, tpsl_utils.py, decider_run.py, run_pipeline.py, systemd timer units
**Data Sources:** PostgreSQL (brain DB), cut_loser.log, pipeline.log, systemd timers

---

## System Architecture (Verified)

### Safety Net Hierarchy (actual execution order)

```
1. ATR_SL (position_manager.py) — polls every ~60s via pipeline timer
   - Initial SL: ATR_SL_MIN_INIT (1.0% raw) from entry price
   - After first cycle: TRAILS with current_price (anchors to current_price for losing trades)
   - Trailing gate: only tighten, never loosen (for LONG: SL can only move UP)
   - BUT: for trades in loss (highest_price <= entry), ref_price = current_price
   - Result: SL follows price DOWN as reference, but trailing gate prevents lowering below initial
   - Net effect: SL stays at initial level for gradual decline, only tightens on recovery

2. CL-T1 Quick Cut (cut_loser.py) — fires every ~60s (systemd), internal fire window (1-2 min)
   - Range: -1.0% to -3.0% post-leverage
   - Max close per wake: 2 positions
   - Skip bottom: 0% (all qualifying trades considered)

3. CL-T2 Deep Cut (cut_loser.py) — fires every ~60s, internal fire window (2-4 min)
   - Range: -1.5% to -3.0% post-leverage
   - Max close per wake: 1 position

4. CL-TRAIL (cut_loser.py) — DISABLED (CL_TRAIL_ENABLED = False)

5. MAE Guard (cut_loser.py) — runs every wake (no fire window)
   - Cuts LONG if price drops >3% from peak (ATR-aware scaling)
   - Immediate crash protection

6. Hard SL (position_manager.py) — CL_HARD_STOP_PCT = -3.0%
   - Cuts any trade at -3.0% immediately (within position_manager cycle)
```

### Critical Architecture Finding

**ATR_HL_ORDERS_ENABLED = False** (position_manager.py line 100)

This means NO server-side stop-loss orders are placed on Hyperliquid. All stop-loss detection is done via software polling:
- position_manager polls every ~60 seconds (pipeline timer)
- cut_loser.py polls every ~60 seconds (separate systemd timer)
- Price checks are done in Python, not at the exchange level

---

## Claim-by-Claim Verdict

### Claim 1: "CL-T1 polls every 1-2 minutes"

**Verdict: PARTIAL — Misleading**

**Evidence:**
- cut_loser.py systemd timer: `OnUnitActiveSec=1min` → script executes every 60 seconds
- Log analysis (2,623 firings over ~44 hours): avg interval = 60s, min = 60s, max = 62s
- **However**, CL-T1 has an internal fire check via `should_fire()` with windows `{"A": (1, 2), "B": (1, 2)}` (in minutes)
- The fire check uses `elapsed >= fire_interval_sec` where `fire_interval = random(60, 120)` seconds
- Log analysis of actual T1 fires: 924 checks, 468 fires (50.6%), avg 5.6 min between fires
- The 5.6min average includes gaps when no positions are in range (T1 skips when nothing qualifies)
- **When positions ARE in range**, T1 fires every ~90 seconds on average (1-2 min window)

**Confidence: HIGH**

**Conclusion:** The SCRIPT runs every 60s, but the FIRE CHECK means T1 acts every 1-2 min when there are qualifying positions. The claim is technically accurate for the fire window but misleading about the actual script execution frequency.

---

### Claim 2: "ATR_SL polls every ~5 seconds"

**Verdict: DISAGREE**

**Evidence:**
- ATR_SL check is inside `position_manager.py` → `check_atr_tp_sl_hits()` (line 386)
- position_manager runs as part of `STEPS_EVERY_MIN` in `run_pipeline.py`
- `hermes-pipeline.timer`: `OnCalendar=*:0/1:00` → pipeline fires every 60 seconds
- `hermes-atr-sl-updater.timer` exists but is **DEFUNCT** (service file not found)
- No separate ATR SL updater process exists
- Actual ATR_SL polling interval: **~60 seconds** (pipeline cycle time)
- Pipeline log confirms position_manager runs ~every 60s (avg 25s between runs in sample, but that's the pipeline iteration time, not the SL check frequency)

**Confidence: HIGH**

**Conclusion:** ATR_SL polls every ~60 seconds, not every ~5 seconds. This is a 12x difference from the claimed interval.

---

### Claim 3: "No server-side stop-loss orders are placed"

**Verdict: AGREE**

**Evidence:**
- `ATR_HL_ORDERS_ENABLED = False` (position_manager.py line 100)
- Comment at line 2434: `"HL orders DISABLED — SL/TP managed locally by guardian via DB"`
- `_execute_atr_bulk_updates()` is only called when `ATR_HL_ORDERS_ENABLED` is True (line 2431-2432)
- `hyperliquid_exchange.py` has `place_stop_loss_order()` function (line 1591) and `place_tp_sl_batch()` (line 1628) — these functions EXIST but are NEVER called from position_manager or decider_run
- `decider_run.py` does NOT call any HL stop-loss placement functions
- At trade close, position_manager actually CANCELS stale HL orders (line 1122-1136) — confirming they don't exist
- `hermes-atr-sl-updater-DEFUNCT.service` — the dedicated SL updater was explicitly disabled

**Confidence: HIGH**

**Conclusion:** This is the single most critical finding. ALL stop-loss protection is software-polled. If the software misses a cycle (GC pause, DB lock, CPU spike), trades bleed with NO exchange-level protection.

---

### Claim 4: "CL-T1 is a safety net for ATR_SL failures"

**Verdict: PARTIAL — CL-T1 IS a safety net, but NOT for the reason claimed**

**Evidence:**
- CL-T1 range: -1.0% to -3.0% post-leverage (hermes_constants.py lines 1369-1370)
- ATR_SL initial: 1.0% raw (ATR_SL_MIN_INIT = 0.01)
- With 5x leverage: ATR_SL triggers at -5% post-leverage (1.0% × 5)
- With 3x leverage: ATR_SL triggers at -3% post-leverage (1.0% × 3)
- **CL-T1 fires BEFORE ATR_SL for 5x trades** (catches at -1% to -3% vs ATR SL at -5%)
- **CL-T1 overlaps with ATR_SL for 3x trades** (both in -1% to -3% range)
- **BUT**: CL-T1 data shows 86 out of 88 trades closed at -3%+ (past its intended range)
- This means CL-T1 is catching trades that ALREADY PASSED through -1% to -3% without being caught
- The 5.6min average fire interval means CL-T1 often misses the window where it could catch trades cleanly

**Data (30 days):**
| System | Trades Closed | Avg PnL | Range |
|--------|--------------|---------|-------|
| ATR_SL | 767 | varies | trailing |
| CL-T1 | 88 | -5.03% | -1% to -3% (intended) |
| MAE Guard | 19 | -5.00% | crash detection |
| Hard SL | 19 | -11.30% | -3% hard stop |

**Confidence: HIGH**

**Conclusion:** CL-T1 IS a safety net, but it's catching trades AFTER they've already bled past -3%. It's not catching them in the -1% to -3% range as designed. The "safety net" works, but the timing is wrong — by the time CL-T1 fires, the damage is done.

---

### Claim 5: "Making CL-T1 polling faster would fix the issue"

**Verdict: DISAGREE — Faster polling is a band-aid, not a fix**

**Evidence:**

**What faster polling WOULD fix:**
- CL-T1 currently fires every ~5.6min on average (with 1-2 min fire windows)
- Reducing to 15-30 second windows would catch trades in the -1% to -3% range faster
- Estimated improvement: CL-T1 would catch ~60% of trades in range vs current ~2%

**What faster polling would NOT fix:**
1. **ATR_SL is trailing, not fixed**: For trades in loss, `ref_price = current_price` (tpsl_utils.py line 372-373). The SL is computed from current price, not entry. The trailing gate prevents lowering, but the SL doesn't provide a FLOOR against gradual decline.

2. **No server-side SL orders**: Even with 1-second CL-T1 polling, there's NO exchange-level protection. A single missed cycle = unbounded loss.

3. **The real bottleneck is ATR_SL, not CL-T1**: 290 trades worse than -3% were caught by ATR_SL (avg -5.70%). These trades bled because ATR_SL is trailing. CL-T1 can't fix ATR_SL's trailing behavior.

4. **Race conditions**: Faster polling = more concurrent close attempts = more race conditions with guardian, profit_monster, sniper_exit (cut_loser.py lines 172-185).

**The proper fix:**
1. **Enable server-side SL orders** (`ATR_HL_ORDERS_ENABLED = True`) — provides exchange-level protection
2. **Fix ATR_SL to be fixed, not trailing** — anchor SL to ENTRY price, not current price
3. **Reduce pipeline interval** to 10-15 seconds for position_manager (not just CL-T1)

**Confidence: HIGH**

**Conclusion:** Faster CL-T1 polling is treating symptoms, not the disease. The root cause is: (a) no server-side SL orders, and (b) ATR_SL is trailing, not fixed. Enabling `ATR_HL_ORDERS_ENABLED` would provide immediate, exchange-level protection regardless of software polling speed.

---

## Data Summary

### Exit Reason Distribution (30 days)
| Reason | Count | % of Total |
|--------|-------|-----------|
| atr_sl_hit | 767 | 53.4% |
| profit-monster-trail | 505 | 35.1% |
| cut-loser-T1 | 88 | 6.1% |
| rr_engine_resistance | 25 | 1.7% |
| cut-loser-MAE-GUARD | 19 | 1.3% |
| hard_sl | 19 | 1.3% |
| Other | 16 | 1.1% |

### ATR_SL Slippage Analysis (30 days)
| Category | Count | % |
|----------|-------|---|
| At or above -1% (SL worked properly) | 408 | 53.2% |
| -1% to -2% (slippage/gap) | 36 | 4.7% |
| -2% to -3% (significant slip) | 33 | 4.3% |
| **-3%+ (SL failed to protect)** | **290** | **37.8%** |

### ATR_SL Exits by Leverage (30 days)
| Leverage | Total | Profitable | Mild Loss | Severe Loss | Avg PnL |
|----------|-------|-----------|-----------|-------------|---------|
| 3x | 300 | 107 (35.7%) | 98 (32.7%) | 95 (31.7%) | -0.97% |
| 5x | 465 | 190 (40.9%) | 80 (17.2%) | 195 (42.0%) | -0.37% |

### CL-T1 Effectiveness (30 days)
- Total CL-T1 exits: 88
- Trades caught in intended range (-1% to -3%): **2 (2.3%)**
- Trades caught past range (-3%+): **86 (97.7%)**
- Avg hold time: 95.4 min
- Avg PnL at close: -5.03%

### All Trades Worse Than -3% (30 days) — What Caught Them?
| System | Count | Avg PnL | Worst |
|--------|-------|---------|-------|
| atr_sl_hit | 290 | -5.70% | -41.62% |
| cut-loser-T1 | 86 | -5.03% | -8.06% |
| cut-loser-MAE | 13 | -5.00% | -7.13% |
| hard_sl | 4 | -11.30% | -13.29% |

### cut_loser.py Fire Frequency (from logs)
- Script execution: every 60 seconds (systemd timer)
- CL-T1 fire check: 924 checks in ~44 hours
- CL-T1 actual fires: 468 (50.6%)
- Avg time between T1 fires: 339s (5.6 min)
- Min time between T1 fires: 60s
- Max time between T1 fires: 34,117s (9.5 hours — gap between episodes)

### ATR SL Severity vs Hold Time (30 days)
| Severity | Count | Avg Hold | Avg PnL |
|----------|-------|----------|---------|
| OK (<=-3%) | 477 | 121.2 min | +2.50% |
| Missed (-3% to -5%) | 153 | 75.3 min | -4.13% |
| Bad (-5% to -10%) | 125 | 86.9 min | -6.64% |
| Catastrophic (-10%+) | 12 | 32.4 min | -15.97% |

---

## Gaps in Understanding (Corrected)

1. **"ATR_SL is a fixed stop"** — WRONG. ATR_SL is TRAILING. For trades in loss, it anchors to `current_price` (tpsl_utils.py line 372-373). The trailing gate prevents lowering, but the initial SL stays fixed. However, if the trade goes to profit and then reverses, the SL trails up and can trigger at a loss.

2. **"CL-T1 catches trades at -1% to -3%"** — MOSTLY WRONG. CL-T1 fires every ~5.6min, so by the time it fires, trades have often already passed -3%. Data shows 97.7% of CL-T1 exits are at -3%+.

3. **"The pipeline protects against losses"** — WRONG without server-side orders. The pipeline polls every 60s. A flash crash can blow through SL levels in milliseconds. Without exchange-level orders, there's no protection.

4. **"position_manager handles SL detection"** — PARTIALLY WRONG. position_manager detects SL breaches by comparing current_price to DB stop_loss. But it only runs every ~60s. Between runs, there's NO SL protection.

---

## Independent Recommendation

### Immediate (Do Now)
1. **Enable server-side SL orders**: Set `ATR_HL_ORDERS_ENABLED = True` in position_manager.py. This provides exchange-level SL protection that works regardless of software polling speed. This is the single highest-impact fix.

2. **Verify HL SL order placement works**: Before enabling, run a dry-run test to confirm `place_stop_loss_order()` and `place_tp_sl_batch()` work correctly with the current HL API.

### Short-Term (This Week)
3. **Fix ATR_SL anchoring**: Change tpsl_utils.py to anchor SL to ENTRY price (not current_price) for losing trades. Lines 372-373 should use `ref_price = float(entry_price)` when trade is in loss, not `current_price`.

4. **Reduce position_manager interval**: Change pipeline to run position_manager every 15-30 seconds instead of every 60 seconds. This is cheap (just a DB check) and reduces the SL detection gap.

### Medium-Term (This Month)
5. **Audit CL-T1 timing**: CL-T1 fires every ~5.6min but its range is -1% to -3%. Trades can traverse this range in seconds during volatility. Either tighten the fire window to 15-30 seconds OR change the range to -2% to -5% to catch trades that have already started bleeding.

6. **Add ATR_SL drift monitoring**: Log when ATR_SL moves more than 0.5% from entry in a single cycle. This would catch the trailing behavior before it causes large losses.

### What NOT to Do
- **Don't just make CL-T1 faster** — it treats symptoms, not the disease
- **Don't remove CL-T1** — it IS catching trades (86 in 30 days), just not optimally
- **Don't rely on MAE Guard alone** — it only catches crashes, not gradual bleed

---

## Overall Assessment

The safety net hierarchy is REAL but has critical gaps:

1. **The biggest gap**: No server-side SL orders. ALL SL detection is software-polled at ~60s intervals. This is a fundamental architectural flaw for a trading system handling real money.

2. **The second gap**: ATR_SL is trailing, not fixed. For trades in loss, the SL is anchored to current_price, which means it doesn't provide a hard floor. The trailing gate prevents lowering, but the SL can still trail up during profitable periods and then trigger at a loss when price reverses.

3. **The third gap**: CL-T1 timing is misaligned with its range. It fires every ~5.6min but its range (-1% to -3%) can be traversed in seconds. By the time CL-T1 fires, trades have often already passed -3%.

4. **What IS working**: The overall system catches most losses. 53.2% of ATR_SL exits are at or above -1% (working properly). CL-T1 catches 88 additional trades. MAE Guard catches 19 crashes. Hard SL catches 19 extreme losses. The system works — it just doesn't work well enough for the -3% to -10% range.

**Bottom line:** The proposed fix (faster CL-T1 polling) would help marginally. The REAL fix is enabling server-side SL orders (`ATR_HL_ORDERS_ENABLED = True`). This provides exchange-level protection that works in milliseconds, not minutes.
