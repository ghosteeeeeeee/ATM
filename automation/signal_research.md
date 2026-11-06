# Signal Research — 2026-11-05 15:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 973 | 72.1% | +0.7906% | ✅ PASS |
| volume_breakout | 20 | 323 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 92 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=66.7%, 438 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=76.6%, 535 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
