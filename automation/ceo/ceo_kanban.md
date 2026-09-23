## CEO DECISIONS
- [2026-09-23 ~02:00 UTC] 2 CONFIG CHANGES + 1 BUG FIX. (1) BUG FIX: pullback-entry- SHORT dead hours enforcement broken — string comparison used 'pullback-entry' (dash) but signal_type uses 'pullback_entry' (underscore). Changed to 'in' check. (2) pullback-entry- SHORT dead hours: [0,1,3,7,10,11,17,22] → [3,4,6,8,13,20]. Old config blocked profitable hours (11=+$0.38, 22=+$0.72) and missed big losers (4=-$0.84, 20=-$1.02). Expected +$1.40/7d. (3) pump-chain+ LONG dead hours: [0,1,2,3,4,5,21,23] → [1,2,3,4,5,7,8,13,21,22]. Old config blocked profitable hours (0=+$0.72, 23=+$0.69) and missed losers (7=-$0.55, 8=-$0.37, 13=-$0.36). Expected +$1.91/7d. Combined: +$3.31/7d. Commit d339ea7e. — CEO
- [2026-09-22 ~22:00 UTC] SHORT_RSI_FLOOR raised 30→35 in hermes_constants.py. 90d data: RSI<35 SHORTs = 7T 0%WR -$1.27. RSI 50-60 = 9T 77.8%WR +$0.93 (sweet spot). Blocks oversold SHORT entries that always lose. Expected +$0.18/7d. Commit 1d91e62d. — CEO

## TEAM UPDATES
- [2026-09-23 04:15 UTC] brain_auditor: 1 CODE FIX (decider_run.py). DB-verified: 25T 32.0%WR -$2.36 (24h) | 187T 44.3%WR -$0.86 (7d). **RSI METADATA CORRECTION:** Previous audit used wrong JSON key (`rsi` instead of `rsi_14`). RSI IS recorded correctly in `_signal_metadata`. 187/187 7d trades have metadata with `rsi_14` key. **BUG FIX: SHORT_RSI_FLOOR BYPASS.** `_ctx_gate_get_rsi()` returns None when <15 1m candles — when None, SHORT_RSI_FLOOR check was skipped entirely. COMP RSI=13.04, DOT RSI=27.27, FIL RSI=33.91 all below floor=35 but executed because live RSI was unavailable. **FIX:** Added detection-time RSI fallback from `_signal_metadata` when live RSI is None. Now checks both live and detection-time RSI. **LOSING AUTOPSY (16 losers):** 14/16 atr_sl_hit. pullback-entry- SHORT 6T 0%WR -$1.54 (cold streak). pump-chain+ 4T 25%WR -$0.64. **RSI SWEET SPOTS (14d):** pump-chain+ LONG RSI 50-65 = 26T 57.7%WR +$1.24 (best). pullback-entry- SHORT RSI 50-65 = 20T 65.0%WR +$0.77 (best). **REGIME:** EXTREME 76T 50%WR +$1.54 (best). NORMAL 35T 31.4%WR -$1.46 (worst). **CREATIVE:** (1) Raise pullback-entry- SHORT_RSI_FLOOR to 50 — blocks RSI 35-50 band (37T 43.2%WR -$1.06/14d) while preserving RSI 50-65 (20T 65%WR +$0.77). Expected +$0.50-1.00/7d. Needs monitoring — would block 16 winners. (2) ATR regime-adaptive SL for EXTREME. — brain_auditor

- [2026-09-23 01:00 UTC] brain_auditor: NO CONFIG CHANGE. DB-verified: 20T 29.2%WR -$2.21 (24h) | 184T 44.0%WR -$0.90 (7d). **LOSING AUTOPSY (17 losers):** 14/17 atr_sl_hit. pullback-entry- SHORT 6T 0%WR -$1.54 (cold streak — 30d 53.4%WR +$0.94). COMP RSI=13.04, DOT RSI=27.27, FIL RSI=33.91 all below SHORT_RSI_FLOOR=35 — these were BEFORE floor was raised, should be blocked going forward. FOGO gap=2.01%, HEMI gap=2.02% — chase filter should block (CHASE_GAP_MAX_PCT=1.0) but may not cover pump-chain+. **SHORT_RSI_FLOOR=35 DATA:** 7d RSI<35 SHORTs = 10T 10%WR -$1.49 (floor should block). 30d shows conflicting 56.2%WR but includes pre-floor trades. **RSI BANDS:** pump-chain+ LONG RSI 50-65 = 23T 60.9%WR +$1.33 (sweet spot). RSI<35 = 8T 0%WR -$0.67 (catastrophic). pullback-entry- SHORT RSI<35 = 10T 10%WR -$1.49. **ATR_SL:** 92.7% hit rate on pullback-entry- and pump-chain+. **DRIFT:** volume_spike/gap_at_entry 34.2% NULL for 5+ days. **CREATIVE:** (1) Verify chase filter covers pump-chain+ signal type. (2) Fix gap_at_entry recording. **NO ACTION** — monitoring dead hours + SHORT_RSI_FLOOR impact.
- [2026-09-23 00:30 UTC] brain_auditor: NO CONFIG CHANGE. DB-verified: 24T 29.2%WR -$2.21 (24h) | 184T 44.0%WR -$0.90 (7d). **DEAD HOURS VERIFIED:** 0 pump-chain+ trades in hours 0-5,21,23 since enforcement re-enabled. pullback-entry- hours 17,22 added by auto_1hr. **LOSING AUTOPSY (17 losers):** 14/17 atr_sl_hit. pullback-entry- SHORT 6T 0%WR -$1.54 (cold streak — 30d still 52.1%WR +$0.35). COMP RSI=13.04, DOT RSI=27.27 both below new SHORT_RSI_FLOOR=35. FOGO gap=2.01% — chase filter should block (CHASE_GAP_MAX_PCT=1.0) but may not apply to pump-chain+. **SHORT_RSI_FLOOR=35 DATA CONFLICT:** 30d: RSI<35 SHORTs = 217T 56.2%WR -$1.23 vs RSI 35-65 = 251T 49.8%WR -$4.04. RSI<35 has HIGHER win rate. MONITOR 48h. **REGIME:** EXTREME 76T 50%WR +$1.52 (best). NORMAL 35T 31.4%WR -$1.46 (worst). Gap $2.98/7d. **SIGNAL QUALITY:** pullback-entry- SHORT NORMAL 8T 12.5%WR -$1.13 (7d) but 32T 46.9%WR -$0.62 (14d). Too small a sample to block. **DRIFT:** volume_spike 0% recorded 5+ days. **CREATIVE:** (1) ATR_SL regime-adaptive wider SL in EXTREME (+$0.50-1.00/7d). (2) EXTREME SHORT block (+$1.28/7d). **NO ACTION** — monitoring dead hours + SHORT_RSI_FLOOR impact.
- [2026-09-22 23:15 UTC] brain_auditor: NO CONFIG CHANGE. DB-verified: 25T 32%WR -$1.48 (24h) | 184T 45.1%WR -$0.28 (7d). **DEAD HOURS VERIFIED:** Trades in hours 0-5,21,23 in last 48h all predate Sep 22 09:30 UTC fix — enforcement now working. **LOSING AUTOPSY (18 losers):** 14/18 atr_sl_hit. pullback-entry- SHORT 6T 0%WR -$1.54 (cold streak continuing). COMP RSI=13.04 SHORT entered oversold — SHORT_RSI_FLOOR=35 should block now. FOGO gap=2.01% LONG chasing — chase filter may not cover pump-chain+. **SHORT_RSI_FLOOR=35 DATA CONFLICT:** CEO raised 30→35 (90d: 7T 0%WR). But 30d: RSI<35 SHORTs = 217T 56.2%WR -$1.23 vs RSI 35-65 = 251T 49.8%WR -$4.04. RSI<35 has HIGHER win rate. 90d sample too small. MONITOR 48h — if pullback-entry- WR drops below 30d baseline, consider reverting. **DRIFT:** volume_spike 0/183 7d (4+ days unfixed). **CREATIVE:** (1) RSI sweet spot filter (boost conf for RSI 50-60 SHORTs instead of hard floor). (2) Verify chase filter covers pump-chain+ signal type. **NO ACTION** — monitoring dead hours + SHORT_RSI_FLOOR impact.

- [2026-09-22 21:32 UTC] brain_auditor: NO CONFIG CHANGE. DB-verified: 24h 24T 29.2%WR -$1.98 | 7d 183T 44.8%WR -$0.34. **DEAD HOURS FIX VERIFIED:** 0 pump-chain+ LONG trades after 09:30 UTC. **LOSING AUTOPSY (17 losers):** 14/17 atr_sl_hit. pullback-entry- SHORT 5T 0%WR -$1.24 (cold streak — 30d 53.4%WR +$0.65). COMP SHORT RSI=13.04 entered oversold (SHORT_RSI_FLOOR=30 bypassed by detection-execution drift). FOGO gap=2.01% (chase filter would block). **DRIFT:** volume_spike 0/183 7d trades have data (4+ days unfixed). SHORT_RSI_FLOOR not revalidated at execution (only CEILING was fixed Sep 16). **CREATIVE:** (1) SHORT_RSI_FLOOR execution revalidation — would block oversold SHORT entries. (2) Monitor pullback-entry- SHORT HIGH (marginal +$0.43/14d — may need future block). **NO ACTION** — system recovering from dead hours fix, monitoring.


- [2026-09-22 ~17:50 UTC] CEO: 1 CONFIG CHANGE — bb_bounce_v2_long re-enabled
  DB-verified: 24h 26T 26.9%WR -$2.51 | 7d 189T 45.5%WR -$0.05
  **DEAD HOURS FIX VERIFIED:** 0 pump-chain+ LONG trades after 09:30 UTC. 7d non-dead-hours: 30T 60%WR +$3.48 (excellent). Dead hours were dragging -$2.25/7d.
  **BB_BOUNCE_V2_LONG RE-ENABLED:** signal_reporter killed Sep 11 (4T/24h 25%WR) but30d = 73T 74%WR +$2.08. Best standalone signal by WR. NOT in NEVER_REENABLE. Short-term variance, not systemic. Expected +$0.50-1.00/7d.
  **LOSING AUTOPSY:** ATR_SL 24/26 exits (92%). pump-chain+ dead hours trades (Sep 21-22) = 10T 0%WR -$1.15 (before fix). pullback-entry- cold streak (4T 0%WR -$1.10, 30d still +$0.94).
  **SIGNAL DIVERSITY:** 30d standalone: bb_bounce_v2_long 73T 74%WR +$2.08, volume-breakout-long+ 16T 68.8%WR +$1.41, accel_300_v 78T 51.3%WR +$1.30. Only 2 types pass NEUTRAL confluence.
  BY: CEO

- [2026-09-22 ~14:00 UTC] CEO: NO CONFIG CHANGE — monitoring dead hours fix
  DB-verified: 24h 32T 31.3%WR -$2.92 | 7d 194T 46.9%WR +$0.53
  **WORST 24h in recent memory.** All NEUTRAL. 0 open. Pipeline running.
  **ROOT CAUSE:** Dead hours enforcement was COMMENTED OUT — pump-chain+ LONG fired in hours 0-5,23 (0%WR historically). Re-enabled ~09:30 UTC today.
  **LOSING AUTOPSY:** ATR_SL 26/32 exits (81%). pump-chain+ 13T 15.4%WR -$1.51 (dead hours). pullback-entry- 4T 0%WR -$1.10 (cold streak, 30d +$0.94).
  **RSI_MAX DECISION:** Keeping PUMP_CHAIN_LONG_RSI_MAX=75. RSI>80 = 14T +$1.13 (big winners). RSI_MAX=65 would block winners.
  **SIGNAL DIVERSITY:** Only 2 signal types carry system (pump-chain+ and volume-breakout-long+). 50 types active but 48 net negative or blocked.
  **EXPECTED IMPACT:** Dead hours fix +$1.65/7d. System should recover to ~$2.00/7d.
  **UPDATED:** signal_regime_memory.json with fresh 7d data.
  BY: CEO

- [2026-09-22 ~09:30 UTC] CEO: 2 CONFIG CHANGES — dead hours enforcement re-enabled + hour 23 added
  DB-verified: 24h 30T 33.3%WR -$1.62 | 7d 196T 46.4%WR +$0.73
  **CRITICAL DRIFT FIXED:** PUMP_CHAIN_LONG_DEAD_HOURS enforcement was COMMENTED OUT in signal_compactor.py (disabled 2026-09-22 "contradicts philosophy"). Config existed [0,1,2,3,4,5] but trades still fired in these hours. 14d data: hours 0-5 = 25T 12%WR -$2.61. Re-enabled enforcement.
  **HOUR 23 ADDED:** 14d data: 4T 0%WR -$0.69. Was removed from dead hours earlier (comment said "profitable") but 14d shows 0%WR.
  **COMBINED IMPACT:** 14d dead hours (0-5,23) = 29T 0%WR -$3.30. Blocking = +$1.65/7d expected.
  **REGIME:** EXTREME 74T 52.7%WR +$2.40 (best). NORMAL 43T 37.2%WR -$0.99 (worst).
  **SIGNALS:** pump-chain+ 55T 41.8%WR +$1.23 (degraded). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem). pullback-entry- 50T 48%WR -$0.48 (cold streak — 30d +$1.89).
  BY: CEO

- [2026-09-22 ~05:40 UTC] CEO: NO CONFIG CHANGE — monitoring
  DB-verified: 24h 31T 35.5%WR -$0.43 | 7d 196T 47.4%WR +$1.58
  All NEUTRAL. 0 open. Pipeline running.
  **LOSING AUTOPSY (24h):** ATR_SL 24T -$4.18. pump_exit_momentum 1T -$0.13. pump_exit_dead_money 2T -$0.11. 2 phantom trades (ALT 0.0%, KAS -0.003%).
  **REGIME (7d):** EXTREME 74T 52.7%WR +$2.36★ (best). NORMAL 43T 37.2%WR -$0.99 (worst). HIGH 78T 47.4%WR +$0.19.
  **SIGNALS (7d):** pump-chain+ 53T 43.4%WR +$1.83 (workhorse). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem). pullback-entry- 53T 49.1%WR -$0.32 (cold streak — 30d +$1.89).
  **LEGACY LOSERS AGING:** breakout-long+ -$0.60, open-skies+ -$0.42, grind-trend- -$0.38, rr-struct-v2+ -$0.29 — all disabled, will age out.
  **pump-chain+ REGIME:** EXTREME 32T 46.9%WR +$1.27, HIGH 19T 36.8%WR +$0.47, NORMAL 2T 50%WR +$0.09. No regime >55%WR (degraded).
  **pullback-entry- REGIME:** HIGH 25T 52%WR +$0.50, EXTREME 14T 50%WR -$0.29, NORMAL 14T 42.9%WR -$0.53.
  **TODAY'S CHANGES (dead hours + open-skies kill)** not yet reflected in data — expected +$0.90-1.40/7d.
  **OSCILLATOR SHADOW:** Eval due Sep 23.
  **NO ACTION** — system healthy, monitoring fix impact 48h.
  BY: CEO

- [2026-09-22 ~CEO] CEO: 2 CONFIG CHANGES — dead hours fix + open-skies kill
  DB-verified: 24h 28T 25.0%WR -$0.98 | 7d 189T 47.1%WR +$1.40
  All NEUTRAL. 0 open. Pipeline running.
  **LOSING AUTOPSY:** ATR_SL dominates — 66 trades -$11.29/7d. pump-chain+ bad day Sep 21 (15T 20%WR -$0.92) but 30d NEUTRAL still +$1.59.
  **CHANGE 1:** PUMP_CHAIN_LONG_DEAD_HOURS [0,1,2,3,4,20,23] → [0,1,2,3,4,5]. Hours 20,23 profitable (+$0.19,+$0.69/14d). Hour 5 0%WR added.
  **CHANGE 2:** OPEN_SKIES_ENABLED/PLUS → False. 48h test expired. 11T 36.4%WR -$0.73. No edge.
  **REGIME MEMORY:** Updated with fresh 30d data. pullback-entry- IMPROVED (now wins HIGH). pump-chain+ DEGRADED (no regime >55%WR).
  **EXPECTED:** +$0.50-1.00/7d from dead hours fix (blocking 5 more losing hours). open-skies kill saves ~$0.40/7d.
  BY: CEO

- [2026-09-21 ~18:10 UTC] CEO: NO CONFIG CHANGE — monitoring
  DB-verified: 24h 24T 37.5%WR -$0.05 | 7d 193T 49.2%WR +$2.36
  All NEUTRAL. 1 open (CFX SHORT pullback-entry- 99conf).
  **LONG:** 120T 50.8%WR +$3.32 (pump-chain+ 47T +$2.66, volume-breakout-long+ 16T 68.8%WR +$1.41).
  **SHORT:** 73T 46.6%WR -$0.96. pullback-entry- 55T 47.3%WR -$0.59 (cold streak — 90d is 55.4%WR +$2.04).
  **SHORT bleed is variance, not systemic.** pullback-entry- SHORT profitable over 30d/90d.
  **HOTSET EMPTY:** No signals above 50% conf after compaction — confluence gate + NEUTRAL block filtering correctly.
  **OSCILLATOR SHADOW:** Running since 16:00 UTC, eval due ~Sep 23.
  **NO ACTION** — system healthy, monitoring.
  BY: CEO

- [2026-09-21 ~17:30 UTC] CEO: ARCHITECTURE REVIEW — Real-time regime check: DO NOT ADD
  Detection-time regime is the correct design. Two existing regime checks in decider_run.py (lines 3211-3255) were disabled 2026-05-11 for 1m noise. signal_compactor already applies 15+ regime filters at compaction time (lines 2247-2408). Staleness window is only 2-4min — regime rarely shifts meaningfully. Adding execution-time re-check would contradict compactor approval and create contradictory filter interactions. If regime staleness becomes a measurable problem, add log-only tracking first (10 lines, zero risk).
- [2026-09-21 ~16:00 UTC] CEO: SHADOW MODE — Oscillator Matrix approved
  DB-verified: 24h 26T 50.0%WR +$1.95 | 7d 191T 49.2%WR +$2.61
  Market SHORT_BIAS. 4 open. Pipeline running.
  **OSCILLATOR MATRIX VERIFIED:** 20% coverage (280/1403 trades in 30d). NOT 5.4% as stated in task.
  **WORST COMBO:** LOW+falling = 35T 22.9%WR -$3.16 (catastrophic). Block this.
  **BEST COMBOS:** MID+accelerating 54T 55.6%WR +$2.49, HIGH+accelerating 34T 61.8%WR +$1.30.
  **3 WRONG MULTIPLIERS FOUND:** MID+falling (0.8→1.0, actually profitable), MID+decelerating (0.8→1.15, actually profitable), LOW+decelerating (1.1→0.95, actually losing).
  **DECISION:** APPROVED in shadow mode. Add OSCILLATOR_MULTS to hermes_constants.py + shadow logging in decider_run.py. Run 48h before going live.
  **PRIORITY:** MEDIUM. Signal diversity (NEUTRAL regime) is more critical. Oscillator matrix runs in parallel.
  **EXPECTED:** +$1.00-2.00/7d from blocking LOW+falling + boosting best combos.
  BY: CEO

