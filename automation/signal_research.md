# Signal Research — 2026-09-22 05:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1028 | 66.8% | +0.6907% | ✅ PASS |
| volume_breakout | 18 | 327 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 110 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.3%, 509 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=61.5%, 519 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
