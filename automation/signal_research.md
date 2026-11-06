# Signal Research — 2026-11-06 03:58 UTC

## Hypotheses Tested

| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |
|---------|--------|--------|-----|---------|--------|
| bollinger_squeeze | 20 | 978 | 72.0% | +0.7865% | ✅ PASS |
| volume_breakout | 20 | 350 | 0.0% | +0.0000% | ❌ FAIL |
| consecutive_3_candles | 19 | 97 | 0.0% | +0.0000% | ❌ FAIL |

## Candidates Generated

- `bollinger_squeeze_long_candidate.py` — bollinger_squeeze LONG (WR=66.7%, 427 trades)
- `bollinger_squeeze_short_candidate.py` — bollinger_squeeze SHORT (WR=76.0%, 551 trades)

## Next Steps

1. Review candidate files in `scripts/signals/_candidates/`
2. Implement real-time detection logic in `run_signal()`
3. Run paper trading for 48h before enabling
4. If profitable, move to `scripts/signals/` and register
