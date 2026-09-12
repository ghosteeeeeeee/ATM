# Signal Performance Report
**Generated:** 2026-09-12 ~08:30 UTC
**Period:** Last 6h | 24h
**Total 24h trades:** 53

---

## KILLED (executed today)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 20.0% | -$0.27 | 5 | `PUMP_FLOW_PLUS_ENABLED = False` (killed 15:10 UTC) |

**Note:** All 5 pump-chain+ trades closed before the kill was applied. No new pump-chain+ signals should fire.

---

## BOOSTED (no action needed)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover+ | LONG | 100% | +$0.36 | 3 | Strong — consistent 100% WR |
| mover- | SHORT | 100% | +$0.46 | 3 | Strong — consistent 100% WR |
| rr-struct+ | LONG | 100% | +$0.14 | 3 | Strong — 100% WR |
| open-skies+ | LONG | 66.7% | +$0.16 | 3 | Solid |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 69.2% | +$0.02 | 13 | Winning — high volume, consistent |
| pullback-entry- | SHORT | 60.0% | +$0.10 | 5 | Winning — NORMAL regime blocked |
| trend_purity+ | LONG | 57.1% | +$0.01 | 7 | Marginal winner |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v4-short- | SHORT | 0% | -$0.27 | 2 | Watch — 0% WR in HIGH, 50% in EXTREME. Already penalized (0.3x HIGH). Not enough data for kill. |
| rr-struct- | SHORT | 50% | $0.00 | 2 | Neutral — too few trades |

---

## REGIME BLOCKS (already in place)

| Signal | Regime | Multiplier | Reason |
|--------|--------|------------|--------|
| pullback-entry- | NORMAL | 0.0 | 42.9% WR in NORMAL |
| accel-300 (all) | EXTREME | 0.0 | 37% WR in EXTREME |
| accel-300 (all) | HIGH | 0.3 | 35% WR in HIGH (penalized, not blocked) |

---

## ISSUES

- **No direction inversions** found in last 24h
- **pump-chain+ LONG** is the only kill candidate — already executed earlier today
- **accel-300-v4 SHORT** showing 0% WR in HIGH regime but only 2 trades — too small to act on. Currently penalized at 0.3x. Monitor.

---

## ACTIONS TAKEN

None this cycle. The only kill candidate (pump-chain+ LONG) was already handled at 15:10 UTC today.
