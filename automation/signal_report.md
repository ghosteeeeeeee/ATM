# Signal Performance Report
**Generated:** 2026-09-23 13:45 UTC | **Period:** Last 6h + 24h

## 6h Performance

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| mover+ | LONG | 2 | 0.0% | -$0.50 |
| bb-bounce-v2-long+ | LONG | 5 | 40.0% | -$0.06 |

## 24h Performance

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pullback-entry- | SHORT | 5 | 0.0% | -$1.25 |
| mover+ | LONG | 3 | 33.3% | -$0.34 |
| bb-bounce-v2-long+ | LONG | 8 | 50.0% | -$0.07 |

**24h Total:** 24 trades | 37.5% WR | -$1.64 PnL

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0.0% | -$1.25 | 5 | Already disabled (flag=False since Sep 22 23:12 UTC). 24h trades predate kill. |

No new kills needed. All kill-criteria signals already disabled.

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 66.7% | +$1.46 | 18 (7d) | Already at 1.15x weight. EXTREME 70% WR. No change needed. |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover+ | LONG | 33.3% | -$0.34 | 3 (24h) | ENABLED — Historical 66.7% WR (18T). Bad 24h streak. Watch. |
| bb-bounce-v2-long+ | LONG | 50.0% | -$0.07 | 8 (24h) | ENABLED — Near breakeven. Bollinger family, EXTREME/HIGH only. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 66.7% | +$1.46 | 18 (7d) | ENABLED — 1.15x weight. EXTREME 70% WR. Consistent. |

---

## ISSUES

- **No signal inversions found.** All signals respect direction labels.
- **No anomalies detected.** Large losses only from already-killed signals.
- **24h overall WR is low (37.5%)** but sample size is small (24 trades). Not a systemic issue.

---

## Regime Performance Context

**pullback-entry- SHORT (7d):**
- EXTREME: 12T, 41.7% WR, -$0.39
- HIGH: 18T, 38.9% WR, -$0.78
- NORMAL: 8T, 12.5% WR, -$1.13
- **All regimes < 50% WR → blanket kill confirmed correct**

**mover+ LONG (lifetime):**
- EXTREME: 7T, 57.1% WR, -$0.48
- HIGH: 9T, 66.7% WR, +$0.09
- NORMAL: 2T, 100% WR, +$0.15
- **Wins in HIGH/NORMAL, loses in EXTREME. No regime block needed yet.**

**bb-bounce-v2-long+ LONG (lifetime):**
- EXTREME: 2T, 50% WR, -$0.24
- HIGH: 10T, 50% WR, -$0.06
- **Bollinger family already blocked in HIGH via VOL_PHASE_MULTS. EXTREME at 0.4x.**

---

## Actions Taken

None. All signals already at correct state. No new kills or boosts needed.
