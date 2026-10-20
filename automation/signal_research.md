# Signal Research — 2026-10-20 16:06 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 883 | 69.5% | +0.7190% | ✅ PASS |
| volume_breakout | 20 | 336 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 101 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=67.2%, 445 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=71.9%, 438 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
