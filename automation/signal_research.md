# Signal Research — 2026-10-02 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 885 | 70.6% | +0.7524% | ✅ PASS |
| volume_breakout | 17 | 351 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 15 | 106 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=74.6%, 480 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=65.9%, 405 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
