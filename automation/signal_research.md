# Signal Research — 2026-10-28 04:06 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 996 | 70.5% | +0.7381% | ✅ PASS |
| volume_breakout | 20 | 340 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 91 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=67.0%, 479 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=73.7%, 517 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
