# Signal Research — 2026-10-10 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 790 | 70.5% | +0.7608% | ✅ PASS |
| volume_breakout | 20 | 390 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 122 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=71.6%, 423 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=69.2%, 367 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
