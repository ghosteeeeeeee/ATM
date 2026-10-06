# Signal Research — 2026-10-06 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 845 | 71.6% | +0.7847% | ✅ PASS |
| volume_breakout | 20 | 385 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 16 | 106 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.0%, 443 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=71.1%, 402 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
