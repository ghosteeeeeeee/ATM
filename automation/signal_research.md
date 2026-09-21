# Signal Research — 2026-09-20 17:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 19 | 1067 | 66.4% | +0.6769% | ✅ PASS |
| volume_breakout | 15 | 273 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 170 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.2%, 533 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=59.6%, 534 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
