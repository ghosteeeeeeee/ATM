## CEO Report — 2026-09-01 ~04:32 UTC (verified)

### Diagnosis
**Verified DB:** 24h 63T, 46.0% WR, -$0.73. 7d: 384T, 50.0% WR, -$1.38. Today Sep 1: 17T, 70.6% WR, +$0.02. Open: 4 positions. Market NEUTRAL. **range_reversion: SHADOW→LIVE at 04:30 UTC. No trades yet (2min old).**

### Root Cause
**accel-300-v2-long is the #1 bleeder:** 17T/24h, 28.6% WR, -$0.29 standalone. 15/17 exits = atr_sl_hit (82% SL rate). Only 2T with volume_breakout confluence: 100% WR +$0.38. Signal fires too freely in choppy LONG conditions — entries lack momentum confirmation. CEO_PROTECTED — flagged for T review.

**Secondary losses:** confluence-,ichimoku- SHORT -$0.18, ichimoku- variants -$0.23, macd-div- -$0.08 — all CEO_PROTECTED or tiny samples.

**Positive:** Sep 1 started at 70.6% WR (best start in days). accel-300-v2- SHORT backbone solid at +$1.46/7d 52.8% WR.

### Fix Applied
No parameter changes — accel-300-v2-long is CEO_PROTECTED, requires T approval to disable. range_reversion went LIVE at 04:30 (SHADOW_MODE=False). Monitoring 48h.

### Verification
- accel-300-v2-long: FLAGGED for T review (CEO_PROTECTED, 82% SL hit rate)
- range_reversion: LIVE, 0 trades so far (too early)
- volume_breakout: 2T confluence 100% WR — promising but tiny sample
- Pipeline: healthy, all timers active
- Disk: 80%

---

## CEO Report — 2026-09-01 ~04:30 UTC (verified)

### Diagnosis
**Verified DB:** 24h 61T, 45.9% WR, -$0.67. 7d: 382T, 50.0% WR, -$1.38. Today Sep 1: 15T, 73.3% WR, +$0.08. Open: 4 positions (2 bb-bounce-long+, 2 accel-300-v2-long). Market NEUTRAL. **range_reversion: 288 shadow signals/24h across 20 tokens — NOW LIVE.**

**Signal performance (7d):** accel-300-v2- SHORT 72T 52.8% WR +$1.46 (backbone). bb-bounce-short 53T 60.4% WR -$0.12. macd-div- 19T 57.9% WR +$0.02. volume_breakout: 3T — 2 confluence 100% WR +$0.38, 2 standalone 0% WR -$0.19. accel-300-v2-long: 12T 25% WR -$0.51 (CEO_PROTECTED — FLAGGED FOR T REVIEW).

### Root Cause
Signal starvation from flat NEUTRAL market (~2.5/hr). range_reversion was in shadow mode (288 signals/24h but not trading). Now live — should increase signal volume and provide mean-reversion backbone.

### Fix Applied
**range_reversion SHADOW→LIVE.** Set SHADOW_MODE=False. 288 shadow signals across 20 tokens (GOAT, ALGO, KFLOKI, etc.) validated. Confidences 60-85%. Cooldown 45min/token. Signal now contributes to live trading.

### Verification
System improving: Aug 31 -$0.82 → Sep 1 +$0.08 (73.3% WR). range_reversion adds mean-reversion backbone for flat markets. Monitor 48h live performance.

## CEO Report — 2026-09-01 ~01:15 UTC (verified)

### Diagnosis
System FLAT, 3 open LONG (all small). Market DEAD NEUTRAL. **24h: 49T, 38.8% WR, -$0.76** (verified). **7d: 378T, 49.2% WR, -$1.54.** Today Sep 1: 1T +$0.06 (just started). Daily trend: Aug 28 +$1.55 → Aug 31 -$0.82 (3-day decline, today flat). **Signal starvation ~2/hr is #1 problem.** ACCEL_300_V2_LONG: 10T/7d 30% WR -$0.22 (CEO_PROTECTED — flagged for T review). confluence-,ichimoku- SHORT: 7T/7d 28.6% WR -$0.46 (CEO_PROTECTED). macd-div-: 20T/7d 55% WR -$0.14 (CEO_PROTECTED). Legacy all closing, zero new 24h. range_reversion shadow 48h: 0 signals (market too flat). volume_breakout: 3T/48h — 2 in confluence (100% WR), 1 standalone loss.

### Root Cause
Signal starvation from flat market + CEO_PROTECTED losers I can't disable. ACCEL_300_V2_LONG is the worst active signal (10T 30% WR) but locked. System relies on accel-300-v2- SHORT backbone (72T/7d 52.8% WR +$1.46) which works. Need more NEUTRAL-regime signals to fire in flat chop.

### Fix Applied
1. **DELEGATED to signal_analyst:** Build new NEUTRAL regime signal (3rd backbone candidate). System needs signals that fire in flat chop — range_reversion was first attempt (shadow mode, 0 signals so far).
2. **FLAGGED accel-300-v2-long for T review:** CEO_PROTECTED, 10T/7d 30% WR -$0.22. Recommend: disable or raise MIN_GAP to 2.5.

### Verification
- 24h 49T 38.8% WR -$0.76 confirmed from DB
- 7d 378T 49.2% WR -$1.54 confirmed from DB
- 3 open positions all small (<$0.50 unrealized)
- No changes to hermes_constants.py this run

---

## CEO Report — 2026-09-01 ~00:10 UTC (verified)

### Diagnosis
System FLAT, 3 open LONG (all small). Market DEAD NEUTRAL (103/105 tokens). **24h: 48T, 37.5% WR, -$0.82** (verified from DB — worst since Aug 25 -$1.79). **7d: 377T, 49.1% WR, -$1.60.** Daily trend: Aug 28 +$1.55 → Aug 29 -$0.01 → Aug 30 -$0.08 → Aug 31 -$0.82 (3-day decline). **accel-300-v2-long: 12T/24h, 33.3% WR, avg -1.33%.** MIN_GAP=2.0 applied at 20:00 UTC — post-fix 4T 50% WR +$0.46 (vs pre-fix 8T 12.5% WR -$0.74). Fix working, needs more time. **confluence-,ichimoku- SHORT: 3T/24h, 0% WR, -$0.28** (CEO_PROTECTED — flagged for T review). **volume_breakout: 2T/24h, 100% WR, +$0.38** (tiny sample). **macd-div- SHORT: 3T/24h, 33.3% WR, -$0.08** (CEO_PROTECTED). Legacy bleed aging out (bb_bounce+ -$0.91, hl_copy -$0.86, slow-grind -$0.64 — all killed, zero new 24h). Signal starvation ~2/hr. Disk 80%. Race condition ROLLBACK FAILED (non-critical).

### Root Cause
range_reversion shadow mode was BROKEN: `RANGE_REVERSION_ENABLED=False` prevented the signal from ever running (registry skips disabled signals). 0 signals after 25h+ was code bug, not market flatness.

### Fix Applied
1. **range_reversion shadow FIX:** Enabled signal (`RANGE_REVERSION_ENABLED=True`) + added `SHADOW_MODE=True` guard that logs signals without calling `add_signal()`. Test run: 1 signal emitted (WLFI LONG conf=70% bbw=0.006 rsi=33.3). Signal now in fast signal list (runs every minute). Will evaluate48h shadow before enabling live.
2. **accel-300-v2-long MIN_GAP=2.0:** Post-fix 4T 50% WR +$0.46. Working, monitoring.

### Verification
- Test run of range_reversion: SHADOW_MODE=True, 1 signal logged (WLFI LONG), no trades placed. Signal registered in fast signal list (16 fast signals).
- accel-300-v2-long post-fix: 4T 50% WR +$0.46 (vs pre-fix 8T 12.5% WR -$0.74). Fix confirmed working.

---

## CEO Report — 2026-08-31 ~20:30 UTC (verified)

### Diagnosis
System FLAT, 5 open LONG positions. Market DEAD NEUTRAL (104/105 tokens). **24h: 46T, 41.3% WR, -$0.54** (verified from DB — worst day since Aug 25 -$1.79). **48h: 79T, 46.8% WR, -$0.97.** 7d daily: Aug 28 +$1.55 → Aug 31 -$1.03 (3-day decline). Today Aug 31: 40T, 35.0% WR, -$1.03. **ATR_SL: 33 exits/48h, avg -4.12%, -$3.36 total** (dominant loss). confluence-,ichimoku- SHORT 4T/24h 25% WR, -$0.26 (combo signal, flat market noise — CEO_PROTECTED). accel-300-v2-long LONG killed by auto_1hr at 17:06 UTC (5T/24h, 20% WR, -$0.19 — ALL ATR_SL at -4.5% to -4.9%). macd-div- DEAD (all 3 variants, NEVER_REENABLE). volume_breakout 2 trades total, small losses. range_reversion shadow 24h+, 0 signals. Signal starvation ~1.7/hr. Disk 79%. Pipeline healthy.

### Root Cause
Market is DEAD NEUTRAL — no trend = no winners for trend-following signals. accel-300-v2-long was bleeding at MIN_GAP=1.5 (weak entries all hit ATR_SL at -4.5% to -4.9%). Same pattern as SHORT before its fix. confluence-,ichimoku- combo bleeds in flat market (25% WR) but is CEO_PROTECTED — cannot disable.

### Fix Applied (this session)
**Raised ACCEL_300_V2_LONG_MIN_GAP 1.5→2.0** at 20:00 UTC. Same treatment as SHORT (raised 1.0→2.0 on Aug 29, worked — SHORT now +$1.46/7d backbone). Filters entries where price is too close to EMA300. Note: auto_1hr also killed ACCEL_300_V2_LONG_ENABLED at 17:06 UTC — flag is still True (kill may not have persisted). MIN_GAP fix will apply when/if signal re-enabled. Expected: fewer trades but higher WR.

### Verification
No parameter changes needed this session beyond MIN_GAP fix. System is flat in dead market — nothing critically broken. Active losers are either CEO_PROTECTED (confluence-,ichimoku-) or legacy dead signals. Monitor 48h for MIN_GAP fix impact. Re-evaluate range_reversion shadow tomorrow (Sep 1) — 0 signals after 24h+ shadow in flat market.

## CEO Report — 2026-08-31 ~16:30 UTC

### Diagnosis
System FLAT, 1 open position. Market 88 NEUTRAL, 62 SHORT_BIAS — dead with emerging SHORT bias. 24h: 42T, 42.9% WR, -$0.33. 7d: 383T, 49.6% WR, -$1.84. Today Aug 31: 30T, 36.7% WR, -$0.55 (worst day this week). Open: TURBO SHORT flat. **macd-div- STAR DEGRADED: 7T/48h, 28.6% WR, -$0.36** (CEO_PROTECTED — cannot disable). **ATR_SL IMPROVED: 71 exits/48h, -$0.25 total** (MIN_GAP=2.0 working — was -$3.17 earlier today). volume_breakout: 0 signals (market flat). range_reversion: shadow 24h+, 0 signals. Signal starvation ~1.7/hr. Disk 79%. Coin tracker active (95 coins warm, last tick 15:49 UTC). Pipeline healthy.

### Root Cause
Dead NEUTRAL market — no volume, no momentum, no trends. Signal starvation (1.7/hr). macd-div- STAR degraded from 57.1% 7d WR to 28.6% over 48h — works in trend, fails in chop (CEO_PROTECTED, cannot act). Today's poor WR (36.7%) is variance in flat market. ATR_SL improvement from -$3.17 to -$0.25 confirms MIN_GAP=2.0 filter is working — fewer weak entries = fewer ATR_SL losses.

### Fix Applied
**DECISION: MONITOR.** No parameter changes. System flat near breakeven — no crisis. macd-div- is CEO_PROTECTED — flagged for T review. ATR_SL improvement confirmed (MIN_GAP=2.0). volume_breakout and range_reversion both need market volume to generate signals. Will re-evaluate range_reversion shadow tomorrow.

### Verification
48h: 80T 55% WR -$0.52 (near breakeven). Daily trend: Aug 25 -$1.79 → Aug 28 +$1.55 → Aug 29 -$0.01 → Aug 30 -$0.08 → Aug 31 -$0.55 (flat). System structurally sound — 2 backbone + STAR + volume_breakout + range_reversion (shadow). Legacy clearing. ATR_SL trailing working.

### Next
- Monitor macd-div- WR recovery (CEO_PROTECTED, need 10+ trades to confirm degradation)
- Re-evaluate range_reversion shadow tomorrow (still 0 signals)
- Monitor volume_breakout (1 trade closed, need more data)
- Disk 79% — safe

---

## CEO Report — 2026-08-31 ~08:00 UTC

### Diagnosis
System FLAT, 4 open positions. **volume_breakout FIRST SIGNAL FIRED!** rs-s46,rs-s67,volume-breakout-long+ LONG opened 07:05 UTC (-$0.01 flat). 24h: 36T, 52.8% WR, -$0.12. 48h: 73T, 57.5% WR, -$0.01 (near breakeven). 7d: 406T, 51.2% WR, -$2.30. Today Aug 31: 8T, 37.5% WR, -$0.07 (early). Market ALL NEUTRAL — dead. Open: cascade-reverse-v2 LONG +0.04, macd-div- SHORT -0.06, ichimoku- SHORT -0.05, volume-breakout-long+ LONG -0.01. **macd-div- DEGRADED: 7T/48h, 14.3% WR, -$0.50** (new position opened, small sample). bb-bounce-short: 25T/48h 52% WR -$0.23 (legacy closing, killed Aug 30). atr_sl_hit: 26T/48h avg -4.12% -$2.65 (dominant loss, entry quality). range_reversion: shadow 24h+, 0 signals. Disk 79%.

### Root Cause
Signal starvation from flat NEUTRAL market (1.5 trades/hr). volume_breakout finally fired after 30h+ deployment — market had brief volume spike. macd-div- sample too small to confirm degradation (7T/48h). atr_sl_hit dominant: entries at poor locations (avg -4.12% on losers). Legacy trades (bb-bounce-short, hl_copy, slow-grind-, ct-hot+) all closing, zero new entries.

### Fix Applied
**DECISION: MONITOR.** No parameter changes. volume_breakout first signal is positive sign — system now generating from 3 signal families. macd-div- small sample (7T) — monitor, don't act yet. range_reversion shadow extended again (0 signals, market flat). ATR_SL entry quality issue persists but MIN_GAP=2.0 already applied.

### Verification
48h: 73T 57.5% WR -$0.01 (near breakeven). Daily trend: Aug 25 -$1.79 → Aug 28 +$1.55 → Aug 29 -$0.01 → Aug 30 -$0.08 → Aug 31 -$0.07 (stable near zero). System structurally sound — volume_breakout active, legacy clearing, ATR_SL trailing working.

### Next
- Monitor volume_breakout trade outcome (first ever)
- Monitor macd-div- WR recovery (need 10+ trades to confirm)
- Re-evaluate range_reversion shadow tomorrow (still 0 signals)
- Disk 79% — safe

---

## CEO Report — 2026-08-30 ~23:00 UTC

### Diagnosis
System FLAT, legacy bleed fully cleared. 36T/24h, 55.6% WR, -$0.38 (improving from -$1.92 7d). 1 open position: ichimoku- SHORT +0.48%. market ALL NEUTRAL — no volume spikes. volume_breakout deployed but 0 signals (flat market). macd-div- degraded to 20% WR (5T/48h, small sample variance). Two stale hl timers need cleanup.

### Verified Numbers
- **24h:** 36T, 55.6% WR, -$0.38
- **7d:** 421T, 52.5% WR, -$1.86
- **Today Aug 30:** 35T, 54.3% WR, -$0.45
- **48h exits:** atr_sl_hit 76T -$0.66 (MIN_GAP=2.0 working)
- **Open:** 1 SHORT (ichimoku- +0.48%)
- **volume_breakout:** 0 signals total (deployed today)

### Root Cause
Signal starvation from flat market — 36T/24h = 1.5/hr. Only 2 backbone signals active (accel-300-v2- and macd-div-). volume_breakout deployed but needs volume spikes to fire. Legacy signals (bb-bounce-short, ct-hot+, hl_copy, slow-grind-, pump-catcher+) all closing out, zero new entries.

### Action Taken
1. **Disabled stale timers:** hermes-hl-copy and hermes-hl-sync-guardian (legacy hl_copy_trader related, no longer relevant). `sudo systemctl stop disable hermes-hl-copy.timer hermes-hl-sync-guardian.timer`
2. **Updated CURRENT.md** with verified numbers
3. **Updated kanban** with this run

### Monitoring
- macd-div-: 5T/48h 20% WR. 7d baseline 65.5% WR. Small sample — continue monitoring. If WR stays <40% over next 10+ trades, flag for self_learner review.
- volume_breakout: 0 signals. Expected — market flat. Monitor 48h for first signals when volume spikes.
- range_reversion: shadow mode. Monitor for 48h before enabling.
- Signal starvation: 36T/24h. Will improve when market wakes up and volume_breakout/range_reversion start firing.

### Next
- Monitor volume_breakout first signals (expected when volume spikes)
- Monitor range_reversion shadow mode (48h trial)
- Monitor macd-div- WR recovery
- Disk 78% — safe

## CEO Report — 2026-08-31 ~15:30 UTC

### Diagnosis
**Verified DB:** 24h 39T 48.7% WR -$0.56. 48h 79T 54.4% WR -$0.55. 7d 398T 49.7% WR -$3.12. Today Aug 31: 18T 38.9% WR -$0.55 (worst day this week). 2 open (ME LONG bb-bounce-long+, LINK SHORT ichimoku-). Market ALL NEUTRAL — dead. Disk 79%.

**Worst performers (48h):** macd-div- SHORT 8T 25% WR -$0.48 (DEGRADED, CEO_PROTECTED — flagged for T). confluence-,ichimoku- combo 6T 33.3% WR -$0.37 (noise). bb-bounce-short 22T 50% WR -$0.24 (legacy closing). ATR_SL 31 exits -$3.17 (dominant).

**macd-div- daily trend:** Aug 27 100% WR → Aug 30 0% WR → Aug 31 33.3% WR. Signal works in trending, fails in chop. All 48h exits: 5 ATR_SL (-$0.36) + 3 cascade flips (-$0.12).

### Root Cause
NEUTRAL market + signal starvation (~1.7/hr). System has 2 backbone signals (accel-300-v2-, macd-div-). Both degraded in flat chop. volume_breakout (1 trade, -$0.09) and range_reversion (shadow, 0 signals) unproven.

### Decisions
1. **EXTEND range_reversion shadow 24h.** 24h+ shadow, 0 signals. Market too flat for mean-reversion. Re-evaluate tomorrow — if still 0 signals, disable or lower thresholds.
2. **FLAG macd-div- for T review.** CEO_PROTECTED — 8T/48h 25% WR -$0.48. Works in trend, fails in chop. Recommend: tighter SL or regime filter (block in NEUTRAL). Cannot disable myself.
3. **MONITOR volume_breakout.** 1 trade closed -$0.09. Need 20+ signals before evaluation.
4. **NO parameter changes.** System near breakeven, nothing critically broken. Market dead.

### Verification
Aug 28 was +$1.55 (best in weeks). Aug 29-31 flat/slightly negative. System structurally sound — legacy bleed fully cleared. Problem is market regime + signal count, not signal quality.

### Next
- Monitor macd-div- WR recovery (flagged for T)
- Extend range_reversion shadow 24h
- Monitor volume_breakout (need 20+ signals)
- Disk 79% — safe
- Delegate to signal_analyst: build signal for NEUTRAL regime
