# Signal Performance Report
**Generated:** 2026-10-12 17:12 UTC | **Period:** Last 6h + 24h

## Overview (verified from PostgreSQL brain DB)
- **6h:** 1 closed trade | net $0.00 (near-zero activity)
- **24h:** 21 closed trades | WR 42.9% | net **+$0.10**
- System live, all timers active, pipeline running normally. Low trade volume = market conditions, not a fault.

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met kill criteria |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met boost criteria (no signal had 5+ trades with WR>55% in 24h) |

---

## LOSERS (watch list)

| Signal | Dir | 24h WR | 24h PnL | Trades | All-time | Status |
|--------|-----|--------|---------|--------|----------|--------|
| pump-chain+ | LONG | 25.0% | -$0.31 | 4 | 44% WR, +$2.91 (109 trades) | WATCH — below 5-trade kill threshold; all-time profitable; wins in EXTREME (48.6% WR, +$3.31) and HIGH (37.9%, +$0.02) regimes; only NORMAL regime is negative (n=6, 16.7%) |
| ai-trader+ | LONG | 33.3% | -$0.13 | 3 | 66.7% WR, +$0.05 (9 trades) | WATCH — bad day; all-time solid |
| hmacd_mtf-- | SHORT | 0% | -$0.12 | 1 | 25% WR, -$0.19 (4 trades) | WATCH — sample too small; recheck next report |
| oversold-bounce+ | LONG | 0% | -$0.07 | 2 | 66.7% WR, +$0.25 (6 trades) | WATCH — bad day; all-time solid |

## WINNERS

| Signal | Dir | 24h WR | 24h PnL | Trades | Status |
|--------|-----|--------|---------|--------|--------|
| ai-trader-manual | LONG+SHORT | 100% | +$0.59 | 2 | ENABLED — manual overrides, not auto-boostable |
| hl_copy_trader | LONG | 100% | +$0.09 | 1 | ENABLED — copy-trader path |
| volume-buildup+ | LONG | 50% | +$0.05 | 2 | ENABLED — needs more data for boost |

---

## ISSUES

- **No direction inversions** in 24h (checked long-signal/SHORT and short-signal/LONG) — clean.
- **Trade 16066 (BTC, 2026-10-11 18:12):** `signal = NULL`, closed as `guardian_orphan` at $0.00 PnL. Orphan position caught and neutralized by guardian — working as designed, no leak, but worth noting why a signal-less trade exists (manual/legacy open path?). Low severity.
- **hard_max_loss dominance:** 8 of 10 24h losers closed via `hard_max_loss` (totaling -$0.57). Stop discipline is working (losses capped, avg -$0.07/loser) — no single blowups.
- **6h near-zero activity** (1 trade): not a bug — pipeline confirmed LIVE, timers healthy, portfolio 0 open positions at check time.

## Kill/Boost Decision Log

- **pump-chain+:** Kill criteria require WR<30% AND 5+ trades AND PnL<-$0.10 AND active>24h. Has 4 trades — **fails trade-count gate**. Regime analysis also blocks kill: EXTREME (its dominant regime, n=74) is 48.6% WR and +$3.31 all-time. 24h loss = 3 EXTREME-regime losers on a slow day, not a broken signal.
- **ai-trader+:** WR 33.3% is above the <30% kill line; all-time 66.7%. Watch.
- **Boosts:** No signal had 5+ trades with WR>55% and PnL>$0.05 in 24h. ai-trader-manual hit 100%/+$0.59 but only 2 trades and is a manual path.

---
*Next report due: ~2026-10-12 23:12 UTC. Recheck hmacd_mtf-- and pump-chain+ NORMAL-regime exposure then.*
