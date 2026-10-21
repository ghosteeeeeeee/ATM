# Signal Research — 2026-10-21 04:06 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 776 | 70.6% | +0.7695% | ✅ PASS |
| volume_breakout | 20 | 401 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 111 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=71.0%, 379 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=70.3%, 397 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
