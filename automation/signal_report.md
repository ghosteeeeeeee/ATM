# Signal Performance Report
**Generated:** 2026-10-22 15:36 UTC | **Period:** Last 6h | 24h | (48h context)

All numbers verified by direct PostgreSQL query against brain DB this run.

## Overall Windows
- **6h:** 0 closed trades, $0.00 PnL
- **24h:** 9 closed trades, -$0.33 PnL
- **48h:** 44 closed trades, -$1.04 PnL

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met kill criteria (WR<30%, 5+ trades, PnL<-$0.10, 24h) |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal had 5+ trades in 24h |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 33.3% | -0.23 | 3 (24h) | watch — below kill bar (3<5T); 48h is 62.5% +0.03, all-time regime: FLAT 4/4 +0.17, NORMAL ~51%, HIGH 55.6%, EXTREME 46% — not a blanket kill |
| pump-chain+ | LONG | 0.0% | -0.32 | 6 (48h) | watch — 24h only 1T (fails 24h kill bar); all-time EXTREME 43% WR **+$3.73** → regime-dependent, would need vol-gate not kill |
| r2v2-long3 | LONG | 42.9% | -0.21 | 7 (48h) | watch — WR in tune range but 48h only, no 24h signal |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader-pending | SHORT | 100% | +0.11 | 1 (24h) | n=1, no boost |
| continuum-trend+ | LONG | 66.7% | +0.05 | 3 (48h) | n=3, no boost |
| bb-bounce-v2-long+ | LONG | 62.5% | +0.03 | 8 (48h) | healthy over 48h despite 24h blip |

## ISSUES

### 1. System is fully gated — 0 trades closed in 6h (MEDIUM, by design so far)
- 188 signals created in 6h (998 in 24h): 162 EXPIRED, 12 PENDING, 11 SKIPPED, 3 FAILED, **0 APPROVED**.
- Filter sandwich during the dump:
  - **LONG blocked** by `LONG-NEUTRAL-CHOP` (BTC below EMA300): 212 blocks in log window.
  - **SHORT blocked** by `SHORT-RSI-HARD-FLOOR` (floor=45): ~1,300 blocks across ~60 tokens, most with 5m RSI 28–35.
- The BTC-bearish exemption for shorts (`RSI >= OVERSOLD_SHORT_RSI_MAX`=35 + continuum LEAN_BEAR/BEAR, age<600s) shipped **today 14:39 UTC** and is live (confirmed in log: "SHORT allowed at approval — BTC bearish"). RSI<35 shorts stay hard-dead per BANANA lesson.
- **Action taken:** none — the exemption is <2h old, needs observation window before further gate changes. Re-evaluate at next run: if 0 approvals persist 6h after the override, the RSI<35 hard-dead band + LONG chop block is a collision trap and needs CEO decision.

### 2. No inversions (clean)
- 24h direction-mismatch query: 0 rows.

### 3. Hotset fallback warning (LOW)
- `[hotset] fallback DB query returned 0 tokens` in pipeline.log — follows from empty hotset, not an independent bug.

---
*Kill/boost thresholds applied: kill = WR<30% + 5T + PnL<-$0.10 (24h, active>24h); boost = WR>55% + 5T + PnL>$0.05 (24h). Regime check required before any kill.*
