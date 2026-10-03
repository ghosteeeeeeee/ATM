# Signal Performance Report
**Generated:** 2026-10-03 23:13 UTC | **Period:** Last 6h + 24h
**Source:** PostgreSQL brain DB (queried live, not cached)

---

## 6h Performance (≥2 trades)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-v3-long+ | LONG | 2 | 0.0% | -$0.14 |
| bb-squeeze+ | LONG | 2 | 50.0% | -$0.04 |

## 24h Performance (≥3 trades)

| Signal | Dir | Trades | WR | PnL | Avg Win | Avg Loss |
|--------|-----|--------|-----|-----|---------|----------|
| bb-squeeze+ | LONG | 10 | 70.0% | +$0.33 | $0.099 | -$0.120 |
| pump-chain+ | LONG | 8 | 62.5% | +$0.95 | $0.302 | -$0.187 |
| pump-chain- | SHORT | 5 | 60.0% | +$0.18 | $0.167 | -$0.160 |
| bb-bounce-v3-long+ | LONG | 5 | 60.0% | -$0.02 | $0.040 | -$0.070 |

7d context: bb-squeeze+ 36T 61.1% +$0.27 | pump-chain+ 8T 62.5% +$0.95 (re-enabled 10-02) | pump-chain- 34T 50.0% +$0.02 | bb-bounce-v3-long+ 10T 60.0% +$0.09

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met kill criteria (WR<30% + 5T + PnL<-$0.10) |

Kill-path re-verified: no flag changes. MTF_REGIME_TREND_PLUS, PUMP_CHAIN_V5, ACCEL_300_* all already False.

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 70.0% | +$0.33 | 10 | Weight 1.0→1.2 in signal_compactor.py + combo_weights.json 1.02→1.2 |
| pump-chain+ | LONG | 62.5% | +$0.95 | 8 | Weight (new static 1.2) + combo_weights.json 0.6→1.2 |

Multi-token consistency: bb-squeeze+ winners on SYRUP/SEI/XPL/ARB/MON; pump-chain+ winners on ME/LDO/ENS/DYDX/GMT.

Note: combo_weights.json (self_learner auto-tune) takes priority over static SIGNAL_SOURCE_WEIGHTS in `_get_source_weight()`. Both updated. **RESTART PIPELINE** to load signal_compactor.py static change.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 60.0% | -$0.02 | 5 | WATCH — WR ok, PnL slightly negative, R:R inverted (win 0.04 vs loss 0.07). 7d +$0.09. No change. |
| pump-chain- | SHORT | 60.0% | +$0.18 | 5 | WATCH — meets boost letter on 24h but 7d 34T 50% breakeven. EXTREME mult already boosted 0.5→1.0 earlier today (12:05). No additional boost. |
| volume-breakout-long+ | LONG | 0.0% | -$0.11 | 1 | Below threshold. Weight already 1.25 from earlier today. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 70.0% | +$0.33 | 10 | ENABLED — BOOSTED this cycle. EXTREME regime-blocked (bb-squeeze 0.0). HIGH 63.6%WR kept. |
| pump-chain+ | LONG | 62.5% | +$0.95 | 8 | ENABLED — BOOSTED this cycle. HIGH blocked, dead-hours blocked, EXTREME 1.0. |
| pump-chain- | SHORT | 60.0% | +$0.18 | 5 | ENABLED — EXTREME mult 1.0 (boosted 12:05). NORMAL 1.0. HIGH blocked. |
| bb-bounce-v2-long+ | LONG | 100.0% | +$0.01 | 1 | ENABLED — 30d 73T 74%WR +$2.08 lifetime winner. |
| pump-chain-v5 | LONG | 100.0% | +$0.16 | 1 | FLAG=False (killed 10-01 10:18) — this trade is pre-kill close aging out. |

---

## SIGNAL INVERSIONS (24h)

**None.** Query: signal LIKE '%long%' AND direction='SHORT' OR signal LIKE '%short%' AND direction='LONG' → 0 rows.

---

## ISSUES

1. **Prior report numbers were wrong** — signal_report.md from 23:03 listed pump-chain+ +5.43 and bb-squeeze+ +2.50 (percent units presented as USD). Actual PG: +$0.95 and +$0.33. This report uses PG USDT values only.
2. **combo_weights.json is the live authority** for source weights (checked before static map). Any static-only boost is inert if a combo_weights entry exists. Future boosts must update both.
3. **bb-bounce-v3-long+ R:R inverted** — avg win $0.04 vs avg loss $0.07. WR 60% keeps it net near-zero. Monitor; if 7d turns negative, tune SL or kill.
4. **ACE coin-level bleed** — blacklisted 2026-10-03 (7d 3T 0W -$0.55 across bb-squeeze+/pump-chain+). Not a signal-logic issue; blacklist handles it.
5. **self_learner may overwrite** manual combo_weights boosts on next run. Re-verify weights after next self_learner pass.

---

*Report auto-generated. Next report: ~6h from now.*
