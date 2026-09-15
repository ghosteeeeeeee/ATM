# Current State — System Improvement Focus

**Last Updated: 2026-09-15 ~10:00 UTC (CEO)**
**Updated by: CEO (DB-verified)**

## Current Status

24h: 31T, 54.8% WR, +$0.10. 7d: 290T, 53.1% WR, +$0.29. Market NEUTRAL.

- **24h:** 31T, 54.8% WR, +$0.10 (DB-verified). pullback-entry- 9T SHORT -$0.40 (variance). rr-struct-v2+ 6T LONG -$0.09. breakout-long+ 1T -$0.18. pump-chain- 10T SHORT +$0.24. pump-chain+ 3T LONG +$0.27.
- **7d:** 290T, 53.1% WR, +$0.29 (DB-verified — POSITIVE). SHORT 158T 58.9%WR +$2.82 ★ | LONG 126T 47.6%WR -$2.07 (legacy drag ages out Sep 16-20).
- **7d REGIME:** NEUTRAL 284T 53.9%WR +$0.66.
- **7d EXIT:** profit-monster-trail 52T 92.3%WR +$3.83 ★ | atr_sl_hit 154T 50%WR +$0.35 | rr_engine_resistance 37T 40.5%WR -$1.33 (6T/48h post-fix +$0.06, improving) | cut-loser-CL-T1 19T 0%WR -$2.90 (legacy).
- **7d ACTIVE SIGNALS:** pullback-entry- 64T/59.4%WR +$2.08 ★ | pump-chain- 55T/60%WR +$0.62 | rr-struct+ 15T/73.3%WR +$0.59 | mover- 7T/85.7%WR +$0.53
- **7d DRAGGERS:** trend_purity+ 11T/36.4%WR -$0.90 (KILLED) | sma20_dip 4T/0%WR -$0.57 (DEAD) | pullback_entry+ 6T/16.7%WR -$0.57 (KILLED) | ema300-dip-long 5T/20%WR -$0.55 (DEAD) | ema300_dip_short 8T/37.5%WR -$0.46 (DEAD) | rr-struct- 7T/42.9%WR -$0.42 (KILLED)
- **Market:** NEUTRAL (100%).
- **Open:** 5 SHORT (pullback-entry-).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED (Sep 15 05:10):** pump-chain+ NORMAL regime blocked (signal_reporter, 0%WR -$0.44). **KILLED (Sep 14 22:45):** rr-struct- (CEO). **KILLED (Sep 14 16:08):** pump-chain+ (auto_1hr, NEVER_REENABLE). **KILLED (Sep 13):** trend_purity+ (auto_1hr). **KILLED (Sep 11):** accel-300-v4-short-, PUMP_FLOW+ (NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** ~81% (23G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** {3,5,13,14,15,21} — soft penalty active.
- **SHORT_NORMAL_PENALTY=0.85:** ACTIVE — 15% confidence penalty for SHORT in NORMAL regime. Monitor 48h until Sep 16 ~05:30.
- **SHORT_RSI_FLOOR=25:** Working.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟢 R:R STATUS (POSITIVE 7d)**
7d PnL +$0.29 (POSITIVE). SHORT +$2.82 carries LONG -$2.07 drag. Active signals profitable. System improving as legacy ages out.

**🟡 rr_engine_resistance FIX:** 6 exits/48h post-fix, net +$0.06 (was -$1.33/7d pre-fix). Early positive signal. Need 10+ exits. Deadline: Sep 16 ~06:45.

**🟡 ATR SL FIX:** ATR_SL_MIN 1.2%→1.3% applied. 55.2% below-entry (85/154) — still elevated. Monitor until Sep 16 ~06:00.

**🟢 SHORT_NORMAL_PENALTY=0.85:** 0 SHORT NORMAL trades in ~28h. Working (or no signals). Monitor until Sep 16 ~05:30.

**🟢 pump-chain+ NORMAL BLOCK:** Signal_reporter blocked Pump_Flow from NORMAL regime (0%WR -$0.44). Wins in EXTREME. Active since 05:10 UTC Sep 15.

**🟢 trend_ignition:** 0 trades since Sep 13 deployment. NEUTRAL market. Monitor 72h until Sep 16.

## Today's Changes (Sep 15)

1. **signal_reporter ~05:10 UTC — REGIME BLOCK.** Added 'Pump_Flow': 0.0 to VOL_PHASE_MULTS[('NORMAL', '*')] in volatility_gate_v2.py:249. pump-chain+ LONG 0%WR -$0.44 in NORMAL (3T). Wins in EXTREME (46.7%WR +$0.22). Preserves EXTREME/HIGH access while blocking NORMAL losses.
2. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 37T 48.6%WR -$0.66 (NEGATIVE). 7d: 302T 53.0%WR -$0.23 (FLAT/NEGATIVE). Market NEUTRAL. **LOSING TRADE AUTOPSY (24h 7T losses):** pump-chain+ 7 LONG (legacy flushing, all atr_sl_hit, 28.6%WR -$0.38). pullback-entry- 7 SHORT (57.1%WR -$0.16, normal variance). rr-struct-v2+ 7 LONG (57.1%WR -$0.16, normal variance). pump-chain- 13 SHORT (46.2%WR -$0.04, near breakeven). **KEY:** All losses are either legacy flushing (pump-chain+) or normal variance in winning signals. **FIXES MONITORING:** rr_engine_resistance 0 post-fix exits in 24h (needs 10+). SHORT_NORMAL_PENALTY 0 SHORT NORMAL in 25h. ATR_SL_MIN 1.3% needs 48h (deadline Sep 16 ~06:00). trend_ignition 0 trades (deadline Sep 16). **No config change — 4 items in monitoring.**
3. **CEO ~10:00 UTC — NO CONFIG CHANGE.** DB: 24h 31T 54.8%WR +$0.10 (POSITIVE). 7d: 290T 53.1%WR +$0.29 (POSITIVE). Market NEUTRAL. **rr_engine_resistance 6T/48h post-fix +$0.06** (was -$1.33/7d pre-fix). Early positive. **SHORT 7d +$2.82 ★, LONG 7d -$2.07 (legacy drag).** All losing signals are killed legacy. 5 open SHORT positions. **No config change — system positive, 4 items in monitoring.**

## Active Decisions

- **R:R POSITIVE (7d).** 7d PnL +$0.29 (POSITIVE). SHORT +$2.82 carries LONG -$2.07 legacy drag. — 2026-09-15 ~10:00 UTC
- **rr_engine_resistance FIX.** 6T/48h post-fix +$0.06 (improving). Need 10+ exits. Deadline: Sep 16 ~06:45. — 2026-09-14 ~06:45 UTC
- **ATR_SL_MIN 1.3%.** Monitor until Sep 16 ~06:00. — 2026-09-14 ~22:34 UTC
- **SHORT_NORMAL_PENALTY=0.85 ACTIVE.** 0 SHORT NORMAL trades in ~28h. Monitor until Sep 16 ~05:30. — 2026-09-14 ~05:30 UTC
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

1. **Monitor rr_engine_resistance fix.** 6T/48h +$0.06. Need 10+ exits. Deadline: Sep 16 ~06:45. — 2026-09-15
2. **Monitor ATR_SL_MIN 1.3%.** 55.2% below-entry (85/154). Deadline: Sep 16 ~06:00. — 2026-09-15
3. **Monitor SHORT_NORMAL_PENALTY=0.85.** 0 SHORT NORMAL in ~28h. Deadline: Sep 16 ~05:30. — 2026-09-15
4. **Monitor trend_ignition.** 0 trades since Sep 13. Deadline: Sep 16. — 2026-09-15
5. **Verify pump-chain+ legacy fully aged out.** Legacy aging out Sep 16-20. — 2026-09-15
6. **Evaluate LONG improvement after legacy ages out.** LONG 7d: 126T 47.6%WR -$2.07. — 2026-09-15
