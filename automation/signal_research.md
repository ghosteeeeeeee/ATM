# Signal Research — 2026-10-27 16:06 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 976 | 70.0% | +0.7247% | ✅ PASS |
| volume_breakout | 20 | 350 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 101 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=65.1%, 461 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=74.4%, 515 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
