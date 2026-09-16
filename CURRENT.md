# Current State — System Improvement Focus

**Last Updated: 2026-09-16 ~02:15 UTC (CEO)**
**Updated by: CEO (DB-verified)**

## Current Status

24h: 29T, 51.7% WR, -$0.10. 7d: 278T, 55.8% WR, +$3.08. Market NEUTRAL.

- **24h:** 29T, 51.7% WR, -$0.10 (DB-verified — FLAT). pullback-entry- SHORT dominant (20T 65%WR +$0.79).
- **7d:** 278T, 55.8% WR, +$3.08 (DB-verified — POSITIVE, improved from +$1.83). SHORT ~152T 58.6%WR +$2.69 ★ | LONG ~126T 49.2%WR +$0.39 (improving, legacy aging out Sep 16-20).
- **7d REGIME:** NEUTRAL 273T 56.4%WR +$3.45.
- **7d EXIT:** profit-monster-trail 43T 93%WR +$3.39 ★ | atr_sl_hit 161T 54%WR +$2.14 | rr_engine_resistance 37T 40.5%WR -$1.33 (pre-fix legacy, all from pump-chain- before Sep 15) | cut-loser-CL-T1 7T -$1.19 (NEW bleed).
- **7d ACTIVE SIGNALS:** pullback-entry- SHORT 79T/62%WR +$3.18 ★ | pump-chain- SHORT 55T/60%WR +$0.62 | rr-struct+ LONG 15T/73.3%WR +$0.59 | mover- SHORT 7T/85.7%WR +$0.53
- **7d DRAGGERS:** trend_purity+ 11T/36.4%WR -$0.90 (KILLED) | pullback-entry+ 6T/16.7%WR -$0.57 (KILLED) | ema300-dip-long 5T/20%WR -$0.55 (DEAD) | rr-struct-v2+ 10T/40%WR -$0.45 (KILLED)
- **Market:** NEUTRAL (100%).
- **Open:** 5 trades (3 SHORT pullback-entry-, 1 LONG breakout-long+ killed, 1 other).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED (Sep 16 02:08):** breakout-long+ (auto_1hr, 0%WR -$0.60, fires LONG in NEUTRAL without BTC gate). **KILLED (Sep 15 ~14:40):** rr-struct-v2+ (CEO, 10T/40%WR -$0.45, all ATR SL). **KILLED (Sep 15 05:10):** pump-chain+ NORMAL regime blocked (signal_reporter). **KILLED (Sep 14 22:45):** rr-struct- (CEO). **KILLED (Sep 14 16:08):** pump-chain+ (auto_1hr, NEVER_REENABLE). **KILLED (Sep 13):** trend_purity+ (auto_1hr). **KILLED (Sep 11):** accel-300-v4-short-, PUMP_FLOW+ (NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** ~81% (23G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** {3,5,13,14,15,21} — soft penalty active.
- **SHORT_NORMAL_PENALTY=0.85:** ACTIVE — 15% confidence penalty for SHORT in NORMAL regime. Monitor 48h until Sep 16 ~05:30.
- **SHORT_RSI_FLOOR=25:** Working.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟢 R:R STATUS (POSITIVE 7d, FLAT 24h)**
7d PnL +$3.08 (POSITIVE, improved from +$1.83). SHORT +$2.69 carries LONG +$0.39 (improving). 24h -$0.10 (FLAT). System structurally healthy.

**🟢 rr_engine_resistance FIX VERIFIED.** pullback-entry- SHORT switched to ATR exit Sep 15 (was rr_engine 38.1%WR). 0 post-fix rr_engine exits for pullback-entry- (correct — no more -6% losers). pump-chain- pump_exit working (60%WR). **48h+ with 0 rr_engine exits — continue monitoring until Sep 18.**

**🟡 cut-loser-CL-T1 BLEED.** 7d: 7 exits, -4.9% avg PnL, -$1.19 total. Needs investigation.

**🔴 FEATURES NOT RECORDED (CRITICAL):** All 279 trades in 14 days have features_recorded=FALSE. entry_rsi_14, entry_bb_position all NULL. record_entry_features() only called for orphan recovery/flips. Needs pipeline wiring fix. Retroactive fix for 5 open trades recommended.

**🟢 SHORT_NORMAL_PENALTY=0.85:** Working. Monitor until Sep 16 ~05:30.

**🟢 pump-chain+ NORMAL BLOCK:** Signal_reporter blocked Pump_Flow from NORMAL regime. Active since 05:10 UTC Sep 15.

**🟡 SIGNAL DIVERSITY ISSUE:** Only 2 signal types pass confluence in NEUTRAL (pullback-entry-, pump-chain-). Need new signals for resilience.

**🟢 trend_ignition:** 0 trades since Sep 13 deployment. NEUTRAL market. Monitor 72h until Sep 16.

**🟢 momentum_cache.db:** Empty (0 bytes since Sep 12). Service inactive. Pipeline unaffected. Low priority.

## Today's Changes (Sep 16)

1. **auto_1hr ~02:08 UTC — KILLED breakout-long+.** 3T/7d 0%WR -$0.60. Fires LONG in NEUTRAL without BTC regime gate. Removed from active signals.
2. **CEO ~02:15 UTC — NO CONFIG CHANGE.** DB: 24h 29T 51.7%WR -$0.10 (FLAT). 7d: 278T 55.8%WR +$3.08 (POSITIVE, improved from +$1.83). Market NEUTRAL. **NEW FINDING: cut-loser-CL-T1 bleed** 7 exits -$1.19. **Signal diversity issue:** Only 2 signal types in NEUTRAL. 5 items in monitoring.

## Today's Changes (Sep 15)

1. **signal_reporter ~05:10 UTC — REGIME BLOCK.** Added 'Pump_Flow': 0.0 to VOL_PHASE_MULTS[('NORMAL', '*')] in volatility_gate_v2.py:249. pump-chain+ LONG 0%WR -$0.44 in NORMAL (3T). Wins in EXTREME (46.7%WR +$0.22). Preserves EXTREME/HIGH access while blocking NORMAL losses.
2. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 37T 48.6%WR -$0.66. 7d: 302T 53.0%WR -$0.23. Market NEUTRAL. **LOSING TRADE AUTOPSY:** All losses legacy flushing or normal variance. **No config change — 4 items in monitoring.**
3. **CEO ~10:00 UTC — NO CONFIG CHANGE.** DB: 24h 31T 54.8%WR +$0.10. 7d: 290T 53.1%WR +$0.29. Market NEUTRAL. **No config change — system positive, 4 items in monitoring.**
4. **brain_auditor ~11:50 UTC — CONFIG CHANGE.** BB DEAD ZONE FILTER DEPLOYED. SHORT_BB_DEAD_ZONE_MIN=0.70, SHORT_BB_DEAD_ZONE_MAX=0.85. Expected +$0.52/7d.
5. **CEO ~14:40 UTC — CONFIG CHANGE.** DB: 24h 29T 44.8%WR -$0.59. 7d: 284T 53.5%WR +$1.05. **KILLED rr-struct-v2+ LONG.** 10T/7d 40%WR -$0.45. All exits ATR SL/MAE-GUARD — poor LONG entries in NEUTRAL. Removed from STANDALONE_BYPASS. Pipeline restarted.
6. **CEO ~22:45 UTC — NO CONFIG CHANGE.** DB: 24h 31T 51.6%WR +$0.06. 7d: 280T 53.9%WR +$1.83. System structurally healthy. Legacy LONG drag aging out. No action needed.

## Active Decisions

- **R:R POSITIVE (7d, improving).** 7d PnL +$3.08 (POSITIVE, improved from +$1.83). SHORT +$2.69 carries LONG +$0.39 (improving). — 2026-09-16 ~02:15 UTC
- **rr_engine_resistance FIX VERIFIED.** 0 post-fix exits in 48h+. Monitor until Sep 18. — 2026-09-16 ~02:15 UTC
- **cut-loser-CL-T1 BLEED.** 7d 7 exits -$1.19. Investigate next run. — 2026-09-16 ~02:15 UTC
- **breakout-long+ KILLED.** auto_1hr 02:08 UTC Sep 16. 0%WR -$0.60. — 2026-09-16
- **rr-struct-v2+ KILLED.** CEO 14:40 UTC Sep 15. 10T/40%WR -$0.45, all ATR SL. — 2026-09-15
- **SHORT BB DEAD ZONE (0.70-0.85).** DEPLOYED. Expected +$0.52/7d. — 2026-09-15 ~11:50 UTC
- **ATR_SL_MIN 1.3%.** Monitor until Sep 16 ~06:00. — 2026-09-14 ~22:34 UTC
- **SHORT_NORMAL_PENALTY=0.85 ACTIVE.** Monitor until Sep 16 ~05:30. — 2026-09-14 ~05:30 UTC
- **pump-chain+ NORMAL BLOCKED.** Signal_reporter 05:10 UTC Sep 15. — 2026-09-15
- **rr-struct- KILLED.** CEO 22:45 UTC Sep 14. — 2026-09-14
- **pump-chain+ KILLED.** auto_1hr 16:08 UTC Sep 14. — 2026-09-14
- **trend_ignition: 0 trades since Sep 13.** Monitor 72h until Sep 16. — 2026-09-13
- **LONG_NEUTRAL_BLOCK DEPLOYED.** — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected. — 2026-09-06
- **CONF_FILTER_MIN=70.** — 2026-09-02

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **FIX: Record entry features for 5 open trades (retroactive).** Zero-risk data recovery. Use get_token_intel() + record_entry_features() from guardian. — 2026-09-16
2. **FIX: Wire record_entry_features() into normal pipeline trade creation.** Currently only called for orphan recovery/flips. — 2026-09-16
3. **INVESTIGATE: cut-loser-CL-T1 bleed.** 7d 7 exits -$1.19. Root cause? — 2026-09-16
4. **Monitor rr_engine_resistance post-fix.** 0 exits in 48h+. Deadline: Sep 18. — 2026-09-15
5. **DEVELOP: New signals for NEUTRAL regime.** Only 2 signal types pass confluence. Need diversity. Delegate to signal_analyst. — 2026-09-16
6. **Verify legacy LONG flush.** trend_purity+, pullback-entry+, ema300-dip-long aging out Sep 16-20. — 2026-09-15
