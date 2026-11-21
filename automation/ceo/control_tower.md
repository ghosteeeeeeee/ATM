# CONTROL TOWER — shadows, trials, decision calendar
generated 2026-11-21T04:47:48.606430+00:00 by scripts/shadow_disposition.py (daily 08:15 + on any registry change via hermes-shadow-disposition.path) — REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)
32 open / 101 done / 133 registry entries

## 🟠 DUE ≤24h (3)
- 2026-11-22 [T-1] `win-side-capture-shadow` (owner: CEO)
  - bar: MFE_EXIT_GIVEBACK_PCT 0.30→0.20 and/or PM_TRAIL_DISTANCE_PCT 0.002→0.003 SHADOW: prove no ATR-SL race first — constan...
  - progress: —
  - if silent: no change (winners capture 56.7% of MFE price today)
- 2026-11-22 [T-1] `amplify-ai-trader-pending-normal-short-btc-cell` (owner: CEO (ai-trader = CEO domain, steer-001 owns the signal-level view))
  - bar: EARLY LABEL. Cell already passes windows (7d 21T +0.64 / 14d 21T +0.64 / 30d 26T +0.64, all net>0). Remaining bars be...
  - progress: —
  - if silent: NO CHANGE — mult stays 1.0, cell NOT added to WINNER_CELLS_VALIDATED until all four bars pass
- 2026-11-22 [T-1] `amplify-rider-fade-threshold-walk` (owner: brain_auditor #280 AMPLIFY (weekly emit))
  - bar: WALK LIMB: reconstruct fire-level cohort (pc+ fires 30d x candles_1m pre15) and walk thresholds {0.05,0.10,0.15,0.20}...
  - progress: —
  - if silent: NO FLIP — keep BTC_PUMP_RIDER_FADE_BLOCK_MODE='shadow'; walk is pre-ship robustness only

## 🟡 DUE ≤7d (20)
- 2026-11-23 [T-2] `amplify-jup-long-blocked-clonehunt` (owner: brain_auditor #280 AMPLIFY (weekly emit; uncovered LONG leg — jup-short-walk owns SHORT))
  - bar: SHIP only if ALL: (i) correct-key token-day n>=15 maintained (have 37); (ii) 1m/5m candle-walk of blocked LONG first-...
  - progress: —
  - if silent: NO SHIP — provenance suspect (blocked>bested vs live WR); walk only, no gate exempt until (ii)+(iv)
- 2026-11-24 [T-3] `ai-trader-pending-tag-split` (owner: signal_analyst)
  - bar: split tag ai-trader-pending vs -auto so the auto-ladder cohort is judged separately; gate ONLY the auto cohort if it ...
  - progress: —
  - if silent: no change to armed pending path
- 2026-11-24 [T-3] `gate-interaction-cross-tab` (owner: signal_analyst)
  - bar: Interaction cross-tab: per SHORT candidate, which of floor45/regime-gate/vol-gate fired (overlap % matrix) + token-da...
  - progress: —
  - if silent: no change — single-gate KEEP rulings stand (no blanket kills; marginal-only evidence so far)
- 2026-11-24 [T-3] `brake-counterfactual-shadow` (owner: main-session)
  - bar: Every SKIP: DailyFillCap [blocked TOK DIR src] line joins an outcome row (fwd4h, token-day dedup, $13.44, 0.09-0.106%...
  - progress: —
  - if silent: brake unchanged (LEAVE ruling 20261120T1548Z stands; margin option fee_net<-$0.50 awaits T)
- 2026-11-24 [T-3] `regime-gate-tension-check` (owner: signal_analyst)
  - bar: RECONCILE two disagreeing reads: (a) A1 tag-join 11-17: exempting SHORT_BIAS singles = net -$0.83 (bar NOT met, keep ...
  - progress: —
  - if silent: keep A1 ENFORCE=False + regime-gate as-is (both prior readings stand until reconciled — do NOT flip on either alone)
- 2026-11-25 [T-4] `watch-contrarian-live` (owner: main-session)
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 38 vs >=1 real fade trades (pc- LONG opens since started) — OK
  - if silent: report-only: if still 0 real trades at deadline, either extend watch 7d with evidence or disable CONTRARIAN_LIVE_PREF...
- 2026-11-25 [T-4] `amplify-bbsqueeze-module-rsi-reband` (owner: brain_auditor)
  - bar: PARAM-WIDEN counterfactual BB_SQUEEZE_LONG_RSI_MAX 65->70 on validated cell bb-squeeze+|NORMAL|LONG. MANDATORY: use M...
  - progress: —
  - if silent: NO CHANGE (BB_SQUEEZE_LONG_RSI_MAX stays 65)
- 2026-11-25 [T-4] `amplify-structure-flip-early-exit` (owner: brain_auditor)
  - bar: SHIP only if 14d 1m-candle walk on never-armed losers: n>=30 decided AND net delta >= +$2.00 pnl_usdt (UNITS GUARD — ...
  - progress: —
  - if silent: NO SHIP (default) — log-only shadow first, zero behavior
- 2026-11-25 [T-4] `amplify-pcfade-windowfix-repromote-review` (owner: brain_auditor weekly AMPLIFY + CEO/T sign-off (CONTRARIAN_LIVE is a live flag))
  - bar: ALL bars before ANY live action: (i) corrected pc- overall flip-WR >=58 at the 11-18 read AND both halves same-sign; ...
  - progress: —
  - if silent: —
- 2026-11-25 [T-4] `hotset-pin-approved-shadow` (owner: CEO)
  - bar: baseline fell-out=42/day longs; after pin enable: fell-out longs <10/24h AND long APPROVED→EXECUTED >=8/day (vs 2-3 n...
  - progress: —
  - if silent: stay pinned-off
- 2026-11-26 [T-5] `storm-confl-waiver` (owner: CEO label + T sign-off 2026-10-29 ('All three'))
  - bar: >=3 CONSECUTIVE storms (auto_1hr [STORM-READINESS] packets with |BTC 1h|>=1.5%) each showing positive counterfactual;...
  - progress: —
  - if silent: KEEP shadow (do not enforce)
- 2026-11-27 [T-6] `pc-plus-weight-monitor` (owner: brain_auditor)
  - bar: 14d BOTH-regimes-negative with n>=40 -> kill 1.4 weight; else KEEP with rationale. Cell-scoped: 30d EXTREME net<=0 tw...
  - progress: —
  - if silent: KEEP weight (INSUFFICIENT sample)
- 2026-11-27 [T-6] `amplify-linregfade-volgate-admit` (owner: brain_auditor weekly AMPLIFY run #253)
  - bar: ENFORCE admit 'linreg-fade-','linreg_fade_short' to REGIME_SIGNALS['NORMAL'] ONLY IF at read time: (i) killed-EXEC 30...
  - progress: —
  - if silent: NO SHIP — current read fails (i) n=26<40 and (ii) ~+$0.56<$1.00
- 2026-11-27 [T-6] `stop-family-entry-filter-shadow` (owner: CEO)
  - bar: shadow-block entry when direction=LONG AND ((detect-time rsi_exec in [55,70]) OR (gap_pct in [0.5,1.0])) PLUS exec-ti...
  - progress: —
  - if silent: NO-SHIP (bar set deliberately strict: #261 shows rsi/gap/momentum do NOT predict never-armed bleed; jup's rsi>=55 gat...
- 2026-11-27 [T-6] `other-gate-short-withhold-review` (owner: signal_analyst)
  - bar: Per-gate split of the 'none' cell (n=526 token-days, +$14.48, WR58.2%, p=0.0002, both halves positive, LOO +$13.69): ...
  - progress: —
  - if silent: no change — KEEP rulings stand (cross-tab cell is aggregate, not per-gate)
- 2026-11-28 [T-7] `amplify-jup-short-walk` (owner: brain_auditor weekly AMPLIFY run)
  - bar: walk first-fire-per-token with the live exit engine, units guard (pnl_usdt = price_move% x notional; never compare ra...
  - progress: —
  - if silent: NO SHIP — counterfactual walk stays analysis-only, no code; re-register when OOS days exist past ~2026-11-13 (status ...
- 2026-11-28 [T-7] `reentry-study` (owner: AMPLIFY weekly run / signal-lab)
  - bar: Design + backtest a re-entry rule (re-enter at reclaim-of-BE or +0.25pp structure confirmation within the 8h horizon)...
  - progress: —
  - if silent: NO CHANGE until design delivered
- 2026-11-28 [T-7] `amplify-cell-conf-tilt-floorproof` (owner: CEO+T (confidence path touches live scoring -> needs sign-off before enforce))
  - bar: SHADOW ONLY first. Deliverable bar measured against the POST-REVERT baseline (set net14 computed with WINNER_CELL_SIZ...
  - progress: —
  - if silent: NO CHANGE — notional axis already fails its own bar (winner-cell-size-125 pre-adjudicated FAIL 2026-11-07); this prop...
- 2026-11-28 [T-7] `amplify-r2v2-long3-clonehunt` (owner: brain_auditor #260 AMPLIFY (weekly emit))
  - bar: SHIP only if ALL: (i) blocked-LONG cohort reaches tok_n>=50 on the PRIMARY fwd_4h basis (NOT would_win/would_pnl — se...
  - progress: —
  - if silent: NO SHIP — coverage entry only; re-measure at 11-21 with fresh OOS days
- 2026-11-28 [T-7] `amplify-longbypass-dual-basis-reconcile` (owner: brain_auditor #284 AMPLIFY (weekly-adjacent emit; formal weekly = 11-23))
  - bar: Reconcile FIRST: (1) run both bases on the SAME cohort and SAME window (fwd_4h PRIMARY vs the 11-17 joinable realized...
  - progress: —
  - if silent: NO CHANGE — measurement only; do not relax a CEO SHIP-LIVE gate on a single-basis read

## 📅 DUE 8–14d (7)
- 2026-11-29 [T-8] `tape-at-long-remeasure-1129` (owner: brain_auditor)
  - bar: SHIP-review only if ALL: n>=150 stamped closed LONG-AT trades, net<0 in BOTH >=14d and >=30d halves (same-sign), two-...
  - progress: —
  - if silent: —
- 2026-11-30 [T-9] `long-rsi-floor30-shadow` (owner: CEO)
  - bar: token-day dedup join of WOULD-BLOCK cohort → enforce floor30 iff cohort net-of-fee negative AND WR<45% at n>=20 AND b...
  - progress: —
  - if silent: keep floor 20
- 2026-11-30 [T-9] `hl-copy-plus-shadow` (owner: CEO)
  - bar: counterfactual: enforce disable only if would-skip cohort keeps LONG net-of-fee negative at n>=10 with any regime ≥55...
  - progress: —
  - if silent: keep enabled until counterfactual reads
- 2026-12-01 [T-10] `linreg-fade-storm-admission-shadow` (owner: CEO)
  - bar: pre-registered band for linreg-fade- (a SHORT family whose RSI runs 25-50 in dumps — floor kills it at <45): shadow w...
  - progress: —
  - if silent: stay blocked (floor holds)
- 2026-12-01 [T-10] `jup-atrsl-shadow-parity` (owner: T fix + CEO shadow-first order honored (11-02 order: shadow → OOS → widen))
  - bar: First 5 post-fix [JUP-SHADOW-ATRSL] lines: db-stored levels vs norm-computed (the log's db_sl/db_tp vs fix columns — ...
  - progress: —
  - if silent: KEEP SHADOW (parity monitor) → auto-KILL on 14d zero-diff
- 2026-12-02 [T-11] `amplify-pumpchain-normal-short-early` (owner: brain_auditor weekly AMPLIFY run #274)
  - bar: SHIP only if ALL: (i) PG cell n>=10 decided AND net pnl_usdt > 0 (units guard); (ii) 7d/14d/30d same-sign; (iii) fk <...
  - progress: —
  - if silent: NO CHANGE — early monitor only; log why-not at deadline if n stays <10
- 2026-12-03 [T-12] `kill-line-shadow-enforce` (owner: CEO)
  - bar: ENFORCE (auto-disable of ONE signal source) ONLY if ALL: (a) actual kill line CROSS (pct_consumed >=1.00 in data/kill...
  - progress: —
  - if silent: KEEP SHADOW log-only — no disable, no trading-path change; re-derive lines only via committed --derive refresh if a b...

## LATER (>14d) (2)
- 2026-12-06 [T-15] `atr-trend-accel-shadow` (owner: CEO)
  - bar: KEEP at deadline (2026-12-06) requires n >= 30 AND WR >= 52% AND net PnL >= $0; any limb unmet -> KILL. PnL limb is a...
  - progress: —
  - if silent: KILL: set ATR_TREND_ACCEL_ENABLED=False (PLUS/MINUS too) — any limb unmet; 24h CEO clock on the kanban packet
- 2026-12-15 [T-24] `amplify-ugb-bypass-hole` (owner: brain_auditor weekly AMPLIFY run #222)
  - bar: SHIP only if DISTINCT trade ids >=20 in the widened cohort AND cf net delta >= +$0.15/30d AND killed-winners = 0 AND ...
  - progress: —
  - if silent: NO SHIP — keep the 2026-10-31 bypass skip; monitor only

## ⚗️ RUNNING TRIALS (1)
- `watch-contrarian-live` — due 2026-11-25 | owner: main-session
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 38 vs >=1 real fade trades (pc- LONG opens since started) — OK

## 📅 CALENDAR — every dated open item, date-ordered
- 2026-11-22 [T-1]: win-side-capture-shadow, amplify-ai-trader-pending-normal-short-btc-cell, amplify-rider-fade-threshold-walk
- 2026-11-23 [T-2]: amplify-jup-long-blocked-clonehunt
- 2026-11-24 [T-3]: ai-trader-pending-tag-split, gate-interaction-cross-tab, brake-counterfactual-shadow, regime-gate-tension-check
- 2026-11-25 [T-4]: watch-contrarian-live, amplify-bbsqueeze-module-rsi-reband, amplify-structure-flip-early-exit, amplify-pcfade-windowfix-repromote-review, hotset-pin-approved-shadow
- 2026-11-26 [T-5]: storm-confl-waiver
- 2026-11-27 [T-6]: pc-plus-weight-monitor, amplify-linregfade-volgate-admit, stop-family-entry-filter-shadow, other-gate-short-withhold-review
- 2026-11-28 [T-7]: amplify-jup-short-walk, reentry-study, amplify-cell-conf-tilt-floorproof, amplify-r2v2-long3-clonehunt, amplify-longbypass-dual-basis-reconcile
- 2026-11-29 [T-8]: tape-at-long-remeasure-1129
- 2026-11-30 [T-9]: long-rsi-floor30-shadow, hl-copy-plus-shadow
- 2026-12-01 [T-10]: linreg-fade-storm-admission-shadow, jup-atrsl-shadow-parity
- 2026-12-02 [T-11]: amplify-pumpchain-normal-short-early
- 2026-12-03 [T-12]: kill-line-shadow-enforce
- 2026-12-06 [T-15]: atr-trend-accel-shadow
- 2026-12-15 [T-24]: amplify-ugb-bypass-hole

## ✅ DONE / REVERTED (101)
flip-contrarian-pc, trial-coupled-cutsloser-sl, eval-midband-long-4564, gate-shadow, shadow-trader-bypass, expiry-t5-shadow, mfe-cut-arm-be, relative-regime, rr-engine-shadow, chase-ratio, ichimoku-dampen-flooradmit, volmom-volbreak, tc-temporal-confluence, mom-filter-shadow, acceleration-threshold, wyckoff-shadow, ai-trader-extreme-shadow, oscillator-shadow, bb-tat-shadow, db-mirror-0byte, escalation-17, ugb-pt-045, disposition-cadence-revert, fade-ctx-exempt, winner-cell-size-125, bb-squeeze-hml-entry-profile, amplify-weekly-mandate, fade-volgate-split-analysis, fade-btc-crash-postflip, storm-readiness-packet, signal-zombie-purge, momentum-cache-regime-coverage, pump-detect-ceiling-mismatch, override-vs-ceiling-contradiction, ichimoku-short-solo-counterfactual, jup-yolo-regime-review, amplify-winner-cell-mult-150, atrtrail-clip-12, chase-move-shadow, conf-filter-parity-split, ichimoku-bypass-lowjoin-ticket, stop-asymmetry-highwr, short-relax-shadow-study, pump-chain-plus-weight-kill-review, trial-wider-sl, trial-extended-time, gate-shadow-capture-coverage-fix, candle-collector-coverage-audit, stop-tighten-enforce-eval, amplify-grind-breakout-deploy, amplify-pc-fade-cell-split, amplify-stop-tighten-probe-080, jup-hml-shadow-065-050, jup-trail-shadow-1xatr, short-regime-exempt-shadow, flip1-bear-override-reshadow, ichimoku-short-pause, rsi-ceiling-75-live, bear-single-source-shadow, volgate-short-exempt-shadow, maxxed-short-exempt-shadow, gate-shadow-dedup-convention, long-bypass-regime-shadow, short-shadow-join-builder, timer-cadence-recheck, harvest-ship-2026-11-04, amplify-xmirror-giveback, daily-fill-cap-brake, amplify-vb-high-short-clonehunt, amplify-jup-short-high-cell, amplify-ema300-underdeploy, amplify-bbsqueeze-chop-exempt, jup-cluster-gate, jup-anti-chase, jup-pro-selection, btc-standalone-deny-shadow, setup-recall-shadow, linreg-fade-fill-funnel, amplify-bbsqueeze-warrior-uninert, amplify-bbsqueeze-neutral-exempt, amplify-prearm-breakeven-lock, dailyfillcap-identity-verify, amplify-stoptighten-scope-widen, amplify-winner-cell-drop-pcplus, stop-tighten-slippage-column, hml-vol-atr-mult-shadow, amplify-atr-trend-short-cell-watch, amplify-tat-neverarmed-age-widen, amplify-atr-trend-short-clonehunt, amplify-ugb-bypass-armgap, amplify-jup-long-flat-cell, amplify-grind-breakout-underdeploy, compaction-stale-trend-band-eval, exitstack-day-kpi-1114, amplify-vb-high-short-underdeploy, amplify-warrior-sr-normal-long, watch-pc-flip-demote-55, amplify-slope-jup-short-exempt, amplify-pcv6-extreme-short-cell, amplify-short-rsi-hard-ceiling-85-walk, floor-admit-same-sign-verdict

---
freshness: FRESH | registry mtime: 2026-11-21T04:47:48+00:00 | prev tower render: 2026-11-21T04:45:21+00:00 | last run: 0 packet(s), 0 entry error(s)
