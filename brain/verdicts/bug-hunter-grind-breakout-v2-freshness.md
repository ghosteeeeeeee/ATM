# Bug Hunter: grind-breakout-v2 Freshness Gate Fix

**Commit:** fd09b02e — "fix: freshness gate — switch from latest_prices to candles_5m"
**Verified:** 2026-10-12 17:00–17:07 UTC (live DB, live pipeline, actual code executed)
**Verifier:** bug_hunter subagent

## Verdict: ISSUES FOUND

The gate **logic is correct** (units, skip paths, boundary handling all verified by execution),
but the **10-minute threshold is misaligned with how the candle pipeline actually keeps
`candles_5m` fresh**. Instead of expanding coverage (the fix's stated goal: 87 → 182 tokens),
the new gate **collapses scan coverage to 5–27 of 182 tokens** at any given moment — a net
loss of ~66–88 tokens vs the old gate. Root cause is upstream (candle lag), but shipping
this as-is delivers the opposite of the commit's intent.

## Issues Found

### 1. MEDIUM-HIGH — Threshold/cadence misalignment: coverage collapses instead of expanding
Measured live (samples every 45s, 17:02–17:06 UTC): new gate passes **5, 13, 13, 16, 13, 20, 27
of 182** tokens — oscillating with the 5m candle-close phase. Same-moment comparison at 17:06:22:
old gate 93 pass / new gate 27 pass; intersection only 12; **15 tokens gained** (the intended
blind-spot fix, e.g. POPCAT, RSR, RUNE, SNX...) but **81 tokens lost**.

Root cause — the candle pipeline's natural lag:
- `_aggregate_tf` (price_collector.py) only closes window W once `last_closed >= W+300`, i.e.
  **≥10 minutes after W started** (5–10 min after it ended), because the fill query's
  `bar_count >= 4` filter plus the per-token `last_closed_dict` scan-back skips W on the first
  pass. So a token's newest *closed* 5m candle is **always ~5–11+ min old**, sitting exactly on
  top of the 10-min gate threshold. Tokens flip pass→fail→pass every cycle, in lockstep.
- Additionally **89 of 182 tokens are blacklisted from the aggregator**
  (`skip = (LONG_BLACKLIST | SHORT_BLACKLIST) - BROAD_MARKET_TOKENS`); their candles refresh only
  via the slow seed (10 tokens/run, with its own "already fresh" skip). Measured: 76 blacklisted
  tokens >15 min stale, 6 aggregator-covered tokens (kBONK, kFLOKI, kLUNC, kNEIRO...) 49–54 min
  stale. MEGA: 37 min stale (blocked by new gate; blacklisted both directions anyway, no impact).

Net: pre-fix, grind_breakout_v2 scanned 93 tokens — but on data that was often >10 min stale
(the actual bug being fixed). Post-fix, it scans 5–27 tokens honestly. Neither is healthy; the
real defect is upstream candle freshness. The fix makes the blindness *visible*, but does not
achieve "182 tokens scanned."

### 2. LOW — Connection not closed on the exception path
`_freshness_conn` is closed only on the happy path (line 377). If `execute()`/`fetchone()`
raises, `except Exception: continue` fires **without closing** — verified empirically: connection
stays open after the exception path. In CPython the leak is self-healing (next loop iteration
rebinds the name → refcount 0 → dealloc closes it), and SQLite holds no inter-statement locks, so
real-world "database locked" risk is minimal. But it violates the codebase convention
("always close in `finally`" — AGENTS.md). Also: the loop opens **182 fresh connections per run,
every minute** (pipeline cadence); one pre-loop
`SELECT token, MAX(ts) FROM candles_5m WHERE is_closed=1 GROUP BY token` would replace all of them.

### 3. INFO — `import time as _time` inside the loop
Redundant: `time` is already imported at module top (line 33). Cost is negligible — measured
0.12 µs/iteration (sys.modules cache hit), ~22 µs per full run of 182 tokens. No functional or
performance impact. Style cleanup only.

### 4. UPSTREAM (pre-existing, surfaced by this verification) — candles_5m freshness lag
The aggregator's one-window-late closing means **no 5m-based signal with a 10-min freshness gate
can see most of the universe most of the time**. This affects every consumer of candles_5m with
freshness checks (coiled_spring, ma_cross_5m, bb_bounce_v3, trend_ride, r2_rev, ...). Also seen
in logs: one collector cycle reported "Collected 0 prices" (transient HL fetch miss), and the
slow-seed cursor grows unboundedly (214748/178 — harmless due to modulo, but untidy).

## Verification Checklist (executed, not assumed)

| # | Check | Result |
|---|-------|--------|
| 2 | Connection closed in all paths? | **NO** — exception path leaks until GC (Issue 2, LOW) |
| 3 | `import time as _time` in loop a problem? | **NO** — redundant but negligible (0.12 µs/iter; `time` already at module top) |
| 4 | `ts` is epoch seconds not ms? | **CONFIRMED** — INTEGER column; sample 1791824100 = 2026-10-12 16:55:00 UTC matches wall clock. Had it been ms, the gate would never skip stale tokens; empirically stale tokens DO get skipped. SAFE |
| 5 | Skips tokens with no candle data? | **YES** — synthetic tests: token with no rows → SKIP_NODATA; token with only `is_closed=0` candle → SKIP_NODATA |
| 6 | Skips stale candles (>10 min)? | **YES** — synthetic: 60-min-old → SKIP_STALE; 10.02-min-old → SKIP_STALE |
| 7 | Allows fresh candles (≤10 min)? | **YES** — synthetic: 5-min-old → PASS; 9.98-min-old → PASS (boundary correct) |

## Token Count Comparison

| Gate | Pass / 182 | Notes |
|------|-----------|-------|
| OLD (`price_age_minutes`, latest_prices) | **93** | Checks a table `detect()` never reads; let 81 stale-candle tokens through |
| NEW (candles_5m MAX ts, ≤10 min) — sampled 17:02 | **5** | Post-candle-close trough |
| NEW — sampled 17:03–17:05 | 13–16 | Oscillates with 5m close phase |
| NEW — sampled 17:06 | 20–27 | Peak of observed cycle |
| Gained vs old (intended fix) | +15 | POPCAT, PROVE, RSR, RUNE, S, SKR, SKY, SNX, SOPH, VIRTUAL... |
| Lost vs old | −81 | Every aggregator-covered token most of the time |

Universe: 182 distinct tokens in candles_5m (matches commit claim).

## Recommendation

**FIX FIRST** — keep the candles_5m-based gate logic (it is semantically correct: it checks the
table `detect()` actually consumes), but do not ship with a 10-min threshold as-is:

1. Raise the threshold to **15–16 min** (worst-case close lag ~11 min + margin) as a named
   constant in `hermes_constants.py` (no hardcoded numbers per house rule). This restores
   coverage to ~all 93 aggregator-covered tokens while still catching genuinely dead data.
2. Move the freshness query **before the loop** (single GROUP BY) and close the connection in a
   `finally` — removes both the per-token connection churn and the exception-path leak.
3. File an upstream ticket: fix `_aggregate_tf` to close the just-ended window in the same run
   (window-bounded `bar_count` filter), which would make even a 10-min gate pass ~all covered
   tokens. That is the root-cause fix ("no bandaids").

If the CEO prefers speed over coverage, shipping as-is is **safe for correctness** (it can only
skip tokens, never emit bad signals from stale data) — but expect grind_breakout_v2 signal volume
to drop dramatically, and understand the commit message's "42-token blind spot fixed" claim is
**not what the code delivers**: net scan coverage is ~66–88 tokens *smaller* than before.
