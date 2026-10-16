# Signal Research — 2026-10-16 02:48 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 730 | 68.9% | +0.7232% | ✅ PASS |
| volume_breakout | 20 | 424 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 144 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=73.8%, 382 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=63.5%, 348 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
