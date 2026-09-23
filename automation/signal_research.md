# Signal Research — 2026-09-23 05:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1037 | 67.2% | +0.6979% | ✅ PASS |
| volume_breakout | 18 | 326 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 108 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.1%, 519 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=62.4%, 518 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
