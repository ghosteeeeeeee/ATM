=== Signal Performance Report ===
Generated: 2026-10-18 09:33 UTC
Period: Last 6h | 24h (context: 72h)

Volume note: only 12 closed trades in 24h — thin data, no kill/boost thresholds met.

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met kill criteria (WR<30% + 5+ trades + PnL<-$0.10, 24h) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met boost criteria (WR>55% + 5+ trades + PnL>$0.05, 24h) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 33.3% | -$0.07 | 3 (24h) | WATCH — below WR target, low volume; recheck next cycle |
| doji-bottom-long | LONG | 45.5% | -$0.51 | 11 (72h) | WATCH — 72h loser, only 0-2 trades in 24h window |
| pump-chain- | SHORT | 0.0% | -$0.49 | 8 (72h) | WATCH — 0% WR over 72h; only 1 combo trade in 24h |
| bb-bounce-v2-long+ | LONG | 28.6% | -$0.36 | 7 (72h) | WATCH — below WR target on 72h; 1 trade in 24h |
| ai-trader+ | LONG | 50.0% | -$0.37 | 10 (72h) | WATCH — breakeven WR, negative PnL (slippage/RR) |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain-,pump-chain-v6- | SHORT | 100% | +$0.47 | 1 (24h) | OK — single trade, no boost on n=1 |
| volume-buildup- | SHORT | 75.0% | -$0.03 | 4 (72h) | OK — high WR, costs eating edge; watch |

ISSUES:
- No direction inversions in last 24h (0 found) — signal naming intact.
- Very low trade volume (12 closed in 24h vs typical) — likely regime/throttle; no action.
- 72h losers (doji-bottom-long, pump-chain- SHORT, bb-bounce-v2-long+) fall below 24h kill window; regime check deferred until 24h sample rebuilds.

---
*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-18 | 836de28 | brain_auditor: Captain audit Oct 18 06:40 — soak #11, 0 conf... |
| 2026-10-17 | 209c5ae | brain_auditor: trail-arm-timeout candle OOS (all 4 cohorts) ... |
| 2026-10-17 | b01d329 | brain_auditor: captain run Oct 17 06:45 — 0 changes, verify+... |
| 2026-10-17 | 75b2af2 | brain_auditor: REGIME_CONF_EXTREME_MULT 1.15→0.85 — stale Se... |
| 2026-10-17 | ece01f3 | scripts: MFE-CUT shadow collector (T=45m, zero behavior) + a... |
| 2026-10-17 | 70f45e4 | brain_auditor: ai-trader RSI drift guard + MFE exit-ladder a... |
| 2026-10-17 | 5a95263 | signals: pump-chain+ LONG dead-gap falling-knife block (gap<... |
| 2026-10-17 | 66716f2 | scripts: extend trail-arm-timeout SHADOW to ai-trader+ LONG ... |
| 2026-10-17 | 02f6d4e | config: ATR_SL_MIN 1.3% → 1.5% |
| 2026-10-16 | 70ff616 | scripts: bb-bounce-v2 trail-arm-timeout SHADOW collector T=5... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*