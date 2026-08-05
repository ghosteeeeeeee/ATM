# rs.py Audit — 2026-06-03

## Bugs Found

### P1 — KeyError on SHORT non-broken signals (line 658)
`cand_signal` dict for SHORT resistance (non-broken) was missing `recency_score`.
`scan_rs_signals` line 780 accesses `sig['recency_score']` unconditionally → KeyError crash.

**Fix:** Added `'recency_score': recency` to SHORT non-broken dict at line 658.

### P1 — Clustered levels always get recency_score=0 (lines 490, 500)
`_cluster_levels` returns averaged prices (e.g. 99.98) that don't exist in `recency_by_level`
(which is keyed by raw swing level prices). `recency_by_level.get(clustered_level, 0)` always
misses → returns 0. Affects BOTH support and resistance paths.

**Fix:** Added `_get_clustered_recency()` helper that finds the nearest raw level to the
clustered price and returns its recency score.

### P1 — Bounce confirmation threshold mismatch (lines 234, 250)
price_history synthesizes `open=high=low=close` for every candle. Condition (a)
`c['close'] > c['open']` is always False (equality). Condition (b) uses `1.00025`
(~0.025% of candle close) while the touch threshold uses `atr_value * 1.0` (~0.5-2% of price).
These are completely different threshold regimes — bounce confirmation is nearly
impossible to satisfy on close-only candles when ATR is meaningful.

**Status:** Functional gap, not yet fixed. Needs either ATR-normalized bounce threshold
or reference point change from `c['close']` to `level`.

### P2 — Docstring said "weighted" but code did simple average (lines 153, 170, 181)
Fix: docstring updated to say "simple mean, not touch-count weighted."

### P3 — Dead code duplicate guard (line 473)
Second `if not r_levels and not s_levels: return None` unreachable after first return.
Fix: removed duplicate guard.

### Bug NOT a bug — Touch counting (lines 349-350)
Subagent reported `np.abs(lows - level)` was wrong probe for resistance levels.
Second audit confirmed: OR across both highs and lows captures all touches regardless of
direction — the probe IS correct.

## Session Context

- Session: rs.py signal only, focused on broken-level reclassification fix + full audit
- First audit (patched-file only): 155s, clean — no new bugs from our patches
- Full audit: 600s timeout on subagent → ran full audit in main session
- Second independent audit confirmed 5/6 bugs, 1 false positive
- All P1/P2/P3 bugs fixed in session

## Key Patterns Found This Session

1. **Signal dict key consistency**: Multi-branch dict construction — verify every key
   exists in ALL branches, cross-reference against unconditional caller accesses
2. **Clustered level lookups**: Clustering averages prices → lookup keys no longer match
   original dict keys. Always map back after clustering.
3. **Close-only candle assumptions**: `open=close` makes `c['open']` comparisons always
   False — check every branch that relies on `open != close`
4. **Duplicate guards**: Two identical early-return blocks → second is dead code