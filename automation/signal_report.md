# Signal Performance Report
**Generated:** 2026-09-13 12:00 UTC | **Period:** Last 6h + 24h

---

## 6h Performance

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| trend_purity+ | LONG | 3 | 0.0% | -0.75 |

No other signals had 2+ trades in 6h.

---

## 24h Performance

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| rr-struct+ | LONG | 5 | 80.0% | +0.67 |
| pullback-entry- | SHORT | 6 | 50.0% | 0.00 |
| rr-struct- | SHORT | 4 | 75.0% | -0.02 |
| trend_purity+ | LONG | 7 | 14.3% | -0.92 |

---

## ACTIONS TAKEN

**REGIME BLOCK EXECUTED:**
- `trend_purity+` removed from HIGH regime whitelist in `volatility_gate_v2.py`
- Added `Trend_Purity: 0.0` to (`HIGH`, `*`) VOL_PHASE_MULTS
- Rationale: 33.3% WR, -$0.50 PnL in HIGH (3 trades). Wins in EXTREME (57.1%, -$0.01 breakeven).
- **Not a blanket kill** — signal remains active in NORMAL (primary) and EXTREME (penalized 0.15x)

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| rr-struct+ | LONG | 5 | 80.0% | +0.67 | ACTIVE |

---

## LOSERS (WR < 30%, PnL < -$0.10)

| Signal | Dir | Trades | WR | PnL | Action |
|--------|-----|--------|-----|-----|--------|
| trend_purity+ | LONG | 7 | 14.3% | -0.92 | Regime block (HIGH) — wins in EXTREME |

---

## WATCH LIST (marginal)

| Signal | Dir | Trades | WR | PnL | Note |
|--------|-----|--------|-----|-----|------|
| rr-struct- | SHORT | 4 | 75.0% | -0.02 | High WR but INJ loss (-$0.25) in HIGH. Already blocked in HIGH via VOL_PHASE_MULTS. |
| pullback-entry- | SHORT | 6 | 50.0% | 0.00 | Breakeven. Regime blocks already in place for losing regimes. |

---

## SIGNAL INVERSIONS

**No inversions found.** All signals respect their direction labels.

---

## REGIME PERFORMANCE (trend_purity+ LONG)

| Regime | Trades | Wins | WR | PnL |
|--------|--------|------|-----|-----|
| EXTREME | 14 | 8 | 57.1% | -0.01 |
| HIGH | 3 | 1 | 33.3% | -0.50 |

**Decision:** Block HIGH only. EXTREME is breakeven, NORMAL is primary.

---

## NOTES

- Pullback-entry- SHORT is exactly breakeven — regime blocks already active for losing regimes (NORMAL blocked at 0.0x per line 239).
- rr-struct- SHORT has 75% WR but -$0.25 INJ loss in HIGH wiped gains. Already blocked in HIGH (line 249).
- No signals hit kill threshold (WR < 30% with 5+ trades AND net PnL < -$0.10 AND active > 24h).
