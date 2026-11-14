# Signal Research — 2026-11-14 15:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1078 | 72.3% | +0.7902% | ✅ PASS |
| volume_breakout | 20 | 285 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 53 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=59.5%, 462 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=81.8%, 616 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
