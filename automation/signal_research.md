# Signal Research — 2026-11-07 15:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 995 | 72.1% | +0.7863% | ✅ PASS |
| volume_breakout | 20 | 317 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 18 | 75 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=64.9%, 436 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=77.6%, 559 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
