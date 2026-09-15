# Current State — System Improvement Focus

**Last Updated: 2026-09-15 ~14:40 UTC (CEO)**
**Updated by: CEO (DB-verified)**

## Current Status

24h: 29T, 44.8% WR, -$0.59. 7d: 284T, 53.5% WR, +$1.05. Market NEUTRAL.

- **24h:** 29T, 44.8% WR, -$0.59 (DB-verified). pullback-entry- 8T SHORT -$0.43 (variance). rr-struct-v2+ 4T LONG -$0.03 (KILLED this run). pump-chain- 4T SHORT -$0.15. pump-chain+ 1T LONG +$0.28.
- **7d:** 284T, 53.5% WR, +$1.05 (DB-verified — POSITIVE, improved from +$0.29). SHORT 152T 58.6%WR +$2.69 ★ | LONG 132T 47.0%WR -$1.64 (legacy drag ages out Sep 16-20).
- **7d REGIME:** NEUTRAL 278T 54.3%WR +$1.42.
- **7d EXIT:** profit-monster-trail 52T 92.3%WR +$3.83 ★ | atr_sl_hit 154T 50%WR +$0.35 | rr_engine_resistance 37T 40.5%WR -$1.33 (post-fix improving) | cut-loser-CL-T1 19T 0%WR -$2.90 (legacy).
- **7d ACTIVE SIGNALS:** pullback-entry- 67T/59.7%WR +$2.21 ★ | pump-chain- 55T/60%WR +$0.62 | rr-struct+ 15T/73.3%WR +$0.59 | mover- 7T/85.7%WR +$0.53
- **7d DRAGGERS:** trend_purity+ 11T/36.4%WR -$0.90 (KILLED) | ema300_dip_short 5T/0%WR -$0.61 (DEAD) | pullback_entry+ 6T/16.7%WR -$0.57 (KILLED) | ema300-dip-long 5T/20%WR -$0.55 (DEAD) | bb-bounce-v2-long+ 5T/40%WR -$0.45 (DEAD) | rr-struct-v2+ 10T/40%WR -$0.45 (KILLED this run) | rr-struct- 7T/42.9%WR -$0.42 (KILLED)
- **Market:** NEUTRAL (100%).
- **Open:** 5 SHORT (pullback-entry-).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED (Sep 15 ~14:40):** rr-struct-v2+ (CEO, 10T/40%WR -$0.45, all ATR SL). **KILLED (Sep 15 05:10):** pump-chain+ NORMAL regime blocked (signal_reporter). **KILLED (Sep 14 22:45):** rr-struct- (CEO). **KILLED (Sep 14 16:08):** pump-chain+ (auto_1hr, NEVER_REENABLE). **KILLED (Sep 13):** trend_purity+ (auto_1hr). **KILLED (Sep 11):** accel-300-v4-short-, PUMP_FLOW+ (NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** ~81% (23G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** {3,5,13,14,15,21} — soft penalty active.
- **SHORT_NORMAL_PENALTY=0.85:** ACTIVE — 15% confidence penalty for SHORT in NORMAL regime. Monitor 48h until Sep 16 ~05:30.
- **SHORT_RSI_FLOOR=25:** Working.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟡 R:R STATUS (POSITIVE 7d, NEGATIVE 24h)**
7d PnL +$1.05 (POSITIVE, improved). SHORT +$2.69 carries LONG -$1.64 drag. 24h -$0.59 (pullback-entry- variance, rr-struct-v2+ KILLED). System improving as legacy ages out.

**🟡 rr_engine_resistance FIX:** Post-fix exits improving. Need 10+ exits. Deadline: Sep 16 ~06:45.

**🟡 ATR SL FIX:** ATR_SL_MIN 1.2%→1.3% applied. Still elevated below-entry rate. Monitor until Sep 16 ~06:00.

**🟢 SHORT_NORMAL_PENALTY=0.85:** 0 SHORT NORMAL trades in ~34h. Working. Monitor until Sep 16 ~05:30.

**🟢 pump-chain+ NORMAL BLOCK:** Signal_reporter blocked Pump_Flow from NORMAL regime. Active since 05:10 UTC Sep 15.

**🟢 trend_ignition:** 0 trades since Sep 13 deployment. NEUTRAL market. Monitor 72h until Sep 16.

## Today's Changes (Sep 15)

1. **signal_reporter ~05:10 UTC — REGIME BLOCK.** Added 'Pump_Flow': 0.0 to VOL_PHASE_MULTS[('NORMAL', '*')] in volatility_gate_v2.py:249. pump-chain+ LONG 0%WR -$0.44 in NORMAL (3T). Wins in EXTREME (46.7%WR +$0.22). Preserves EXTREME/HIGH access while blocking NORMAL losses.
2. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 37T 48.6%WR -$0.66. 7d: 302T 53.0%WR -$0.23. Market NEUTRAL. **LOSING TRADE AUTOPSY:** All losses legacy flushing or normal variance. **No config change — 4 items in monitoring.**
3. **CEO ~10:00 UTC — NO CONFIG CHANGE.** DB: 24h 31T 54.8%WR +$0.10. 7d: 290T 53.1%WR +$0.29. Market NEUTRAL. **No config change — system positive, 4 items in monitoring.**
4. **brain_auditor ~11:50 UTC — CONFIG CHANGE.** BB DEAD ZONE FILTER DEPLOYED. SHORT_BB_DEAD_ZONE_MIN=0.70, SHORT_BB_DEAD_ZONE_MAX=0.85. Expected +$0.52/7d.
5. **CEO ~14:40 UTC — CONFIG CHANGE.** DB: 24h 29T 44.8%WR -$0.59. 7d: 284T 53.5%WR +$1.05. **KILLED rr-struct-v2+ LONG.** 10T/7d 40%WR -$0.45. All exits ATR SL/MAE-GUARD — poor LONG entries in NEUTRAL. Removed from STANDALONE_BYPASS. Pipeline restarted.

## Active Decisions

- **R:R POSITIVE (7d).** 7d PnL +$1.05 (POSITIVE, improved). SHORT +$2.69 carries LONG -$1.64 legacy drag. — 2026-09-15 ~14:40 UTC
- **rr-struct-v2+ KILLED.** CEO 14:40 UTC Sep 15. 10T/40%WR -$0.45, all ATR SL. — 2026-09-15
- **rr_engine_resistance FIX.** Post-fix exits improving. Need 10+ exits. Deadline: Sep 16 ~06:45. — 2026-09-14 ~06:45 UTC
- **SHORT BB DEAD ZONE (0.70-0.85).** DEPLOYED. Expected +$0.52/7d. — 2026-09-15 ~11:50 UTC
- **ATR_SL_MIN 1.3%.** Monitor until Sep 16 ~06:00. — 2026-09-14 ~22:34 UTC
- **SHORT_NORMAL_PENALTY=0.85 ACTIVE.** 0 SHORT NORMAL trades in ~34h. Monitor until Sep 16 ~05:30. — 2026-09-14 ~05:30 UTC
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

1. **Monitor rr_engine_resistance fix.** Post-fix exits improving. Need 10+ exits. Deadline: Sep 16 ~06:45. — 2026-09-15
2. **Monitor ATR_SL_MIN 1.3%.** Still elevated below-entry rate. Deadline: Sep 16 ~06:00. — 2026-09-15
3. **Monitor SHORT_NORMAL_PENALTY=0.85.** 0 SHORT NORMAL in ~34h. Deadline: Sep 16 ~05:30. — 2026-09-15
4. **Monitor trend_ignition.** 0 trades since Sep 13. Deadline: Sep 16. — 2026-09-15
5. **Verify pump-chain+ legacy fully aged out.** Legacy aging out Sep 16-20. — 2026-09-15
6. **Evaluate LONG improvement after legacy ages out.** LONG 7d: 132T 47.0%WR -$1.64. — 2026-09-15
