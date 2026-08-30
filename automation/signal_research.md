# Signal Research — 2026-08-30 05:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1460 | 0.0% | +0.0000% | ❌ FAIL |
| volume_breakout | 17 | 101 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 16 | 102 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- No candidates passed backtest criteria

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
