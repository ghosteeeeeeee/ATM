# Signal Performance Report
**Generated:** 2026-10-16 01:35 UTC | **Period:** Last 6h + 24h (+7d watch list)

## Trade Volume
- **6h closed:** 7 trades | **24h closed:** 15 trades
- Low-volume window — no signal met kill or boost thresholds in 24h.

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met kill criteria (WR<30%, n>=5, PnL<-$0.10, 24h) |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — pump-chain+ LONG best at 50% WR (needs >55%) |

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 18.8% | -0.76 | 16 (7d) | WATCH — EXTREME 10% WR (n=10), HIGH 42.9% (n=7); no regime >=55%, kill candidate if 24h volume returns |
| hmacd_mtf-+ | LONG | 25.0% | -0.46 | 8 (7d) | WATCH — EXTREME 33.3% (n=3) |
| oversold-bounce+ | LONG | 28.6% | -0.32 | 7 (7d) | WATCH — EXTREME 0% WR (n=3), HIGH 50% (n=4) |
| volume-buildup+ | LONG | 20.0% | -0.21 | 5 (7d) | WATCH — NORMAL regime 20% WR (n=5) |
| bb-bounce-v2-long+ | LONG | 0.0% | -0.15 | 1 (24h) | Single trade, insufficient data |
| grind-breakout- | SHORT | 0.0% | -0.12 | 1 (24h) | Single trade, insufficient data |
| ai-trader-manual | SHORT | 0.0% | -0.18 | 1 (24h) | Manual trade, not signal-tunable |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 50.0% | +1.03 | 6 (24h) | 35.5% WR / +0.93 over 7d (n=31) — marginally profitable, keep |
| ai-trader+ | LONG | 100% | +0.13 | 1 (24h) | Single win, insufficient data |
| liq-hunt+ | LONG | 100% | +0.05 | 1 (24h) | Single win, insufficient data |
| doji-bottom-long | LONG | 100% | +0.02 | 1 (24h) | Single win, insufficient data |

## ISSUES

- No direction inversions found (24h).
- Low trade throughput: only 15 closed trades in 24h — signal stats are noise-dominated; no aggressive actions taken.
- 7d losers (volume-breakout-long+, hmacd_mtf-+, oversold-bounce+, volume-buildup+) all lose in EXTREME regime; no regime has >=55% WR, so they qualify for blanket kill IF 24h criteria are met on a future run with adequate sample.
- ai-trader-manual SHORT (-0.18) is a manual trade — flagging to CEO but not signal-tunable.
