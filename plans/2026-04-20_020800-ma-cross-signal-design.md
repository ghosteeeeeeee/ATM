# Plan: MA Cross Signal (10 EMA × 200 EMA on 1m)

## Status: COMPLETE

---

## What Was Built

### `scripts/ma_cross_signals.py` — Detection engine
- `detect_ma_cross(token, candles, price)` — pure detection, no guards
- `scan_ma_cross_signals(prices_dict)` — scanner (pre-filtered input), returns `(count, signaled_tokens_set)`
- Reads from `candles.db` directly (no Binance calls)
- Signal type: `ma_cross` | Sources: `ma-golden{N}`, `ma-death{N}`

### `scripts/run_ma_cross_signals.py` — Standalone runner
- Gets prices from candles.db, applies all guards, calls scanner
- Cooldown: 15 minutes per signaled token+direction

---

## Key Design Decisions

| Decision | Choice |
|----------|--------|
| Fast MA | EMA(10) |
| Slow MA | EMA(200) |
| Timeframe | 1m (aggregated from candles.db) |
| LONG trigger | 10 EMA crosses ABOVE 200 EMA (golden cross) |
| SHORT trigger | 10 EMA crosses BELOW 200 EMA (death cross) |
| Cooldown | 15 minutes |
| Confidence | 65 base + separation bonus + recency bonus (cap 88) |

## Confidence Scoring
```
base = 65
separation_bonus = min(|ema10 - ema200| / price * 100 * 3, 15)   # up to +15
recency_bonus = max(10 - bars_since_cross, 0)                   # up to +10
confidence = min(base + sep_bonus + recency_bonus, 88)
```

## Files Created
| File | Role |
|------|------|
| `scripts/ma_cross_signals.py` | Detection engine |
| `scripts/run_ma_cross_signals.py` | Standalone runner |
| `.hermes/plans/2026-04-20_020800-ma-cross-signal-design.md` | This plan |

## Bugs Fixed During Implementation

1. **Cross detection alignment** — `valid_ema10[j]` and `valid_ema200[j]` had different candle indices (EMA10 valid from idx 9, EMA200 from idx 199). Fixed by building aligned dicts by candle index and iterating over common indices only.

2. **Cooldown write-all bug** — `scan_rs_signals()` returned only count, not which tokens fired. Runner wrote cooldowns for ALL scanned tokens (165 instead of 42). Fixed both scanners to return `(count, signaled_tokens_set)`.

## Run
```bash
python3 /root/.hermes/scripts/run_ma_cross_signals.py
```

## Validation (2026-04-20)
```
40 signals emitted
Cooldowns written: 40 tokens × 15min (80 entries)
```
