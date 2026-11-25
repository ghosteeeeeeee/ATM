# CONTROL TOWER — shadows, trials, decision calendar
generated 2026-11-25T12:44:22.403508+00:00 by scripts/shadow_disposition.py (daily 08:15 + on any registry change via hermes-shadow-disposition.path) — REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)
37 open / 116 done / 153 registry entries

## 🟠 DUE ≤24h (2)
- 2026-11-26 [T-1] `storm-confl-waiver` (owner: CEO label + T sign-off 2026-10-29 ('All three'))
  - bar: >=3 CONSECUTIVE storms (auto_1hr [STORM-READINESS] packets with |BTC 1h|>=1.5%) each showing positive counterfactual;...
  - progress: —
  - if silent: KEEP shadow (do not enforce)
- 2026-11-26 [T-1] `regime-conf-extreme-revert-read` (owner: brain_auditor #299)
  - bar: SHIP boost 0.85->1.15 only if: 7d AND 14d EXTREME net>0 AND 30d EXTREME net>0 AND no other regime-mult change in same...
  - progress: —
  - if silent: —

## 🟡 DUE ≤7d (26)
- 2026-11-27 [T-2] `pc-plus-weight-monitor` (owner: brain_auditor)
  - bar: 14d BOTH-regimes-negative with n>=40 -> kill 1.4 weight; else KEEP with rationale. Cell-scoped: 30d EXTREME net<=0 tw...
  - progress: —
  - if silent: KEEP weight (INSUFFICIENT sample)
- 2026-11-27 [T-2] `amplify-linregfade-volgate-admit` (owner: brain_auditor weekly AMPLIFY run #253)
  - bar: ENFORCE admit 'linreg-fade-','linreg_fade_short' to REGIME_SIGNALS['NORMAL'] ONLY IF at read time: (i) killed-EXEC 30...
  - progress: —
  - if silent: NO SHIP — current read fails (i) n=26<40 and (ii) ~+$0.56<$1.00
- 2026-11-27 [T-2] `stop-family-entry-filter-shadow` (owner: CEO)
  - bar: shadow-block entry when direction=LONG AND ((detect-time rsi_exec in [55,70]) OR (gap_pct in [0.5,1.0])) PLUS exec-ti...
  - progress: —
  - if silent: NO-SHIP (bar set deliberately strict: #261 shows rsi/gap/momentum do NOT predict never-armed bleed; jup's rsi>=55 gat...
- 2026-11-27 [T-2] `other-gate-short-withhold-review` (owner: signal_analyst)
  - bar: Per-gate split of the 'none' cell (n=526 token-days, +$14.48, WR58.2%, p=0.0002, both halves positive, LOO +$13.69): ...
  - progress: —
  - if silent: no change — KEEP rulings stand (cross-tab cell is aggregate, not per-gate)
- 2026-11-28 [T-3] `amplify-jup-short-walk` (owner: brain_auditor weekly AMPLIFY run)
  - bar: walk first-fire-per-token with the live exit engine, units guard (pnl_usdt = price_move% x notional; never compare ra...
  - progress: —
  - if silent: NO SHIP — counterfactual walk stays analysis-only, no code; re-register when OOS days exist past ~2026-11-13 (status ...
- 2026-11-28 [T-3] `reentry-study` (owner: AMPLIFY weekly run / signal-lab)
  - bar: Design + backtest a re-entry rule (re-enter at reclaim-of-BE or +0.25pp structure confirmation within the 8h horizon)...
  - progress: —
  - if silent: NO CHANGE until design delivered
- 2026-11-28 [T-3] `amplify-cell-conf-tilt-floorproof` (owner: CEO+T (confidence path touches live scoring -> needs sign-off before enforce))
  - bar: SHADOW ONLY first. Deliverable bar measured against the POST-REVERT baseline (set net14 computed with WINNER_CELL_SIZ...
  - progress: —
  - if silent: NO CHANGE — notional axis already fails its own bar (winner-cell-size-125 pre-adjudicated FAIL 2026-11-07); this prop...
- 2026-11-28 [T-3] `amplify-r2v2-long3-clonehunt` (owner: brain_auditor #260 AMPLIFY (weekly emit))
  - bar: SHIP only if ALL: (i) blocked-LONG cohort reaches tok_n>=50 on the PRIMARY fwd_4h basis (NOT would_win/would_pnl — se...
  - progress: —
  - if silent: NO SHIP — coverage entry only; re-measure at 11-21 with fresh OOS days
- 2026-11-28 [T-3] `amplify-longbypass-dual-basis-reconcile` (owner: brain_auditor #284 AMPLIFY (weekly-adjacent emit; formal weekly = 11-23))
  - bar: Reconcile FIRST: (1) run both bases on the SAME cohort and SAME window (fwd_4h PRIMARY vs the 11-17 joinable realized...
  - progress: —
  - if silent: NO CHANGE — measurement only; do not relax a CEO SHIP-LIVE gate on a single-basis read
- 2026-11-28 [T-3] `amplify-maker-entry-fill-walk` (owner: ?)
  - bar: SHIP only if ALL: (i) 3m fill rate >=80% [MET 82.3%]; (ii) missed-cohort net pnl >=0 [MET -0.25 means skipping is net...
  - progress: —
  - if silent: —
- 2026-11-28 [T-3] `prearm-enforce-day7-read` (owner: brain_auditor #288 (registry ship — deadline was only recorded inside a done disposition, would have been dropped))
  - bar: At 7 enforce days: (1) fk via full walk (not reach-proxy): share of prearm exits whose NORMAL exit-engine outcome wou...
  - progress: —
  - if silent: keep PREARM_LOCK_ENFORCE=True (CEO GO stands), NO param change; divergence guard needs CEO even if bar (3) trips
- 2026-11-29 [T-4] `tape-at-long-remeasure-1129` (owner: brain_auditor)
  - bar: SHIP-review only if ALL: n>=150 stamped closed LONG-AT trades, net<0 in BOTH >=14d and >=30d halves (same-sign), two-...
  - progress: —
  - if silent: —
- 2026-11-30 [T-5] `long-rsi-floor30-shadow` (owner: CEO)
  - bar: token-day dedup join of WOULD-BLOCK cohort → enforce floor30 iff cohort net-of-fee negative AND WR<45% at n>=20 AND b...
  - progress: —
  - if silent: keep floor 20
- 2026-11-30 [T-5] `hl-copy-plus-shadow` (owner: CEO)
  - bar: counterfactual: enforce disable only if would-skip cohort keeps LONG net-of-fee negative at n>=10 with any regime ≥55...
  - progress: —
  - if silent: keep enabled until counterfactual reads
- 2026-11-30 [T-5] `amplify-rider-extreme-long-cell` (owner: brain_auditor #291 weekly AMPLIFY)
  - bar: SHIP cell-add only if ALL: (i) 30d n>=10 net>0 (HAVE: 13T +0.35 WR 61.5% arm 69.2% 11 tokens); (ii) 7d/14d/30d same-s...
  - progress: —
  - if silent: —
- 2026-11-30 [T-5] `amplify-atp-short-normal-cell` (owner: brain_auditor #293 weekly AMPLIFY)
  - bar: SHIP cell-add only if ALL: (i) CEO has ratified OR vetoed the atp SHORT RSI<35 half-size dampen first; (ii) 30d n>=10...
  - progress: —
  - if silent: —
- 2026-12-01 [T-6] `linreg-fade-storm-admission-shadow` (owner: CEO)
  - bar: pre-registered band for linreg-fade- (a SHORT family whose RSI runs 25-50 in dumps — floor kills it at <45): shadow w...
  - progress: —
  - if silent: stay blocked (floor holds)
- 2026-12-01 [T-6] `jup-atrsl-shadow-parity` (owner: T fix + CEO shadow-first order honored (11-02 order: shadow → OOS → widen))
  - bar: First 5 post-fix [JUP-SHADOW-ATRSL] lines: db-stored levels vs norm-computed (the log's db_sl/db_tp vs fix columns — ...
  - progress: —
  - if silent: KEEP SHADOW (parity monitor) → auto-KILL on 14d zero-diff
- 2026-12-01 [T-6] `win-side-capture-shadow` (owner: CEO)
  - bar: MFE_EXIT_GIVEBACK_PCT 0.30→0.20 and/or PM_TRAIL_DISTANCE_PCT 0.002→0.003 SHADOW: prove no ATR-SL race first — constan...
  - progress: —
  - if silent: no change (winners capture 56.7% of MFE price today)
- 2026-12-01 [T-6] `hotset-pin-approved-shadow` (owner: CEO)
  - bar: baseline fell-out=42/day longs; after pin enable: fell-out longs <10/24h AND long APPROVED→EXECUTED >=8/day (vs 2-3 n...
  - progress: —
  - if silent: stay pinned-off
- 2026-12-01 [T-6] `amplify-capture-leaderboard-giveback` (owner: brain_auditor #287 AMPLIFY (weekly emit))
  - bar: BLOCKED until win-side-capture-shadow reaches its 11-25 read bar (n>=40 distinct trade_ids AND pace >= +$0.10/day AND...
  - progress: —
  - if silent: NO CHANGE — global win-capture still collecting; this entry cannot fire before 11-25
- 2026-12-01 [T-6] `prearm-band-lower-candle-oos` (owner: brain_auditor)
  - bar: candle-OOS net >= +1.00/14d in pnl_usdt UNITS (guard #193 landmine) AND fk<20% AND 30d same-sign; default NO SHIP
  - progress: —
  - if silent: NO SHIP if bar unmet at 12-01 read
- 2026-12-01 [T-6] `amplify-stale-block-bleed5` (owner: brain_auditor #295 weekly AMPLIFY emit)
  - bar: SHADOW first: log [STALE-BLOCK-SHADOW] would-block lines (zero behavior) at detect for the 5 signals when is_stale=tr...
  - progress: —
  - if silent: —
- 2026-12-02 [T-7] `watch-contrarian-live` (owner: main-session)
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 38 vs >=1 real fade trades (pc- LONG opens since started) — OK
  - if silent: report-only: if still 0 real trades at deadline, either extend watch 7d with evidence or disable CONTRARIAN_LIVE_PREF...
- 2026-12-02 [T-7] `amplify-pcfade-windowfix-repromote-review` (owner: brain_auditor weekly AMPLIFY + CEO/T sign-off (CONTRARIAN_LIVE is a live flag))
  - bar: ALL bars before ANY live action: (i) corrected pc- overall flip-WR >=58 at the 11-18 read AND both halves same-sign; ...
  - progress: —
  - if silent: —
- 2026-12-02 [T-7] `amplify-pumpchain-normal-short-early` (owner: brain_auditor weekly AMPLIFY run #274)
  - bar: SHIP only if ALL: (i) PG cell n>=10 decided AND net pnl_usdt > 0 (units guard); (ii) 7d/14d/30d same-sign; (iii) fk <...
  - progress: —
  - if silent: NO CHANGE — early monitor only; log why-not at deadline if n stays <10

## 📅 DUE 8–14d (8)
- 2026-12-03 [T-8] `kill-line-shadow-enforce` (owner: CEO)
  - bar: ENFORCE (auto-disable of ONE signal source) ONLY if ALL: (a) actual kill line CROSS (pct_consumed >=1.00 in data/kill...
  - progress: —
  - if silent: KEEP SHADOW log-only — no disable, no trading-path change; re-derive lines only via committed --derive refresh if a b...
- 2026-12-05 [T-10] `amplify-bbsqueeze-module-rsi-reband` (owner: brain_auditor)
  - bar: PARAM-WIDEN counterfactual BB_SQUEEZE_LONG_RSI_MAX 65->70 on validated cell bb-squeeze+|NORMAL|LONG. MANDATORY: use M...
  - progress: —
  - if silent: NO CHANGE (BB_SQUEEZE_LONG_RSI_MAX stays 65)
- 2026-12-05 [T-10] `amplify-structure-flip-early-exit` (owner: brain_auditor)
  - bar: SHIP only if 14d 1m-candle walk on never-armed losers: n>=30 decided AND net delta >= +$2.00 pnl_usdt (UNITS GUARD — ...
  - progress: —
  - if silent: NO SHIP (default) — log-only shadow first, zero behavior
- 2026-12-06 [T-11] `atr-trend-accel-shadow` (owner: CEO)
  - bar: KEEP at deadline (2026-12-06) requires n >= 30 AND WR >= 52% AND net PnL >= $0; any limb unmet -> KILL. PnL limb is a...
  - progress: —
  - if silent: KILL: set ATR_TREND_ACCEL_ENABLED=False (PLUS/MINUS too) — any limb unmet; 24h CEO clock on the kanban packet
- 2026-12-06 [T-11] `winner-side-protection-review` (owner: auto_1hr/weights)
  - bar: Protect, don't cut: pc- 30d payoff 2.13, ai-trader-pending 30d payoff 1.65 (only live positive-payoff carriers); any ...
  - progress: —
  - if silent: no weight change (protection = do not cut, do not reweight upward without bar)
- 2026-12-07 [T-12] `amplify-vbo-short-killreview` (owner: brain_auditor #293 weekly AMPLIFY)
  - bar: SHIP re-enable review only if ALL: (i) restart shadow detection for the source and collect >=60 deduped rows over 14d...
  - progress: —
  - if silent: —
- 2026-12-08 [T-13] `amplify-mfe-giveback-armed-lossers-scope` (owner: brain_auditor #296)
  - bar: SHIP only if: (i) n>=15 distinct armed losers in scope; (ii) candle-OOS walk on the wider armed population: fk<20% (a...
  - progress: —
  - if silent: NO-SHIP until bars met (n=10 < 15)
- 2026-12-09 [T-14] `double-fire-concurrent-cap-shadow` (owner: brain_auditor #299)
  - bar: Promote to enforce only if shadow n>=20 double-fire events AND blocked cohort would-be net saved >= +$1.00 AND Fisher...
  - progress: —
  - if silent: —

## LATER (>14d) (1)
- 2026-12-15 [T-20] `amplify-ugb-bypass-hole` (owner: brain_auditor weekly AMPLIFY run #222)
  - bar: SHIP only if DISTINCT trade ids >=20 in the widened cohort AND cf net delta >= +$0.15/30d AND killed-winners = 0 AND ...
  - progress: —
  - if silent: NO SHIP — keep the 2026-10-31 bypass skip; monitor only

## ⚗️ RUNNING TRIALS (1)
- `watch-contrarian-live` — due 2026-12-02 | owner: main-session
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 38 vs >=1 real fade trades (pc- LONG opens since started) — OK

## 📅 CALENDAR — every dated open item, date-ordered
- 2026-11-26 [T-1]: storm-confl-waiver, regime-conf-extreme-revert-read
- 2026-11-27 [T-2]: pc-plus-weight-monitor, amplify-linregfade-volgate-admit, stop-family-entry-filter-shadow, other-gate-short-withhold-review
- 2026-11-28 [T-3]: amplify-jup-short-walk, reentry-study, amplify-cell-conf-tilt-floorproof, amplify-r2v2-long3-clonehunt, amplify-longbypass-dual-basis-reconcile, amplify-maker-entry-fill-walk, prearm-enforce-day7-read
- 2026-11-29 [T-4]: tape-at-long-remeasure-1129
- 2026-11-30 [T-5]: long-rsi-floor30-shadow, hl-copy-plus-shadow, amplify-rider-extreme-long-cell, amplify-atp-short-normal-cell
- 2026-12-01 [T-6]: linreg-fade-storm-admission-shadow, jup-atrsl-shadow-parity, win-side-capture-shadow, hotset-pin-approved-shadow, amplify-capture-leaderboard-giveback, prearm-band-lower-candle-oos, amplify-stale-block-bleed5
- 2026-12-02 [T-7]: watch-contrarian-live, amplify-pcfade-windowfix-repromote-review, amplify-pumpchain-normal-short-early
- 2026-12-03 [T-8]: kill-line-shadow-enforce
- 2026-12-05 [T-10]: amplify-bbsqueeze-module-rsi-reband, amplify-structure-flip-early-exit
- 2026-12-06 [T-11]: atr-trend-accel-shadow, winner-side-protection-review
- 2026-12-07 [T-12]: amplify-vbo-short-killreview
- 2026-12-08 [T-13]: amplify-mfe-giveback-armed-lossers-scope
- 2026-12-09 [T-14]: double-fire-concurrent-cap-shadow
- 2026-12-15 [T-20]: amplify-ugb-bypass-hole

## ✅ DONE / REVERTED (116)
flip-contrarian-pc, trial-coupled-cutsloser-sl, eval-midband-long-4564, gate-shadow, shadow-trader-bypass, expiry-t5-shadow, mfe-cut-arm-be, relative-regime, rr-engine-shadow, chase-ratio, ichimoku-dampen-flooradmit, volmom-volbreak, tc-temporal-confluence, mom-filter-shadow, acceleration-threshold, wyckoff-shadow, ai-trader-extreme-shadow, oscillator-shadow, bb-tat-shadow, db-mirror-0byte, escalation-17, ugb-pt-045, disposition-cadence-revert, fade-ctx-exempt, winner-cell-size-125, bb-squeeze-hml-entry-profile, amplify-weekly-mandate, fade-volgate-split-analysis, fade-btc-crash-postflip, storm-readiness-packet, signal-zombie-purge, momentum-cache-regime-coverage, pump-detect-ceiling-mismatch, override-vs-ceiling-contradiction, ichimoku-short-solo-counterfactual, jup-yolo-regime-review, amplify-winner-cell-mult-150, atrtrail-clip-12, chase-move-shadow, conf-filter-parity-split, ichimoku-bypass-lowjoin-ticket, stop-asymmetry-highwr, short-relax-shadow-study, pump-chain-plus-weight-kill-review, trial-wider-sl, trial-extended-time, gate-shadow-capture-coverage-fix, candle-collector-coverage-audit, stop-tighten-enforce-eval, amplify-grind-breakout-deploy, amplify-pc-fade-cell-split, amplify-stop-tighten-probe-080, jup-hml-shadow-065-050, jup-trail-shadow-1xatr, short-regime-exempt-shadow, flip1-bear-override-reshadow, ichimoku-short-pause, rsi-ceiling-75-live, bear-single-source-shadow, volgate-short-exempt-shadow, maxxed-short-exempt-shadow, gate-shadow-dedup-convention, long-bypass-regime-shadow, short-shadow-join-builder, timer-cadence-recheck, harvest-ship-2026-11-04, amplify-xmirror-giveback, daily-fill-cap-brake, amplify-vb-high-short-clonehunt, amplify-jup-short-high-cell, amplify-ema300-underdeploy, amplify-bbsqueeze-chop-exempt, jup-cluster-gate, jup-anti-chase, jup-pro-selection, btc-standalone-deny-shadow, setup-recall-shadow, linreg-fade-fill-funnel, amplify-bbsqueeze-warrior-uninert, amplify-bbsqueeze-neutral-exempt, amplify-prearm-breakeven-lock, dailyfillcap-identity-verify, amplify-stoptighten-scope-widen, amplify-winner-cell-drop-pcplus, stop-tighten-slippage-column, hml-vol-atr-mult-shadow, amplify-atr-trend-short-cell-watch, amplify-tat-neverarmed-age-widen, amplify-atr-trend-short-clonehunt, amplify-ugb-bypass-armgap, amplify-jup-long-flat-cell, amplify-grind-breakout-underdeploy, compaction-stale-trend-band-eval, exitstack-day-kpi-1114, amplify-vb-high-short-underdeploy, amplify-warrior-sr-normal-long, watch-pc-flip-demote-55, amplify-slope-jup-short-exempt, amplify-pcv6-extreme-short-cell, amplify-short-rsi-hard-ceiling-85-walk, floor-admit-same-sign-verdict, amplify-ai-trader-pending-normal-short-btc-cell, amplify-rider-fade-threshold-walk, amplify-jup-long-blocked-clonehunt, ai-trader-pending-tag-split, gate-interaction-cross-tab, brake-counterfactual-shadow, regime-gate-tension-check, amplify-ema300-breakthrough-underdeploy, tp-vs-trail-shadow, goal-metric-restructure, post822-payoff-regrouping, kpi-framework-formal, r2-drawdown-tier-wiring, arm-rate-control-tower, entry-hl-entry-invariant

---
freshness: FRESH | registry mtime: 2026-11-25T12:44:22+00:00 | prev tower render: 2026-11-25T08:49:53+00:00 | last run: 1 packet(s), 0 entry error(s)
