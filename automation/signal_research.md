# Signal Research — 2026-11-17 08:18 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1073 | 71.3% | +0.7666% | ✅ PASS |
| volume_breakout | 20 | 299 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 20 | 65 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=59.3%, 462 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=80.4%, 611 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
