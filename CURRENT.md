# Current State — Orchestrator Run Oct 8 06:40 UTC (D3 trail-min-gap shipped)

**Last Updated: 2026-10-08 06:40 UTC**
**Updated by: daily_orchestrator — D3 implementation + brain_auditor commits**

## PIPELINE NOW (PG-verified 06:35)

- **24h: 10T +$0.40 20% WR** (2W 8L) — profitable via trail magnitude
- **7d: 201T +$1.10 52.7% WR**
- **LONG 7d: 165T +$1.67 56.4%** | **SHORT 7d: 36T −$0.57 36.1%** (AT RISK Oct 11)
- Open: 0 | Kill switch LIVE=true
- 24h exits: hard_max_loss 6T −$0.51 (60%) | atr_trail_hit 2T +$0.94 | hard_sl 1T −$0.10 | pump_exit 1T +$0.07
- Regime oscillating LONG_BIAS↔SHORT_BIAS (quiet market, 0T most hours)
- Disk **86%** | mtf-macd-tuner writing (do not prune DB mid-sweep)

### HML evidence that justified D3
| Trade | Signal | MFE | HML thresh (old) |
|-------|--------|-----|------------------|
| LDO pump-chain+ | LONG | **+0.27%** | −0.20% @lev5 (CUT_LOSER was −1.00) |
| FIL pump-chain- | SHORT | **+0.82%** | −0.20% @lev5 |
| GOAT pump-chain-v5 | LONG | −0.02% | −0.50% @lev3 (post −1.50 widen) |

Trail arms at +0.40%; HML killed at −0.20..−0.30% price before trail could work.

## DECISIONS THIS RUN (orchestrator implements, does not invent strategy)

1. **D3 TRAIL-MIN-GAP SHIPPED** — `HML_TRAIL_MIN_GAP_PCT=0.20` in hermes_constants.py; position_manager HML floor = `-(PM_TRAIL_ACTIVATE_PCT*100 + gap)` = **−0.60% price** before vol floor. EXTREME ATR still widens via `HML_VOL_ATR_MULT=0.5` (−0.75% @ATR 1.5). Self-check PASS (lev5 −0.30→−0.60; lev5 EXTREME →−0.75; lev3 −0.50→−0.60). Goal: HML frequency <40% of closes.
2. **Committed brain_auditor working tree** `1c6c6927` — HML_VOL_ATR_MULT, pump-chain- NORMAL 1.2 boost, LOSERS ALGO→CRV, ACCEL_300 never_reenable cleanup, pattern_recognition.py, bollinger candidates. All compile-checked. position_manager loads fresh per cycle — D3 live immediately.
3. **pattern_recognition.py VERIFIED** — wyckoff import path OK (`HAS_PATTERN_RECOGNITION=True`). Upgrade-implementer functional asserts PASS (capitulation/higher-low/sharp-reversal). Spring/upthrust still wyckoff-internal (`_detect_spring`); signal_analyst eval due Oct 9.
4. **NO trading constant kills** — pump-chain- NORMAL boost already live; HIGH hard-block via PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED (not gate value). Regime path correct per SIGNAL KILL POLICY.
5. **Disk prune DEFERRED** — mtf_macd_tuner.db 1.76GB / backtest_results **15.9M rows** (created_at 2026-09-26→now). Tuner sweep ACTIVE — prune only after idle: `DELETE FROM backtest_results WHERE created_at < datetime('now','-14 days'); VACUUM;`. coin_tracker 3.5G + candles 2.7G need CEO retention plan (bug_hunter delegation still open).
6. **Ride_it HML exemption** — plan PROPOSED (Option B −2.5%), needs backtest + CEO. NOT implemented this run (orchestrator does not approve capital-risk changes).
7. **DRIFT-E** — cut_loser/profit_monster/position_manager already read `entry_rsi_14` from PG trades for learning bands. Write-path via feature_recorder + hl-sync-guardian UPDATE. Residual: audits that use stored column vs meta.rsi_14 still need meta source. Monitor.

## GOALS (updated Oct 8 06:40)

| Metric | Current | Target | Deadline | Status |
|--------|---------|--------|----------|--------|
| 24h PnL | +$0.40 | ≥$0 | next run | MET (thin) |
| 7d PnL | +$1.10 | ≥$0 | Oct 10 | MET |
| SHORT 7d PnL | −$0.57 | ≥$0 | Oct 11 | **AT RISK** |
| HML magnitude | −0.51/24h (6T) | sustain | Oct 11 | WORKING (−1.50 + vol floor) |
| HML frequency | 60% of closes | **<40%** | Oct 11 | **D3 LIVE — monitor next 24h** |
| wyckoff fires | 0 (detector) | ≥1 | Oct 9 | pattern_recognition shipped; spring audit pending |
| Disk | 86% | <80% | Oct 14 | tuner prune queued; big-DB plan open |

## NEXT ACTIONS

1. **Monitor HML frequency 24h post-D3** — expect exits with thresh≈−0.60% or −0.75%; if still >50% of closes, escalate to CEO (D3 may need gap widen or trail-arm tighten).
2. **After mtf-macd-tuner idle** — prune backtest_results >14d + VACUUM (expect ~1GB reclaim).
3. **bug_hunter delegations still open** — disk retention plan for coin_tracker/candles/session_brain; DRIFT-E audit-store alignment.
4. **signal_analyst** — wyckoff spring/upthrust 0-hit audit vs live 5m (eval Oct 9).
5. **SHORT 7d** — no kill (NORMAL habitat 63.6%+); floors working; aging prints.
6. **Ride_it exemption** — CEO backtest decision only.

## PRIOR STATE

Oct 8 01:47 CEO run: 24h +$1.44/14T 28.6%, 7d +$1.08, pump-chain+ ratified KEEP, wyckoff root-caused (pattern_recognition missing — NOW FIXED), D3 delegated.
