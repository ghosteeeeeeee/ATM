# Signal Research — 2026-11-04 15:21 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 976 | 72.6% | +0.8030% | ✅ PASS |
| volume_breakout | 20 | 334 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 92 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=67.1%, 432 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=77.0%, 544 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
