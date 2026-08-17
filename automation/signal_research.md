# Signal Research — 2026-08-17 17:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1948 | 0.0% | +0.0000% | ❌ FAIL |
| volume_breakout | 0 | 0 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 7 | 20 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- No candidates passed backtest criteria

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
