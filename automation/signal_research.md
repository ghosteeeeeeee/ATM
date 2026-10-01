# Signal Research — 2026-10-01 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 894 | 69.1% | +0.7209% | ✅ PASS |
| volume_breakout | 17 | 359 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 15 | 120 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=74.1%, 487 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=63.1%, 407 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
