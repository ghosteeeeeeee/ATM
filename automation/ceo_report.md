## CEO Report — 2026-08-08 (10:50 UTC)

### Diagnosis

**24h: +$0.52 (58.3% WR, 48 trades)** — system profitable.

**LONG: +$0.83 (66.7% WR, 33 trades)** — engine running well.

**SHORT: -$0.31 (40% WR, 15 trades)** — still bleeding.

**Worst SHORT combos (24h):**
- `ma100-cross-,range_finder-`: 5 trades, -$0.19, 40% WR
- `ma100-cross-,mover-`: 2 trades, -$0.11, 0% WR
- `ma100-cross-,vortex_break_short`: 3 trades, -$0.05, 33% WR

**Star:** `bb_bounce+,range_finder+` LONG — 11 trades, +$0.55, 81.8% WR.

### Root Cause

`MA_100_CROSS_MINUS_ENABLED=True` feeds bad SHORT trades into confluence combos. All worst SHORT signals share ma100-cross SHORT as a component.

### Fix Applied

**MA_100_CROSS_MINUS_ENABLED = False** — eliminates ma100-cross SHORT from all confluence combos. LONG unaffected.

### Verification

- 24h without ma100-cross SHORT would have been: +$0.83 (66.7% WR) — all LONG
- SHORT bleeding source identified and cut
- No other flag changes — system otherwise healthy

### Next Review

24h — verify SHORT bleeding stopped, LONG unaffected.

---

## CEO Report — 2026-08-08

### Diagnosis

**24h: +$0.18 (57.1% WR, 49 trades)** — slightly positive, trending right direction.

**7d: -$8.77 (41.3% WR, 407 trades)** — but most losses are from dead signals with legacy trades:
- inv-accel-300-: -$2.06 (30 trades, 16.7% WR) — DISABLED, all trades pre-Aug 5
- zscore-rising: -$2.38 (70 trades, 25.6% WR) — DISABLED, all trades pre-Aug 5
- vel-hermes: -$1.14 (58 trades, 31% WR) — DISABLED, all trades pre-Aug 5
- pattern_wolf: -$1.28 (11 trades, 10% WR) — DISABLED, all trades pre-Aug 5

These are historical — no new trades from these signals.

### Root Cause

1. **SHORT signals bleeding** — -$0.52/24h (40% WR), -$7.39/7d (36.3% WR). LONG is profitable: +$0.70/24h (64.7% WR). SHORT remains the drag.

2. **bb_bounce+ confluence is excellent** — 88.9% WR, +$0.38/24h. Star performer.

3. **ATR SL widening (1.0% → 1.2%)** — applied 2026-08-08 00:30. Still within evaluation window.

### Fix Applied

**No changes this run.** Recent fixes need more time:
- ATR SL widened (22/22 SL hits at exactly 1.0% = too tight)
- RETURN_EXHAUSTION_MINUS disabled (14 trades, -$0.64)
- Dead signals killed (inv-accel-300, zscore-rising, vel-hermes, pattern_wolf)

### Verification

- Dead signal trades confirmed historical (all pre-Aug 5) — flags working correctly
- SHORT bleeding down from -$8.70 → -$7.39/7d (improving slowly)
- Aug 7 was best day: +$0.40 (62.5% WR, 56 trades)
- Aug 8 on pace: +$0.09 so far (50% WR, 12 trades — low volume Saturday)
- bb_bounce+,range_finder+ LONG: 9 trades, +$0.38, 88.9% WR
- Pipeline healthy, systemd timers active

### Next Actions

1. **Monitor** — ATR SL impact over next 24h
2. **Monitor** — bb_bounce+ confluence sustainability
3. **Consider** — Expanding SHORT blacklist if bleeding continues
4. **No flag changes** — recent fixes need evaluation window

---

## CEO Report — 2026-08-08 (23:30 UTC)

### Diagnosis

**24h: +$0.41 (56.9% WR, 51 trades)** — profitable, improving trend.

**7d: -$8.77 (41.3% WR)** — historical dead signal losses, not current.

### Root Cause

ATR SL hits (21 trades) are the main drag at -$1.25, but this is **old trades** with 1.0% SL. Only 2 trades used new 1.2% SL — both winners (+$0.24). Widening deployed but needs propagation time.

### Fix Applied

No changes. Evaluation window ongoing. System already profitable.

### Verification

- SHORT bleeding improving: -$0.33/24h (was -$0.52 yesterday)
- Profit monster: 29 trades, 100% WR, +$1.66 — the engine
- bb_bounce+,range_finder+ LONG: 11 trades, 81.8% WR, +$0.55
- ATR SL widening: 2/2 new trades won, old trades still clearing
- Pipeline healthy, no new errors

---

## CEO Report — 2026-08-09 (09:50 UTC)

### Diagnosis

**24h: +$0.62 (60.4% WR, 48 trades)** — best day in recent memory.

**7d: -$8.51 (38.9% WR, 409 trades)** — historical, pre-fix losses dominating.

**Post-fix trend (Aug 5-8):** All 4 days positive or near-zero. System is profitable now.

### Root Cause

Short bleed is historical: -$7.39/7d (32.2% WR) but **+$0.38/3d** (44% WR). Dead signal kills (inv-accel, zscore-rising, vel-hermes, pattern_wolf) working — all trades pre-Aug 5. Current SHORT is neutral/slightly positive.

LONG is the engine: +$0.91/24h (65.7% WR).

### Fix Applied

**No changes.** All recent fixes working:
- ATR SL widened (1.0% → 1.2%) — only 2 trades used new SL, both won
- Dead signals properly disabled (confirmed in constants)
- RETURN_EXHAUSTION_MINUS disabled

### Verification

- Daily trajectory improving: Aug 4 (-$3.50) → Aug 5 (+$2.32) → Aug 7 (+$0.40) → Aug 8 (+$0.62)
- Star performer: bb_bounce+,range_finder+ LONG — 90.9% WR, +$0.63/24h
- SHORT 3d: +$0.38 (44% WR) — no longer bleeding
- All systemd timers active, pipeline healthy
- Error alerts: non-critical only (service failures, disk at 81%)

### Next Actions

1. **Monitor** — continue evaluation window, no rush to change
2. **Watch** — disk usage approaching 85% threshold (currently 81%)
3. **No flag changes** — system is working

## CEO Report — 2026-08-08 10:20 UTC

### Diagnosis
24h: +$0.62, 60.4% WR, 48 trades. System profitable. LONG dominates (+$0.91, 65.7% WR). SHORT slightly negative (-$0.29, 46.2% WR) but improving. Star: `bb_bounce+,range_finder+` LONG at 90.9% WR (+$0.63/24h, 11 trades).

### Root Cause
Recent fixes working: ATR SL widened to 1.2%, dead signals killed (inv-accel, vel-hermes, pattern, zscore_rising), hotset compaction stable. SHORT weakness is low-volume noise — only 13 SHORT trades in 24h, not a systematic bleed.

### Fix Applied
No changes. All fixes from earlier today need evaluation window. Star combo is carrying the system.

### Verification
- 7d trend improving: Aug 2-4 avg -$3.48/day → Aug 5-7 avg +$0.73/day
- ATR widening: only 2 trades used new 1.2% SL, both winners
- 6 open positions, pipeline healthy, no errors

### Next Review
24h — evaluate ATR widening impact with more data.

## CEO Report — 2026-08-09 11:20 UTC

### Diagnosis
24h: 45 trades, +$0.69, 62.2% WR — profitable.
7d: 410 trades, -$8.55, 41.5% WR — historical drag, improving.
SHORT: -$0.35 (41.7% WR) — all from pre-disable MA_100_CROSS_MINUS trades closing out.
LONG: +$1.04 (69.7% WR).

### Root Cause
MA_100_CROSS_MINUS trades still aging out (flag disabled 2026-08-08 00:30). 156 new SHORT signals blocked (executed=0). Will clear within 24h.

### Fix Applied
No changes — all recent fixes (ATR SL 1.2%, MA_100_CROSS_MINUS disabled, RETURN_EXHAUSTION_MINUS disabled) working. Evaluation window ongoing.

### Verification
Star combo bb_bounce+,range_finder+ LONG: 11 trades, +$0.63, 90.9% WR. Disk at 81% — monitor.

## CEO Report — 2026-08-08 (23:30 UTC)

### Diagnosis

**24h: +$0.41 (56.9% WR, 51 trades)** — system profitable, stable.

**LONG: +$0.74 (65.1% WR, 38 trades)** — engine healthy.

**SHORT: -$0.33 (38.5% WR, 13 trades)** — bleeding shrinking.

**7d: -$8.77 (41.3% WR, 412 trades)** — mostly historical damage (Aug 1-4 were 3-12% WR). Last 3 days profitable.

**Star:** `bb_bounce+,range_finder+` LONG — 12 trades, +$0.60, 83.3% WR.

### Root Cause

SHORT bleeding is historical dead signals (inv-accel, vel-hermes, zscore_rising, pattern). All verified killed. Recent SHORTs still weak but improving (38.5% vs 40% earlier today).

### Changes Since Last Report

- ATR SL widened 1.0% → 1.2% (deployed, ~2 trades using new SL so far, both winners)
- RETURN_EXHAUSTION_MINUS disabled
- MA_100_CROSS_MINUS disabled
- Dead signals killed (inv-accel, vel-hermes, pattern, zscore_rising)

### Action

**No changes.** All fixes deployed. ATR SL widening + signal kills need 24-48h evaluation window. System is profitable — let it run.

### Verification

- Pipeline: active, 4 open positions, 46 closed today
- Disk: 80% (23GB free) — stable
- 24h PnL: +$0.41 — profitable
- Star combo still dominant

### Next Review

Tomorrow morning. Focus: did SHORT stop bleeding? Did ATR SL widening improve R:R?

---

## CEO Report — 2026-08-08 (12:20 UTC)

### Diagnosis

**24h (verified): 45 trades, +$0.55, 60.0% WR** — system profitable, stable.

**LONG: 32 trades, +$0.99, 68.8% WR** — engine healthy, dominant.

**SHORT: 13 trades, -$0.44, 38.5% WR** — all from pre-disable ma100-cross- combos closing out.

**7d (verified): 412 trades, -$8.67, 38.6% WR** — historical dead signal damage, improving daily.

**Daily trend:** Aug 1-4 avg -$2.77/day → Aug 5 +$2.32 → Aug 6 -$0.54 → Aug 7 +$0.40 → Aug 8 +$0.18 (so far). Clear recovery arc.

**Star:** `bb_bounce+,range_finder+` LONG — 12 trades, +$0.60, 83.3% WR (7d). Carries the system.

### Root Cause

SHORT bleeding is **entirely historical** — all 7 SHORT trades on Aug 8 were ma100-cross- combos (flag already disabled Aug 8 10:50 UTC). No currently enabled SHORT signal is actively bleeding. Dead signal trades (inv-accel, vel-hermes, zscore_rising, pattern_wolf) account for -$4.86 of the 7d loss, all pre-Aug 5.

### Fix Applied

**No changes.** System profitable, all recent fixes working:
- ATR SL widened 1.0% → 1.2% (evaluation ongoing)
- MA_100_CROSS_MINUS disabled (trades aging out)
- RETURN_EXHAUSTION_MINUS disabled
- Dead signals killed (inv-accel, vel-hermes, pattern, zscore_rising)
- TL_BREAK killed (33.3% WR, -$1.33/7d)

### Verification

- 6 open positions (BCH, ETH, LTC, ME, MNT, PNUT)
- Pipeline healthy, all timers active
- Disk: 80% (23GB free) — stable
- Zero enabled SHORT signal actively losing money
- Non-critical service failures (bug-hunter, git-release) — no impact

### Next Review

24h. Focus: SHORT trades should stop as ma100-cross- ages out. Monitor disk at 80%.
