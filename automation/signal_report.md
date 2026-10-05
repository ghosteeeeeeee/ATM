# Signal Performance Report
**Generated:** 2026-10-05 05:15 UTC | **Period:** Last 6h + 24h

## System Snapshot
- **24h:** 39 closed | 59.0% WR | **-$0.54** net
- **7d:** 231 closed | 55.0% WR | **+$1.32** net
- **Inversions (24h):** 0

---

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None |

No signal met kill criteria (WR < 30% with 5+ trades AND PnL < -$0.10 AND active > 24h).

---

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None |

No signal met boost criteria (WR > 55% AND PnL > $0.05 AND 5+ trades 24h AND multi-token consistency).

---

## LOSERS (watch list)
| Signal | Dir | 24h WR | 24h PnL | 24h Trades | 7d WR | 7d PnL | Status |
|--------|-----|--------|---------|------------|-------|--------|--------|
| bb-bounce-v3-long+ | LONG | 42.9% | -$0.42 | 7 | 52.6% | -$0.33 | NORMAL blocked 0.0x (2026-10-04, live). HIGH allowed 1.0x. 24h NORMAL trades opened pre-block — not new bleed. Watch. |
| bb-squeeze+ | LONG | 57.1% | -$0.37 | 21 | 61.7% | +$0.32 | HIGH 24h bleed (10T 40% -$0.59) is **noise** — lifetime HIGH 32T 62.5% WR +$0.12. EXTREME already blocked 0.0x. No HIGH block. Watch R:R. |
| btc-pump-rider+ | LONG | 0.0% | -$0.01 | 1 | — | -$0.19 | Lifetime 0/4 all losses, flag True. Below 5T kill threshold. Watch. |

---

## WINNERS
| Signal | Dir | 24h WR | 24h PnL | 24h Trades | 7d WR | 7d PnL | Status |
|--------|-----|--------|---------|------------|-------|--------|--------|
| bb-bounce-v2-long+ | LONG | 100% | +$0.21 | 3 | 75.0% | +$0.40 | Boost-eligible if 24h hits 5+ trades. Not yet. |
| mtf-regime-trend- | SHORT | 100% | +$0.11 | 2 | 100% | +$0.11 | New signal (first trade 2026-10-04). Too early. |
| pump-chain+ | LONG | 100% | +$0.14 | 2 | — | — | Lifetime 90T 44.4% WR +$2.04 (positive via R:R). Not boost-eligible 24h (2T). |

---

## ISSUES
- **None critical.** No inversions. No kill-eligible signals. No new regime blocks needed.
- **System R:R note:** 24h 59% WR but -$0.54 net — wins are small (+$0.02–$0.06), hard_max_loss exits -$0.12 to -$0.26. 7d is +$1.32 at 55% WR — recovering. Not a signal-level kill; exit-quality issue if it persists.
- **v3 NORMAL block confirmed live** — `('NORMAL','bb-bounce-v3-long'): 0.0` in volatility_gate_v2.py:344. Pipeline restarted 05:10 UTC 2026-10-05, code loaded. 24h NORMAL losses are pre-block trades.
- **bb-squeeze+ HIGH left open** — 24h HIGH 10T 40% -$0.59 vs lifetime HIGH 32T 62.5% +$0.12. Regime-block policy: only block when lifetime regime loses. 24h is variance.

---

## ACTIONS TAKEN
1. Verified all 24h/6h numbers directly from PostgreSQL brain DB (not from prior report).
2. Confirmed bb-bounce-v3-long+ NORMAL 0.0x block present and pipeline fresh — no re-apply.
3. Evaluated bb-squeeze+ HIGH for regime block — **rejected** (lifetime profitable).
4. No hermes_constants.py flag changes.
5. No signal_compactor.py weight changes.
6. OpenMemory skipped per task instructions (tenant_mismatch errors).

*Next report: ~6h. Re-check bb-bounce-v2-long+ trade count for boost eligibility.*
