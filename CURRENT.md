# Current State — brain_auditor #138 2026-10-25 11:55 UTC
**Last Updated: 2026-10-25 11:55 UTC**
**Updated by: brain_auditor #138. Prior: #137 10:42 (preserved in git history).**

## HEADLINE 1 — ESCALATION #17 CLOSED AS SUPERSEDED (no new CEO GO needed)
**UGB-PT (CEO GO, run #130, enforced live since 2026-10-25 01:47) already IS the universal
post-arm floor the #136 CEO-GO ask proposed to build.** `position_manager.py:3912-3927`
enforces peak-giveback **D=0.30** on every armed trade (`fav >= +0.40%`) that is **not in
profit_monster trail-state** — which is exactly the PM-exempt/bypass cohort. Live proof this
run: **HYPE #16383 `hl_copy_trader` (bypass signal) closed `ugb_pt` +0.16 at 02:18; PURR #16393
`r2v2-long3` UGB-PT shadow-fired 11:08 — neither is in trail_state (verified).**
Coverage is now universal: PM-managed armed → PM trail (D=0.20, CEO-protected); every other
armed trade → UGB-PT (D=0.30); unarmed-reached-0.40 → UGB-PT.
**Residual = tighten `UGB_PT_DISTANCE_PCT` 0.30 → 0.20**: scoped bypass D=0.30 `+$2.247`/30d
p=0.023 (all bars) vs D=0.20 `+$2.368` → **delta `+$0.12`/30d = noise → MONITOR, not change.**
The #136 shadow-line ship vehicle is **redundant** — the enforcement exists. Remove
"D=0.20 post-arm floor GO" from the CEO stack; optional distance-tighten stays a monitor item.

## HEADLINE 2 — GATE INTEGRITY: [CONTINUUM-BLOCK] is ADVISORY for backtested-standalone passes
**Root cause:** `_btc_mom_ok_for_bypass` (signal_compactor Layer B, :2754-2908) is only read by
the LONG/SHORT-NEUTRAL blocks (:2949/:3040/:3067). The **confluence gate's backtested-standalone
pass (:3455-3495) and the HOTSET-FINAL / PENDING-APPROVE / SAFETY-FILTER standalone bypasses
never read it** → the block prints `🚫 BLOCKED` and the trade executes in the same second.
Confirmed instance: **SAGA 07:15:00 CONTINUUM-BLOCK → 07:15:18 EXEC → trade #16391** (closed
-0.05). 95 block→EXEC events (one-cycle 65s slack); 37 matched closed trades.
**Measured (`brain/analysis/blocked_but_executed_2026-10-25.py`, selfcheck PASS; bug_hunter
post-ship review SHIP-STANDS + 4 hardening fixes applied): LONG n=34 11W/23L WR 32.4% net
`-0.90` (Oct 11–25) vs base 14d LONG 37.9% → binom p=0.317 = cohort is NOT worse than base
(robust slack 30–180s, p=0.24–0.47).** fkA 12.8% pass, both halves (17/17) negative pass, **p FAIL → PRE-REGISTERED
CRITERIA NOT MET → NO enforcement ship.** Re-eval at n>=50 (criteria locked in script docstring).
Verdict: the watchdog's mid-band steer stays advisory; enforcement would block at base rate —
consistent with #61 (ema300 bands p>0.05) and #128 (dampen sign-flip). **Log semantics flagged
as observability debt: "BLOCKED" should read advisory for standalone-pass signals.**

## WATCHDOG TRIAGE (11:14 cycle) — P1/P2/P3/P4 all dispositioned, 0 param changes
- **P1 mid-band LONG 45-64 VERIFIED**: 7d 46T 18W 39.4% `-1.33` / 14d 110T `-2.71` / 30d 244T
  `-0.31`. Blanket block fk = 117/304 = **38.6% > 20% bar → FAIL**; #128 size-dampen already
  rejected (30d sign flip), **re-measure Oct 27**. Standing condition steer holds. No change.
- **P2 bb-bounce-v2-long+ decay VERIFIED (exact signal)**: 30d 56T 28W 50% `-0.56` | 14d `-1.01`
  | 7d `-0.55`, **7d 16/18 in meta_rsi 45-64** = subsumed by P1 steer. Regime: NORMAL `-0.50`/38T
  + EXTREME `-0.37`/10T vs FLAT+HIGH `+$0.31`/8T. **Kill bars FAIL (fk 50% of 30d winners) →
  NO disable.** Stale re-enable basis comment corrected in-file (comment-only, value True).
  In flight: compactor co-signal stamp before bypass-removal lever.
- **P3 pump-chain+**: subsumed, 30d +1.84 positive → no action (matches #129).
- **P4 ICP/CHIP wrong-side pair**: n=2; 7d LONG 65-75 still `+$0.50` → ceiling stays 75.
- **P5 dead-signal check**: agrees, already killed. **P6** CHOP-long shadow n=11 observation.

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 62nd CONSECUTIVE RUN
Adverse-first `recovery_replay.py` (selfcheck PASS): **48h n=12 = 2 never-adverse / 5
recovered-after-adverse / 5 NEVER.** NEVER = ALT `−0.17` / CC `−0.15` / ZRO `−0.11`
volume-buildup- shorts (structural never-recover, price ran away) + BTC pending `−0.08` +
PUMP r2v2 `−0.01` — all tiny. 0 new patterns. Winning side = flat.
Valid refs: #61 p=0.116, #84 t=−0.04.

## SHADOW (mandate 2b) — 2/5 answerable
- **contrarian RE-RAN this run**: pump-chain- flip-WR **64.0% n=339** STANDS (Oct-27 PROMOTE);
  btc-pump-rider+ 25.0% n=196 = do NOT flip.
- shadow_trader --report: 20,497 signals / 19,868 closed; **EXEC-BLOCK would_win 7% avg −0.51 =
  best gate**; CONFLUENCE-EXPIRY 48% avg −0.12; exit A/B pm_trail `+2841` vs hard_max `−4418`.
- oscillator frozen-by-design / wyckoff pending join / floor_admit join collecting (Nov-15) /
  rr_shadow orphaned → do not cite.

## SHIPS THIS RUN
1. `brain/analysis/blocked_but_executed_2026-10-25.py` — gate-collision cohort measurement +
   pre-registered enforcement criteria (selfcheck PASS). Zero trading behavior.
2. `hermes_constants.py` **comment-only**: `BB_BOUNCE_V2_LONG_ENABLED` dead re-enable basis
   ('73T 74%WR +$2.08') replaced with fresh #138 numbers + kill-bar FAIL verdict. Value True
   unchanged; git diff = 1 line; CEO_PROTECTED untouched.

## LAST-RUN VERIFY (#135/#136/#137) — ALL PASS
[TRAIL] `trade_id` field LIVE (PURR 11:01:15 trade_id=16393) · spider fix floors sane
(+0.65/+0.45/+0.29), spider dormant · trail_distance/pm_activation selfchecks PASS ·
UGB-PT 21 log hits today, correct-by-traffic · constants diff = this run's comment line only ·
size-reduce file absent = 1.0x · session lock absent · pipeline Traceback today = known Sun 03:00
self-healing dispatcher (fix `83f99f71`, verify Sun Nov 1) · watchdog-agent 5 SQL errors today =
its own ad-hoc queries (round(double precision) etc.), not pipeline code.

## READINESS
0 open = **correct** — chop tape (BTC under 1m EMA300 5.7h, gap narrowing −0.144%, regime
sources disagree, vol LOW). LONGs only on sustained reclaim WITH volume; SHORTs only under
EMA300 with 4h aligned; mid-band = no trade; trail-family first; size 1.0x.

## CEO STACK (updated)
- ~~D=0.20 post-arm floor GO~~ → **CLOSED — covered by live UGB-PT at 0.30; optional tighten 0.30→0.20 = monitor**
- spider tier veto window (one-line revert story unchanged)
- pump-chain+ NO-KILL + CONF_FLOOR fkA ruling + pump-chain TAT base-vs-variant
- Oct 27: contrarian pump-chain- PROMOTE (64.0% n=339) + coin_regime n>=50 + mid-band dampen re-measure
- Nov 1: self-healing SKIP verify · Nov 15: floor_admit same-sign · re-eval blocked-but-executed at n>=50
