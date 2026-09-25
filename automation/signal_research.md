# Signal Research — 2026-09-25 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 980 | 68.1% | +0.7099% | ✅ PASS |
| volume_breakout | 18 | 357 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 125 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.6%, 508 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=62.1%, 472 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
