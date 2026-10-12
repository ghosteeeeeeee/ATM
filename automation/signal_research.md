# Signal Research — 2026-10-12 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 805 | 69.9% | +0.7503% | ✅ PASS |
| volume_breakout | 20 | 398 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 123 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.3%, 437 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=67.1%, 368 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
