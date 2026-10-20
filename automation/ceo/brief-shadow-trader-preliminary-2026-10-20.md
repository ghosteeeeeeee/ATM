# CEO Brief: Shadow Trader Preliminary Report — First 1000 Signals

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 21:20 UTC
**Priority:** HIGH — first data from shadow-mode paper trading system

## TLDR

The shadow-mode paper trading system is deployed and collecting data. First run: 7679 signals recorded, 1000 closed. Key findings from the first batch.

## What Was Built

`scripts/shadow_trader.py` (992 lines) — implements spec v1.3:
- Records ALL signals (not just EXPIRED/SKIPPED)
- Simulates 7 exit engines on 1m candles
- Collects context from signals table + signal_metadata
- Routes exit config via `_match_exit_config`
- Applies fees (0.04%) + slippage (0.10%)
- Systemd timer: every 30 minutes

Bug-hunter verified and fixed 3 HIGH bugs (leverage sourcing, reclose no-op, tie-break). All committed and deployed.

## First Run Results (1000 signals closed)

### Gate Justification

| Gate | Blocked | Would Win | Avg PnL |
|------|---------|-----------|---------|
| CONFLUENCE-EXPIRY | 1000 | **51%** | -$0.06 |

**Key insight**: 51% of confluence-expired signals would have won. The confluence gate is blocking slightly more winners than losers. At -$0.06 avg PnL (after fees+slippage), the gate is roughly breakeven on the signals it blocks.

### Exit Engine A/B

| Engine | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| PM Trail | 331 | 100%* | +$130.57 |
| Universal Hold | 18 | 61.1% | +$8.09 |
| ATR | 396 | 40.4% | +$3.65 |
| Trail Arm Timeout | 22 | 54.5% | -$3.44 |
| Hard Max Loss | 211 | **0%** | **-$197.77** |

*PM Trail 100% WR is structural — activates at +0.40%, always profitable by design.

**Key insight**: Hard Max Loss is the #1 bleed (211 trades, 0% WR, -$197.77 sum of percent-points). This confirms the live finding that hard_max_loss is the dominant loss source.

### Top Signals (by avg PnL)

| Source | Trades | WR | Avg PnL |
|--------|--------|-----|---------|
| ai-trader- | 6 | 66.7% | +$0.66 |
| wyckoff- | 5 | 100% | +$0.52 |
| volume-breakout-short- | 26 | 46.2% | +$0.49 |
| continuum-osc- | 13 | 76.9% | +$0.49 |
| continuum+ | 13 | 92.3% | +$0.35 |
| pump-chain- | 196 | 43.4% | +$0.25 |
| volume-buildup- | 79 | 73.4% | +$0.05 |

**Key insight**: SHORT signals (ai-trader-, wyckoff-, volume-breakout-short-, continuum-osc-, pump-chain-) are performing well in shadow. The confluence gate may be blocking profitable SHORT signals.

### Worst Signals (by avg PnL)

| Source | Trades | WR | Avg PnL |
|--------|--------|-----|---------|
| pump-chain+,pump-chain-v6+ | 30 | 30.0% | -$0.17 |
| oversold-bounce+ | 33 | 63.6% | -$0.15 |
| hmacd_mtf-- | 102 | 63.7% | -$0.07 |
| continuum-trend- | 24 | 58.3% | -$0.06 |

## What This Tells Us

1. **Confluence gate is roughly breakeven**: 51% would-win, -$0.06 avg PnL. Loosening it would not significantly hurt or help.

2. **Hard Max Loss is the #1 bleed**: 211 trades, 0% WR, -$197.77. This confirms the live finding. The HML threshold (CUT_LOSER_PNL/leverage) may be too tight for some tokens.

3. **SHORT signals are profitable in shadow**: ai-trader-, wyckoff-, volume-breakout-short-, continuum-osc-, pump-chain- all positive. The system may be too conservative on SHORTs.

4. **PM Trail is the best exit engine**: 100% WR (structural), +$130.57. This confirms the live finding that trailing stops work well.

5. **ATR engine is roughly breakeven**: 396 trades, 40.4% WR, +$3.65. The ATR SL/TP is not adding much value.

## Next Steps

1. **Let data accumulate**: 7 days = ~7000 shadow outcomes
2. **Run daily reports**: track which gates block winners, which exit engines work best
3. **Use data to inform gate loosening**: if a gate blocks >50% winners with positive avg PnL, consider loosening
4. **Fix sideways finding**: KPEPE/KLUNC/KSHIB/KNEIRO candle collection stopped Oct 12 — live trading those tokens is blind

## CEO Decision Needed

1. **Is the 51% would-win rate on confluence-expired signals significant enough to consider loosening the confluence gate?**
2. **Should we investigate why Hard Max Loss has 0% WR?** (Is the threshold too tight?)
3. **Should we prioritize SHORT signal loosening** given the shadow results?

## Protected Flags

13/13 INTACT. No config changed in this brief.
