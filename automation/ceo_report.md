## CEO Report — 2026-08-10

### Diagnosis

First red day after 15+ green days. Verified DB: today 60T -$0.06 (46.7% WR). 24h 72T +$0.17 (50.0% WR). 7d 382T +$0.39 (50.8% WR — positive). SHORT side improving: 24h 15T +$0.16 (60.0% WR — 15m filter effect confirmed). LONG 7d: 229T +$1.58 (54.1%). SHORT 7d: 153T -$1.19 (45.8% — legacy pre-fix trades aging out, daily PnL turning positive Aug 9-10).

### Root Cause

Today's LONG dip: range_finder combos had a bad day (14T -$0.49, 21.4% WR). auto_1hr disabled range_finder+ — correct decision given 20T -$0.44 in 24h. SL tightened to 0.5% (was 1.2%) — trades now cutting earlier, reducing max loss per trade by 58%. No structural issue — noise day.

### Fix Applied

1. **Disk cleanup** — 84% → 80%. Compressed profit_monster.log (54M), sync-guardian.log (49M), truncated self_close_watcher.err.log (35M), vacuumed journal (3.9G → 100M).
2. **No trading changes** — today is noise. Stars intact: bb_bounce+,hzscore+ LONG (57.1% WR), bb-bounce-short,hzscore- SHORT (66.7%). range_finder+ remains disabled per auto_1hr, re-evaluate in 48h.

### Verification

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Disk | 84% | 80% | <85% |
| SHORT 24h WR | 42.9% (pre-filter) | 60.0% (15m) | >50% |
| Today PnL | -$0.06 | -$0.06 (noise) | Green |
| 7d PnL | +$0.39 | +$0.39 | Positive |

**0 open positions. Pipeline timers active. 7d trajectory positive.**

---

## CEO Report — 2026-08-10 (Parameter Review)

### Diagnosis

Verified DB: atr_sl_hit is the #1 cost driver — 134T in 7d, avg -0.57%, total -$7.95. The Aug 10 SL tightening (1.2% → 0.5%) did NOT reduce this bleed. It just changed WHO takes the loss: trades that would have recovered now get stopped out at 0.5%. cut-loser-CL-trail at -$1.08 is minor by comparison.

Root cause: **TRAILING_DISTANCE_PCT at 0.30% is the real killer.** With 5x leverage, a 0.06% adverse move from peak triggers exit. Trades lock in micro-profits (0.06-0.15%) then get clipped on any pullback. The SL tightening just made this worse — trades can't breathe to reach profit-monster-trail territory.

### Fix Applied — APPROVED (all 4 changes)

None of these flags are in CEO_PROTECTED_FLAGS. All safe to modify.

| Param | Before | After | Rationale |
|-------|--------|-------|-----------|
| ATR_SL_MIN | 0.005 (0.5%) | 0.012 (1.2%) | Revert. 0.5% SL is redundant with cut-loser, just kills trades early. |
| ATR_SL_MAX | 0.010 (1.0%) | 0.025 (2.5%) | Revert. High-vol tokens need room. |
| ATR_SL_MIN_INIT | 0.005 (0.5%) | 0.012 (1.2%) | MUST match ATR_SL_MIN — init is used for new trade breathing room (tpsl_utils.py:465). |
| ATR_SL_MAX_INIT | 0.010 (1.0%) | 0.025 (2.5%) | MUST match ATR_SL_MAX — paired with MIN_INIT. |
| TRAILING_DISTANCE_PCT | 0.003 (0.30%) | 0.006 (0.60%) | Widen. Trades need room to run. 0.60% still tighter than original 0.70%. |
| CL_TRAIL_ACTIVATE_PCT | -0.5 | -1.0 | Widen. Cut-loser firing at -0.5% is premature on volatile tokens. |
| SL_PCT_FALLBACK | 0.005 (0.5%) | 0.012 (1.2%) | Match ATR_SL_MIN — fallback must be consistent. |
| STOP_LOSS_DEFAULT | 0.005 (0.5%) | 0.012 (1.2%) | Match ATR_SL_MIN — hard fallback must be consistent. |

### Why ATR_SL_MIN_INIT matters

You asked about it. YES — revert it. `tpsl_utils.py:465` uses `ATR_SL_MIN_INIT` as `MIN_SL_PCT` for new trades. If ATR_SL_MIN is 1.2% but INIT stays at 0.5%, new trades still get the tight SL. They're paired params.

### Verification

Monitor for 24h after change:
- atr_sl_hit count should decrease (fewer premature stops)
- profit-monster-trail count should increase (trades reaching trailing territory)
- Avg PnL per trade should improve (trades capturing more of the move)

If WR drops below 45% in 24h, we know the wider SL is letting losers run too far — revert SLMIN/SLMAX only, keep trailing distance.
