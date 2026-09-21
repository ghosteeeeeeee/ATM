# Signal Research — 2026-09-21 05:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1031 | 66.7% | +0.6937% | ✅ PASS |
| volume_breakout | 18 | 320 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 109 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.5%, 505 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=61.2%, 526 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
