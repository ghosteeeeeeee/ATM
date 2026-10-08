# Signal Research — 2026-10-07 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 820 | 70.9% | +0.7660% | ✅ PASS |
| volume_breakout | 20 | 391 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 16 | 105 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=70.8%, 428 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=70.9%, 392 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
