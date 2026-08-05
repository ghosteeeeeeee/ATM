# rs-s-broken post-fix analysis (2026-06-03)

## Session 2026-06-03 audit: patches verified clean

Five specific claims audited for the two patches (support broken lines 543-597, resistance broken lines 607-670):

### (1) No new bugs introduced
Both patches are internally consistent. The price-level comparison guards are correct:
- Support path (line 550): `price > level` → reclassify as active support. `price == level` falls through to original broken SHORT path (correct, level acts as resistance when exactly at it).
- Resistance path (line 614): `price < level` → reclassify as active resistance. `price == level` falls through to original broken LONG path (correct).

### (2) bounce=True override correctness for downstream schema
- The `'bounce'` field is written to the signal dict at lines 576 and 596, but `add_signal()` (line 767) only receives `{token, direction, signal_type, source, confidence}`. The `bounce` field is consumed only by `scan_rs_signals`'s print logger (line 780: `bounce={sig["bounce"]}`). **No schema conflict.**
- Override at line 552 (`bounces = True`) feeds `_compute_confidence(..., bounces=bounces, ...)` correctly, and the resulting confidence is what gets passed to `add_signal`.

### (3) bounces variable usage in resistance path
- `bounces` is set at line 603 via `_bounce_confirmation(candles, level, 'SHORT', ...)` — direction is `'SHORT'` (rejection/bounce downward).
- In the resistance broken path, a SHORT bounce is directionally coherent with the SHORT signal fired at line 651.
- When `price < level` redirects to `broken=False` (line 614-615), the `else` block (641-662) fires SHORT with `bounces` reflecting a downward rejection — semantically consistent.

### (4) Downstream source-field semantics
- `RS_SOURCE_PREFIX = 'rs'`. Sources: `'rs-s{N}'`, `'rs-r{N}'`, `'rs-s-broken'`, `'rs-r-broken'`.
- No callers parse `'-broken'` substring for logic. Source is passed to `add_signal` as a plain tag. Blacklist check in `signal_schema.py` uses exact match on source string, not substring.
- When support patch redirects `price > level` to `broken=False`, source becomes `'rs-s{touch_count}'` (not `'rs-s-broken'`) — correctly resets to normal LONG source.

### (5) Confidence/regime penalty consistency
| Path | Signal | Regime | Penalty | Correct? |
|------|--------|--------|---------|-----------|
| Support broken (554-577) | SHORT | LONG_BIAS+conf>50 | ×0.80 | ✓ counter-trend |
| Support non-broken (578-597) | LONG | SHORT_BIAS+conf>50 | ×0.80 | ✓ counter-trend |
| Resist broken (617-640) | LONG | SHORT_BIAS+conf>50 | ×0.80 | ✓ counter-trend |
| Resist non-broken (641-662) | SHORT | LONG_BIAS+conf>50 | ×0.80 | ✓ counter-trend |

**Comment drift: lines 558 and 622** have wrong regime names in their inline comments (`SHORT_BIAS` in support broken comment, `LONG_BIAS` in resistance broken comment). Code is correct — penalty conditions match the signal direction, not the comment text. Flag for doc cleanup but not a bug.

## Lesson
When auditing signal patches, trace the full call chain: `detect_rs_signal` → returned dict fields → `scan_rs_signals` → `add_signal`. Many dict fields (`bounce`, `level`, `atr_dist`, `recency_score`) are produced but only a subset reach `add_signal`. Confirm which fields are consumed where before flagging a field override as a potential conflict.

---

## Previous sessions

## Key finding: two different price DBs

**CRITICAL:** `signals/rs.py` uses TWO candle sources:
- `candles.db` (used in manual testing) — GALA last ts: 05-28, stale
- `signals_hermes.db` → `price_history` table — GALA last ts: 06-03 01:11, live

Always trace with `signals.rs._get_candles_1m()` which reads live `signals_hermes.db`, NOT `candles.db`.

Evidence:
```
candles.db GALA:  05-28 04:27: 0.003006  ← stale
signals_hermes.db GALA: 06-03 01:11: 0.002882  ← live
```

When candles are stale: near=False → no support found → `detect_rs_signal` returns `None` — BUT the function was returning `rs-s-broken` in prior sessions. This means prior sessions WERE reading from `signals_hermes.db` somehow, or the code path was different.

## Post-fix signal counts (runtime DB, last 6h)
```
rs-s[N]  normal LONG:  471 signals
rs-s-broken SHORT:   2764 signals
accel-300+:          102 signals (LONG)
accel-300-:          482 signals (SHORT)
Direction ratio: 85-93% SHORT across every hour — persistent market condition
```

## GALA trace (live price_history)
```
GALA price=0.002882, nearest support=0.002881 (0.035% away)
broken=True — 3 confirmed cross-downs with follow-through below
rs-s-broken SHORT fires correctly
```

## The fix is correct
Old logic: any candle closing below level = broken (single-cross trap for bounces)
New logic: must have cross candle + NEXT candle also closed below = confirmed break

Test results (7/7 pass):
- Bounce (dip then recover): broken=False → normal LONG path ✓
- Confirmed break (stays below): broken=True → rs-s-broken SHORT ✓
- No cross: broken=False ✓
- Single candle (no next): broken=False ✓

## Lesson
When debugging signal generation, always use `_get_candles_1m(token)` which reads the live `price_history` table in `signals_hermes.db`. Using `candles.db` directly gives stale data and produces wrong signal directions.