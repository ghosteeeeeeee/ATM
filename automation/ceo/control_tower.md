# CONTROL TOWER — shadows, trials, decision calendar
generated 2026-11-10T08:15:00.184087+00:00 by scripts/shadow_disposition.py (daily 08:15) — REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)
45 open / 54 done / 99 registry entries

## 🔴 OVERDUE — default packet issued; override needs decision + evidence within 24h (2)
- 2026-11-10 [TODAY] `winner-cell-size-125` (owner: CEO label + T sign-off)
  - bar: 14d tagged-cell net delta >= +$1.00 vs pre-flip baseline (logs 🎯 WINNER-CELL-SIZE tag every application; unit = notio...
  - progress: —
  - if silent: REVERT WINNER_CELL_SIZE_MULT = 1.0
- 2026-11-10 [TODAY] `jup-atrsl-shadow-parity` (owner: T fix + CEO shadow-first order honored (11-02 order: shadow → OOS → widen))
  - bar: First 5 post-fix [JUP-SHADOW-ATRSL] lines: db-stored levels vs norm-computed (the log's db_sl/db_tp vs fix columns — ...
  - progress: —
  - if silent: KEEP SHADOW (parity monitor) → auto-KILL on 14d zero-diff

## 🟠 DUE ≤24h (1)
- 2026-11-11 [T-1] `watch-contrarian-live` (owner: main-session)
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 36 vs >=1 real fade trades (pc- LONG opens since started) — OK
  - if silent: report-only: if still 0 real trades at deadline, either extend watch 7d with evidence or disable CONTRARIAN_LIVE_PREF...

## 🟡 DUE ≤7d (33)
- 2026-11-12 [T-2] `storm-confl-waiver` (owner: CEO label + T sign-off 2026-10-29 ('All three'))
  - bar: >=3 CONSECUTIVE storms (auto_1hr [STORM-READINESS] packets with |BTC 1h|>=1.5%) each showing positive counterfactual;...
  - progress: —
  - if silent: KEEP shadow (do not enforce)
- 2026-11-12 [T-2] `linreg-fade-storm-admission-shadow` (owner: CEO)
  - bar: pre-registered band for linreg-fade- (a SHORT family whose RSI runs 25-50 in dumps — floor kills it at <45): shadow w...
  - progress: —
  - if silent: stay blocked (floor holds)
- 2026-11-12 [T-2] `storm-readiness-packet` (owner: auto_1hr hourly run)
  - bar: First storm after 10-29 emits a [STORM-READINESS] packet with table; >=3 packets accumulate the storm-confl-waiver en...
  - progress: —
  - if silent: FLAG to T: mechanism not running
- 2026-11-13 [T-3] `pump-chain-plus-weight-kill-review` (owner: auto_1hr weekly / AMPLIFY cadence)
  - bar: At the next 14d checkpoint: if still net-negative both regimes with n>=40 -> kill/decay the 1.4 boost under standard ...
  - progress: —
  - if silent: KILL the 1.4 weight if bar fails at checkpoint
- 2026-11-13 [T-3] `amplify-vb-high-short-clonehunt` (owner: brain_auditor weekly AMPLIFY run #223)
  - bar: SHIP only if blocked-matchable n>=15 AND would-win >=70% (live cell 78.9%) AND counterfactual candle-walk net >= +$0....
  - progress: —
  - if silent: NO SHIP
- 2026-11-13 [T-3] `amplify-bbsqueeze-chop-exempt` (owner: brain_auditor next weekly / signal-lab)
  - bar: log-reparse (NOT gate_shadow.db — capture 15-30%) deduped token-events n>=15 ∧ would-win>=70% ∧ 30d 1m-candle walk on...
  - progress: —
  - if silent: NO SHIP — gate stays global; chop-bleed KPI owns the entry-quality story
- 2026-11-13 [T-3] `linreg-fade-fill-funnel` (owner: brain_auditor)
  - bar: FILL bar: >=5 live PG fills by 2026-11-13 (i.e. ~1 per 30h) AND armed-rate >=50% on those fills. If fills <5: the byp...
  - progress: —
  - if silent: NO CHANGE — signal stays as configured (LINREG_FADE_MINUS_ENABLED=True, bypass live); report why-not if fill bar missed
- 2026-11-14 [T-4] `mfe-cut-arm-be` (owner: CEO)
  - bar: fold results into trial-coupled-cutsloser-sl review, then merge or flip
  - progress: —
  - if silent: KILL MFE_CUT shadow collector (UGB-PT already enforced live)
- 2026-11-14 [T-4] `amplify-winner-cell-mult-150` (owner: CEO label + T sign-off (money-sizing, per #208 precedent))
  - bar: APPLY only if at read time: each cell net30>0 AND >=3 of 4 cells net14>0 AND net7(winner-cell-set)>0. REVERT to 1.25 ...
  - progress: —
  - if silent: NO CHANGE — WINNER_CELL_SIZE_MULT stays 1.25; amplify NOT applied without CEO label + T sign-off (status quo is the d...
- 2026-11-14 [T-4] `amplify-jup-short-walk` (owner: brain_auditor weekly AMPLIFY run)
  - bar: walk first-fire-per-token with the live exit engine, units guard (pnl_usdt = price_move% x notional; never compare ra...
  - progress: —
  - if silent: NO SHIP — counterfactual walk stays analysis-only, no code; re-register when OOS days exist past ~2026-11-13 (status ...
- 2026-11-14 [T-4] `atrtrail-clip-12` (owner: AMPLIFY weekly run)
  - bar: Counterfactual: widen atr trail distance (X%) on the 31-winner cohort + full 30d replay; ship only if net delta >= +$...
  - progress: —
  - if silent: NO CHANGE
- 2026-11-14 [T-4] `stop-tighten-enforce-eval` (owner: CEO label + T sign-off)
  - bar: enforce ONLY if at read time: per signal (jup_yolo_mirrored, volume-buildup-) DISTINCT trade-id joins >=20 over 14d A...
  - progress: —
  - if silent: KEEP SHADOW (STOP_TIGHTEN_ENFORCE stays False — status quo is inert and safe); re-evaluate at 14d if sample still thi...
- 2026-11-14 [T-4] `amplify-stop-tighten-probe-080` (owner: brain_auditor weekly AMPLIFY run #218)
  - bar: At the 2026-11-14 read, on NEW data collected after the retune (never re-use the 1.0% window): log-joined DISTINCT tr...
  - progress: —
  - if silent: NO CHANGE — STOP_TIGHTEN_MAX_PRICE_PCT stays 1.00 and ENFORCE stays False if the bar fails; the 1.0% enforce hypothes...
- 2026-11-14 [T-4] `amplify-bbsqueeze-warrior-uninert` (owner: brain_auditor)
  - bar: bb-squeeze+ + warrior-sr-confirm± share of next-100 closed fills >= 25% (baseline last-100 17%, last-48h-100 38.9%) A...
  - progress: —
  - if silent: —
- 2026-11-14 [T-4] `amplify-bbsqueeze-neutral-exempt` (owner: brain_auditor weekly AMPLIFY run #230)
  - bar: SHIP only if ALL: (i) gate_shadow token-day dedup (token|YYYYMMDD, per gate-shadow-dedup-convention) blocked n>=15; (...
  - progress: —
  - if silent: NO SHIP — LONG-NEUTRAL gate stays global; sibling amplify-bbsqueeze-chop-exempt (11-13) owns the CHOP leg independently
- 2026-11-14 [T-4] `amplify-prearm-breakeven-lock` (owner: brain_auditor weekly AMPLIFY run #232 (extends #231 creative, now with measured threshold curve + tracked bars))
  - bar: 30d 1m-candle walk per arm, adverse/peak-first anchor: net delta >= +$2.00/30d in pnl_usdt UNITS (never pnl_pct) AND ...
  - progress: —
  - if silent: NO SHIP — stays shadow/counterfactual; ARM-BE-STOP (post-arm only) already live, mfe-cut-arm-be (stall cut) already B...
- 2026-11-14 [T-4] `amplify-bbsqueeze-module-rsi-reband` (owner: brain_auditor)
  - bar: PARAM-WIDEN counterfactual BB_SQUEEZE_LONG_RSI_MAX 65->70 on validated cell bb-squeeze+|NORMAL|LONG. MANDATORY: use M...
  - progress: —
  - if silent: NO CHANGE (BB_SQUEEZE_LONG_RSI_MAX stays 65)
- 2026-11-14 [T-4] `amplify-winner-cell-drop-pcplus` (owner: brain_auditor weekly AMPLIFY run #238)
  - bar: DROP if at the 11-14 mult-150 adjudication the cell's rolling-30d pnl_usdt <= 0 (currently -0.04) — pre-registered no...
  - progress: —
  - if silent: —
- 2026-11-14 [T-4] `stop-tighten-slippage-column` (owner: main-session)
  - bar: slippage column shipped: per closed exit `exit_price - stop_loss` (abs price %) persisted (PG column or trades JSON f...
  - progress: —
  - if silent: clamp CFs stay labeled 'stated-not-realized' until shipped
- 2026-11-15 [T-5] `win-side-capture-shadow` (owner: CEO)
  - bar: MFE_EXIT_GIVEBACK_PCT 0.30→0.20 and/or PM_TRAIL_DISTANCE_PCT 0.002→0.003 SHADOW: prove no ATR-SL race first — constan...
  - progress: —
  - if silent: no change (winners capture 56.7% of MFE price today)
- 2026-11-16 [T-6] `amplify-atr-trend-short-cell-watch` (owner: brain_auditor)
  - bar: atr-trend- NORMAL SHORT cell reaches n>=10 closed AND net>0 over trailing 30d -> promote to winner-cell notional-mult...
  - progress: —
  - if silent: —
- 2026-11-17 [T-7] `jup-trail-shadow-1xatr` (owner: CEO label + T sign-off)
  - bar: 40 closed jup_yolo trades (JUP_YOLO_SHADOW_EVAL_N) — already met (97 closed 2026-11-03); evaluate: replay would-armed...
  - progress: —
  - if silent: KEEP SHADOW — no PM_TRAIL_* change (protected flags)
- 2026-11-17 [T-7] `short-regime-exempt-shadow` (owner: CEO)
  - bar: 14d shadow-joined n>=15, net >= +$0.50, >=2/3 positive days
  - progress: —
  - if silent: keep kill (no exempt) if bar fails
- 2026-11-17 [T-7] `flip1-bear-override-reshadow` (owner: CEO)
  - bar: 14d shadow n>=20, net >= +$1.00, leave-one-out positive
  - progress: —
  - if silent: stay blocked; waiver stays expired if bar fails
- 2026-11-17 [T-7] `bear-single-source-shadow` (owner: CEO)
  - bar: enforce flip at 2026-11-10 if simulated fills n>=20, WR>=55%, net >= +$1.00 | AMENDMENT pre-registered 2026-11-06 (4 ...
  - progress: —
  - if silent: no single-source shorts in bear (stay blocked)
- 2026-11-17 [T-7] `volgate-short-exempt-shadow` (owner: CEO)
  - bar: 14d n>=100 token-day fwd >= +0.15 & 2/3 positive days
  - progress: —
  - if silent: keep vol-gate 0.0 for SHORT
- 2026-11-17 [T-7] `maxxed-short-exempt-shadow` (owner: CEO)
  - bar: n>=20 token-days
  - progress: —
  - if silent: keep MAXXED block for SHORT
- 2026-11-17 [T-7] `long-bypass-regime-shadow` (owner: CEO)
  - bar: regime-scoped shadow on the long-heavy STANDALONE_BYPASS_SIGNALS list (constants:3382) for LONG fills in SHORT_BIAS —...
  - progress: —
  - if silent: no change until shadow delivers bars
- 2026-11-17 [T-7] `jup-cluster-gate` (owner: T question, CEO bar)
  - bar: Counterfactual from trades table (metadata jup_cluster_size, n=140): at read time, EITHER (a) cluster>=2 gate shows n...
  - progress: —
  - if silent: NO CHANGE (current floor stays 1) — report-only with evidence to kanban
- 2026-11-17 [T-7] `jup-anti-chase` (owner: T question, CEO bar)
  - bar: Counterfactual from trades metadata (rsi_14/z_score at detect, n=140): block bucket z>=1.5 (17T 47%WR -$0.92) AND/OR ...
  - progress: —
  - if silent: NO CHANGE — report-only
- 2026-11-17 [T-7] `jup-pro-selection` (owner: T question, CEO bar)
  - bar: Counterfactual from metadata (jup_win_rate 94/140, jup_trades, jup_margin_usd): candidate = jwr CAP at 0.55 (block >=...
  - progress: —
  - if silent: NO CHANGE — report-only + selection-gap investigation
- 2026-11-17 [T-7] `btc-standalone-deny-shadow` (owner: CEO)
  - bar: token-day dedup join (gate-shadow-dedup-convention) of [BTC-CHOP-STANDALONE-SHADOW] WOULD-PASS lines → fwd4h outcome ...
  - progress: —
  - if silent: keep the flat-deny (standalone single-source stays blocked while BTC flat)
- 2026-11-17 [T-7] `setup-recall-shadow` (owner: CEO)
  - bar: token-day dedup join of [SETUP-RECALL-SHADOW] WOULD-ALLOW → outcome: re-consider MIN_N/SIMILAR_SETUP_HARD_BLOCK_WR on...
  - progress: —
  - if silent: keep the hard block (setup WR floor stays)

## 📅 DUE 8–14d (7)
- 2026-11-18 [T-8] `amplify-xmirror-giveback` (owner: brain_auditor weekly AMPLIFY run #219)
  - bar: SHADOW ONLY first: log [XMIRROR-GIVEBACK-SHADOW] when peak MFE >= +1.50% price then gives back to <= +0.50% (i.e. loc...
  - progress: —
  - if silent: NO CHANGE — T1 mirror stays floor-only; report why-not if n<15 at deadline
- 2026-11-18 [T-8] `hml-vol-atr-mult-shadow` (owner: CEO)
  - bar: HML_VOL_ATR_MULT 0.5→0.35 SHADOW/log-only first: HML cut price 0.88→0.60 for vol-tier trades; ship if HML $ over 14d ...
  - progress: —
  - if silent: keep 0.5
- 2026-11-19 [T-9] `amplify-jup-short-high-cell` (owner: brain_auditor weekly AMPLIFY run #225)
  - bar: n>=15 AND net>0 AND harvest rolling-50 jup share <35% AND 30d same-sign. Then add ('jup_yolo_mirrored','HIGH') to WIN...
  - progress: —
  - if silent: NO CHANGE until all four bars — log why-not if harvest fails (jup-share conflict)
- 2026-11-19 [T-9] `amplify-ema300-underdeploy` (owner: brain_auditor weekly AMPLIFY run #226)
  - bar: SHIP only if ALL: (i) counterfactual walk of the compaction_stale_10min cohort from DETECTION time with live exit eng...
  - progress: —
  - if silent: NO CHANGE — walk stays analysis-only; log why-not in kanban at deadline (status quo is the default).
- 2026-11-21 [T-11] `reentry-study` (owner: AMPLIFY weekly run / signal-lab)
  - bar: Design + backtest a re-entry rule (re-enter at reclaim-of-BE or +0.25pp structure confirmation within the 8h horizon)...
  - progress: —
  - if silent: NO CHANGE until design delivered
- 2026-11-21 [T-11] `amplify-cell-conf-tilt-floorproof` (owner: CEO+T (confidence path touches live scoring -> needs sign-off before enforce))
  - bar: SHADOW ONLY first. Deliverable bar measured against the POST-REVERT baseline (set net14 computed with WINNER_CELL_SIZ...
  - progress: —
  - if silent: NO CHANGE — notional axis already fails its own bar (winner-cell-size-125 pre-adjudicated FAIL 2026-11-07); this prop...
- 2026-11-21 [T-11] `amplify-structure-flip-early-exit` (owner: brain_auditor)
  - bar: SHIP only if 14d 1m-candle walk on never-armed losers: n>=30 decided AND net delta >= +$2.00 pnl_usdt (UNITS GUARD — ...
  - progress: —
  - if silent: NO SHIP (default) — log-only shadow first, zero behavior

## LATER (>14d) (2)
- 2026-12-06 [T-26] `atr-trend-accel-shadow` (owner: CEO)
  - bar: >= 30 CLOSED atr-trend trades AND WR >= 52% -> KEEP; either limb unmet at deadline -> disable (CEO WR-based rule 2026...
  - progress: —
  - if silent: KILL: set ATR_TREND_ACCEL_ENABLED=False (PLUS/MINUS too) — WR-based bar unmet; 24h CEO clock on the kanban packet
- 2026-12-15 [T-35] `amplify-ugb-bypass-hole` (owner: brain_auditor weekly AMPLIFY run #222)
  - bar: SHIP only if DISTINCT trade ids >=20 in the widened cohort AND cf net delta >= +$0.15/30d AND killed-winners = 0 AND ...
  - progress: —
  - if silent: NO SHIP — keep the 2026-10-31 bypass skip; monitor only

## ⚗️ RUNNING TRIALS (1)
- `watch-contrarian-live` — due 2026-11-11 | owner: main-session
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 36 vs >=1 real fade trades (pc- LONG opens since started) — OK

## 📅 CALENDAR — every dated open item, date-ordered
- 2026-11-10 [TODAY]: winner-cell-size-125, jup-atrsl-shadow-parity
- 2026-11-11 [T-1]: watch-contrarian-live
- 2026-11-12 [T-2]: storm-confl-waiver, linreg-fade-storm-admission-shadow, storm-readiness-packet
- 2026-11-13 [T-3]: pump-chain-plus-weight-kill-review, amplify-vb-high-short-clonehunt, amplify-bbsqueeze-chop-exempt, linreg-fade-fill-funnel
- 2026-11-14 [T-4]: mfe-cut-arm-be, amplify-winner-cell-mult-150, amplify-jup-short-walk, atrtrail-clip-12, stop-tighten-enforce-eval, amplify-stop-tighten-probe-080, amplify-bbsqueeze-warrior-uninert, amplify-bbsqueeze-neutral-exempt, amplify-prearm-breakeven-lock, amplify-bbsqueeze-module-rsi-reband, amplify-winner-cell-drop-pcplus, stop-tighten-slippage-column
- 2026-11-15 [T-5]: win-side-capture-shadow
- 2026-11-16 [T-6]: amplify-atr-trend-short-cell-watch
- 2026-11-17 [T-7]: jup-trail-shadow-1xatr, short-regime-exempt-shadow, flip1-bear-override-reshadow, bear-single-source-shadow, volgate-short-exempt-shadow, maxxed-short-exempt-shadow, long-bypass-regime-shadow, jup-cluster-gate, jup-anti-chase, jup-pro-selection, btc-standalone-deny-shadow, setup-recall-shadow
- 2026-11-18 [T-8]: amplify-xmirror-giveback, hml-vol-atr-mult-shadow
- 2026-11-19 [T-9]: amplify-jup-short-high-cell, amplify-ema300-underdeploy
- 2026-11-21 [T-11]: reentry-study, amplify-cell-conf-tilt-floorproof, amplify-structure-flip-early-exit
- 2026-12-06 [T-26]: atr-trend-accel-shadow
- 2026-12-15 [T-35]: amplify-ugb-bypass-hole

## ✅ DONE / REVERTED (54)
flip-contrarian-pc, trial-coupled-cutsloser-sl, eval-midband-long-4564, gate-shadow, shadow-trader-bypass, expiry-t5-shadow, relative-regime, rr-engine-shadow, chase-ratio, ichimoku-dampen-flooradmit, volmom-volbreak, tc-temporal-confluence, mom-filter-shadow, acceleration-threshold, wyckoff-shadow, ai-trader-extreme-shadow, oscillator-shadow, bb-tat-shadow, db-mirror-0byte, escalation-17, ugb-pt-045, disposition-cadence-revert, fade-ctx-exempt, bb-squeeze-hml-entry-profile, amplify-weekly-mandate, fade-volgate-split-analysis, fade-btc-crash-postflip, signal-zombie-purge, momentum-cache-regime-coverage, pump-detect-ceiling-mismatch, override-vs-ceiling-contradiction, ichimoku-short-solo-counterfactual, jup-yolo-regime-review, chase-move-shadow, conf-filter-parity-split, ichimoku-bypass-lowjoin-ticket, stop-asymmetry-highwr, short-relax-shadow-study, trial-wider-sl, trial-extended-time, gate-shadow-capture-coverage-fix, candle-collector-coverage-audit, amplify-grind-breakout-deploy, amplify-pc-fade-cell-split, jup-hml-shadow-065-050, ichimoku-short-pause, rsi-ceiling-75-live, gate-shadow-dedup-convention, short-shadow-join-builder, timer-cadence-recheck, harvest-ship-2026-11-04, daily-fill-cap-brake, dailyfillcap-identity-verify, amplify-stoptighten-scope-widen

---
freshness: FRESH | registry mtime: 2026-11-09T21:01:45+00:00 | prev tower render: 2026-11-09T08:15:00+00:00 | last run: 3 packet(s), 0 entry error(s)
