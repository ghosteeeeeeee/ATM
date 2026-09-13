# Signal Performance Report
**Generated:** 2026-09-12 ~23:30 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Total closed trades:** 29
- **Overall WR:** 62.1% | **PnL:** +$0.63

---

## REGIME BREAKDOWN (24h)

| Regime | Trades | WR | PnL |
|--------|--------|-----|------|
| EXTREME | 13 | 69.2% | +$0.67 |
| HIGH | 12 | 50.0% | -$0.52 |
| NORMAL | 4 | 100% | +$0.43 |

**Key finding:** HIGH regime is the only losing regime. EXTREME and NORMAL are profitable.

---

## EXECUTED KILLS (regime-based)

No blanket kills — all signals have mixed performance across regimes. Applied **HIGH regime blocks** instead:

| Signal | Dir | WR | PnL | Regime | Action |
|--------|-----|-----|-----|--------|--------|
| rr-struct- | SHORT | 33% (HIGH) | -$0.25 | HIGH | BLOCKED 0.0x in HIGH |
| pullback-entry- | SHORT | 0% (HIGH) | -$0.36 | HIGH | BLOCKED 0.0x in HIGH (was 0.7x, upgraded to 0.0x) |

Both signals still trade in EXTREME/NORMAL where they're profitable.

---

## BOOST CANDIDATES

| Signal | Dir | 24h WR | 24h PnL | Trades | Action |
|--------|-----|--------|---------|--------|--------|
| rr-struct+ | LONG | 83.3% | +$0.07 | 6 | Monitor — strong but low volume |

---

## WINNERS (24h)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| rr-struct+ | LONG | 83.3% | +$0.07 | 6 | ✅ Keep |
| mover+ | LONG | 100% | +$0.31 | 1 | ✅ Keep (low count) |
| open-skies+,trend_purity+ | LONG | 100% | +$0.21 | 1 | ✅ Keep (low count) |
| trend_purity+,volume-breakout-long+ | LONG | 100% | +$0.15 | 1 | ✅ Keep (low count) |

---

## LOSERS / WATCH LIST (24h)

| Signal | Dir | WR | PnL | Trades | Status | Note |
|--------|-----|-----|-----|--------|--------|------|
| rr-struct- | SHORT | 50% | -$0.20 | 4 | HIGH blocked | 33% WR in HIGH, 100% in NORMAL |
| trend_purity+ | LONG | 50% | -$0.15 | 8 | Watch | 63.6% in EXTREME, dragged by other regimes |
| pullback-entry- | SHORT | 50% | +$0.05 | 6 | HIGH blocked | 0% in HIGH, 100% in NORMAL/EXTREME |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## CHANGES MADE

1. **market_phase_gate.py** — Added `R2_Structural` family to FAMILY_MAP (maps rr-struct variants)
2. **volatility_gate_v2.py** — BLOCKED `R2_Structural` 0.0x in HIGH regime (rr-struct- SHORT: 33% WR, 3 trades, -$0.25)
3. **volatility_gate_v2.py** — Upgraded `Pullback_Entry_Short` from 0.7x to 0.0x in HIGH regime (0% WR, 3 trades, -$0.36)

---

*Report auto-generated. Next report: ~6h from now.*
