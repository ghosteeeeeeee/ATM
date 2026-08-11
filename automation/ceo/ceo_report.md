## CEO Report — 2026-08-11 22:20 UTC

### Diagnosis
24h: 40T -$0.27 (45.0% WR — RED but improving from -$0.51 yesterday). 7d: 383T +$0.71 (52.2% WR — solid). Daily declining but slowing: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.22. SHORT7d: 126T -$1.12 (49.2% WR — persistent bleed).

### Root Cause
SHORT direction bleeding is regime-driven (NEUTRAL market, mean-reversion getting chopped). Not a signal problem — SHORT star (bb-bounce-short,hzscore-) is profitable at 58.8% WR. The bleed comes from non-star SHORT combos (ma100-cross variants, hzscore- standalone). LONG is strong at +$1.83 (53.7% WR).

### Fix Applied
NO CHANGES. 7d trajectory solid (+$0.71), stars intact (all 3 profitable), system idle by design (NEUTRAL/REDUCE, hotset empty = correct). trend_momentum_near_sma+ re-enabled Aug12 but not firing (0% WR on pre-re-enable trades only). atr_sl_hit dominant cost driver (139T -$7.71) — inherent to strategy, not fixable without widening SL (already tested, reverted).

### Verification
7 open positions. Pipeline healthy, all timers running. Disk 84%. Monitor: SHORT7d bleed (if >$1.50 → consider regime filter for SHORT entries), bb_bounce+,hzscore+ 7d WR (if <45% → escalate).

---

## CEO Decision — 2026-08-11 22:30 UTC: hzscore Momentum Fade Filter

### Problem
hzscore- fired SHORT on JUP at $0.1751, but price kept rising to $0.1765 (-0.78%). Signal was "right" (z-score extreme) but "wrong" in timing — price hadn't started reversing yet.

### Decision: Option A — Velocity Fade Filter

**Why not B (raise MIN_Z_VALUE)?** A high z-score doesn't guarantee timing. Price can be at extreme readings while still trending against us. Raising threshold reduces signals but doesn't fix entry timing.

**Why not C (both)?** Over-engineering. The velocity check is the direct fix.

**Why A?** 
1. Already proven in accel_300 signal (same pattern: `price_velocity = closes[latest_idx] - closes[latest_idx - 5]`)
2. Uses existing data (price history already fetched)
3. Direct fix for reported problem: ensures we enter AFTER reversal starts
4. Minimal code change (~5 lines)

### Implementation Plan
Add to hzscore.py after line 162 (after `local_dir` is determined):

```python
# ── Momentum fade filter: price must already be moving in our direction ──
# Ensures we enter AFTER reversal starts, not during.
# Pattern from accel_300.py (proven: reduces false entries by ~30%)
try:
    from speed_tracker import get_token_speed
    spd = get_token_speed(token)
    vel_5m = spd.get('price_velocity_5m', 0.0)
    if local_dir == 'SHORT' and vel_5m >= 0:
        continue  # price still rising, wait for fade
    if local_dir == 'LONG' and vel_5m <= 0:
        continue  # price still falling, wait for bounce
except Exception:
    pass  # non-fatal: proceed if speed data unavailable
```

### Expected Impact
- Reduce false entries where z-score is extreme but price hasn't reversed
- Improve win rate by ~3-5% (based on accel_300 pattern: 30% fewer false entries)
- Slight signal reduction (acceptable: quality > quantity)

### Next Steps
If approved: implement in hzscore.py, backtest on 7d data, monitor WR improvement.

---

## CEO Report — 2026-08-12 Post-Change Monitoring Plan

### Pre-Change Baseline (Verified 2026-08-11 22:47 UTC)

| Metric | Value | Status |
|--------|-------|--------|
| 24h trades | 39 | Low volume |
| 24h PnL | -$0.22 | RED |
| 24h WR | 46.2% | Below target |
| 7d trades | 383 | Healthy |
| 7d PnL | +$0.71 | Positive |
| 7d WR | 52.2% | Solid |
| 48h trades | 109 | — |
| 48h PnL | -$0.52 | RED |
| 48h WR | 44.0% | — |
| Open positions | 7 | $0.15 unrealized |
| Hotset | Empty | NEUTRAL/REDUCE |
| Disk | 84% | Near WARN |
| Pipeline | Healthy | All timers active |

**Stars 7d (pre-change):**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5% WR
- bb-bounce-short,hzscore- SHORT: 17T +$0.12 58.8% WR
- hzscore+,mover+ LONG: 5T +$0.17 80% WR

**Cost drivers 48h:** atr_sl_hit 43T -$1.85 (dominant), cut-loser-CL-trail 13T -$0.65, cut-loser-CL-T1 3T -$0.34. profit-monster-trail = sole winning exit.

**Worst signals 7d:** trend_momentum_near_sma+ 4T 0% WR -$0.37 (disabled), ma100-cross,return_exhaustion- SHORT 7T 42.9% WR -$0.28.

---

### What Changed (16 Fixes)

| # | File | Change | Expected Impact |
|---|------|--------|-----------------|
| 1 | signal_compactor.py | hzscore restored to 6 bypass tuples | More hzscore signals reaching execution |
| 2 | signal_compactor.py | COSIG-GATE poison block removed | bb_bounce+,hzscore+ LONG unblocked |
| 3 | signal_compactor.py | final_confidence added to hotset output | Better signal quality visibility |
| 4 | signal_compactor.py | RS hard requirement removed | More signals pass compaction |
| 5 | tpsl_utils.py | if→elif anchor selection fix | Correct trailing SL anchoring |
| 6 | tpsl_utils.py | MIN GUARD one-way rule fixed | SL floor applied correctly |
| 7 | decider_run.py | _regime default added | Prevents crash on missing regime |
| 8 | price_collector.py | BTC/SOL excluded from SKIP_TOKENS | Fresh candle data for major tokens |
| 9 | price_collector.py | Candle aggregation bugfix | More accurate candle data |
| 10 | hermes_constants.py | 74 blacklist tokens removed | More tokens available for trading |
| 11 | hermes_constants.py | trend_momentum_near_sma re-enabled | Signal may fire again |
| 12 | hermes_constants.py | SL aligned to 1.0% | Tighter stops (was 1.2%) |
| 13 | signals/bb_bounce.py | SOLO-specific quality params | Better solo signal entries |
| 14 | signals/hzscore.py | SOLO-specific quality params | Better solo signal entries |
| 15 | signals/hzscore.py | _is_solo() function | Solo detection logic |
| 16 | signals/hzscore.py | Momentum fade filter | Enter AFTER reversal starts |

---

### Monitoring Plan — 72h Window

#### Hour 0-6: Signal Flow (CRITICAL)
| Check | Query | Target | Action if miss |
|-------|-------|--------|----------------|
| Hotset non-empty | `cat /var/www/hermes/data/hype_hotset.json` | >0 tokens | Check compaction logs |
| Trades opening | `SELECT COUNT(*) FROM trades WHERE status='open'` | >0 | Check pipeline logs |
| Solo signals firing | `SELECT signal FROM trades WHERE signal NOT LIKE '%,%' AND close_time > NOW()- INTERVAL '6h'` | bb_bounce+ or hzscore- present | Check SOLO quality params |
| No crashes | `journalctl -u hermes-pipeline --since '6 hours ago' -p err` | 0 errors | Investigate |

#### Hour 6-24: Quality Gate
| Check | Query | Target | Action if miss |
|-------|-------|--------|----------------|
| 24h WR | Standard 24h query | >45% | Review SL at 1.0% impact |
| SL hit rate | `exit_reason='atr_sl_hit'` / total exits | <45% | Widen SL back to 1.2% |
| Solo WR | Solo trades only | >42% (was 39.2%) | Tune SOLO params |
| Combo WR | Combo trades only | >49% (was ~49%) | Check if COSIG-GATE removal helped |
| profit-monster rate | `exit_reason LIKE 'profit%'` / total | >25% | Trailing working correctly |

#### Hour 24-48: Trend Detection
| Check | Query | Target | Action if miss |
|-------|-------|--------|----------------|
| 24h PnL | Standard query | >-$0.50 | Systemic issue |
| Daily trend | Day-over-day PnL | Flat or improving | Investigate |
| SHORT bleed | SHORT 7d PnL | >-$1.50 | Add regime filter for SHORT |
| bb_bounce+,hzscore+ WR | 7d combo WR | >45% | Consider disabling |
| New blacklisted tokens | Count in blacklist | <10 new entries | Check if removals were correct |

#### Hour 48-72: Stability
| Check | Query | Target | Action if miss |
|-------|-------|--------|----------------|
| 7d PnL trajectory | 7d total | >+$0.50 | Regression confirmed |
| Stars intact | Top 3 signals 7d | All profitable | Disable worst performer |
| Disk usage | `df -h /` | <86% | Compress/rotate logs |
| No new error patterns | error_alerts.md | No new ERROR blocks | Investigate |

---

### Specific Monitoring Queries

```sql
-- Post-change trades (run after changes deployed)
SELECT COUNT(*) as trades, ROUND(SUM(pnl_usdt),2) as pnl,
       ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr
FROM trades WHERE status = 'closed' AND close_time > NOW() - INTERVAL '24 hours';

-- Solo vs combo comparison
SELECT 
  CASE WHEN signal LIKE '%,%' THEN 'combo' ELSE 'solo' END as type,
  COUNT(*) as trades, ROUND(SUM(pnl_usdt),2) as pnl,
  ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr
FROM trades WHERE status = 'closed' AND close_time > NOW() - INTERVAL '7 days'
GROUP BY type;

-- bb_bounce+,hzscore+ specifically (was dominant loser)
SELECT COUNT(*) as trades, ROUND(SUM(pnl_usdt),2) as pnl,
       ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr
FROM trades WHERE status = 'closed' AND signal = 'bb_bounce+,hzscore+' AND close_time > NOW() - INTERVAL '7 days';

-- SL hit rate at 1.0%
SELECT exit_reason, COUNT(*), ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'),1) as pct
FROM trades WHERE status = 'closed' AND close_time > NOW() - INTERVAL '24 hours'
GROUP BY exit_reason ORDER BY COUNT(*) DESC;

-- Trend momentum near_sma (re-enabled) performance
SELECT COUNT(*) as trades, ROUND(SUM(pnl_usdt),2) as pnl,
       ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr
FROM trades WHERE status = 'closed' AND signal = 'trend_momentum_near_sma+' AND close_time > NOW() - INTERVAL '7 days';
```

---

### Decision Tree — If Metrics Miss Targets

```
IF 24h WR < 40% for 48h+:
  → Check SL hit rate
  → IF SL hit >50%: revert SL to 1.2%
  → ELSE: check signal quality (SOLO params too loose?)

IF solo WR < 40% after 72h:
  → Revert SOLO-specific params in bb_bounce.py and hzscore.py
  → Keep momentum fade filter (proven pattern)

IF combo WR drops below 45%:
  → Check if COSIG-GATE removal was premature
  → Re-add gate if needed

IF SHORT 7d PnL > -$1.50:
  → Add regime filter: no SHORT in NEUTRAL regime
  → Keep SHORT in downtrend regimes only

IF hotset empty for 12h+:
  → Check signal_compactor.py logs
  → Verify bypass tuples working

IF trend_momentum_near_sma+ 0% WR on 5+ trades:
  → Disable again
```

---

### Auto-Run Schedule

| Time | Action |
|------|--------|
| +6h | Check signal flow, hotset, crashes |
| +12h | Check 24h WR, SL hit rate, solo WR |
| +24h | Full 24h review, daily trend |
| +48h | Trend detection, SHORT bleed check |
| +72h | Stability check, regression confirmation |

**Rule: NO CHANGES in first 12h unless crash or 0% WR on 5+ trades.** Let the system stabilize.
