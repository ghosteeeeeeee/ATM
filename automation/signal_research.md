# Signal Research — 2026-09-19 17:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1111 | 66.3% | +0.6691% | ✅ PASS |
| volume_breakout | 17 | 319 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 15 | 102 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.0%, 551 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=59.8%, 560 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
