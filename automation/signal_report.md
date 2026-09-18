# Signal Performance Report
**Generated:** 2026-09-18 05:09 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **24h:** 16 trades | 25.0% WR | -$1.41 PnL
- **6h:** 5 trades | 20.0% WR | -$0.35 PnL
- **All time:** 2,508+ trades | 51.8% WR

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No new kills this cycle |

**open-skies+** already killed 2026-09-17 (flags=False, NEVER_REENABLE). Confirmed dead.

---

## VOLATILITY GATE FIXES (executed)

| Signal | Regime | Old Mult | New Mult | Reason |
|--------|--------|----------|----------|--------|
| pullback-entry- | EXTREME | 0.5 (penalized) | 1.0 (pass) | 68% WR +$1.46 lifetime, 64% WR +$0.43/7d |
| pullback-entry- | HIGH | 0.7 (boosted) | 0.5 (penalized) | 47% WR -$0.38/7d, deteriorating |
| pullback-entry- | NORMAL | 0.0 (blocked) | 0.0 (blocked) | No change — 50% WR breakeven |

**Why not kill pullback-entry-?** EXTREME regime = 68.4% WR (19T lifetime), 63.6% WR (11T/7d). HIGH = 55.3% WR lifetime. Signal is net profitable ($2.09 lifetime). The 24h loss is HIGH regime variance, not a broken signal.

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No clear boost candidates |

---

## LOSERS (watch list)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| pullback-entry- | SHORT | 4 | 0.0% | -$0.61 | 5 | 20.0% | -$0.59 | Gate-fixed |

---

## MARGINAL

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| volume-breakout-long+ | LONG | 4 | 50.0% | -$0.04 | OK | Breakeven, needs more data |

---

## WINNERS

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| grind-breakout+ | LONG | 1 | 100% | +$0.01 | OK (low volume) |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DONE] Fix pullback-entry- regime multipliers** — EXTREME was penalized (0.5) despite 68% WR. HIGH was boosted (0.7) despite deteriorating. Corrected to 1.0/0.5/0.0.
2. **[WATCH] pullback-entry- HIGH regime** — 47% WR/7d. If next cycle shows continued losses, drop multiplier to 0.0 (block HIGH entirely).
3. **[MONITOR] volume-breakout-long+** — 50% WR breakeven. No action yet.
4. **[LOW VOLUME]** Only 16 trades in 24h. System is signal-starved. Consider loosening entry thresholds or adding new signals.

---

## CEO KANBAN

## TEAM UPDATES
- [2026-09-18 05:09 UTC] signal_reporter: No kills — open-skies+ already dead. Fixed pullback-entry- volatility gate: EXTREME 0.5→1.0 (68% WR), HIGH 0.7→0.5 (47% WR/7d). NORMAL blocked (correct). 24h: 16T 25%WR -$1.41. Low volume. No inversions.
