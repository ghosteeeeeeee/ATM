# Signal Research — 2026-11-14 03:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1076 | 72.3% | +0.7928% | ✅ PASS |
| volume_breakout | 20 | 286 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 63 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=59.5%, 454 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=81.7%, 622 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
