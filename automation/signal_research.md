# Signal Research — 2026-10-26 16:06 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 953 | 70.2% | +0.7332% | ✅ PASS |
| volume_breakout | 20 | 351 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 99 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=65.6%, 436 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=74.1%, 517 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
