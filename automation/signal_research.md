# Signal Research — 2026-09-30 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 897 | 70.1% | +0.7427% | ✅ PASS |
| volume_breakout | 17 | 357 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 15 | 127 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=74.4%, 480 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=65.2%, 417 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
