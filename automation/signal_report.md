# Signal Performance Report

**Generated:** 2026-10-25 | Period: last 6h / 24h | Source: PostgreSQL `brain.trades` (queried live)

Trading volume was very light: 5 closed trades in 6h, 14 closed trades in 24h. No signal met the kill threshold (WR <30% with 5+ trades AND negative PnL). No signal met the full boost threshold (WR >55% with 5+ trades) — nearest is `volume-buildup-` SHORT at 75% WR / 4 trades.

No direction inversions detected. No anomalies found.

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None. No kill candidates. |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None. Closest: volume-buildup- SHORT (75% WR, +$0.27, 4 trades) — below 5-trade minimum. Watch for boost if it continues. |

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 0.0% | -$0.06 | 2 | Watch. Only 2 trades, not enough to act. |
| r2v2-long3 | LONG | 0.0% | -$0.10 | 1 | Watch. Single trade. |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 75.0% | +$0.27 | 4 | Boost candidate pending 5th trade. |
| continuum+ | LONG | 100.0% | +$0.20 | 2 | Healthy. |
| bb-squeeze+ | LONG | 100.0% | +$0.04 | 1 | Healthy (low volume). |
| ai-trader-pending | LONG/SHORT | 100.0% | +$0.16 | 2 | Healthy (manual/pending orders). |
| hl_copy_trader | LONG | 100.0% | +$0.16 | 1 | Healthy. |
| pump-chain+ | LONG | 100.0% | +$0.05 | 1 | Healthy. |

## ISSUES

- None. No direction inversions, bugs, or anomalies in this window.
- Note: `volume-buildup-` full history shows NORMAL regime at 52.9% WR (9/17, -$0.08) and EXTREME at 57.1% WR (4/7, -$0.04) but HIGH at 100% (5/5, +$0.57). If it degrades, tune regime gate before killing.

## Actions taken

None this cycle — trading too light to trigger kill/boost rules.
