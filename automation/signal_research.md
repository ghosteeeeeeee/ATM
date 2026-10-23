# Signal Research — 2026-10-23 04:06 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 898 | 69.9% | +0.7293% | ✅ PASS |
| volume_breakout | 20 | 338 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 106 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=67.9%, 448 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=72.0%, 450 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
