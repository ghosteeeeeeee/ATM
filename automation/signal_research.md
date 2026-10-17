# Signal Research — 2026-10-17 02:48 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 722 | 70.2% | +0.7596% | ✅ PASS |
| volume_breakout | 20 | 421 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 141 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.6%, 379 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=66.5%, 343 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
