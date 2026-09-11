# Signal Research — 2026-09-11 17:42 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 19 | 1184 | 64.9% | +0.6499% | ✅ PASS |
| volume_breakout | 16 | 251 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 16 | 171 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=74.3%, 595 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=55.5%, 589 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
