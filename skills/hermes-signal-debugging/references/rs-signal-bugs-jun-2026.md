# RS Signal Bugs Found (2026-06-14)

## Bug 1: Recency Scoring Inverted
**File:** `signals/rs.py` line ~389  
**Symptom:** Ancient touches receive boost multiplier, recent touches are diluted. Fresh support levels score lower than stale ones.  
**Formula before:** `recency_score = recency_touches + RS_RECENCY_BOOST_K * ancient_touches`  
**Formula after:** `recency_score = RS_RECENCY_BOOST_K * recency_touches + ancient_touches`  
**Each recent touch now counts as K ancient touches** — fresh levels correctly prioritized.

## Bug 2: Bounce Confirmation Dead Code
**File:** `signals/rs.py` `_bounce_confirmation()`  
**Symptom:** `open == close` on all synthesized candles (price_history is close-only). Condition (a) checking `close > open` / `close < open` can never be true.  
**Fix:** Removed dead condition (a) branches. Only follow-through path (b) remains: next candle must move >0.025% in direction of bounce.  
**Note:** Monitor WR impact — bounce confirmation is weaker than designed.

## Bug 3: scan_rs_signals Return Type Inconsistent
**File:** `signals/rs.py` `scan_rs_signals()`  
**Symptom:** Returns bare `0` (int) when `RS_ENABLED=False`, but caller unpacks as `(int, list[str])` → crash.  
**Fix:** Changed to `return 0, []`.

## Bug 4: RS_COOLDOWN_HOURS Never Applied
**File:** `signals/rs.py` — `RS_COOLDOWN_HOURS` imported, never used.  
**Symptom:** No per-token cooldown between RS signals of same direction.  
**Fix:** Added cooldown enforcement query against signal_history before `add_signal()`.

## Bug 5: add_signal Missing Params
**File:** `signals/rs.py` call to `add_signal()` at line ~815  
**Symptom:** `value`, `exchange`, `timeframe` not passed.  
**Fix:** Added all three params.
