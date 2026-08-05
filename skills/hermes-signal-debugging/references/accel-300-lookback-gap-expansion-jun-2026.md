# accel-300 Signal Bugs — June 2026 Loss Cluster

## Session Context
- Date: 2026-06-07
- Problem: String of 24 losses (both LONG and SHORT), accel-300 firing on micro-gaps near EMA that immediately reverse
- Root cause: multiple logic bugs, not threshold tuning

---

## Bug 1 — ACCEL_300_LOOKBACK=35 Far Too Short (CRITICAL)

**Symptom:** Signals finding crosses 208-266 bars ago (4+ hours) via fallback search.

**Mechanism:** Primary search `range(i - ACCEL_300_LOOKBACK, i)` with LOOKBACK=35 misses crosses >35 bars ago. Fallback `range(i-1, -1, -1)` then finds the oldest bar where `gap_pcts[j] <= 0` — which can be 200-400 bars ago in quiet markets.

**Effect:** gap_at_cross ≈ 0% (ancient cross). With `MIN_GAP_EXPANSION=0.00`, any current gap >0 trivially passes the expansion gate. The gate becomes non-functional noise.

**Fix:** `ACCEL_300_LOOKBACK: 35 → 500` (at least 500 bars = ~8h for 1m)

---

## Bug 2 — MIN_GAP_EXPANSION=0.00 Gate Never Blocks

**Symptom:** Gap expansion check passes for all LONG signals regardless of whether momentum is actually building.

**Mechanism:** `gap_now (e.g., 1.55%) < gap_at_cross (-0.035%) + 0.00%` → always True since gap_at_cross ≈ 0% from ancient cross. The gate was intended to require "gap is growing vs the cross bar" but with an ancient cross at gap≈0%, any positive gap passes.

**Fix:** `ACCEL_300_MIN_GAP_EXPANSION: 0.00 → 0.05` (require 0.05% meaningful growth)

---

## Bug 3 — ACCEL_300_STALE_BARS=200 Defined But Never Used

**Symptom:** Constant exists in hermes_constants.py but is never referenced in accel_300.py.

**Mechanism:** Intended to block signals where `bars_since_cross > 200` (cross too old). Code removed this check in prior sessions but left the constant. Stale gate only checks gap decay ratio, not cross age.

**Effect:** Misleading dead code. bars_since_cross=999 in logs is cosmetic (sentinel when fallback used) but not the actual problem.

**Fix:** Either wire it up as blocking condition or remove from constants. Recommend: remove, since fallback cross_bar search is the correct behavior for sustained trends.

---

## Bug 4 — EMA(300) Unreliable on Limited Data

**Symptom:** When price_history has <350 bars for a token, EMA(300) has not converged.

**Mechanism:** EMA(300) on 185 bars = heavily recent-price-weighted approximation, not a true 300-period EMA. Gap calculations are unreliable.

**Effect:** Tokens with limited history get garbage gap values. Signal fires on noise.

**Fix:** Add minimum bars check in scan_accel_300_signals: skip tokens with <350 bars. Current check `len(prices) < PERIOD + LOOKBACK + PERSISTENCE_BARS + 5` = 300+35+4+5=344 — close but not quite enough for EMA convergence.

---

## Bug 5 — Stale Gate Skipped When Signal Fires at n-2

**Symptom:** Gap collapsing after signal bar but trade still taken.

**Mechanism:** Stale gate only runs when `i < newest_idx` (signal bar older than 2 bars ago). If signal fires at `i = n-2` (current bar), stale gate is skipped. Gap can collapse immediately post-signal without detection.

**Effect:** Signal fires at peak gap, price mean-reverts 2-4 bars later, SL hit.

**Fix:** Always check newest bar gap regardless of signal bar position. The stale gate's purpose (gap collapsing = signal stale) applies equally to signals at n-2.

---

## Recommended Constants (post-fix)

| Constant | Value | Note |
|---|---|---|
| `ACCEL_300_LOOKBACK` | 500 | Find recent cross, not 4h-old |
| `ACCEL_300_MIN_GAP_EXPANSION` | 0.05 | Require 0.05% gap growth |
| `ACCEL_300_PERSISTENCE_BARS` | 6 | Require 6 bars vs 4 |
| Minimum bars for scan | 350 | Skip unconverged EMA(300) |
| `ACCEL_300_STALE_BARS` | remove | Dead code, remove from constants |