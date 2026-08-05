# Signal Logic Fix Log

Session-anchored reference for non-obvious signal logic bugs that were found and fixed.
Each entry: symptom → root cause → fix. Not a general troubleshooting guide.

---

## accel_300.py — returns oldest qualifying bar instead of most recent

**Symptom:** accel_300 fires signals with stale price timestamps; signal fires for a setup from hours ago even when recent bars also qualify.

**Root Cause:** Detection loop scans forward over ~370 historical bars and uses `return` on the FIRST qualifying bar found. All subsequent (more recent) bars are never evaluated. The signal carries the oldest bar's price and gap values.

**Fix (2026-06-14):**
- Changed loop from early-`return` to tracking `signal_bar` state variable
- After the full scan, return the last (most recent) qualifying bar
- Added `ACCEL_300_STALE_LOOKBACK = 400` as absolute backstop gate
- Code: loop saves state per qualifying bar and `break`s, rather than immediate `return`

**Key pattern:** When a signal fires but the price/gap values don't match the current market, suspect the loop returns on the first match instead of the last.

---

## rs.py — recency formula inverted (ancient weighted more than recent)

**Symptom:** Levels touched recently do not win the selection over ancient levels, despite "recent touches count more" being the stated intent.

**Root Cause (code):**
```python
recency_score = RS_RECENCY_BOOST_K * recency_touches + ancient_touches
# K * recent + ancient → recent is multiplied, ancient is not
# → ancient touches receive the K multiplier, weighted MORE
```

**Root Cause (spec + comment):** The spec prose says "recent touches count more" but the literal formula `recent + K×ancient` has the same inversion as the code. Both were wrong.

**Fix (2026-06-14):**
```python
recency_score = recency_touches * RS_RECENCY_BOOST_K + ancient_touches
# recent × K + ancient → recent is multiplied, weighted MORE
```

**Also fixed:**
- Level selection: was `dist_pct < best_support_dist` (distance primary), recency secondary
- Now: `recency > best_recency` (recency primary), distance as tiebreaker
- Bounce confirmation: was optional bonus, now hard gate (`if not bounces: skip level`)
- `RS_TOUCH_HARD_CAP`: was `if RS_TOUCH_HARD_CAP and ...` — bypassed when 0/None; changed to `is not None` check

**Key pattern:** When a scoring/selection formula seems backwards, check if the operator precedence is grouping what you expect. `K * recent + ancient` groups as `(K * recent) + ancient` — not as `K * (recent + ancient)`.
