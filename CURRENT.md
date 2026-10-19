# Current State — brain_auditor Run Oct 19 05:35 UTC

**Last Updated: 2026-10-19 05:35 UTC**
**Updated by: brain_auditor — 0 config changes (soak #16), precheck CONF fix verified PASS**

## PIPELINE STATUS (05:35 UTC)

- **Trading LIVE** with 0.3x size-reduce (7d WR 33.8% < 37 AND 7d PnL −$3.79 < $0 — both resume conditions still failing). Resume ~Oct 23.
- **24h 13T 6W −$0.12 (46.2%). | 7d 195T 66W −$3.79 (33.8%). | 30d 747T 330W −$3.53 (44.2%).**
- **0 open.** Regime: SHORT_BIAS (66/127 tokens), NORMAL vol, BTC trend_quality UP, above EMA300.
- Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #16 (45min follow-up to 04:45)

**0 config changes** (soak discipline; resume-day stack already 12+ unvalidated).

**LAST-RUN VERIFY:**
- ai_trader_precheck CONF argv fix — **PASS** (live output shows regime gate evaluating with conf instead of fail-open)
- SHORT floor-45 — HOLDING (0 trades RSI 35-45 SHORT since Oct 18 revert)
- ai-trader+ EXTREME LONG conf-demote shadow — n=0 since ship, collecting, re-eval at n≥20
- bb-bounce-v2-long+ kill-watch — CLEARED (ETC trail +$0.05; 3d still 8T 3W −$0.25 monitor)

**STEER-001 VERIFIED (5 wrong-side losses >2%):**
- BTC SHORT −5.36% at EMA300 floor (MFE≈0, squeezed 26m; manual LONG 7min later +4.31%)
- ETC −4.13% HML 6m chop, BANANA −2.24%, IO −2.11% TAT — alt LONGs in SHORT_BIAS chop
- PUMP SHORT −2.10% armed-reverse (MFE 0.58% → ATR SL, EXTREME)
- All covered by existing entry defenses — no new filter (n too small, soak)

## ATR-SL MFE PARADOX (3rd consecutive run — THE remaining lever)

| Cohort | n | PnL | Note |
|--------|---|-----|------|
| atr_sl_hit MFE≥0.40, 7d | 20/52 | −$0.98 | trail threshold reached, still ATR SL |
| Same, 14d | 29 | −$1.67 | 24/29 EXTREME, avg MFE 0.82% |
| pump-chain- slice, 7d | 11 | −$0.48 | biggest signal slice |
| False-kill risk pool | 97 winners | +$11.19/14d | trail winners with MFE≥0.40 — unknown how many dip below BE after arm |

**CREATIVE PRE-REGISTERED: EXTREME post-arm breakeven-ratchet SHADOW** — zero-behavior spec in creative_improvements.json; flip criteria save>$1 AND fk<10% AND candle-OOS PASS. **Added to Oct 23 resume-day stack — NOT shipped now.**

## WEALTH GAP (7d) — UNCHANGED

| Family | Trades | WR | PnL |
|--------|--------|-----|-----|
| Trail family (PM/atr_trail/rr/trail_sl) | ~60 | ~90% | **+$5.70** |
| hard_max_loss + atr_sl_hit + hard_sl | 108 | 0.9% | −$8.84 |

## ACTIVE SHADOWS

- ai-trader+ EXTREME LONG conf-demote — n=0 since Oct 18 16:45, collecting
- pp-conditional penalty floor — 637 events in floor_admit_shadow.jsonl
- MFE-CUT / bb-bounce TAT (single-condition) / contrarian PROMOTE — collecting
- RR-engine would-blocks — ~10/hr

## NEXT

- Oct 23 resume-day CEO eyeball: 12+ unvalidated changes + BE-ratchet shadow spec
- ai-trader+ EXTREME re-eval at n≥20
- contrarian pump-chain- PROMOTE re-eval ~Oct 29
- hl_copy NORMAL recheck at n≥10
- Infra gap: trail_activated bool not stamped to trade metadata (verify arm from DB impossible; PM close-path candidate)
- self_learner candle-OOS still missing — brain_auditor runs scoped sims when needed
