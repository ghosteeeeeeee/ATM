# Signal Research — 2026-10-10 05:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 851 | 69.8% | +0.7389% | ✅ PASS |
| volume_breakout | 20 | 394 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 117 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=69.6%, 450 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=70.1%, 401 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
