# Signal Research — 2026-10-11 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 879 | 70.0% | +0.7339% | ✅ PASS |
| volume_breakout | 20 | 360 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 103 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.8%, 478 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=66.6%, 401 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
