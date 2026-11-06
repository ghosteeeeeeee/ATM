# Signal Research — 2026-11-06 15:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 958 | 71.9% | +0.7841% | ✅ PASS |
| volume_breakout | 20 | 343 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 97 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=66.8%, 419 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=75.9%, 539 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
