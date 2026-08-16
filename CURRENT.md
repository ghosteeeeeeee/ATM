# Current State — System Improvement Focus

**Last Updated:** 2026-08-16 16:16 UTC  
**Updated by:** CEO (33rd run — verified)

## What We're Working On

**Completed:** All eval windows FINALIZED. PM_TRAIL dist 0.15% WORKING (66.7% WR +$1.09/48h). All legacy losers killed. range_finder+ DISABLED (0.12:1 R:R). range_finder- DISABLED (0% WR SHORT). Signal starvation fix applied (hl_copy_trader bypass, NEUTRAL relax). COIN_TRACKER_HOT RE-ENABLED with MIN_COMPOSITE 55.

**Current status:** Signal quality push. 24h 50T -$0.57 (36.0% WR — legacy ct-hot+ draining). 48h: 92T -$0.80 (41.3% WR). 7d 436T -$2.61 (48.4% WR). Today Aug16: 27T -$0.72 (22.2% WR — worst day, ct-hot+ 10T -$0.51 + 4 phantom + 13 real). 3 open SYRUP LONG r2-trend-long5 +$0.05, KAS return_exhaustion +$0.00, W r2-trend-long4 -$0.01. ATR_SL 48h: 36T 2.8% WR -$2.37 (avg -0.663%). PM_TRAIL 48h: 36T 66.7% WR +$0.98 (avg +0.262%). R:R 0.40:1 (PM_TRAIL +0.262% vs ATR_SL -0.663%). ct-hot+ DISABLED AGAIN — MIN_COMPOSITE 55 still bleeding. SIGNAL_FILTER_SPEED_MIN 40. SHORT side dead (8.3% WR). Regime NEUTRAL.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** — 2026-08-13
- **Context layers separated:** stable (AGENTS.md) vs current (this file) vs history (logs, Hebbian). — 2026-08-13
- **Direction Lock: 30min after catastrophic loss (4+/5).** — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** — 2026-08-13
- **Blacklist testing complete.** 77 tokens tested, 0 KEEP. Signal filters are the bottleneck. — 2026-08-15
- **PM_TRAIL breakeven guard REMOVED.** Was capping avg exit at 0.24% despite 0.40% activation. Now exits at trail_floor. — 2026-08-16
- **PM_TRAIL_ACTIVATE lowered 0.40%→0.30%.** More trades qualify for trailing. Floor = -0.20%. — 2026-08-16
- **PM_TRAIL_DISTANCE tightened 0.60%→0.50%.** Protect gains after breakeven guard removal. — 2026-08-16
- **PM_TRAIL_DISTANCE_PCT reverted 0.50%→0.15%.** Per user request (commit a0a971a). Working: 66.7% WR +$1.09 (avg +0.273%). Floor = +0.15%. Keep. — 2026-08-16
- **All legacy losers killed.** range_breakout+, continuation+, wave_catcher+, trend_momentum disabled. — 2026-08-16
- **ATR_TP_K_MULT reverted 2.5→2.0.** 2.5x TP unreachable (1 hit/48h). — 2026-08-16
- **COIN_TRACKER_HOT_ENABLED DISABLED.** 25T/24h 36% WR -$0.56. ATR_SL 18T 0% WR -$1.23 dominates. Re-enable when WR >55% with 20+ trades. — 2026-08-16
- **ATR_SL_MAX widened 2.5%→3.0%.** Reduced avg loss per hit (-0.76%→-0.71%) but NOT hit count. Entry quality is the bottleneck. — 2026-08-16
- **hl_copy_trader added to STANDALONE_BYPASS.** Copy-trading signal blocked by confluence gate in NEUTRAL. Now passes standalone. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Allows single-type signals when regime is NEUTRAL (addresses starvation). — 2026-08-16
- **RANGE_FINDER_ENABLED DISABLED.** 9T/7d 33.3% WR -$0.14. R:R 0.12:1. — 2026-08-16
- **RANGE_FINDER_MINUS_ENABLED DISABLED.** 3T/48h SHORT 0% WR -$0.12. Bleeds both directions. — 2026-08-16
- **RANGE_FINDER_SHORT_ENABLED DISABLED.** All range_finder variants dead. — 2026-08-16
- **SHORT side is a net drag.** 12T/48h 8.3% WR -$0.40. All range_finder SHORT killed. Do NOT enable new SHORT signals until regime shifts to SHORT_BIAS. — 2026-08-16
- **COIN_TRACKER_HOT DISABLED AGAIN.** MIN_COMPOSITE 55 still bleeding — 10T opened today 18.2% WR -$0.51. Real system (excl ct-hot+) 43.2% WR nearly flat. Re-enable only with composite 70+ after backtest. — 2026-08-16
- **SIGNAL_FILTER_SPEED_MIN raised 30→40.** ATR_SL 37T/48h 2.7% WR -$2.45 dominates. Higher speed min = fewer but better entries. NEUTRAL override at15 unchanged. — 2026-08-16

## Known Limitations

- **No session handoff protocol** — context lost on session end. — 2026-08-13
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS for most tokens even when 15m/4h is NEUTRAL. May need higher-timeframe regime check. — 2026-08-16
- **Phantom trades** — guardian_orphan creates trades with empty signal from HL sync. ~6T/day, -$0.10. Root cause in hl-sync-guardian. — 2026-08-16

## System Improvement Backlog

### Worth Doing
1. Investigate phantom trades (guardian_orphan with empty signal) — root cause in hl-sync-guardian
2. Consider higher-timeframe regime for confluence relaxation (1m too noisy)
3. Extend checkpoint_utils.py to write human-readable progress summaries
4. Create contextmap.md for the 58-signal ecosystem
5. Formalize 4-layer context separation in AGENTS.md

### Implemented (no action)
- Weather Vane Components 1-3 all live (2026-08-15). Shield trail 0.30%, force-close 30min on counter-regime losers.

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies — just markdown files and minor script changes
- Don't duplicate Z-Score + Acceleration filter — already in decider_run.py

## Stop Conditions

- CURRENT.md >50 lines → trim
- No update in 48h → investigate
- Agents stop reading → check orchestrator prompts

## Next Actions

1. **Monitor daily trades post ct-hot+ disable.** Should drop from 27 to ~13-17 real trades. Must stay >10T. — 2026-08-16
2. **Monitor SIGNAL_FILTER_SPEED_MIN 40.** Daily trades must stay >20T. If drops below, revert to 35. — 2026-08-16
3. **SHORT side audit.** All SHORT signals dead (8.3% WR 48h). Do NOT re-enable until regime shifts to SHORT_BIAS. — 2026-08-16
4. **PM_TRAIL 0.15% dist monitoring.** Working at 66.7% WR. Must hold >60% WR over 48h. — 2026-08-16
5. **Phantom trades.** 4T today -$0.14, root cause in guardian_orphan (hl-sync-guardian). Backlog item. — 2026-08-16
6. **ATR_SL entry quality.** 36T/48h, 2.8% WR -$2.37. SIGNAL_FILTER_SPEED_MIN 40 should reduce hits. Monitor. — 2026-08-16
7. **Stars7d intact:** return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, r2-trend-long2 17T 64.7%. — 2026-08-16
