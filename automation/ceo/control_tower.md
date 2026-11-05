# CONTROL TOWER — shadows, trials, decision calendar
generated 2026-11-04T16:46:45.786265+00:00 by scripts/shadow_disposition.py (daily 08:15) — REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)
> ⚠️ **STALE** — last render 2026-11-03T08:15:04+00:00 (>26h ago): the daily timer likely missed a cycle. Re-run `python3 scripts/shadow_disposition.py` before trusting the dates below.
35 open / 37 done / 72 registry entries

## 🟠 DUE ≤24h (1)
- 2026-11-05 [T-1] `fade-btc-crash-postflip` (owner: main-session after CEO label)
  - bar: 24h shadow log of post-flip crash verdicts: count would-kills on faded entries; flip to enforced hoist if log shows t...
  - progress: —
  - if silent: KEEP pre-flip behavior

## 🟡 DUE ≤7d (17)
- 2026-11-06 [T-2] `momentum-cache-regime-coverage` (owner: next brain_auditor weekly AMPLIFY/kill run)
  - bar: Coverage audit: % of hotset/recent-traded tokens with fresh (<4h) regime_4h rows; stale/NULL list; whether NEUTRAL-fa...
  - progress: —
  - if silent: REPORT + fix coverage (writer) if <90% fresh
- 2026-11-06 [T-2] `gate-shadow-capture-coverage-fix` (owner: main-session)
  - bar: per-gate capture >= 90% vs full log reparse for every SHORT/LONG gate (baseline side-find: SHORT-RSI-HARD-FLOOR 43%, ...
  - progress: —
  - if silent: Nov 6 re-audit uses a log-reparse frame instead of gate_shadow.db for per-gate n and carries the capture-limitation c...
- 2026-11-06 [T-2] `candle-collector-coverage-audit` (owner: main-session)
  - bar: every token blocked >=5x in gate_shadow has >=1d of 5m candles in data/candles.db; full LIT/TESTTOKEN/ZZZ* list resol...
  - progress: —
  - if silent: report the gap list with root cause (collector pair coverage) and either fix the collector pair or register the token...
- 2026-11-07 [T-3] `volmom-volbreak` (owner: CEO)
  - bar: pre-registered n>=20 bar
  - progress: —
  - if silent: KILL build (flags already False)
- 2026-11-07 [T-3] `jup-yolo-regime-review` (owner: main-session weekly AMPLIFY run)
  - bar: Counterfactual per-regime: would a regime gate (mirror only in EXTREME/NORMAL?) or size dampener in HIGH/whipsaw impr...
  - progress: —
  - if silent: NO CHANGE (mirror keeps trading) — eval only
- 2026-11-07 [T-3] `harvest-ship-2026-11-04` (owner: CEO)
  - bar: jup share rolling-50 <35% within 48h AND HML 7d <15 AND daily net >= $0 sustained 72h AND LONG fills in SHORT_BIAS -5...
  - progress: —
  - if silent: revert whichever of the 4 ships fails its metric (constants back / flags off), report to kanban
- 2026-11-09 [T-5] `signal-zombie-purge` (owner: main-session -> next consult if T cares)
  - bar: DECISION NEEDED: extending the purge deletes forensic history (we actively use expired-row tombstone reasons for diag...
  - progress: —
  - if silent: NO CHANGE (leave zombies) — storage cost acceptable at ~950/day
- 2026-11-10 [T-6] `mfe-cut-arm-be` (owner: CEO)
  - bar: fold results into trial-coupled-cutsloser-sl review, then merge or flip
  - progress: —
  - if silent: KILL MFE_CUT shadow collector (UGB-PT already enforced live)
- 2026-11-10 [T-6] `ichimoku-dampen-flooradmit` (owner: CEO)
  - bar: n>=15 joined outcomes per stream
  - progress: —
  - if silent: per-stream FLIP/KILL packets
- 2026-11-10 [T-6] `fade-ctx-exempt` (owner: CEO label + T sign-off 2026-10-29 ('proceed'))
  - bar: 7d window: >=15 fade fills AND fade net >= +$1.00 (trades whose source contains pump-chain- AFTER the fade flip; comp...
  - progress: —
  - if silent: KEEP shadow-only (do not enforce)
- 2026-11-10 [T-6] `winner-cell-size-125` (owner: CEO label + T sign-off)
  - bar: 14d tagged-cell net delta >= +$1.00 vs pre-flip baseline (logs 🎯 WINNER-CELL-SIZE tag every application; unit = notio...
  - progress: —
  - if silent: REVERT WINNER_CELL_SIZE_MULT = 1.0
- 2026-11-10 [T-6] `conf-filter-parity-split` (owner: CEO label via main-session / AMPLIFY)
  - bar: Source-scoped jup conf-99 proposal (counterfactual + measurement) OR leave; floor leg NEVER; wholesale stays log-only.
  - progress: —
  - if silent: KEEP SHADOW (wholesale + floor dead; cap via source-scope only)
- 2026-11-10 [T-6] `watch-contrarian-live` (owner: main-session)
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 32 vs >=1 real fade trades (pc- LONG opens since started) — OK
  - if silent: report-only: if still 0 real trades at deadline, either extend watch 7d with evidence or disable CONTRARIAN_LIVE_PREF...
- 2026-11-10 [T-6] `jup-atrsl-shadow-parity` (owner: T fix + CEO shadow-first order honored (11-02 order: shadow → OOS → widen))
  - bar: First 5 post-fix [JUP-SHADOW-ATRSL] lines: db-stored levels vs norm-computed (the log's db_sl/db_tp vs fix columns — ...
  - progress: —
  - if silent: KEEP SHADOW (parity monitor) → auto-KILL on 14d zero-diff
- 2026-11-10 [T-6] `rsi-ceiling-75-live` (owner: CEO)
  - bar: REVERT RULE: back to 65 if 14d 65-75 realized n>=15 with WR<50% or net<0
  - progress: —
  - if silent: revert to 65 if bar fails
- 2026-11-10 [T-6] `bear-single-source-shadow` (owner: CEO)
  - bar: enforce flip at 2026-11-10 if simulated fills n>=20, WR>=55%, net >= +$1.00
  - progress: —
  - if silent: no single-source shorts in bear (stay blocked)
- 2026-11-10 [T-6] `gate-shadow-dedup-convention` (owner: main-session)
  - bar: every quoted fwd mean must be token-day deduped first — event n is 7-10x pseudo-replicated (confluence 5,766 events =...
  - progress: —
  - if silent: consumers quoted event-level are wrong — fix reports before citing

## 📅 DUE 8–14d (16)
- 2026-11-12 [T-8] `storm-confl-waiver` (owner: CEO label + T sign-off 2026-10-29 ('All three'))
  - bar: >=3 CONSECUTIVE storms (auto_1hr [STORM-READINESS] packets with |BTC 1h|>=1.5%) each showing positive counterfactual;...
  - progress: —
  - if silent: KEEP shadow (do not enforce)
- 2026-11-12 [T-8] `storm-readiness-packet` (owner: auto_1hr hourly run)
  - bar: First storm after 10-29 emits a [STORM-READINESS] packet with table; >=3 packets accumulate the storm-confl-waiver en...
  - progress: —
  - if silent: FLAG to T: mechanism not running
- 2026-11-13 [T-9] `pump-chain-plus-weight-kill-review` (owner: auto_1hr weekly / AMPLIFY cadence)
  - bar: At the next 14d checkpoint: if still net-negative both regimes with n>=40 -> kill/decay the 1.4 boost under standard ...
  - progress: —
  - if silent: KILL the 1.4 weight if bar fails at checkpoint
- 2026-11-14 [T-10] `amplify-winner-cell-mult-150` (owner: CEO label + T sign-off (money-sizing, per #208 precedent))
  - bar: APPLY only if at read time: each cell net30>0 AND >=3 of 4 cells net14>0 AND net7(winner-cell-set)>0. REVERT to 1.25 ...
  - progress: —
  - if silent: NO CHANGE — WINNER_CELL_SIZE_MULT stays 1.25; amplify NOT applied without CEO label + T sign-off (status quo is the d...
- 2026-11-14 [T-10] `amplify-jup-short-walk` (owner: brain_auditor weekly AMPLIFY run)
  - bar: walk first-fire-per-token with the live exit engine, units guard (pnl_usdt = price_move% x notional; never compare ra...
  - progress: —
  - if silent: NO SHIP — counterfactual walk stays analysis-only, no code; re-register when OOS days exist past ~2026-11-13 (status ...
- 2026-11-14 [T-10] `atrtrail-clip-12` (owner: AMPLIFY weekly run)
  - bar: Counterfactual: widen atr trail distance (X%) on the 31-winner cohort + full 30d replay; ship only if net delta >= +$...
  - progress: —
  - if silent: NO CHANGE
- 2026-11-14 [T-10] `stop-tighten-enforce-eval` (owner: CEO label + T sign-off)
  - bar: enforce ONLY if at read time: per signal (jup_yolo_mirrored, volume-buildup-) DISTINCT trade-id joins >=20 over 14d A...
  - progress: —
  - if silent: KEEP SHADOW (STOP_TIGHTEN_ENFORCE stays False — status quo is inert and safe); re-evaluate at 14d if sample still thi...
- 2026-11-14 [T-10] `amplify-stop-tighten-probe-080` (owner: brain_auditor weekly AMPLIFY run #218)
  - bar: At the 2026-11-14 read, on NEW data collected after the retune (never re-use the 1.0% window): log-joined DISTINCT tr...
  - progress: —
  - if silent: NO CHANGE — STOP_TIGHTEN_MAX_PRICE_PCT stays 1.00 and ENFORCE stays False if the bar fails; the 1.0% enforce hypothes...
- 2026-11-16 [T-12] `short-shadow-join-builder` (owner: main-session)
  - bar: join builder shipped: for each of the 5 shadow tags, token+dir -> outcome window join (same fwd machinery as gate_sha...
  - progress: —
  - if silent: at 11-17 the shadow bars read n=0 and their safe defaults fire (keep kill / stay blocked / no exempt) — decision defa...
- 2026-11-17 [T-13] `jup-trail-shadow-1xatr` (owner: CEO label + T sign-off)
  - bar: 40 closed jup_yolo trades (JUP_YOLO_SHADOW_EVAL_N) — already met (97 closed 2026-11-03); evaluate: replay would-armed...
  - progress: —
  - if silent: KEEP SHADOW — no PM_TRAIL_* change (protected flags)
- 2026-11-17 [T-13] `short-regime-exempt-shadow` (owner: CEO)
  - bar: 14d shadow-joined n>=15, net >= +$0.50, >=2/3 positive days
  - progress: —
  - if silent: keep kill (no exempt) if bar fails
- 2026-11-17 [T-13] `flip1-bear-override-reshadow` (owner: CEO)
  - bar: 14d shadow n>=20, net >= +$1.00, leave-one-out positive
  - progress: —
  - if silent: stay blocked; waiver stays expired if bar fails
- 2026-11-17 [T-13] `volgate-short-exempt-shadow` (owner: CEO)
  - bar: 14d n>=100 token-day fwd >= +0.15 & 2/3 positive days
  - progress: —
  - if silent: keep vol-gate 0.0 for SHORT
- 2026-11-17 [T-13] `maxxed-short-exempt-shadow` (owner: CEO)
  - bar: n>=20 token-days
  - progress: —
  - if silent: keep MAXXED block for SHORT
- 2026-11-17 [T-13] `long-bypass-regime-shadow` (owner: CEO)
  - bar: regime-scoped shadow on the long-heavy STANDALONE_BYPASS_SIGNALS list (constants:3382) for LONG fills in SHORT_BIAS —...
  - progress: —
  - if silent: no change until shadow delivers bars
- 2026-11-18 [T-14] `amplify-xmirror-giveback` (owner: brain_auditor weekly AMPLIFY run #219)
  - bar: SHADOW ONLY first: log [XMIRROR-GIVEBACK-SHADOW] when peak MFE >= +1.50% price then gives back to <= +0.50% (i.e. loc...
  - progress: —
  - if silent: NO CHANGE — T1 mirror stays floor-only; report why-not if n<15 at deadline

## LATER (>14d) (1)
- 2026-11-21 [T-17] `reentry-study` (owner: AMPLIFY weekly run / signal-lab)
  - bar: Design + backtest a re-entry rule (re-enter at reclaim-of-BE or +0.25pp structure confirmation within the 8h horizon)...
  - progress: —
  - if silent: NO CHANGE until design delivered

## ⚗️ RUNNING TRIALS (1)
- `watch-contrarian-live` — due 2026-11-10 | owner: main-session
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 32 vs >=1 real fade trades (pc- LONG opens since started) — OK

## 📅 CALENDAR — every dated open item, date-ordered
- 2026-11-05 [T-1]: fade-btc-crash-postflip
- 2026-11-06 [T-2]: momentum-cache-regime-coverage, gate-shadow-capture-coverage-fix, candle-collector-coverage-audit
- 2026-11-07 [T-3]: volmom-volbreak, jup-yolo-regime-review, harvest-ship-2026-11-04
- 2026-11-09 [T-5]: signal-zombie-purge
- 2026-11-10 [T-6]: mfe-cut-arm-be, ichimoku-dampen-flooradmit, fade-ctx-exempt, winner-cell-size-125, conf-filter-parity-split, watch-contrarian-live, jup-atrsl-shadow-parity, rsi-ceiling-75-live, bear-single-source-shadow, gate-shadow-dedup-convention
- 2026-11-12 [T-8]: storm-confl-waiver, storm-readiness-packet
- 2026-11-13 [T-9]: pump-chain-plus-weight-kill-review
- 2026-11-14 [T-10]: amplify-winner-cell-mult-150, amplify-jup-short-walk, atrtrail-clip-12, stop-tighten-enforce-eval, amplify-stop-tighten-probe-080
- 2026-11-16 [T-12]: short-shadow-join-builder
- 2026-11-17 [T-13]: jup-trail-shadow-1xatr, short-regime-exempt-shadow, flip1-bear-override-reshadow, volgate-short-exempt-shadow, maxxed-short-exempt-shadow, long-bypass-regime-shadow
- 2026-11-18 [T-14]: amplify-xmirror-giveback
- 2026-11-21 [T-17]: reentry-study

## ✅ DONE / REVERTED (37)
flip-contrarian-pc, trial-coupled-cutsloser-sl, eval-midband-long-4564, gate-shadow, shadow-trader-bypass, expiry-t5-shadow, relative-regime, rr-engine-shadow, chase-ratio, tc-temporal-confluence, mom-filter-shadow, acceleration-threshold, wyckoff-shadow, ai-trader-extreme-shadow, oscillator-shadow, bb-tat-shadow, db-mirror-0byte, escalation-17, ugb-pt-045, disposition-cadence-revert, bb-squeeze-hml-entry-profile, amplify-weekly-mandate, fade-volgate-split-analysis, pump-detect-ceiling-mismatch, override-vs-ceiling-contradiction, ichimoku-short-solo-counterfactual, chase-move-shadow, ichimoku-bypass-lowjoin-ticket, stop-asymmetry-highwr, short-relax-shadow-study, trial-wider-sl, trial-extended-time, amplify-grind-breakout-deploy, amplify-pc-fade-cell-split, jup-hml-shadow-065-050, ichimoku-short-pause, timer-cadence-recheck

---
freshness: STALE | registry mtime: 2026-11-04T16:46:45+00:00 | prev tower render: 2026-11-03T08:15:04+00:00 | last run: 2 packet(s), 0 entry error(s)
