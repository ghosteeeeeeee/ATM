# CONTROL TOWER — shadows, trials, decision calendar
generated 2026-11-17T00:50:04.573122+00:00 by scripts/shadow_disposition.py (daily 08:15 + on any registry change via hermes-shadow-disposition.path) — REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)
36 open / 86 done / 122 registry entries

## 🟠 DUE ≤24h (8)
- 2026-11-18 [T-1] `watch-contrarian-live` (owner: main-session)
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 38 vs >=1 real fade trades (pc- LONG opens since started) — OK
  - if silent: report-only: if still 0 real trades at deadline, either extend watch 7d with evidence or disable CONTRARIAN_LIVE_PREF...
- 2026-11-18 [T-1] `amplify-xmirror-giveback` (owner: brain_auditor weekly AMPLIFY run #219)
  - bar: SHADOW ONLY first: log [XMIRROR-GIVEBACK-SHADOW] when peak MFE >= +1.50% price then gives back to <= +0.50% (i.e. loc...
  - progress: —
  - if silent: NO CHANGE — T1 mirror stays floor-only; report why-not if n<15 at deadline
- 2026-11-18 [T-1] `hml-vol-atr-mult-shadow` (owner: CEO)
  - bar: HML_VOL_ATR_MULT 0.5→0.35 SHADOW/log-only first: HML cut price 0.88→0.60 for vol-tier trades; ship if HML $ over 14d ...
  - progress: —
  - if silent: keep 0.5
- 2026-11-18 [T-1] `amplify-atr-trend-short-clonehunt` (owner: brain_auditor weekly AMPLIFY run #246)
  - bar: SHIP only if ALL: (i) gate_shadow token-day dedup (token|YYYYMMDD) blocked n>=15; (ii) would-win >=70% on deduped set...
  - progress: —
  - if silent: NO SHIP — keep all gates global; report n at 11-18
- 2026-11-18 [T-1] `amplify-ugb-bypass-armgap` (owner: ?)
  - bar: SHIP only if ALL: (i) candle-walk UGB-PT (peak-UGB_PT_DISTANCE_PCT) on bypass-signal arm-gap atr_sl cohort n>=20 (30d...
  - progress: —
  - if silent: NO SHIP — collection + candle-walk only; report at 11-18
- 2026-11-18 [T-1] `amplify-jup-long-flat-cell` (owner: ?)
  - bar: Promote to WINNER_CELLS_VALIDATED candidate only if n>=15 AND net>0 AND 30d same-sign AND arm% >= 50. If net<=0 or n<...
  - progress: —
  - if silent: —
- 2026-11-18 [T-1] `amplify-grind-breakout-underdeploy` (owner: ?)
  - bar: SHIP only if: (i) gate_shadow/log blocked-matchable n>=15 token-day deduped; (ii) would-win >=70%; (iii) 30d 1m-candl...
  - progress: —
  - if silent: —
- 2026-11-18 [T-1] `amplify-pcfade-windowfix-repromote-review` (owner: brain_auditor weekly AMPLIFY + CEO/T sign-off (CONTRARIAN_LIVE is a live flag))
  - bar: ALL bars before ANY live action: (i) corrected pc- overall flip-WR >=58 at the 11-18 read AND both halves same-sign; ...
  - progress: —
  - if silent: —

## 🟡 DUE ≤7d (19)
- 2026-11-19 [T-2] `storm-confl-waiver` (owner: CEO label + T sign-off 2026-10-29 ('All three'))
  - bar: >=3 CONSECUTIVE storms (auto_1hr [STORM-READINESS] packets with |BTC 1h|>=1.5%) each showing positive counterfactual;...
  - progress: —
  - if silent: KEEP shadow (do not enforce)
- 2026-11-19 [T-2] `amplify-ema300-underdeploy` (owner: brain_auditor weekly AMPLIFY run #226)
  - bar: SHIP only if ALL: (i) counterfactual walk of the compaction_stale_10min cohort from DETECTION time with live exit eng...
  - progress: —
  - if silent: NO CHANGE — walk stays analysis-only; log why-not in kanban at deadline (status quo is the default).
- 2026-11-20 [T-3] `compaction-stale-trend-band-eval` (owner: CEO)
  - bar: Carve-out test (ruling HOLDS no-relax until proven): admit a compaction_stale single-type signal ONLY when (BTC 1h <=...
  - progress: —
  - if silent: no change — staleness=move-already-happened=chase stays blocked
- 2026-11-20 [T-3] `amplify-vb-high-short-underdeploy` (owner: brain_auditor weekly AMPLIFY run #255)
  - bar: identify block source (confluence/ctx/regime/hotset/exec) for the 30d setup gap; counterfactual-walk 30d blocked setu...
  - progress: —
  - if silent: NO CHANGE — if block is a quality filter (not plumbing), report and close
- 2026-11-20 [T-3] `amplify-warrior-sr-normal-long` (owner: brain_auditor weekly AMPLIFY run #256)
  - bar: SHIP only if: (i) cell reaches n>=10/30d with net>0 same-sign at 7d+14d; OR blocked-matchable n>=15 token-day deduped...
  - progress: —
  - if silent: NO SHIP — close as early-cell noise if n<10 at deadline
- 2026-11-20 [T-3] `hotset-pin-approved-shadow` (owner: CEO)
  - bar: baseline fell-out=42/day longs; after pin enable: fell-out longs <10/24h AND long APPROVED→EXECUTED >=8/day (vs 2-3 n...
  - progress: —
  - if silent: stay pinned-off
- 2026-11-21 [T-4] `amplify-jup-short-walk` (owner: brain_auditor weekly AMPLIFY run)
  - bar: walk first-fire-per-token with the live exit engine, units guard (pnl_usdt = price_move% x notional; never compare ra...
  - progress: —
  - if silent: NO SHIP — counterfactual walk stays analysis-only, no code; re-register when OOS days exist past ~2026-11-13 (status ...
- 2026-11-21 [T-4] `atrtrail-clip-12` (owner: AMPLIFY weekly run)
  - bar: Counterfactual: widen atr trail distance (X%) on the 31-winner cohort + full 30d replay; ship only if net delta >= +$...
  - progress: —
  - if silent: NO CHANGE
- 2026-11-21 [T-4] `reentry-study` (owner: AMPLIFY weekly run / signal-lab)
  - bar: Design + backtest a re-entry rule (re-enter at reclaim-of-BE or +0.25pp structure confirmation within the 8h horizon)...
  - progress: —
  - if silent: NO CHANGE until design delivered
- 2026-11-21 [T-4] `amplify-prearm-breakeven-lock` (owner: brain_auditor weekly AMPLIFY run #232 (extends #231 creative, now with measured threshold curve + tracked bars))
  - bar: 30d 1m-candle walk per arm, adverse/peak-first anchor: net delta >= +$2.00/30d in pnl_usdt UNITS (never pnl_pct) AND ...
  - progress: —
  - if silent: NO SHIP — stays shadow/counterfactual; ARM-BE-STOP (post-arm only) already live, mfe-cut-arm-be (stall cut) already B...
- 2026-11-21 [T-4] `amplify-cell-conf-tilt-floorproof` (owner: CEO+T (confidence path touches live scoring -> needs sign-off before enforce))
  - bar: SHADOW ONLY first. Deliverable bar measured against the POST-REVERT baseline (set net14 computed with WINNER_CELL_SIZ...
  - progress: —
  - if silent: NO CHANGE — notional axis already fails its own bar (winner-cell-size-125 pre-adjudicated FAIL 2026-11-07); this prop...
- 2026-11-21 [T-4] `amplify-bbsqueeze-module-rsi-reband` (owner: brain_auditor)
  - bar: PARAM-WIDEN counterfactual BB_SQUEEZE_LONG_RSI_MAX 65->70 on validated cell bb-squeeze+|NORMAL|LONG. MANDATORY: use M...
  - progress: —
  - if silent: NO CHANGE (BB_SQUEEZE_LONG_RSI_MAX stays 65)
- 2026-11-21 [T-4] `amplify-structure-flip-early-exit` (owner: brain_auditor)
  - bar: SHIP only if 14d 1m-candle walk on never-armed losers: n>=30 decided AND net delta >= +$2.00 pnl_usdt (UNITS GUARD — ...
  - progress: —
  - if silent: NO SHIP (default) — log-only shadow first, zero behavior
- 2026-11-21 [T-4] `amplify-slope-jup-short-exempt` (owner: brain_auditor #259 AMPLIFY)
  - bar: SHIP only if ALL: (i) 1m-candle walk of the n=23 blocked jup SHORTs with live exit engine net >= +$1.00/30d pnl_usdt ...
  - progress: —
  - if silent: NO SHIP — keep SLOPE-FILTER global; report why-not if walk fails
- 2026-11-21 [T-4] `amplify-r2v2-long3-clonehunt` (owner: brain_auditor #260 AMPLIFY (weekly emit))
  - bar: SHIP only if ALL: (i) blocked-LONG cohort reaches tok_n>=50 on the PRIMARY fwd_4h basis (NOT would_win/would_pnl — se...
  - progress: —
  - if silent: NO SHIP — coverage entry only; re-measure at 11-21 with fresh OOS days
- 2026-11-21 [T-4] `amplify-pcv6-extreme-short-cell` (owner: brain_auditor #261 AMPLIFY (weekly emit))
  - bar: Promote to clone-hunt ONLY IF: 30d n>=15 AND net >= +0.50 AND arm >= 60% AND 7d/14d same sign (units = pnl_usdt). Els...
  - progress: —
  - if silent: no change — early cell, watch-only
- 2026-11-21 [T-4] `amplify-short-rsi-hard-ceiling-85-walk` (owner: brain_auditor)
  - bar: SHIP only if ALL: (1) gate_shadow token-day-dedup fwd_4h for the PURE >75 hard-ceiling cohort (regex splits '(hard ce...
  - progress: —
  - if silent: NO-SHIP — hard ceiling stays 75 unless EVERY threshold below clears; 'oversold/bounce-risk even in bear' doctrine (bf...
- 2026-11-22 [T-5] `win-side-capture-shadow` (owner: CEO)
  - bar: MFE_EXIT_GIVEBACK_PCT 0.30→0.20 and/or PM_TRAIL_DISTANCE_PCT 0.002→0.003 SHADOW: prove no ATR-SL race first — constan...
  - progress: —
  - if silent: no change (winners capture 56.7% of MFE price today)
- 2026-11-22 [T-5] `amplify-ai-trader-pending-normal-short-btc-cell` (owner: CEO (ai-trader = CEO domain, steer-001 owns the signal-level view))
  - bar: EARLY LABEL. Cell already passes windows (7d 21T +0.64 / 14d 21T +0.64 / 30d 26T +0.64, all net>0). Remaining bars be...
  - progress: —
  - if silent: NO CHANGE — mult stays 1.0, cell NOT added to WINNER_CELLS_VALIDATED until all four bars pass

## 📅 DUE 8–14d (7)
- 2026-11-27 [T-10] `pc-plus-weight-monitor` (owner: brain_auditor)
  - bar: 14d BOTH-regimes-negative with n>=40 -> kill 1.4 weight; else KEEP with rationale. Cell-scoped: 30d EXTREME net<=0 tw...
  - progress: —
  - if silent: KEEP weight (INSUFFICIENT sample)
- 2026-11-27 [T-10] `amplify-linregfade-volgate-admit` (owner: brain_auditor weekly AMPLIFY run #253)
  - bar: ENFORCE admit 'linreg-fade-','linreg_fade_short' to REGIME_SIGNALS['NORMAL'] ONLY IF at read time: (i) killed-EXEC 30...
  - progress: —
  - if silent: NO SHIP — current read fails (i) n=26<40 and (ii) ~+$0.56<$1.00
- 2026-11-29 [T-12] `tape-at-long-remeasure-1129` (owner: brain_auditor)
  - bar: SHIP-review only if ALL: n>=150 stamped closed LONG-AT trades, net<0 in BOTH >=14d and >=30d halves (same-sign), two-...
  - progress: —
  - if silent: —
- 2026-11-30 [T-13] `long-rsi-floor30-shadow` (owner: CEO)
  - bar: token-day dedup join of WOULD-BLOCK cohort → enforce floor30 iff cohort net-of-fee negative AND WR<45% at n>=20 AND b...
  - progress: —
  - if silent: keep floor 20
- 2026-11-30 [T-13] `hl-copy-plus-shadow` (owner: CEO)
  - bar: counterfactual: enforce disable only if would-skip cohort keeps LONG net-of-fee negative at n>=10 with any regime ≥55...
  - progress: —
  - if silent: keep enabled until counterfactual reads
- 2026-12-01 [T-14] `linreg-fade-storm-admission-shadow` (owner: CEO)
  - bar: pre-registered band for linreg-fade- (a SHORT family whose RSI runs 25-50 in dumps — floor kills it at <45): shadow w...
  - progress: —
  - if silent: stay blocked (floor holds)
- 2026-12-01 [T-14] `jup-atrsl-shadow-parity` (owner: T fix + CEO shadow-first order honored (11-02 order: shadow → OOS → widen))
  - bar: First 5 post-fix [JUP-SHADOW-ATRSL] lines: db-stored levels vs norm-computed (the log's db_sl/db_tp vs fix columns — ...
  - progress: —
  - if silent: KEEP SHADOW (parity monitor) → auto-KILL on 14d zero-diff

## LATER (>14d) (2)
- 2026-12-06 [T-19] `atr-trend-accel-shadow` (owner: CEO)
  - bar: >= 30 CLOSED atr-trend trades AND WR >= 52% -> KEEP; either limb unmet at deadline -> disable (CEO WR-based rule 2026...
  - progress: —
  - if silent: KILL: set ATR_TREND_ACCEL_ENABLED=False (PLUS/MINUS too) — WR-based bar unmet; 24h CEO clock on the kanban packet
- 2026-12-15 [T-28] `amplify-ugb-bypass-hole` (owner: brain_auditor weekly AMPLIFY run #222)
  - bar: SHIP only if DISTINCT trade ids >=20 in the widened cohort AND cf net delta >= +$0.15/30d AND killed-winners = 0 AND ...
  - progress: —
  - if silent: NO SHIP — keep the 2026-10-31 bypass skip; monitor only

## ⚗️ RUNNING TRIALS (1)
- `watch-contrarian-live` — due 2026-11-18 | owner: main-session
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 38 vs >=1 real fade trades (pc- LONG opens since started) — OK

## 📅 CALENDAR — every dated open item, date-ordered
- 2026-11-18 [T-1]: watch-contrarian-live, amplify-xmirror-giveback, hml-vol-atr-mult-shadow, amplify-atr-trend-short-clonehunt, amplify-ugb-bypass-armgap, amplify-jup-long-flat-cell, amplify-grind-breakout-underdeploy, amplify-pcfade-windowfix-repromote-review
- 2026-11-19 [T-2]: storm-confl-waiver, amplify-ema300-underdeploy
- 2026-11-20 [T-3]: compaction-stale-trend-band-eval, amplify-vb-high-short-underdeploy, amplify-warrior-sr-normal-long, hotset-pin-approved-shadow
- 2026-11-21 [T-4]: amplify-jup-short-walk, atrtrail-clip-12, reentry-study, amplify-prearm-breakeven-lock, amplify-cell-conf-tilt-floorproof, amplify-bbsqueeze-module-rsi-reband, amplify-structure-flip-early-exit, amplify-slope-jup-short-exempt, amplify-r2v2-long3-clonehunt, amplify-pcv6-extreme-short-cell, amplify-short-rsi-hard-ceiling-85-walk
- 2026-11-22 [T-5]: win-side-capture-shadow, amplify-ai-trader-pending-normal-short-btc-cell
- 2026-11-27 [T-10]: pc-plus-weight-monitor, amplify-linregfade-volgate-admit
- 2026-11-29 [T-12]: tape-at-long-remeasure-1129
- 2026-11-30 [T-13]: long-rsi-floor30-shadow, hl-copy-plus-shadow
- 2026-12-01 [T-14]: linreg-fade-storm-admission-shadow, jup-atrsl-shadow-parity
- 2026-12-06 [T-19]: atr-trend-accel-shadow
- 2026-12-15 [T-28]: amplify-ugb-bypass-hole

## ✅ DONE / REVERTED (86)
flip-contrarian-pc, trial-coupled-cutsloser-sl, eval-midband-long-4564, gate-shadow, shadow-trader-bypass, expiry-t5-shadow, mfe-cut-arm-be, relative-regime, rr-engine-shadow, chase-ratio, ichimoku-dampen-flooradmit, volmom-volbreak, tc-temporal-confluence, mom-filter-shadow, acceleration-threshold, wyckoff-shadow, ai-trader-extreme-shadow, oscillator-shadow, bb-tat-shadow, db-mirror-0byte, escalation-17, ugb-pt-045, disposition-cadence-revert, fade-ctx-exempt, winner-cell-size-125, bb-squeeze-hml-entry-profile, amplify-weekly-mandate, fade-volgate-split-analysis, fade-btc-crash-postflip, storm-readiness-packet, signal-zombie-purge, momentum-cache-regime-coverage, pump-detect-ceiling-mismatch, override-vs-ceiling-contradiction, ichimoku-short-solo-counterfactual, jup-yolo-regime-review, amplify-winner-cell-mult-150, chase-move-shadow, conf-filter-parity-split, ichimoku-bypass-lowjoin-ticket, stop-asymmetry-highwr, short-relax-shadow-study, pump-chain-plus-weight-kill-review, trial-wider-sl, trial-extended-time, gate-shadow-capture-coverage-fix, candle-collector-coverage-audit, stop-tighten-enforce-eval, amplify-grind-breakout-deploy, amplify-pc-fade-cell-split, amplify-stop-tighten-probe-080, jup-hml-shadow-065-050, jup-trail-shadow-1xatr, short-regime-exempt-shadow, flip1-bear-override-reshadow, ichimoku-short-pause, rsi-ceiling-75-live, bear-single-source-shadow, volgate-short-exempt-shadow, maxxed-short-exempt-shadow, gate-shadow-dedup-convention, long-bypass-regime-shadow, short-shadow-join-builder, timer-cadence-recheck, harvest-ship-2026-11-04, daily-fill-cap-brake, amplify-vb-high-short-clonehunt, amplify-jup-short-high-cell, amplify-bbsqueeze-chop-exempt, jup-cluster-gate, jup-anti-chase, jup-pro-selection, btc-standalone-deny-shadow, setup-recall-shadow, linreg-fade-fill-funnel, amplify-bbsqueeze-warrior-uninert, amplify-bbsqueeze-neutral-exempt, dailyfillcap-identity-verify, amplify-stoptighten-scope-widen, amplify-winner-cell-drop-pcplus, stop-tighten-slippage-column, amplify-atr-trend-short-cell-watch, amplify-tat-neverarmed-age-widen, exitstack-day-kpi-1114, watch-pc-flip-demote-55, floor-admit-same-sign-verdict

---
freshness: FRESH | registry mtime: 2026-11-17T00:50:04+00:00 | prev tower render: 2026-11-16T20:48:34+00:00 | last run: 8 packet(s), 0 entry error(s)
