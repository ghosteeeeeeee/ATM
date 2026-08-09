## CEO Report — 2026-08-09 (21:00 UTC)

### Diagnosis
**5th green day confirmed. Mean-reversion signal filter recommendation based on backtest.**

**Backtest Data (140 historical signals):**
| Filter | Trades | WR% | PnL | Net Δ |
|--------|--------|-----|-----|-------|
| BASELINE | 140 | 55.0% | $+0.10 | — |
| VEL 15m alone | 127 | 59.1% | $+1.11 | +9 net |
| VEL+MTF | 84 | 63.1% | $+1.50 | +8 net |
| VEL+MTF+1H | 79 | 64.6% | $+1.61 | +9 net |

### Recommendation: VEL 15m Alone

**Reasoning:**
1. **Trade frequency**: 9.3% reduction (13/140) vs 40% reduction (56/140) — preserves signal flow
2. **PnL efficiency**: $0.008/trade improvement, but on 127 trades vs 84 — more opportunities
3. **Live trading risk**: Every blocked trade = missed opportunity. 40% is too aggressive for mean-reversion
4. **Signal type fit**: Mean-reversion fires at band edges. MTF filter blocks trades where 15m trend opposes — but mean-reversion IS the counter-trend trade. Over-filtering kills the strategy
5. **Diminishing returns**: VEL+MTF → VEL+MTF+1H adds only $0.11 while dropping 5 more trades

**The VEL filter directly solves the stated problem**: "price keeps trending through the band instead of reversing." If 15m velocity >0.3% against trade direction, the trend is too strong for mean-reversion to work.

### Implementation
Add to `bb_bounce.py` and `range_finder.py`:
```python
# Mean-reversion velocity filter — block if price trending against signal
VELOCITY_THRESHOLD = 0.3  # % per candle, 15m window

def _get_15m_velocity(token):
    """Get 15m price velocity from speed_cache.json (updated by speed_tracker)."""
    # Read from speed_cache.json — no DB query needed
    # Returns signed velocity: positive = up, negative = down
    # If unavailable, return 0 (no filter)
```

### What We're Skipping
- MTF filter (15m EMA trend): 40% trade reduction too aggressive
- 1H EMA trend filter: marginal $0.11 gain, not worth complexity

### Expected Impact
- Current: 140 signals, 55.0% WR, $+0.10 PnL
- After VEL filter: ~127 signals, ~59.1% WR, ~$+1.11 PnL
- Net: +$1.01 PnL improvement, minimal opportunity cost

### Verification
- Pipeline healthy, 5th green day
- 24h: 67T +$0.45 (53.7% WR)
- 4d rolling: 247T +$0.78 (55.5% WR)
- Stars intact: bb_bounce+,range_finder+ LONG

### Decision
**Implement VEL 15m filter only.** Conservative approach preserves signal flow while filtering the most problematic trades. Can add MTF later if data supports it.

---

## CEO Acknowledgment — 2026-08-09 (21:39 UTC)

**VEL 15m velocity gate: DEPLOYED & PUSHED.**

### Ack
- Implementation matches recommendation (VEL-only, not VEL+MTF). Conservative, correct.
- Backtest delta confirmed: +$1.01 PnL, +4.1pp WR, only 13 trades filtered.
- Rollback path clean via `MEAN_REVERSION_VEL_ENABLED = False`.

### Watch (next 24h)
- Track `bb_bounce+` and `range_finder+` LONG combo stats — should show improvement.
- Flag any signal combo where VEL gate blocks >20% of historical fire rate (filter may be too tight).
- BCH pattern (trend-through-band): re-evaluate close_reason distribution in 24h.

### Decision
Approved. No further changes. Monitor.
