# Signal Performance Report
**Generated:** 2026-08-23 23:15 UTC | **Period:** Last 6h + 24h

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| macd-div+ | LONG | 3 | 33.3% | -$0.19 |
| ct-hot+ | LONG | 8 | 37.5% | +$0.13 |

## 24h Performance
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| macd-div+ | LONG | 5 | 20.0% | -$0.55 | KILLED (CEO, residual trades) |
| hzscore- | SHORT | 8 | 37.5% | -$0.35 | KILLED (this report) |
| ct-hot+ | LONG | 23 | 47.8% | +$0.31 | Active — marginal |
| hl_copy_trader | LONG | 10 | 50.0% | +$0.50 | Active — best performer |

---

## KILLED (executed this cycle)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| hzscore- | SHORT | 37.5% | -$0.35 | 8 | `HZSCORE_MINUS_ENABLED = False` + NEVER_REENABLE. Auto-rotation failed, avg loser 2x avg winner. |

**Note:** `macd-div+` was killed by CEO earlier today (2026-08-23 20:33 UTC). 5 residual trades were in progress at time of kill. Flag confirmed `= False`.

---

## BOOSTED
None. No signal meets boost criteria (WR > 55%, 5+ trades, multi-token consistency).

---

## WATCH LIST
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 47.8% | +$0.31 | 23 | Marginal — WR below 50%, monitor |
| hl_copy_trader | LONG | 50.0% | +$0.50 | 10 | Best performer, but WR exactly 50% |
| ct-hot- | SHORT | 0% | -$0.15 | 2 | Too few trades, watch |
| ct-hot-,tl_break_short combo | SHORT | 0% | -$0.23 | 2 | Too few trades, watch |

---

## SIGNAL INVERSIONS
**None found.** All signals respect their direction labels.

---

## ISSUES
- `hzscore-` was auto-rotated today (re-enabled 2026-08-22 for "signal starvation") but immediately started losing. Signal starvation argument invalid — 55T/24h total volume. Now permanently killed.
- `macd-div+` trades continued for ~5 hours after kill flag was set. Expected — trades already in progress close normally.

---

## ACTION SUMMARY
1. **Killed** `hzscore-` SHORT — set `HZSCORE_MINUS_ENABLED = False`, added to `NEVER_REENABLE_FLAGS`
2. **Verified** `macd-div+` kill — flag already `= False`, residual trades expected
3. **No boosts** — no signal meets WR > 55% threshold
4. **No inversions** detected

*Next report: ~6h from now.*
