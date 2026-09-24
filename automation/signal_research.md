# Signal Research — 2026-09-24 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1007 | 66.7% | +0.6825% | ✅ PASS |
| volume_breakout | 18 | 348 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 119 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.1%, 513 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=61.1%, 494 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
