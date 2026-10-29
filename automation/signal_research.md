# Signal Research — 2026-10-29 03:20 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 945 | 70.6% | +0.7613% | ✅ PASS |
| volume_breakout | 20 | 359 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 93 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=69.0%, 448 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=72.0%, 497 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
