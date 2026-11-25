# Signal Research — 2026-11-25 08:18 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 1035 | 70.4% | +0.7489% | ✅ PASS |
| volume_breakout | 20 | 324 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 62 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=58.0%, 464 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=80.6%, 571 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
