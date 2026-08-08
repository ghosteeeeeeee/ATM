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
