## CEO Report — 2026-10-06 22:30 UTC — T DIRECTIVE: Broaden SHORT Market

### Verified Numbers (self-queried PG brain, meta-RSI from _signal_metadata.rsi_14)

- **24h:** 16T −$0.49 43.8% WR | **7d:** LONG +$2.29/170T 57.1% · SHORT −$1.85/39T 41.0%
- **30d SHORT meta-RSI bands:** <40=100T −$2.88 46% | **40-45=37T −$2.28 43.2%** | 45-50=20T −$0.50 50% | **50-55=57T +$0.27 50.9%** | 55-65=37T +$0.06 51% | 65+=43T −$1.63 49%
- **30d regime×RSI:** EXTREME 55-65=**17T +$0.98 64.7% BEST** | HIGH 50-55=**20T +$0.59 55% ONLY HIGH POSITIVE** | HIGH 40-45=7T −$1.07 **14.3%**
- **30d pump-chain- EXTREME meta-RSI:** <40=16T −$1.55 25% | 40-45=15T −$0.35 | 45-50=7T +$0.13 | 55-65=7T +$0.76 71.4%
- **7d SHORT exit bleed:** hard_max_loss **17T −$2.23 0%WR** (sole #1) | hard_sl 7T −$0.58
- **Gate volume:** pipeline.log **14,601 SHORT-CONTINUUM blocks**; BTC score 39-50 z=NEUTRAL mass-blocking (score>30)
- **T's claimed cells NOT reproduced on current 30d meta-RSI:** EXTREME+HIGH 45-55 = 66T +$0.11 51.5% (not 24T +$1.71 79.2%); EXTREME+HIGH 45-65 = 95T +$0.29 51.6% (not 38T +$1.45 65.8%); pump-chain- EXTREME RSI>=40 = 64T +$0.17 54.7% (not 18T +$0.96 72.2%). Prior figures were stale/narrow MoE snapshots. Decisions use current 30d.

### Decisions (one per line — EXECUTED)

1. **SHORT_RSI_FLOOR: RAISE 40→45.** 40-45 band = 37T −$2.28 43.2% — confirmed bleed, cut it. Keeps 45-55 open per T while removing the losing 40-45 slice. `hermes_constants.py`
2. **SHORT regime: ALLOW HIGH + keep EXTREME.** HIGH only profitable band is RSI 50-55 (+$0.59 55%). With floor=45 the 14.3% HIGH 40-45 band is cut. `PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED` already False; volatility_gate HIGH pump_chain- multiplier **0.0→1.0** (was stale block). Keep HIGH blocks on accel-300-/mtf-regime-trend-/trend-ride- (0%WR losers). `volatility_gate_v2.py`
3. **SHORT_CONTINUUM: RELAX SCORE_MAX 30→40.** 14.6k blocks, BTC ranging score 39-50 z=NEUTRAL. Documented revisit path. score<=40 allowed regardless of z; >40 still needs STRONG_NEG. `hermes_constants.py`
4. **PUMP_CHAIN_SHORT_RSI_MIN: RAISE 40→45.** Align with floor. 30d EXTREME 40-45 = 15T −$0.35 (stale 14d "75%WR" not reproducible). `hermes_constants.py`
5. **SHORT_NEUTRAL_BLOCK: KEEP True.** NORMAL SHORT 30d = 74T −$2.19. No flat-market SHORT edge.
6. **SHORT_RSI_CEILING=65: KEEP.** 65+ SHORT = 43T −$1.63 — correctly blocked.
7. **SHORT_RSI_HARD_FLOOR=25: KEEP.** Oversold defense — philosophy (BANANA lesson). Not relaxed.
8. **hard_max_loss: STILL #1 SHORT blocker.** 7d 17T 0%WR −$2.23. Broadening entries without exit fix = more volume into broken exit. bug_hunter leverage-aware fix remains critical path for SHORT 7d ≥$0 (Oct 7).

### Root Cause
Prior SHORT market was over-narrow on RSI (floor 40 left a losing 40-45 slice) while the real volume bottleneck was SHORT_CONTINUUM score=30 blocking ranging-BTC SHORTs. HIGH was blocked on a stale48%WR claim despite HIGH 50-55 being the only positive HIGH cell. T's "broader market" intent is correct; the specific claimed WR numbers were stale.

### Fix Applied
- `SHORT_RSI_FLOOR` 40→45, `PUMP_CHAIN_SHORT_RSI_MIN` 40→45, `SHORT_CONTINUUM_SCORE_MAX` 30→40
- volatility_gate HIGH pump_chain- / pump-chain- 0.0→1.0
- Protected flags untouched (CONFLUENCE_REQUIRED, LIVE_TRADING_ENABLED, PM_TRAIL_*, CEO_PROTECTED_FLAGS all verified)
- NEUTRAL block, RSI ceiling, hard floor, continuum filter enabled — all kept

### Verification / Monitor (48h)
| Metric | Before | Target | Deadline |
|--------|--------|--------|----------|
| SHORT 7d PnL | −$1.85 | ≥$0 (needs hard_max_loss fix too) | Oct 7 |
| SHORT-CONTINUUM blocks | 14.6k all-time, mass fire | Down meaningfully | 48h |
| SHORT trades opened | drought (regime NEUTRAL + continuum block) | Volume up in EXTREME/HIGH | 48h |
| HIGH pump-chain- trades | n=0 blocked | n>0 with RSI≥45, WR tracked | 48h |
| hard_max_loss SHORT | 17T 0%WR −$2.23 7d | ≥50% cut via bug_hunter #1 | Oct 11 |

**DELEGATE self_learner:** 48h monitor — SHORT volume by regime×RSI band; flag if HIGH 40-45 leaks (floor failure) or continuum 30-40 band WR <40%.
**DELEGATE bug_hunter:** hard_max_loss leverage-aware fix remains #1 — broadened SHORT market depends on exit fix to convert to PnL.
**DELEGATE signal_analyst:** if continuum 30-40 band shows edge, snapshot params to signal_regime_memory.json; build pump-chain- HIGH RSI 50-55 confluence partner.
