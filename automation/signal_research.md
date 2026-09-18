# Signal Research — 2026-09-18 17:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1027 | 65.8% | +0.6808% | ✅ PASS |
| volume_breakout | 18 | 342 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 107 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=71.7%, 499 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=60.2%, 528 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
