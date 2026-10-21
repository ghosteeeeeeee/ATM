# Shadow-Mode SL Sweep Report

**Date:** 2026-10-21
**Author:** Hermes (CEO agent)
**Trigger:** T observed "we're getting stopped out too soon in chop"
**Data:** 1000 closed shadow signals

## TLDR

The current ATR SL (0.35% - 1.03%) is in the **WORST zone** — stops out 58-79% of trades. A 4.0% SL would produce **+195% total PnL vs -83% at 0.5%**. LONG signals benefit from wider SL (3-4%). Per-signal optimal SL varies.

## The Problem

T's actual closed trades show the pattern:

| Token | Dir | Entry | SL | SL% | Exit | 1h After |
|-------|-----|-------|-----|-----|------|----------|
| BTC | LONG | 84624 | 84324 | -0.35% | atr_sl_hit | -0.13% |
| SOL | LONG | 108.10 | 107.88 | -0.20% | atr_sl_hit | +0.07% |
| POL | LONG | 0.0969 | 0.0959 | -1.03% | hard_max_loss | -0.88% |
| NEO | LONG | 2.3006 | 2.2898 | -0.47% | atr_sl_hit | -0.20% |
| CFX | SHORT | 0.0559 | 0.0562 | -0.54% | atr_sl_hit | **+0.66%** |
| STX | LONG | 0.3736 | 0.3699 | -0.99% | hard_max_loss | **+1.37%** |

**STX** stopped out at -0.99%, then went **+1.37%** 1h later.
**CFX** stopped out at -0.54%, then **+0.66%** 1h later.

## SL Sweep Results (1000 signals)

| SL Level | WR | Stopped | Total PnL | Avg |
|----------|-----|---------|-----------|-----|
| **0.50%** | 19.9% | **79%** | **-83.13%** | -0.087% |
| 0.75% | 27.0% | 68% | -42.53% | -0.045% |
| 1.00% | 33.3% | 58% | +54.33% | +0.057% |
| 1.50% | 39.7% | 48% | +38.11% | +0.040% |
| 2.00% | 44.9% | 38% | +85.05% | +0.089% |
| 2.50% | 47.2% | 30% | +81.87% | +0.086% |
| 3.00% | 49.8% | 24% | +188.77% | +0.198% |
| **4.00%** | **51.0%** | **15%** | **+195.26%** | **+0.205%** |

**Key insight:** Current ATR SL range (0.35-1.03%) is in the WORST zone.

## Per-Signal Analysis — Optimal SL Varies

### pump-chain family

| Signal | n | Best SL | PnL |
|--------|---|---------|-----|
| **pump-chain+ (LONG)** | 88 | **4.00%** | **+142.06%** |
| **pump-chain+,pump-chain-v6+** | 70 | **3.00%** | **+107.83%** |
| **pump-chain-v6+** | 52 | **4.00%** | **+40.08%** |
| pump-chain- (SHORT) | 263 | 0.50% | -143.18% (loses at all levels) |

### continuum family

| Signal | n | Best SL | PnL |
|--------|---|---------|-----|
| **continuum+ (LONG)** | 95 | **4.00%** | **+8.77%** |
| **continuum-trend+ (LONG)** | 57 | **4.00%** | **+8.54%** |
| **continuum-osc+ (LONG)** | 51 | **4.00%** | **+10.39%** |
| continuum-osc- (SHORT) | 100 | 1.00% | -30.67% |

### Other signals

| Signal | n | Best SL | PnL |
|--------|---|---------|-----|
| bb-bounce | 342 | 1.50% | -0.002% (breakeven) |

## The Pattern

**LONG signals benefit from wider SL (3-4%).** SHORT signals are harder to profit from regardless of SL.

**Current ATR SL (0.35-1.03%) is in the WORST zone** — stops out 58-79% of trades before they have room to breathe.

## How to Run

```bash
# Global SL sweep
python3 scripts/shadow_trader.py --sweep-sl

# Per-signal SL sweep
python3 scripts/shadow_trader.py --sweep-sl --sweep-signal pump-chain
python3 scripts/shadow_trader.py --sweep-sl --sweep-signal bb_bounce

# Direction-specific
python3 scripts/shadow_trader.py --sweep-sl --sweep-dir LONG
```

## Recommendation

1. **Widen SL for LONG signals** — current 0.35-1.03% is too tight
2. **Per-signal SL optimization** — different signals have different optimal SL
3. **Test wider ranges** — up to 50% as T suggested
4. **Combine with exit engine optimization** — SL + trail + HML work together

## Related

- Shadow trader: `scripts/shadow_trader.py --sweep-sl`
- Exit engine analysis: `scripts/shadow_trader.py --analyze-exits`
- HML sweep: `scripts/shadow_trader.py --sweep-hml`
- Arm timeout sweep: `scripts/shadow_trader.py --sweep-arm`
