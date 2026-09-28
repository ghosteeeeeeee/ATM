# Signal Research — 2026-09-28 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 971 | 68.6% | +0.7054% | ✅ PASS |
| volume_breakout | 18 | 379 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 16 | 107 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=71.8%, 525 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=64.8%, 446 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
