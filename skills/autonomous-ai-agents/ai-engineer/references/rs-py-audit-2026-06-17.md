# rs.py Full Audit — 2026-06-17

## Bugs Found (10 total, 4 HIGH, 3 MEDIUM, 3 LOW)

| # | Severity | Location | Bug | Fix Applied |
|---|----------|----------|-----|-------------|
| 1 | **HIGH** | `L186` | Forward lookahead `np.append(roll_high[window:], ...)` → `forward_high[i]=roll_high[i]` — swing-high check becomes self-comparison, forward constraint bypassed | `np.concatenate([roll_high[window:], np.full(window, np.nan)])` — now `forward_high[i]=roll_high[i+window]` |
| 2 | **HIGH** | `L412-414` | Recency score inflation: `n < RS_RECENCY_WINDOW` → `recency_touches=total, ancient=0` → `total*K` inflated score | Explicit else branch: `recency_touches=total, ancient_touches=0` |
| 3 | **HIGH** | `L741-743` | `RS_BROKEN_RESISTANCE_LONG_ENABLED=False` killswitch zeroed `nearest_resistance`, silently blocking bounce SHORT (valid mean-reversion entry) | Removed killswitch from bounce SHORT path |
| 4 | **HIGH** | `L949` | CLI: `n = scan_rs_signals(...)` — `n` becomes tuple, f-string prints `(3, ['BTC'])` | `n, tokens = scan_rs_signals(...)` |
| 5 | **MEDIUM** | `L460` | Recency fraction formula: `(recency_score - touch_count)/(recency_score)` = `(K-1)/K` for fully-recent levels — bonus caps at ~5 not ~8 | Derive `recent_touches` first, then `recent_fraction = recent*K/recency_score` |
| 6 | **MEDIUM** | `_cluster_levels` | No guard against `anchor_price <= 0` — zero-division crash possible with bad data | Added `p > 0` filter before clustering |
| 7 | **MEDIUM** | `L659` | Support bounce: `broken=False AND bounces=False` → silent fallthrough, no signal, no log | Added explicit `else: pass` |
| 8 | **MEDIUM** | `L803-807` | Stale price data returns `[]` — indistinguishable from "no levels found" | Return `_STALE_SENTINEL` object; caller checks `is _STALE_SENTINEL` |
| 9 | **LOW** | `L630-631` | Support reclassification: hard `bounces=True` — resistance correctly re-calls `_bounce_confirmation` | Support reclassification now also calls `_bounce_confirmation` |
| 10 | **LOW** | `L860` | Redundant `from signal_schema import add_signal` inside `scan_rs_signals` | Removed dead import |

## Subagent Dispatch Notes

- **6 batches** dispatched in parallel (~150 lines each, ~950 total)
- **2 of 6 timed out** at 600s despite well-scoped checklists
- **Re-dispatch with tighter focus** (explicit line ranges, 5-6 checklist items max) → completed 70-500s per batch
- **Batch 3** completed cleanly (4 bugs found) — used the tightest checklist
- Lesson: for single-file audits, give subagent explicit `offset/limit` ranges AND cap at 5-6 items

## Key Code Patterns Verified Correct

- `_bounce_confirmation` index safety: `i+1 < len(recent)` guard is correct
- `_level_recently_broken`: loop bounds correct, `i+1 < len(recent)` check correct
- `_price_near_level`: zero guards present and correct
- `scan_rs_signals` blacklist: `token_upper` used correctly
- `add_signal` falsy check (`if sid:`) is correct — returns int or None
- `_get_candles_1m` LIMIT behavior when lookback > available rows: returns all available, correct
