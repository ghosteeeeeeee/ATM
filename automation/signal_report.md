# Signal Performance Report
**Generated:** 2026-10-19 15:45 UTC | **Period:** Last 6h + 24h

## Overall (24h)
- **Closed trades:** 16 | **Net PnL:** -$0.34
- Quiet window — no signal had 5+ trades, so no blanket-kill candidates by threshold.

---

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | NORMAL LONG | 12.5% | -$0.45 | 8 (all-time) | Vol-gate 0.5→0.0 (block) |

**Rationale:** NORMAL is not the habitat — EXTREME LONG is (+$4.01/97T). Dampen at 0.5 (set 2026-10-09) was insufficient: all-time NORMAL still -$0.45 at 12.5% WR. SHORT sibling `pump-chain-` keeps its 1.2 NORMAL boost (64.3% WR, +$0.48). EXTREME LONG stays 1.0. Verified via `_get_signal_type_mult`: NORMAL +→0.0, NORMAL -→1.2, EXTREME +→1.0.

---

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met boost criteria (5+ trades, WR>55%, PnL>$0.05) |

---

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader+ | LONG | 25.0% | -$0.17 | 4 (24h) | EXTREME already blocked 09:41 (b0a2467d). Block verified holding — no trades opened after commit. HIGH 75% WR +$0.11 (8T) and NORMAL 40% kept. Watch NORMAL (5T all-time, 0% last 7d). |
| bb-bounce-v2-long+ | LONG | 75.0% | -$0.14 | 4 (24h) | Not a kill — WR is fine; dragged negative by one ME `stale_exit` -$0.26. EXTREME already blocked. NORMAL 7d 45.5% -$0.32 — exit issue, not signal issue. |
| doji-bottom-long | LONG | 16.7% | -$0.59 | 6 (72h) | All 6 losses were 2026-10-16 HIGH cluster. HIGH all-time still 56.5% WR +$0.09. No trades since 10-16. EXTREME already blocked (10-13). Watch, don't kill. |

---

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-trend+ | LONG | 100% | +$0.04 | 2 (24h) | Too few trades to boost (needs 5+). |
| r2v2-long3 | LONG | 100% | +$0.05 | 1 (24h) | Single trade. |
| ai-trader-manual | LONG | 100% | +$0.05 | 1 (24h) | NORMAL manual already blocked (10-19); EXTREME/FLAT kept. |

---

## ISSUES
- **No signal inversions** in 24h — direction labels all consistent.
- **ai-trader EXTREME block verified live:** 2 EXTREME losses today (LDO, ARB) were both opened *before* the 09:41:40 commit; zero trades opened after. No action needed.
- **bb-bounce ME `stale_exit` -$0.26:** single stale-exit loss wiped out 3 winners. Worth reviewing stale-exit timeout for bb-bounce family — not a signal kill.
- **Low activity:** 16 closed trades / 24h, net -$0.34. Filters tight or market quiet.

---

## ACTIONS TAKEN THIS RUN
1. `scripts/volatility_gate_v2.py`: `('NORMAL','pump_chain+')` and `('NORMAL','pump-chain+')` dampen 0.5→**0.0** (block). Evidence: all-time NORMAL 8T 12.5% WR -$0.45; EXTREME habitat +$4.01/97T kept; SHORT sibling boost preserved.
2. Verified ai-trader EXTREME block (b0a2467d) is holding — no new EXTREME entries since commit.
3. No blanket kills (no signal met 5+ trades with WR<30% in 24h).
4. No boosts applied (no signal met criteria).
