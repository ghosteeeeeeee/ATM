# Signal Research — 2026-10-13 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 936 | 71.4% | +0.7664% | ✅ PASS |
| volume_breakout | 20 | 343 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 15 | 97 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.2%, 497 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=69.2%, 439 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
