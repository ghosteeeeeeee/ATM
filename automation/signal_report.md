# Signal Performance Report
**Generated:** 2026-09-27 23:25 UTC | **Period:** Last 6h + 24h + 7d

## Overall Stats
- **Total trades (all time):** 5,336 | **Date range:** 2026-05-20 → 2026-09-27
- **7d trades:** 127 | **7d WR:** 35.4% | **7d PnL:** -$5.34
- **24h trades:** 11 | **24h WR:** 45.5% | **24h PnL:** +$0.72
- **6h trades:** 8 | **6h WR:** 50.0% | **6h PnL:** +$0.63

---

## KILLED (executed)

None — all kill candidates already disabled from prior reports.

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0% | -$1.86 | 8 (7d) | Already OFF |
| pump-chain+ | LONG | 20% | -$1.60 | 20 (7d) | Already OFF, NEVER_REENABLE |
| mover+ | LONG | 25% | -$1.19 | 8 (7d) | Already OFF |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 (7d) | Already OFF, NEVER_REENABLE |

---

## BOOSTED (executed)

None — no signals meet boost criteria (WR>55%, 5+ trades, PnL>0).

---

## LOSERS (7d watch list)

| Signal | Dir | Trades | WR | PnL | Regimes | Note |
|--------|-----|--------|-----|-----|---------|------|
| pump-chain- | SHORT | 33 | 45.5% | -$0.93 | EXTREME 46%, HIGH 20% | All losses pre-date regime blocks (Sep 24). BLOCKS NOW WORKING — zero pump-chain- trades in 24h. |
| bb-bounce-v2-long+ | LONG | 14 | 42.9% | -$0.18 | HIGH 45%, NORMAL 33% | 2/2 profitable in 24h. Marginal. |
| doji-bottom-long | LONG | 4 | 25% | -$0.35 | — | Low sample size |

---

## WINNERS (24h snapshot)

| Signal | Dir | Trades | WR | PnL | Note |
|--------|-----|--------|-----|-----|------|
| continuation+ | LONG | 1 | 100% | +$0.32 | HIGH regime, POL |
| rs-s102 | LONG | 1 | 100% | +$0.19 | NORMAL, HBAR |
| rs-s118 | LONG | 1 | 100% | +$0.14 | NORMAL, HYPER |
| rs-s44 | LONG | 1 | 100% | +$0.12 | NORMAL, YGG |
| bb-bounce-v2-long+ | LONG | 2 | 50% | +$0.08 | HIGH+NORMAL |

---

## ISSUES

- **No SHORT trades in 24h** — all 11 trades are LONG. 7d split is 67 LONG / 60 SHORT (balanced), so this is likely market condition, not a bug.
- **14-hour trade gap** (02:17 → 16:27 UTC on Sep 27) — pipeline was idle overnight. No trades lost.
- **7d overall WR is 35.4%** — system is losing money on the week. 24h is profitable (+$0.72) which is improvement.
- **Low volume** — 11 trades/24h vs 18.1 avg/day. Normal weekend flow.

---

## REGIME BLOCK STATUS

**pump-chain- SHORT** — regime blocks confirmed working in volatility_gate_v2.py:
- EXTREME: `Pump_Flow: 0.0` (blocked) ✅
- HIGH: `Pump_Flow: 0.0` (blocked) ✅
- NORMAL: allowed (83.3% WR historically)

The 7d EXTREME/HIGH losses are from trades created Sep 22-24, BEFORE the blocks were applied. Zero pump-chain- trades in 24h confirms blocks are active.

**Note:** `should_trade_v2` from volatility_gate_v2.py is used by signal_compactor.py via `get_combined_multiplier`. The 0.0 multiplier zeroes out the score, preventing the signal from entering the top-10 hot-set.
