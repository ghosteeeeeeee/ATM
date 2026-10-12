# Bug Hunter: grind-breakout-v2 Window Implementation

**Verdict: the current-bar-only / window implementation is NOT the cause of the MEGA miss. The actual `detect()` PASSES on MEGA's 12:50 bar and returns a signal. MEGA was never evaluated in production because `run()` skips it — first by a 61-day-stale price gate, and it is also on both blacklists.**

Tested by running the actual `detect()` code from `scripts/signals/grind_breakout_v2.py` against real candles from `/root/.hermes/data/candles.db` (`candles_5m`), replayed with an as-of cutoff at the 2026-10-11 12:50 UTC bar.

## Root Cause

`detect('MEGA')` on the 12:50 bar (replayed with `_get_candles` patched to `ts <= 2026-10-11 12:50`) returns:

```
{'direction': 'LONG', 'confidence': 85, 'value': 1.0251, 'price': 0.04435, 'z_score': 3.7165}
```

All 7 conditions PASS. The signal was suppressed **upstream of `detect()`** in `run()` (grind_breakout_v2.py:367-392):

1. **Staleness gate (line 369) — primary blocker.** `run()` does `if price_age_minutes(token) > 10: continue` before `detect()` is ever called. MEGA's row in `latest_prices` (`signals_hermes.db`) has `updated_at = 2026-08-11 13:33:47 UTC` — price 0.03451 while MEGA actually traded at 0.043–0.044 on Oct 11. `updated_at` only moves forward, so at Oct 11 12:50 the price age was already ~61 days ≫ 10 min → **MEGA was skipped before any condition was checked**.

2. **Blacklist (lines 385-388) — independent second blocker.** MEGA is in both `LONG_BLACKLIST` and `SHORT_BLACKLIST` since **2026-08-11** ("5 trades, 0% WR, -$0.23 — low-price noise coin, all ATR SL hits"). This predates the Oct 11 event, so even with a fresh price the LONG would have been dropped at the blacklist check.

Neither blocker has anything to do with BB windows, current-bar checks, or volume carryover.

## Trace

### Candle loading (a) — fine
- `lookback = BB_PERIOD(20) + COMPRESS_LOOKBACK(10) + 10 = 40`; 40 candles returned (oldest 09:35, current bar 12:50). BB(20) windows are fully populated. No lookback deficiency for this event.

### Compression window (b) — fine
- `compress_start = max(20, 39-10) = 29` → window bars 29–38 = 12:00–12:45. BB widths: 0.868, 0.806, 0.796, 0.781, 0.778, 0.765, 0.761, **0.694**, 0.737, 1.169 % — all < `BB_COMPRESS_MAX=3.0` → `compressed=True`. min BB in window = **0.694%**. The 11:40 compression the previous bug-hunter referenced is simply *extra* history; the actual min needed (12:35, 0.694%) is inside the window.

### Expansion (c) — fine
- Current BB (12:50) = **2.214%**; needed = 2.0 × 0.694 = 1.387%; actual multiple = **3.19x** (matches the previous bug-hunter's "3.2x") → PASS.

### Breakout (d) — fine
- Resistance = max high of the 20 bars before current = **0.043900**; current close = 0.044350 > 0.043900 → LONG breakout PASS. Move from range = 1.025% ≤ `MAX_MOVE_FROM_RANGE=3.0` → PASS.

### Volume (e) — fine
- vol_avg(20) = 325,404; current vol = 1,827,298 → ratio **5.62x** ≥ `VOL_SURGE_MULT=2.5` → PASS. (Note: this differs from the "VR=7.8x" in the premise; with the signal's own 20-bar average definition it is 5.6. Still passes.)

### Other conditions (f) — fine
- Body ratio: open 0.04383, close 0.04435, range 0.00066 → **0.788** ≥ 0.6 → PASS.
- Acceleration: `token_speeds` holds only current state (accel now = -0.0282, unrecoverable historically). Using the signal's own candle-fallback: **+0.4512** > ACCEL_MIN → PASS. (Caveat: the version live at 12:50 was commit `b3a39eb9` with `ACCEL_MIN=0.0` and `<=` comparison, reading `token_speeds`; if MEGA's runtime accel happened to be ≤ 0 at 12:50, that filter would have blocked it too — unverifiable, and moot since `detect()` was never called.)
- MACD hist rising (bonus only): 9.48e-05 > 4.56e-05.

### Bar-by-bar sweep (as-of replay, 12:30–13:30)
```
12:30 None   12:35 None   12:40 None   12:45 None
12:50 → {'LONG', conf 85, value 1.025, z 3.72}   ← ONLY bar that fires
12:55 None   13:00 None   13:05 None … 13:30 None
```
At 12:55 the 12:50 high (0.04442) enters the resistance window and close (0.04416) < resistance → no breakout. That is inherent breakout semantics, not a window bug — a volume-carryover change would not (and should not) make 12:55 fire.

### Production corroboration
- `pipeline.log` Oct 11: `grind_breakout_v2` was registered in the FAST signal list and ran **every minute** (ticks at 12:50:15, 12:51:05 …, "51 done, 0 errors"). The bar-12:50 close at 12:55 would have been seen by the 12:55–12:59 ticks. Cadence was not the problem.
- Signals DB: **zero** `grind*` signals on Oct 11. First grind signals are TRX LONG at 2026-10-12 02:40 / 03:13 (after the 22:59/23:03 accel fixes). TRX is fresh in `latest_prices` (updated 04:35 today) and not blacklisted — consistent with the root cause.
- No cooldown existed for MEGA on Oct 11 (current cooldown_tracker entries expired Apr 2026).

## Recommendation

**No fix needed to the window/current-bar-only implementation for this event** — it correctly identifies the 12:50 bar. The "volume surge doesn't carry over" concern is real in general but caused zero loss here: every condition converged on the 12:50 bar itself. Do not build a carryover mechanism on the premise of this example.

Fix the actual blockers instead:

1. **Staleness gate silently kills ~half the universe (systemic, high severity).** `run()` iterates all 182 tokens in `candles_5m`, but `latest_prices` actively tracks only ~87; **89 stale + 6 missing = 95 tokens are permanently invisible** to grind_breakout_v2 (and any signal using `price_age_minutes`). Candles are collected for MEGA (fresh through Oct 12 04:10) yet its price row froze at Aug 11. Recommended: in candle-driven signals, validate freshness against the token's **last closed candle ts** in `candles_5m` instead of `latest_prices` (the data the signal actually consumes), or sync `latest_prices` from the candle collector.
2. **MEGA is intentionally blacklisted** (0% WR, noise coin, since Aug 11). If the CEO wants MEGA trades, that's a constants change (per `hermes_constants.py` rules, ask first) — the signal never had a chance regardless of logic.
3. **Side observation (low severity):** the signal is single-bar ephemeral — the setup only fires while the exact convergence bar is the last closed bar (~5 min window). With the every-minute FAST runner this is fine, but if grind_breakout_v2 ever moves to the SLOW list (5-min cadence), alignment with bar closes becomes a real miss risk.

*Evidence: replay script used `_get_candles` patched with `ts <= cutoff` and the candle-fallback acceleration; all numbers above come from executing the real module functions, not hand calculation.*
