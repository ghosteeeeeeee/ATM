# Signal Performance Report
**Generated:** 2026-10-22 21:35 UTC | **Period:** Last 6h + 24h (7d context for watch list)

All numbers verified directly against brain DB this run.

## Headline

Trade throughput collapsed: **4 closed trades in 24h** (vs 37 on 10-21, 23 on 10-20).
No signal reaches any kill or boost threshold (all have ≤1 trade in 24h). No kills,
no boosts executed. No direction inversions found (24h or 7d).

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no candidate met 24h criteria (5+ trades) |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no candidate met 24h criteria |

## LOSERS (watch list, 7d — 24h sample too thin)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 6.7% | -1.29 | 15 | WATCH — HIGH blocked at runtime; EXTREME still 1.0 but decaying: 30d +2.54 / 14d +0.25 / **7d 0W-9T -0.79**. Re-evaluate EXTREME if 7d bleed continues; no kill (30d edge exists) |
| bb-bounce-v2-long+ | LONG | 47.6% | -0.60 | 21 | WATCH — FLAT-only admission gate active; NORMAL 9W/17T but still net negative, exit-side issue not entry |
| pump-chain- | SHORT | 0.0% | -0.58 | 10 | WATCH — 8 EXTREME losses all pre/post-block edge on 10-16 only; post-10-16 only 2 NORMAL trades (-0.09). EXTREME 0.0 gate holding |
| ai-trader+ | LONG | 42.9% | -0.54 | 14 | WATCH — EXTREME 0.0 gate (10-19) verified holding: 0 EXTREME opens since. HIGH kept (4W/5T) |
| doji-bottom-long | LONG | 45.5% | -0.51 | 11 | WATCH |
| ai-trader-pending | LONG | 0.0% | -0.14 | 6 | WATCH — n too small |
| r2v2-long3 | LONG | 55.6% | -0.12 | 9 | WATCH — WR ok, PnL negative (exit asymmetry) |

## WINNERS (7d, none boost-eligible in 24h)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-trend+ | LONG | 80.0% | +0.09 | 5 | Not boosted — all 5 trades on one chain (hyperliquid), fails multi-token criterion; n=5 |
| volume-buildup- | SHORT | 66.7% | +0.02 | 6 | Not boosted — PnL below $0.05 bar |
| pump-chain-,pump-chain-v6- | SHORT | 33.3% | +0.31 | 9 | Not boosted — WR below bar |
| 24h: volume-buildup- / warrior-sr-confirm- / ai-trader-pending(+) | — | 100/100/100 | +0.08/+0.08/+0.11 | 1 each | n=1, no action |

## ISSUES

- **Trade drought:** 4 closes in last 24h vs 23-37/day on 10-20/10-21. Pipeline is alive
  (cycle #253060, 46 signals in runner) but pre-filter/confluence-gate passes ≈0-1 signals
  per cycle; hotset wrote 0 tokens at 21:33. Gates are filtering hard — monitor; if 24h
  closes stay <5 tomorrow, audit which gate went hyper-aggressive (visible blocks:
  CONFLUENCE-GATE single-type, PUMP-CHAIN-HIGH, PUMP-CHAIN-RSI-MAX, CONTINUUM-BULL).
- **No inversions:** 0 direction mismatches in 24h and 7d windows.
- **Gate leak check:** pump-chain- EXTREME (blocked 10-16) — no EXTREME opens after
  10-16 14:04 ✓. ai-trader+ EXTREME (blocked 10-19) — no EXTREME opens since ✓.
- Prior kills/regime gates verified in place: volatility_gate_v2.py lines 363/378/385/386.
