# Signal Research — 2026-09-15 05:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 19 | 1111 | 65.3% | +0.6610% | ✅ PASS |
| volume_breakout | 16 | 294 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 173 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.3%, 573 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=56.7%, 538 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
