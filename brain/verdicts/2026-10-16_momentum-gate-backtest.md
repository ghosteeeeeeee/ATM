# Momentum-Gate Backtest Verdict — 2026-10-16 (brain_auditor, 1 day early vs Oct 17 deadline)

**Verdict: FAIL — do NOT ship. Pre-entry 5m momentum does not separate trail winners from chop losers.**

## Hypothesis (as commissioned)

Block entries where |5m candle momentum before entry| < 0.15% — chop entries have no momentum, trending entries do. Would reduce hard_max_loss #1 bleed (7d 59T −$5.44, 0% WR).

## Method

- 768 closed trades, 30d, PG brain (all had candles_5m data, 0 missing).
- Momentum = abs % change of last completed 5m candle close before `open_time` (candles.db `candles_5m`).
- Families: TRAIL = profit-monster-trail/atr_trail_hit/trail_sl/stale_exit/UNIVERSAL_MAX_HOLD; CHOP = hard_max_loss/atr_sl_hit/hard_sl/cut-loser-CL-T1.

## Results

### Family separation (30d) — THE hypothesis is false

| Family | n | WR | PnL | avg |mom5| |
|--------|---|-----|------|----------------|
| TRAIL | 290 | 79.0% | +$21.66 | **0.270%** |
| CHOP | 410 | 19.3% | −$28.71 | **0.259%** |
| OTHER | 68 | 45.6% | +$3.83 | 0.220% |

Delta avgM TRAIL−CHOP = **+0.007pp — indistinguishable.** Entry momentum is the same; the difference shows up post-entry (MFE), which the trail-arm engine already captures.

### Threshold sweep T=0.15 (block |mom5|<T), all 30d

- Blocked n=365 (43.0% WR, −$2.54) | Kept n=403 (45.2% WR, −$0.68)
- **Winner-block rate 46.3%** — 3.5× over the 20% max-kill bar. Non-starter.
- Net-if-blocked +$2.54/30d — tiny, and bought by killing nearly half of all winners.
- Sweep non-monotonic (T=0.20→+$0.15, T=0.25→+$0.97, T=0.30→+$2.59) = noise signature, not an edge.

### OOS (T=0.15)

| Window | blocked | kept | winner-block | NET if blocked |
|--------|---------|------|--------------|----------------|
| 7d | 102 (36.3%WR −$0.62) | 117 (36.8%WR −$0.65) | 46.2% | +$0.62 |
| 14d | 176 (41.5%WR −$2.14) | 197 (41.6%WR +$0.41) | 47.1% | +$2.14 |
| 30d | 365 (43.0%WR −$2.54) | 403 (45.2%WR −$0.68) | 46.3% | +$2.54 |

### Per-signal spot checks — no clean pocket

| Signal | TRAIL avgM | CHOP avgM | delta | winner-block @0.15 | NET if blocked |
|--------|-----------|-----------|-------|--------------------|----------------|
| pump-chain± | 0.324% | 0.317% | +0.007 | 25% | +$1.75 |
| bb-squeeze± | 0.433% | 0.268% | +0.165 | 31% | +$0.52 |
| bb-bounce-v2-long+ | 0.171% | 0.203% | **−0.032** | **69%** | **−$0.17** |
| doji-bottom+ | 0.186% | 0.122% | +0.064 | 47% | −$0.18 |
| ai-trader+ | 0.207% | 0.209% | −0.002 | 22% | +$0.46 |

bb-bounce-v2-long+ and doji are net-NEGATIVE if gated. Only pump-chain± shows +$1.75/30d but at 25% winner-block (above bar) and delta +0.007pp (no separation) — a coincidence cohort, not a mechanism.

## Conclusion

1. **Do not ship any |mom5| entry gate** — fails separation, winner-block, and monotonicity checks.
2. The chop-vs-trend edge lives **post-entry** (MFE/arm-rate), not pre-entry candle momentum. The trail engine + trail_arm_timeout already harvest it.
3. The hard_max_loss bleed (#1, 7d −$9.97 chop family) is an **exit-magnitude problem** (losers ride to −3% account), not an entry-momentum problem. Lever = progressive exit ladder / early no-progress cut — but must carry a home-run-kill guard (dead_money lesson: 116/147 pump-chain+ trades are below +2% at 2h and that IS the grind).
4. Existing entry-quality fixes (RSI bands, SHORT midband 45-55, pump-chain dead-gap, bb-bounce EXTREME block) remain the correct entry-side family. All in soak.

**Confidence: HIGH** (n=768, 3 OOS windows, per-signal checks, full sweep).
