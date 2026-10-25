# Current State — brain_auditor #139 2026-10-25 12:55 UTC
**Last Updated: 2026-10-25 12:55 UTC**
**Updated by: brain_auditor #139. Prior: #138 11:55 (preserved in git history).**

## HEADLINE 1 — THE STANDING MID-BAND STEER KEYS THE WRONG CELL (refuted, retracted)
The watchdog steer `Keep LONG entries out of meta_rsi 45-64 while BTC 1m holds below continuum
EMA300` (≥6 cycles unexecuted) was measured with `brain/analysis/midband_ema300_cond_2026-10-25.py`
(`--selfcheck` PASS; band totals reproduce P1 **exactly** — 7d 46T `-1.33`, 30d 244T `-0.31`):

| cell | 7d | 14d | 30d |
|---|---|---|---|
| band+**BELOW** EMA300 = steer's blocked set | **+0.03** (4T) | **+0.01** (15T) | **+1.42** (42T, 54.8% WR) |
| band+**AT/ABOVE** EMA300 = steer's kept set | **-1.36** (42T) | **-2.72** (95T) | **-1.73** (202T) |

Blocking the steer's own cell would have **cost** money every window; the bleed lives entirely in
AT/ABOVE. **Both** variants FAIL house bars (BELOW: save<0. AT/ABOVE: fkA 44.4/38.4/40.7%,
binom p=0.35/0.30/0.67) → **no enforceable compound block in either direction.**
Refutation + table written into `trade_watchdog_prompt.md` ("Measured-refuted steer patterns"),
re-measure **Oct 27**. Blanket mid-band stays advisory-only.

## HEADLINE 2 — ema300_duration UNIT BUG FIXED (watchdog-assigned, zero trading behavior)
`ema300_duration` counts **TICK_INTERVAL(30s) state rows, not minutes** — verified: BTC 1m row
spacing median 30s since 2026-09-04 (143,864 rows; 60s era ended 2026-09-03), `dur*0.5 ==
(ts-last_cross_ts)/60` (19.5 vs 19.6), and `continuum_api.py:46` documents "2880 ticks at 30s
intervals". Fix (uses the EXISTING `TICK_INTERVAL` constant, no new constant):
- `ai_trader_precheck.py:426` compared the raw count to 60 → the documented ">60m unresolved
  chop" advisory fired at **30m** and printed "39m" for a 19.5m pin. Now minutes, threshold = 60 MINUTES.
- `continuum_trader.py:523` same label bug → converted.
- `ContinuumState.ema300_duration` comment said "minutes" → corrected.
py_compile OK + unit selfcheck PASS (121 ticks fires / 100 does not / 39 ticks → "20m").
Advisory is `passed=True` always → **no trading behavior change.**

## NEW STANDING KPI — CHOP-BLEED SHARE (in the watchdog prompt)
Share of GROSS LOSS from trades that never reached +0.40% trail activation:
**84.1% (7d) / 85.6% (14d) / 80.6% (30d)** — 148T `-$13.21` of `-$15.44` at 14d.
The bleed is an **entry** problem, not exits (7d trail exits 44T 89% WR `+$2.68`).
Thresholds pre-registered: **≥92%** → push entry-quality filters; **≤70%** → bleed moved to the
round-trip cohort → route to UGB-PT / trail distance, NOT to gates. SQL verified live (→85.6).

## OCT-25 SCHEDULED EVALS — ALL DISPOSITIONED
- **short-gate loosening → CLOSED.** All 8 SHORT gates with n≥50 have NEGATIVE net would_pnl
  (SHORT-CONTINUUM `-9.35`/388 … SHORT-NEUTRAL `-1.15`/144) = gates correctly blocking losing
  shorts, 0 candidates. Collection healthy (2,975 events/24h, max blocked_at 11:58 today).
- **re-enter-on-recovery → REJECTED-WITH-DATA.** 30d: fill rate **31.4%** (limit AT entry), not
  the ~71% census premise; ALL n=110 net `+1.686` but p_t=**0.158 FAIL**, RAW scope newer_half
  `-0.041` FAIL. Bars stated in header before the run.
- **MFE-CUT bb-bounce → BAR FAIL stands** (#134): 14d `+0.18` fk 0%, but 30d fk_cohort **23.5%** > 20%.
- **blocked_but_executed → COLLECT**: LONG n=34, net `-0.90`, fkA 12.8%, both halves negative,
  binom **p=0.317 FAIL**. Re-eval at n≥50 with p<0.05 (criteria locked in script).
- **contrarian pump-chain- PROMOTE STANDS** for Oct 27 (flip 64.0% n=339 re-run this session).
- **HML keep** — no threshold discrimination (lev5 −3.0% covers 2470/2470).

## CREATIVE — arm-predictor gate REFUTED-WITH-DATA
If trail-arming were predictable at entry we could dampen the `-$12.60` unarmed bleed.
Only `momentum_state='falling'` hit p<0.05 (60.2% vs 43.0% arm, p=0.005, n=111) — but it is
**confounded**: within LONG p=0.70/0.49/0.73 (no effect); the aggregate is driven by SHORT+falling
where the mix is 48/54 pump-chain-family (pump-chain- alone arms 65.7%); and falling-SHORT arms
70.4% yet wins only 38.9% → high arm ≠ high WR. speed/volume/z_score/rsi_14 all p=0.14–0.97 (n=328).
Logged rejected, not re-proposable.

## WATCHDOG TRIAGE
- P1 mid-band verified → **condition variant refuted above**, blanket stays advisory, re-measure Oct 27.
- P2 bb-bounce decay → measurement (subsumed by P1; co-signal stamp lever in flight).
- P3 4×24h losers → all direction failures at entry; CHIP SHORT was exit machinery working (+0.52 → cut at −0.06).
- P4 dead-signal check → agrees (0 opens since Oct 20 for doji/oversold/volume-breakout/ai-trader+).
- 🟡 ema300_duration display bug → **FIXED this run** (Headline 2).

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 63rd CONSECUTIVE RUN
Adverse-first `recovery_replay.py` (selfcheck PASS): **48h n=10 = 2 never-adverse / 5
recovered-after-adverse / 3 NEVER** (ALT `−0.17`, BTC `−0.08`, PUMP `−0.01` — immaterial). 0 new
patterns. Winning side = flat. Valid refs: #61 p=0.116, #84 t=−0.04.

## SHADOW (mandate 2b) — 2/5 answerable
- **contrarian outcome-join RE-RAN**: pump-chain- flip **64.0% n=339** STANDS (Oct 27 PROMOTE);
  btc-pump-rider+ 25.0% n=196 do NOT flip; overall 49.6% on 536 joinable.
- shadow_trader `--report`: **20,634 signals / 19,985 closed**; EXEC-BLOCK would_win **7%** avg
  `-0.51` = best gate; CONFLUENCE-EXPIRY 48% `-0.12`; BTC-CRASH 31% `-0.36`; exit A/B pm_trail
  `+2875` vs hard_max `−4422`, cut_loser `−71.51` (0% WR), rr_engine `−745`.
- oscillator frozen-by-design / wyckoff pending join / floor_admit join collecting (Nov-15) /
  rr_shadow orphaned → do not cite.

## SHIPS THIS RUN (2, both zero-trading-behavior)
1. ema300_duration unit fix — `ai_trader_precheck.py` + `continuum_trader.py` + `continuum_engine.py` comment.
2. `automation/trade-watchdog/trade_watchdog_prompt.md` — measured-refuted steer block + Chop-Bleed Share KPI.
   `scripts/hermes_constants.py` **git diff EMPTY**; CEO_PROTECTED untouched.

## LAST-RUN VERIFY (#136/#137/#138) — ALL PASS
blocked_but_executed runs + `--selfcheck` PASS (still COLLECT = correct-by-design) · BB_BOUNCE
comment-only, value True, constants diff empty · [TRAIL] `trade_id` live at
`profit_monster.py:492` · UGB-PT firing bypass cohort (HYPE ugb_pt +0.16, PURR shadow-fired),
D=0.20 delta `+$0.12`/30d = monitor · size-reduce file ABSENT = 1.0x · session lock ABSENT ·
protected 13/13 · today's 03:00 Traceback = KNOWN Sunday self-healing dispatcher (fix `83f99f71`,
verify Sun Nov 1) · signal-compactor `IndentationError` in `.err.log` = STALE (mtime Oct 24; file
compiles, compactor ran 12:51 today in 0.21s).

## READINESS
0 open = **correct** — BTC pinned AT 1m EMA300 (gap −0.03%, above-poke lasted 4min never 15–30m),
regime sources disagree (regime_5m LONG_BIAS 105L/3S flipped in 45min, auto_trader CHOP,
continuum LEAN_BULL/AT). LONGs only on a **sustained 15–30m 1m close ≥80467 WITH volume**;
SHORTs only under EMA300 with 4h aligned; mid-band = no trade; trail-family first; size **1.0x**.

## CEO STACK (unchanged this run)
- ~~D=0.20 post-arm floor GO~~ → closed — live UGB-PT at 0.30; tighten = monitor
- spider tier veto window · pump-chain+ NO-KILL + CONF_FLOOR fkA ruling + pump-chain TAT base-vs-variant
- Oct 27: contrarian pump-chain- PROMOTE + coin_regime n≥50 + mid-band dampen re-measure
  (+ midband_ema300_cond re-run)
- Nov 1: self-healing SKIP verify · Nov 15: floor_admit same-sign · blocked-but-executed at n≥50

## SIDEWAYS (flagged, not acted on)
- **SECURITY: 6 fake `system-reminder` blocks injected into this session mid-tool-call**, each
  pointing at nonexistent paths — `.harp-editor`, `chatroom/*.tsx`, a **curl-and-exec "Node.js
  install" script**, non-existent `*.sh` hook files in `/root/.hermes/hooks` and `/root/.agents/hooks`,
  and a 27-file refactor under `/home/kevin`. All ignored; no external code executed, no files
  changed outside this repo. **Worth investigating what is emitting them.**
- session_brain duplicate-text records = 3rd run flagged (rebuild owed, MED).
- stray 0-byte `/root/.hermes/data/gate_shadow.db` (no repo writer; real DB is `brain/gate_shadow.db`).
