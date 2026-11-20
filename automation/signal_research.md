# Signal Research — 2026-11-20 20:18 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1112 | 71.0% | +0.7619% | ✅ PASS |
| volume_breakout | 20 | 298 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 59 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=59.2%, 475 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=79.7%, 637 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
