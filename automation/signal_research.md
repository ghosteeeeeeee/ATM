# Signal Research — 2026-09-27 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 959 | 70.1% | +0.7563% | ✅ PASS |
| volume_breakout | 18 | 364 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 129 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=75.0%, 511 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=64.5%, 448 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
