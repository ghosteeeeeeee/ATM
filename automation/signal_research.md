# Signal Research — 2026-09-30 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 868 | 70.0% | +0.7470% | ✅ PASS |
| volume_breakout | 19 | 392 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 128 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=71.8%, 471 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=68.0%, 397 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
