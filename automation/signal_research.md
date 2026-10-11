# Signal Research — 2026-10-11 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 852 | 71.2% | +0.7790% | ✅ PASS |
| volume_breakout | 20 | 365 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 103 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=72.9%, 458 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=69.3%, 394 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
