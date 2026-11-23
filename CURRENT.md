# Current State — brain_auditor #291 2026-11-23 04:50 UTC
**Last Updated: 2026-11-23 04:50 UTC**
**Updated by: brain_auditor #291. Prior: #290 2026-11-22 20:50 UTC (preserved in git history).**

## HEADLINE — JUP-LONG CLONEHUNT DUE-TODAY EXECUTED → NO SHIP (4/5 bars fail): gate_shadow would_win inflated +14.5pp vs 5m candle truth (68.3%→53.8%). Weekly AMPLIFY emitted: btc-pump-rider+ EXTREME LONG cell (13T +0.35). Floor-join matured → NO-SHIP final (p=0.2711). 0 trading-constant changes.

1. **JUP-LONG BLOCKED WALK (due 11-23) — NO SHIP:** n=41 token-day PASS | walk net **+$0.13** < +0.50 FAIL | fk **100%** FAIL (token-day unit wrong for multi-fire jup — every live-winner day also blocked) | only 1 gate n>=5 net>0 FAIL | split-half H1 +0.27 / H2 −0.13 FAIL. **Provenance suspect CONFIRMED:** pre-walk would_win 68.3% vs walk 53.8% on same 41 events. Artifact: brain/analysis/jup_long_blocked_walk_result.json. Do NOT re-propose without would_win backfill audit + event-level unit.
2. **WEEKLY AMPLIFY (formal):** registered `amplify-rider-extreme-long-cell` — (btc-pump-rider+|EXTREME|LONG) 30d 13T 61.5% +0.35 arm 69.2% 11 tokens, 7d 9T 77.8% +0.39 same-sign, sibling SHORT n=0 direction-pure. Cell-add bars → 11-30 read; mult 1.0→1.25 stays CEO-gated. In-flight offense not duplicated (rider-fade walk done 11-22).
3. **FLOOR-ADMIT FINAL:** join re-ran 04:31Z — floor_only 49.6% n=2117 vs always 46.9% n=498, fisher **p=0.2711**, mature 38d bars PASS (n, same-sign) but p>>0.05 → **NO-SHIP final, route CLOSED** (stops re-asking).
4. **CONTRARIAN re-ran 04:31Z:** overall flip 49.2% n=2599 (flipping loses) · pc- ~58% · rider 48.9% do-NOT · per-signal only. DEMOTE stands.
5. **Chop-bleed ROSE:** 7d **90.5%** (was 82.7% at #290 — +7.8pp in 24h), 14d 87.2% — still under 92% tripwire. Creative: 1-day delta early-warning suggested.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | 17T 41.2% **−0.24** / 119T 50.4% **+0.17 GREEN** |
| 14d / 30d | 230T 47.4% −0.86 · 650T 52.5% −3.53 |
| armed vs never 7d | armed 62T 83.9% **+3.60** vs never 57T 14.0% **−3.43** |
| RR 7d | win +0.0710 / loss −0.0757 = **0.94x** (breakeven WR 52.0%) |
| chop-bleed | **7d 90.5% / 14d 87.2%** (up from 82.7%, still <92) |
| exits 14d | pm_trail 71T 97.2% +4.60 ‖ atr_sl 29T 0% −3.08 · HML 25T 0% −2.63 · manual_sl 25T 0% −2.61 |
| kill screen | 0 sub-50 n>=15 except ai-trader-pending 54T 35.2% **+0.05** CEO-domain net-positive |

### 2. AUTOPSY (48h, recovery_replay adverse-first, SELF-CHECK PASS)
n=22 = 6 never-adverse / 13 recovered / **3 NEVER** (KAS atr-trend- cut-loser · BLUR pc+ prearm · RESOLV atr-trend+ prearm — tiny never-armed class) → **WRONG-SIDE REFUTED 142nd consecutive run** (#61 p=0.116, #84 t=−0.04).

**24h losers (8, −$0.73→−0.24 net after wins):** biggest = BTC ai-trader SHORTs #17058 −0.20 / #17052 −0.17 (oversold short into LONG_BIAS tape — CEO domain, bracketed) · #17059 RSI-85 LONG chase closed SL −0.11 (watchdog HOLD correctly let bracket work) · atr-trend− ×3 tiny (KAS/ANIME/ZRO) = steer-001 cohort. Mid-band longs still the only consistent winners.

### 3. SHADOW (both mandate joins re-ran 04:31Z)
| Source | Status |
|---|---|
| contrarian join | overall flip **49.2% n=2599** · pc- ~58% · rider 48.9% do-NOT · DEMOTE stands |
| floor join | **FINAL NO-SHIP** p=0.2711 mature 38d → route CLOSED |
| jup-long walk | **NO SHIP** net +0.13, provenance +14.5pp inflation (new artifact) |
| shadow_trader | exit A/B **pm_trail +20,771** vs hard_max −26,994 / rr −9,903 = TRAIL-OR-NOTHING |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable + shadow_trader + 2 live joins** |

### 4. CREATIVE (this run)
- **C1:** gate_shadow would_win provenance audit (recompute from candles; quarantine if systematic).
- **C2:** AMPLIFY rider EXTREME LONG cell (registered, above).
- **C3:** chop-bleed 1-day delta early-warning before 92% tripwire.

### 5. DUE
**11-24** ai-trader tag-split / brake-cf / gate-cross-tab / regime-tension → **11-25 WIN-CAPTURE VERDICT** + bbsqueeze reband + structure-flip + watch-contrarian + pcfade + hotset-pin → **11-26** storm waiver (CEO) + capture-leaderboard → **11-27** stop-family + linregfade + pc-weight → **11-28** maker-entry + prearm-enforce-day7 + jup-walk + dual-basis + conf-tilt + r2v2 + reentry → **11-29** tape-at-long → **11-30 rider-cell read (NEW)** → **12-01** prearm-band-lower OOS → 12-03 kill-line → 12-06 atr-trend-accel → 12-15 ugb-bypass.

### 6. CHANGES THIS RUN (data-only, zero trading behavior)
1. `data/shadow_disposition.json` — jup-long-blocked-clonehunt → done/NO SHIP; +amplify-rider-extreme-long-cell (open, 11-30); floor mature NO-SHIP final note. Atomic write.
2. `brain/analysis/jup_long_blocked_walk_result.json` — NEW walk artifact.
3. `brain/audit_recommendations.json`, `brain/creative_improvements.json`, `brain/changes_log.json` — run artifacts (+3 log entries).

### 7. LAST-RUN VERIFY (#290) — ALL PASS
prearm_lock 7d 12T avg −0.011 ✓ · constants EMPTY ✓ · session lock ABSENT ✓ · size-reduce absent=1.0x ✓ · CEO_PROTECTED 16 keys ✓ · 0 Tracebacks ✓ · recovery selfcheck ASSERT PASS ✓ · floor re-ran (p drifted 0.2897→0.2711, direction same) ✓ · win-capture still interim FAIL→continue to 11-25 ✓.

### 8. READINESS (2026-11-23 04:50 UTC)
**0 open — FLAT** (BTC #17059 RSI-85 chase closed manual_sl_hit −0.11 at 04:30Z; bracket did its job). Regime: 15m+4h LONG_BIAS, continuum ABOVE, vol LOW, CALM, trend_quality UP — but flip-rate 25-30/24h unstable → no direction steer. **No fresh counter-trend entries; mid-band longs only; trail-family first; size 1.0x.**

**CEO owed:** V6 kill RATIFY/VETO · rider-fade fk-limb · maker-entry lever · storm bar by 11-26 · edge-diagnosis reconciliations · (new) rider-cell validate→mult-revert at 11-30 if bars hold.
**Flip-KPI:** MET (prearm enforce 11-20). Weekly AMPLIFY: rider cell emitted this run.
