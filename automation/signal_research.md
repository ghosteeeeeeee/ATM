# Signal Research — 2026-11-20 08:18 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1108 | 71.0% | +0.7637% | ✅ PASS |
| volume_breakout | 20 | 289 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 60 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=59.1%, 474 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=80.0%, 634 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
