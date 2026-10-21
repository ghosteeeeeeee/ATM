# Signal Performance Report
**Generated:** 2026-10-21 09:35 UTC | **Period:** Last 6h + 24h
**Window:** 6h closed=4 trades | 24h closed=26 trades | **No OpenMemory (tenant_mismatch workaround)**

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None. No signal met all three kill criteria (WR<30% + 5+ trades + PnL<-$0.10) with all-regimes-<50% WR. |

**Candidate analyzed and rejected:**

`pump-chain-,pump-chain-v6-` SHORT — 24h: 5T, 20% WR, -$0.16. Met raw kill criteria but:
- 7d: 10T, 30% WR, **+$0.28** (profitable window)
- EXTREME regime (only meaningful habitat): 7d 9T 3W +$0.32 | all-time 14T 4W +$0.17
- Combined confluence = v6 RSI floor filtering the bleed; 24h is noise on a profitable confluence
- Blanket kill would violate CEO "never blanket disable pump-chain SHORT, route via regime"

`pump-chain+` LONG — 24h: 4T, 0% WR, -$0.16. Below 5T kill threshold. 7d: 22T 27.3% **+$0.16**. All-time EXTREME habitat 106T 42.5% +$4.18. All 4 losses were `trail_arm_timeout` (exit mechanism, not signal failure). Watch list.

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None. Boost criteria (WR>55% + 5+ trades + PnL>$0.05) not met — top 24h winners each have 1 trade (r2v2-long5 +$0.37, bb-squeeze+ +$0.28, continuum-osc+ +$0.09). |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 0.0% | -$0.16 | 4 (24h) | WATCH — below kill threshold (4T). 7d +$0.16. HIGH regime all-time 35% -$0.74 already dampened 0.5x. NORMAL blocked 0.0. All 24h losses trail_arm_timeout. |
| pump-chain- | SHORT | 8.3% | -$0.55 | 12 (7d) | ROUTED — EXTREME blocked 0.0 (commit 3dabb044, Oct 16 14:44). Post-block: 0 EXTREME trades, 1 NORMAL -$0.05. Pre-registered "revert if 7d WR<50%" trigger is numerically hit but window is pre-block contaminated; regime routing works post-commit. CEO directive: never blanket disable. |
| r2v2-long3 | LONG | 33.3% | -$0.07 | 3 (24h) | WATCH — 3T below kill threshold. 7d 5T 60% +$0.02. All-time EXTREME 7T 42.9% -$0.10 (tiny bleed), HIGH 5T 60% WR. n=13 all-time too small to act. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2v2-long5 | LONG | 100% | +$0.37 | 1 (24h) | Single trade — not boost-eligible |
| bb-squeeze+ | LONG | 100% | +$0.28 | 1 (24h) | Single trade |
| continuum-osc+ | LONG | 100% | +$0.09 | 1 (24h) | Single trade |
| bb-bounce-v2-long+ | LONG | 100% | +$0.08 | 1 (24h) | Single trade |
| continuum-trend+ | LONG | 100% | +$0.04 | 1 (24h) | Single trade |

---

## VERIFICATION NOTES (Step 1 mandatory re-query)

- All numbers queried fresh from PostgreSQL brain DB at 09:32 UTC 2026-10-21. Not trusted from prior report.
- 6h window: 4 closed trades total, no signal+direction group with ≥2 trades. Quiet window.
- 24h: 26 closed trades. Grouped by signal+direction with ≥2: pump-chain+ LONG (4T), pump-chain-,pump-chain-v6- SHORT (5T), r2v2-long3 LONG (3T), ai-trader-manual LONG (2T), ai-trader-pending SHORT (2T). Manual/CEO trades excluded from signal kill analysis.

---

## ISSUES

- **No inversions** (Step 5 clean): 0 direction mismatches in 24h (signal names containing "long"/"short" vs direction column).
- **Standalone pump-chain- EXTREME trades on Oct 16 (01:58–14:04 UTC, 8T 0%WR -$0.49):** all opened BEFORE the `('EXTREME','pump-chain-'): 0.0` block commit at 14:44 UTC (3dabb044). Not a bypass bug — block is effective post-commit. No action needed.
- **Combined-signal EXTREME confluence (`pump-chain-,pump-chain-v6-`):** flows through `('EXTREME','pump-chain-v6-'): 1.0` override (FIRST MATCH WINS, substring match hits v6- before pump-chain-). This is intentional per spec rev1 §6.3 (v6 SHORT neutral in EXTREME; confluence edge +$0.32/7d). Not a bug.
- **Pre-registered revert trigger (PUMP_CHAIN_V5_SHORT_ENABLED "revert if 7d WR<50%"):** numerically hit (8.3% WR standalone 7d) but window contaminated by pre-block trades; post-block routing verified effective (0 EXTREME leaks). Documented for CEO awareness — recommend keeping regime-routed state; blanket revert would contradict "every dump is a SHORT" standing order and kill the profitable v6 confluence.
- **Brain_auditor action already in stack today:** SHORT_RSI_FLOOR_PUMP_CHAIN + SHORT_RSI_HARD_FLOOR_PUMP_CHAIN reverted 40→45 (commit-level change, hermes_constants.py:934,946). Adds another defense layer on pump-chain SHORT oversold entries.

---

## SYSTEM HEALTH

- Kill switches: LIVE_TRADING_ENABLED=True | runtime kill switch untouched
- No flags modified this run. No commits required (no file changes).
- Next report: ~2026-10-21 15:35 UTC
