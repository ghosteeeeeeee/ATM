# Signal Performance Report
**Generated:** 2026-10-06 11:12 UTC | **Period:** Last 6h + 24h

---

## Actions Executed

**KILLED (executed):** None
**BOOSTED (executed):** None

Kill criteria not met by any signal:
- `bb-squeeze+` LONG: 6 trades, 50.0% WR, -$0.23 — WR not <30%
- `trend-ride+` LONG: 7 trades, 42.9% WR, -$0.18 — WR not <30%, active <24h

---

## 24h Performance (verified, live DB)

| Signal | Dir | Trades | WR | PnL | Verdict |
|--------|-----|--------|-----|-----|---------|
| bb-squeeze+ | LONG | 6 | 50.0% | -$0.23 | Watch |
| trend-ride+ | LONG | 7 | 42.9% | -$0.18 | Watch |
| pump-chain- | SHORT | 2 | 50.0% | -$0.19 | Too few trades |
| volume-breakout-long+ | LONG | 1 | 0.0% | -$0.27 | Too few trades |
| btc-pump-rider+ | LONG | 1 | 0.0% | -$0.15 | Too few trades |
| mover+ | LONG | 1 | 0.0% | -$0.14 | Too few trades |
| bb-bounce-v2-long+ | LONG | 2 | 50.0% | -$0.09 | Too few trades |
| continuum_engine | LONG | 1 | 0.0% | $0.00 | Too few trades |
| doji-bottom-long | LONG | 1 | 100.0% | $0.12 | Too few trades |

## 6h Performance (verified, live DB)

Only two closed trades total:
- `pump-chain-` SHORT: 1 trade, -$0.25
- `bb-squeeze+` LONG: 1 trade, -$0.13

No signal had ≥2 trades in 6h — nothing actionable.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 50.0% (24h) / 63.4% (72h) | -$0.23 (24h) / -$0.18 (72h) | 6 / 41 | Watch — 72h WR healthy; loss driven by exits not entries. NORMAL regime 7d: 66.7% WR, +$0.25. HIGH 61.5% WR but -$0.15, EXTREME 50% WR -$0.15 — if losses continue, gate EXTREME regime via volatility_gate_v2.py, do NOT kill. |
| trend-ride+ | LONG | 42.9% | -$0.18 | 7 | Watch — first trade ever 2026-10-05 22:10 (~13h old). Not active >24h, too early to kill. Only HIGH regime data (3 trades, 33.3% WR, -$0.01). |

## WINNERS

None in 24h. No signal met boost criteria (WR >55% with 5+ trades AND PnL > +$0.05).

## ISSUES

- No direction inversions found in last 24h (0 mismatches between signal name direction and trade direction).
- Low trade volume overall in 6h (2 closed trades) — sample too small for regime-gated actions.
- `bb-squeeze+` LONG high-WR-but-negative-PnL pattern (63.4% WR over 72h with -$0.18) suggests exit quality / R:R problem rather than signal quality. Candidate for exit-side review, not a kill.
