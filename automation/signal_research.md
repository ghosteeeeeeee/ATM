# Signal Research — 2026-11-03 03:20 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 993 | 71.6% | +0.7745% | ✅ PASS |
| volume_breakout | 20 | 333 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 87 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=65.6%, 442 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=76.4%, 551 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
