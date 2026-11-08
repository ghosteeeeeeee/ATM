# Signal Research — 2026-11-08 03:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1013 | 72.5% | +0.7884% | ✅ PASS |
| volume_breakout | 20 | 313 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 74 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=64.6%, 435 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=78.4%, 578 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
