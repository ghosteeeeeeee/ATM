# Signal Research — 2026-10-09 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 805 | 68.9% | +0.7371% | ✅ PASS |
| volume_breakout | 19 | 397 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 121 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=69.7%, 416 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=68.1%, 389 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
