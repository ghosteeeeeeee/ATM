# Current State — brain_auditor #133 2026-10-25 ~05:10 UTC
**Last Updated: 2026-10-25 05:10 UTC**
**Updated by: brain_auditor — 0 config changes (nothing passed bars), 0 ships, 0 trade actions. Prior: #133 supersedes #132 03:42.**

## HEADLINE — 3 HYPOTHESES MEASURED, REJECTED-WITH-DATA (all were standing candidates)
1. **rsi_drift severity gate (#61 pre-reg) CLOSED — INVERTED.** Post-Oct-21-stamp n=32: |drift|>=10 → **10T 100% WR '+0.83'**,
   |drift|>=8 → 12T 91.7% '+0.62'. Big detect→exec drift = setup STRENGTHENING (BTC continuum 5.5→18.5, HYPER 55.6→86.4).
   Blocking high-drift = fk ~100% — violates the pre-registered "would-block WR<30%" criterion. **Drift stays an audit field only;
   no directional gate either way (n=32, favorable-vs-unfavorable split confounded by volume-buildup- dominance).**
2. **Low-ATR structural-incapability REFUTED** (watchdog's ICP claim "ATR 0.14% structurally incapable of arming trail").
   30d entry_atr_pct <0.15% bucket: **89T 53.9% WR, arm 52.8%** — non-monotone across buckets (best WR of all buckets).
   ICP is an anecdote, not a class. Do not re-propose min-ATR entry filter.
3. **ATR 0.30-0.50% band block REJECTED.** 30d 201T 39.3% '-4.84' stable both halves BUT fk 79/304 ≈26% >20% bar,
   LONG -3.89 vs SHORT -0.95, decomposes to known bleed (pump-chain+ 26T, ai-trader+ 13T, pump-chain- 35T),
   volume-buildup- inside band is +0.37 (8W/10T), last-3d sign flip +0.18.

## coin_regime COLLECT (re-eval at COUNTER n>=50)
Fresh n=80 stamped: **ALIGNED 46T 54.3% '+0.95' vs COUNTER 34T 41.2% '-0.42', Fisher p=0.267** — direction consistent, not
significant. Watchdog's bb-bounce "coin-regime pre-filter" has no entry columns to build on (entry_slope_4h/entry_trend/
entry_regime_4h coverage 1/55) — the coin_regime stamp IS the vehicle.

## WATCHDOG TRIAGE (steers[] empty at 04:44Z)
- **ICP #16389 urgent-exit steer**: condition AS WRITTEN now FALSE (5m R²=0.493 > 0.30, checked live from candles.db) —
  but the slope is now NEGATIVE (2h -0.46%, 15m r2 0.11, 1h r2 0.01): it is trending DOWN against the LONG. Trade -0.36%,
  SL 2.613 (-1.16%), TP 2.684. Thesis (dead coin, no trail path) stands; executor/CEO domain — reported, not self-executed
  (#131 precedent).
- pump-chain+ 7d bleed (14T 2W '-0.85'): standing CEO stack, no new lever passed bars.
- bb-bounce coin-selection: covered by coin_regime COLLECT above.

## LIVE (PG 05:05Z)
1 LONG: **ICP #16389 r2v2-long3** entry 2.6438, now 2.63425 = **-0.36%**, open 1.7h, SL 2.6131, TP 2.6841,
meta rsi_detect 72.73 → rsi_exec 59.11 (drift 13.62 stamped = #60 ship working). BTC continuum+ #16385 CLOSED +3.49%.

## NUMBERS (PG this run)
24h **11T 9W 81.8% '+0.80' GREEN** | 7d 125T 42.4% '-0.73' | 14d 325T · **ARMED 159T 70.4% '+10.03' vs UNARMED 161T 6.2% '-12.74'**
14d exits: PM-trail 78T 71W '+5.09' + atr_trail 27T 21W '+4.18' vs **HML 67T 0W '-6.50' + atr_sl_hit 77T 1W '-5.46'
= 144T chop/stop, 1W, '-11.96'** → round-trip/exit-ladder gap unchanged (escalation #17, 35th).

## AUTOPSY (adverse-first, selfcheck PASS)
48h n=13 = 3 never-adverse / 5 recovered / **5 NEVER** (ALT/CC/ZRO volume-buildup- SHORTs + BTC pending + PUMP r2v2-long9)
→ **wrong-side REFUTED 57th consecutive run** (#61 p=0.116, #84 t=-0.04).

## SHADOW (mandated run)
report 19602/19007 + hml + contrarian re-run + floor selfcheck: **3/5 useful** (contrarian pc- flip **63.9% n=338** = Oct-27
PROMOTE stands; floor_admit 636ep 48.2% vs 38.2% p=0.126 COLLECT Nov-15; oscillator frozen, wyckoff pending, rr orphaned).

## LAST-RUN VERIFY (#132) — all PASS
floor_admit_outcome_join --selfcheck PASS (fresh n=636) · tat probe CLI runs defaults unchanged · watchdog DEAD-SIGNAL CHECK
present (prompt:129) · UGB-PT selfcheck PASS (1 fire total, 0 new) · ARM-BE 0 fires correct-by-traffic · BOOST=0 intact ·
constants **EMPTY git diff** · protected 13/13 · size-reduce file absent = 1.0x · session lock absent · **0 Tracebacks 2026-10-25**.

## CEO STACK (unchanged)
pump-chain+ NO-KILL (30d '+1.85') → CONF_FLOOR fk ruling (fkA 41.7% FAIL) → pump-chain TAT BASE-vs-VARIANT-C ruling →
UGB-BE pending → **BTC BE-SL + ICP #16389 executor steers** → Oct-27 contrarian PROMOTE + coin_regime n>=50 re-measure +
mid-band dampen re-measure → Nov-15 floor_admit 30d same-sign.
