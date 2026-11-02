# CONTROL TOWER — shadows, trials, decision calendar
generated 2026-11-02T08:15:00.139208+00:00 by scripts/shadow_disposition.py (daily 08:15) — REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)
30 open / 25 done / 55 registry entries

## 🟠 DUE ≤24h (5)
- 2026-11-03 [T-1] `eval-midband-long-4564` (owner: self_learner)
  - bar: fresh SCOPED out-of-sample eval (regime/direction split, n>=15 per cell, p-value + split-halves) delivered to kanban
  - progress: —
  - if silent: no change; escalation packet re-issued with EVAL-OVERDUE label
- 2026-11-03 [T-1] `escalation-17` (owner: CEO)
  - bar: packet answered ONCE with decision + evidence
  - progress: —
  - if silent: auto-close as stale-escalation (no answer = escalation cannot survive without a decision)
- 2026-11-03 [T-1] `ugb-pt-045` (owner: CEO monitors; T direct sign-off 2026-10-28 (session question 'UGB giveback'))
  - bar: 7d ugb_pt cohort avg pnl must not DETERIORATE vs the 0.30 baseline (n>=10) — wider giveback = later exit = deeper per...
  - progress: —
  - if silent: REVERT to 0.30 and report to kanban
- 2026-11-03 [T-1] `disposition-cadence-revert` (owner: main-session (T sign-off 'All three'))
  - bar: After the 11-03 cluster is dispositioned: revert timer OnCalendar to 'Mon *-*-* 08:15:00' (config + /etc + daemon-rel...
  - progress: —
  - if silent: REVERT timer to weekly + close this entry
- 2026-11-03 [T-1] `watch-contrarian-live` (owner: main-session)
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 25 vs >=1 real fade trades (pc- LONG opens since started) — OK
  - if silent: report-only: if still 0 real trades at deadline, either extend watch 7d with evidence or disable CONTRARIAN_LIVE_PREF...

## 🟡 DUE ≤7d (11)
- 2026-11-05 [T-3] `fade-btc-crash-postflip` (owner: main-session after CEO label)
  - bar: 24h shadow log of post-flip crash verdicts: count would-kills on faded entries; flip to enforced hoist if log shows t...
  - progress: —
  - if silent: KEEP pre-flip behavior
- 2026-11-05 [T-3] `ichimoku-bypass-lowjoin-ticket` (owner: main-session -> CEO)
  - bar: Either fix the join measurement (log-to-trade attribution) and re-measure at n>=15, or execute the ticket (ICHIMOKU_L...
  - progress: —
  - if silent: EXECUTE TICKET if join still <floor after measurement fix
- 2026-11-06 [T-4] `momentum-cache-regime-coverage` (owner: next brain_auditor weekly AMPLIFY/kill run)
  - bar: Coverage audit: % of hotset/recent-traded tokens with fresh (<4h) regime_4h rows; stale/NULL list; whether NEUTRAL-fa...
  - progress: —
  - if silent: REPORT + fix coverage (writer) if <90% fresh
- 2026-11-06 [T-4] `gate-shadow-capture-coverage-fix` (owner: main-session)
  - bar: per-gate capture >= 90% vs full log reparse for every SHORT/LONG gate (baseline side-find: SHORT-RSI-HARD-FLOOR 43%, ...
  - progress: —
  - if silent: Nov 6 re-audit uses a log-reparse frame instead of gate_shadow.db for per-gate n and carries the capture-limitation c...
- 2026-11-06 [T-4] `candle-collector-coverage-audit` (owner: main-session)
  - bar: every token blocked >=5x in gate_shadow has >=1d of 5m candles in data/candles.db; full LIT/TESTTOKEN/ZZZ* list resol...
  - progress: —
  - if silent: report the gap list with root cause (collector pair coverage) and either fix the collector pair or register the token...
- 2026-11-07 [T-5] `volmom-volbreak` (owner: CEO)
  - bar: pre-registered n>=20 bar
  - progress: —
  - if silent: KILL build (flags already False)
- 2026-11-07 [T-5] `jup-yolo-regime-review` (owner: main-session weekly AMPLIFY run)
  - bar: Counterfactual per-regime: would a regime gate (mirror only in EXTREME/NORMAL?) or size dampener in HIGH/whipsaw impr...
  - progress: —
  - if silent: NO CHANGE (mirror keeps trading) — eval only
- 2026-11-07 [T-5] `trial-wider-sl` (owner: CEO)
  - bar: wider-arm WR >= 55.0% with >= 200 trades (SHADOW_TRIAL_MIN_WR)
  - progress: 37.7 vs >=55.0 % WR wider-arm, n=7852/200 — NOT MET
  - if silent: KILL trial — pre-registered WR bar missed (fresh 10-31: wider arm 37.7% vs 55.0%); archive exit_wider_sl_json counter...
- 2026-11-07 [T-5] `trial-extended-time` (owner: CEO)
  - bar: extended-arm WR improvement >= 5.0pp with >= 100 trades
  - progress: -13.6 vs >=5.0 pp WR-improvement, n=22608/100 — NOT MET
  - if silent: KILL trial per pre-registered WR bar (fresh 10-31: -15.7pp vs >=+5.0pp); archive exit_extended_time_json, zero live c...
- 2026-11-09 [T-7] `signal-zombie-purge` (owner: main-session -> next consult if T cares)
  - bar: DECISION NEEDED: extending the purge deletes forensic history (we actively use expired-row tombstone reasons for diag...
  - progress: —
  - if silent: NO CHANGE (leave zombies) — storage cost acceptable at ~950/day
- 2026-11-09 [T-7] `amplify-pc-fade-cell-split` (owner: brain_auditor weekly AMPLIFY run)
  - bar: Extend analysis/contrarian_outcome_join.py to emit by-token and by-BTC-regime flip-WR for pump-chain-. Ship bar: cell...
  - progress: —
  - if silent: NO CHANGE if no cell clears bars

## 📅 DUE 8–14d (13)
- 2026-11-10 [T-8] `mfe-cut-arm-be` (owner: CEO)
  - bar: fold results into trial-coupled-cutsloser-sl review, then merge or flip
  - progress: —
  - if silent: KILL MFE_CUT shadow collector (UGB-PT already enforced live)
- 2026-11-10 [T-8] `ichimoku-dampen-flooradmit` (owner: CEO)
  - bar: n>=15 joined outcomes per stream
  - progress: —
  - if silent: per-stream FLIP/KILL packets
- 2026-11-10 [T-8] `fade-ctx-exempt` (owner: CEO label + T sign-off 2026-10-29 ('proceed'))
  - bar: 7d window: >=15 fade fills AND fade net >= +$1.00 (trades whose source contains pump-chain- AFTER the fade flip; comp...
  - progress: —
  - if silent: KEEP shadow-only (do not enforce)
- 2026-11-10 [T-8] `winner-cell-size-125` (owner: CEO label + T sign-off)
  - bar: 14d tagged-cell net delta >= +$1.00 vs pre-flip baseline (logs 🎯 WINNER-CELL-SIZE tag every application; unit = notio...
  - progress: —
  - if silent: REVERT WINNER_CELL_SIZE_MULT = 1.0
- 2026-11-10 [T-8] `conf-filter-parity-split` (owner: CEO label via main-session / AMPLIFY)
  - bar: Source-scoped jup conf-99 proposal (counterfactual + measurement) OR leave; floor leg NEVER; wholesale stays log-only.
  - progress: —
  - if silent: KEEP SHADOW (wholesale + floor dead; cap via source-scope only)
- 2026-11-12 [T-10] `storm-confl-waiver` (owner: CEO label + T sign-off 2026-10-29 ('All three'))
  - bar: >=3 CONSECUTIVE storms (auto_1hr [STORM-READINESS] packets with |BTC 1h|>=1.5%) each showing positive counterfactual;...
  - progress: —
  - if silent: KEEP shadow (do not enforce)
- 2026-11-12 [T-10] `storm-readiness-packet` (owner: auto_1hr hourly run)
  - bar: First storm after 10-29 emits a [STORM-READINESS] packet with table; >=3 packets accumulate the storm-confl-waiver en...
  - progress: —
  - if silent: FLAG to T: mechanism not running
- 2026-11-13 [T-11] `pump-chain-plus-weight-kill-review` (owner: auto_1hr weekly / AMPLIFY cadence)
  - bar: At the next 14d checkpoint: if still net-negative both regimes with n>=40 -> kill/decay the 1.4 boost under standard ...
  - progress: —
  - if silent: KILL the 1.4 weight if bar fails at checkpoint
- 2026-11-14 [T-12] `amplify-winner-cell-mult-150` (owner: CEO label + T sign-off (money-sizing, per #208 precedent))
  - bar: APPLY only if at read time: each cell net30>0 AND >=3 of 4 cells net14>0 AND net7(winner-cell-set)>0. REVERT to 1.25 ...
  - progress: —
  - if silent: NO CHANGE — WINNER_CELL_SIZE_MULT stays 1.25; amplify NOT applied without CEO label + T sign-off (status quo is the d...
- 2026-11-14 [T-12] `amplify-jup-short-walk` (owner: brain_auditor weekly AMPLIFY run)
  - bar: walk first-fire-per-token with the live exit engine, units guard (pnl_usdt = price_move% x notional; never compare ra...
  - progress: —
  - if silent: NO SHIP — counterfactual walk stays analysis-only, no code; re-register when OOS days exist past ~2026-11-13 (status ...
- 2026-11-14 [T-12] `atrtrail-clip-12` (owner: AMPLIFY weekly run)
  - bar: Counterfactual: widen atr trail distance (X%) on the 31-winner cohort + full 30d replay; ship only if net delta >= +$...
  - progress: —
  - if silent: NO CHANGE
- 2026-11-14 [T-12] `stop-tighten-enforce-eval` (owner: CEO label + T sign-off)
  - bar: enforce ONLY if at read time: per signal (jup_yolo_mirrored, volume-buildup-) DISTINCT trade-id joins >=20 over 14d A...
  - progress: —
  - if silent: KEEP SHADOW (STOP_TIGHTEN_ENFORCE stays False — status quo is inert and safe); re-evaluate at 14d if sample still thi...
- 2026-11-14 [T-12] `amplify-grind-breakout-deploy` (owner: brain_auditor)
  - bar: shadow_trader 11-01: grind-breakout- n=26 WR 92.3% avg +1.56 = #1 source by avg_pnl; GRIND_BREAKOUT_MINUS_ENABLED=Tru...
  - progress: —
  - if silent: NO CHANGE — log why-not in kanban (do not force-deploy a thin live cohort)

## LATER (>14d) (1)
- 2026-11-21 [T-19] `reentry-study` (owner: AMPLIFY weekly run / signal-lab)
  - bar: Design + backtest a re-entry rule (re-enter at reclaim-of-BE or +0.25pp structure confirmation within the 8h horizon)...
  - progress: —
  - if silent: NO CHANGE until design delivered

## ⚗️ RUNNING TRIALS (3)
- `watch-contrarian-live` — due 2026-11-03 | owner: main-session
  - bar: >= 1 REAL fade trade (pc- LONG open since started) + Z-FLIP conversion check at the 11-03 dispo
  - progress: 25 vs >=1 real fade trades (pc- LONG opens since started) — OK
- `trial-wider-sl` — due 2026-11-07 | owner: CEO
  - bar: wider-arm WR >= 55.0% with >= 200 trades (SHADOW_TRIAL_MIN_WR)
  - progress: 37.7 vs >=55.0 % WR wider-arm, n=7852/200 — NOT MET
- `trial-extended-time` — due 2026-11-07 | owner: CEO
  - bar: extended-arm WR improvement >= 5.0pp with >= 100 trades
  - progress: -13.6 vs >=5.0 pp WR-improvement, n=22608/100 — NOT MET

## 📅 CALENDAR — every dated open item, date-ordered
- 2026-11-03 [T-1]: eval-midband-long-4564, escalation-17, ugb-pt-045, disposition-cadence-revert, watch-contrarian-live
- 2026-11-05 [T-3]: fade-btc-crash-postflip, ichimoku-bypass-lowjoin-ticket
- 2026-11-06 [T-4]: momentum-cache-regime-coverage, gate-shadow-capture-coverage-fix, candle-collector-coverage-audit
- 2026-11-07 [T-5]: volmom-volbreak, jup-yolo-regime-review, trial-wider-sl, trial-extended-time
- 2026-11-09 [T-7]: signal-zombie-purge, amplify-pc-fade-cell-split
- 2026-11-10 [T-8]: mfe-cut-arm-be, ichimoku-dampen-flooradmit, fade-ctx-exempt, winner-cell-size-125, conf-filter-parity-split
- 2026-11-12 [T-10]: storm-confl-waiver, storm-readiness-packet
- 2026-11-13 [T-11]: pump-chain-plus-weight-kill-review
- 2026-11-14 [T-12]: amplify-winner-cell-mult-150, amplify-jup-short-walk, atrtrail-clip-12, stop-tighten-enforce-eval, amplify-grind-breakout-deploy
- 2026-11-21 [T-19]: reentry-study

## ✅ DONE / REVERTED (25)
flip-contrarian-pc, trial-coupled-cutsloser-sl, gate-shadow, shadow-trader-bypass, expiry-t5-shadow, relative-regime, rr-engine-shadow, chase-ratio, tc-temporal-confluence, mom-filter-shadow, acceleration-threshold, wyckoff-shadow, ai-trader-extreme-shadow, oscillator-shadow, bb-tat-shadow, db-mirror-0byte, bb-squeeze-hml-entry-profile, amplify-weekly-mandate, fade-volgate-split-analysis, pump-detect-ceiling-mismatch, override-vs-ceiling-contradiction, ichimoku-short-solo-counterfactual, chase-move-shadow, stop-asymmetry-highwr, short-relax-shadow-study

---
freshness: FRESH | registry mtime: 2026-11-02T04:49:56+00:00 | prev tower render: 2026-11-01T08:15:02+00:00 | last run: 6 packet(s), 0 entry error(s)
