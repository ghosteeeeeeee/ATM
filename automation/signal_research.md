# Signal Research — 2026-11-19 20:18 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1115 | 70.9% | +0.7616% | ✅ PASS |
| volume_breakout | 20 | 283 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 60 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=58.9%, 475 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=79.8%, 640 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
