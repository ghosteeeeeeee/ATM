# Signal Research — 2026-09-29 17:43 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 926 | 71.2% | +0.7797% | ✅ PASS |
| volume_breakout | 19 | 364 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 17 | 105 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=74.3%, 502 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=67.5%, 424 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
