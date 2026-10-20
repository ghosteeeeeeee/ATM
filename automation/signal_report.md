=== Signal Performance Report ===
Period: Last 6h | 24h — 2026-10-20 ~15:30 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No kill candidates — see LOSERS |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No boost candidates (max 1-2 trades per winner in 24h) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain-,pump-chain-v6- | SHORT | 16.7% | -$0.10 | 6 | NO KILL — NORMAL SHORT habitat is 56.3% WR +$0.39 all-time (>=55% → regime-block only per SOP). HIGH already blocked (PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True). Bare pump-chain- EXTREME already 0.0-blocked (working since 2026-10-16, 0 trades since). Combined EXTREME profitable 7d: 8T 3W +$0.48; v6- EXTREME 14d 12T 4W +$0.35. 24h = small-sample bad day (EXTREME -$0.06/5T, NORMAL -$0.09/2T). |
| pump-chain+ | LONG | 0% | -$0.39 | 2 | WATCH — under kill threshold (needs 5+T). 7d EXTREME +$0.65 (14T). HIGH LONG dampened 0.5x already. |
| ai-trader-manual | LONG | 0% | -$0.13 | 2 | CEO manual trades — out of scope for signal kill |
| ai-trader-pending | LONG | 0% | -$0.07 | 3 | CEO pending trades — out of scope |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2v2-long5 | LONG | 100% | +$0.37 | 1 | OK — 1T, no boost (needs 5+T). ZRO hard_tp. |
| bb-squeeze+ | LONG | 100% | +$0.28 | 1 | OK — 1T, no boost. 7d: 4T 75% +$0.21. HYPE profit-monster-trail. |
| ai-trader-pending | SHORT | 100% | +$0.07 | 1 | CEO trade — OK |

ISSUES:
- No direction inversions in last 24h (checked long-signal/SHORT and short-signal/LONG — zero matches).
- Signal volume is very low this cycle (19 closed trades/24h total; only 1 signal group with 5+ trades). No structural changes made — existing regime blocks already cover the pump-chain SHORT bleed paths.
- Regime checks verified before declining the pump-chain SHORT kill: NORMAL 56.3% WR (+$0.39, 16T), EXTREME SHORT trades now route via v6 (profitable), HIGH blocked. Existing VOL_PHASE_MULTS + HIGH block + EXTREME bare-pump-chain- 0.0 block are all in place and working.

6h snapshot: ai-trader-manual LONG -$0.13 (2T), pump-chain SHORT -$0.03 (4T). Nothing actionable.
