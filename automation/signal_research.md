# Signal Research — 2026-09-12 17:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 19 | 1148 | 64.6% | +0.6380% | ✅ PASS |
| volume_breakout | 16 | 270 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 16 | 176 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=74.2%, 586 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
