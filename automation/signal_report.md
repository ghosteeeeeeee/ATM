# Signal Performance Report
**Generated:** 2026-10-26 15:35 UTC | **Period:** Last 6h + 24h

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met all kill criteria |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met all boost criteria (5+ trades) |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 55.6% | -0.15 | 9 | WATCH — WR fine; two `hard_max_loss` (-0.12, -0.17) drove the day. Lifetime: HIGH 85.7%/+0.47, NORMAL 64.7%/+0.08, EXTREME 55.6%/-0.04 → wins in all regimes, no kill |
| bb-bounce-v2-long+ | LONG | 20.0% | -0.05 | 5 | WATCH — WR<30% ✓ but PnL -0.05 > -0.10 threshold ✗. Lifetime (since 09-10): NORMAL 41.3%/-0.76, EXTREME 41.7%/-0.61, HIGH 52.9%/-0.07 → tuning candidate, not blanket-kill (HIGH ≥50%) |
| pump-chain+ | LONG | 75.0% | -0.03 | 4 | WATCH — high WR, small net loss |
| hl_copy_trader | LONG | 0.0% | -0.16 | 2 | WATCH — n=2, too small |
| pump-chain- | SHORT | 0.0% | -0.12 | 2 | WATCH — n=2, too small |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2v2-long3 | LONG | 100% | +0.09 | 2 | Healthy — n<5, not boostable yet |
| continuum-osc+ | LONG | 100% | +0.04 | 1 | Healthy |
| continuum-trend- | SHORT | 100% | +0.03 | 1 | Healthy |
| continuum-osc- | SHORT | 100% | +0.01 | 1 | Healthy |

### 6h snapshot (n≥2)
- volume-buildup- SHORT: 5 trades, 20% WR, -0.27
- pump-chain+ LONG: 2 trades, 50% WR, -0.08
- r2v2-long3 LONG: 2 trades, 100% WR, +0.09

## ISSUES
- **No direction inversions in 24h** — signal labels match directions.
- **volume-buildup-** hit `hard_max_loss` twice within 35 min (13:54 and 14:14 UTC) — exit-system, not signal, is the loss driver.
- **bb-bounce-v2-long+** is the structural concern: ~-1.3 lifetime PnL, below-50% WR in NORMAL and EXTREME regimes. Candidate for regime multipliers in `volatility_gate_v2.py` next cycle — needs sample-checked backtest first per THE PATTERN rules.
- Quiet day overall: only 11 closed trades in 24h; sample sizes too small for kills/boosts.

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-26 | c7da007 | brain_auditor: audit run #157 — daily-commit guard fixed (po... |
| 2026-10-25 | f6a7ed8 | brain_auditor: audit run #138 — escalation #17 closed as sup... |
| 2026-10-25 | f86261f | brain_auditor: #134 addendum — watchdog 06:44 UTC P1 rejected-wi... |
| 2026-10-24 | f96aa8a | brain_auditor: AUDIT RUN #122 — LONG_RSI_SWEET_SPOT_BOOST 10... |
| 2026-10-24 | c10b227 | scripts: UNCLOG-2 — 4 CEO-approved flips (consult 20261024T1... |
| 2026-10-24 | 186ff1c | watchdog: 14:20 UTC cycle — BTC broke EMA300 pin DOWN (knife... |
| 2026-10-24 | 9482523 | logs: hourly analysis 2026-10-24 12:28 — no change, quiet ho... |
| 2026-10-24 | 7553d4e | brain_auditor: AUDIT RUN #114 (2026-10-24) — entry_regime_4h... |
| 2026-10-23 | c4edf08 | exit-system: breakeven lock for CEO trades — SL→entry at +0.... |
| 2026-10-23 | 10d6898 | Daily trading system update (2026-10-23) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*

*Report auto-generated. Next report: ~6h from now.*
