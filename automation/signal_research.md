# Signal Research — 2026-09-28 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 942 | 69.5% | +0.7430% | ✅ PASS |
| volume_breakout | 19 | 390 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 119 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.2%, 504 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=65.3%, 438 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
