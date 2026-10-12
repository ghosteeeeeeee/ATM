# Signal Research — 2026-10-12 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 880 | 71.5% | +0.7708% | ✅ PASS |
| volume_breakout | 20 | 339 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 91 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.8%, 469 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=68.9%, 411 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
