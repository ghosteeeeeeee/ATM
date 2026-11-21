# Hotset Pin Cohort Readout — what `HOTSET_PIN_APPROVED=True` buys and risks

**Date:** 2026-11-20 (query window through 2026-11-20 23:00 UTC) · **Author:** result-3 (D2 P2), read-only run
**Mandate:** `automation/ceo/checkpoints/20261120T221647Z-decision.md` (D2 row) — give T the data to decide the flip of `HOTSET_PIN_APPROVED` (`scripts/hermes_constants.py:4127`).
**Method:** every number below comes from a query/script executed this run; scripts in `/tmp/pin_readout/` (`extract.py`, `counterfactual.py`, `risk_stats.py`, `robustness.py`). n and windows stated per number. No code or config was modified.

---

## TLDR

- **Shadow emitted 987 raw `WOULD-PIN` lines → 705 distinct events** (token, direction, 10-min bucket) over 4.26 days, 11-16 16:12 → 11-20 22:25 UTC (166 events/day), across 119 distinct token:direction pairs.
- **Execution conversion: 24/705 events (3.4%, Wilson 95% CI 2.3–5.0%)** had a real closed trade opened for the same token+direction within +60 min — but those trades happened *without* the pin (row already dead): 15 distinct trades, 7 distinct pairs, realized **+$0.20** total. Of the 32 events where the pin-candidate row's fate is still observable in SQLite, **0 executed**.
- **fwd1h of the pinned cohort: mean −0.053%, median −0.010%, win 47.8% (n=701)** — statistically indistinguishable from flat. Subset that later traded: mean +0.190%, win 58.3% (n=24) — permutation p=0.136, not significant.
- **The cohort is edgeless, not toxic**; the leak is real (crash day: 47 `approved-fell-out-of-hotset` deaths pre-purge; 9 `EXEC-BLOCK … NOT in hot-set` rows tonight). Risk is structurally bounded (executable dwell ≤15 min, DB ceiling ≤1h, fail-safe degrade, append-after-cap so fresh top-10 is not evicted).
- **Recommendation: FLIP NOW** (one-line `HOTSET_PIN_APPROVED=True`), with a 7-day watch list in §8. More shadow days cannot answer the one remaining question (pinned-row trade quality is unobservable while shadow never executes pinned rows).

---

## 1. Mechanism (exact code)

Flags: `HOTSET_PIN_APPROVED = False` and `HOTSET_PIN_SHADOW = True` (`scripts/hermes_constants.py:4127,4130`; CEO consult 2026-11-16).

**Cohort selection + shadow log — `_hotset_pin_fellout()` (`scripts/signal_compactor.py:2666–2703`), called each compaction cycle at L6247:**

> "SELECT-only cohort for the APPROVED hotset pin: rows with `decision='APPROVED' AND executed=0` whose token:direction is NOT in this cycle's hot-set (top10_keys) — the 'fell out of hotset' population, **both leak classes (expired-this-cycle rows + still-APPROVED-but-not-in-hotset rows that die at decider EXEC-BLOCK)**." (L2667–2671)

Shadow emission (L2699, deduped per `(token:direction, 'hotset-pin', UTC-hour)` per process):

> `👁️ [HOTSET-PIN-SHADOW] {_tok} {_direc} WOULD-PIN — approved signal fell out of hotset (ENFORCE={HOTSET_PIN_APPROVED})`

**Enforcement path (L6232–6273), verbatim comment:**

> "Enforce (HOTSET_PIN_APPROVED=True): pin ids are excluded from those updates via `_pin_clause` (keep APPROVED) AND their prev-hotset entry is re-appended to `hotset_final` so the token stays in hotset.json (decider EXEC-BLOCK requires hot-set membership — both leak classes: **42 fell-out + 13 not-in-hotset**)." (L6235–6238)

Concretely, when the flag is True:
1. `_pin_ids` = cohort row ids (L6248); `_pin_clause = " AND id NOT IN (?…)"` (L6250) is appended to **both** "APPROVED signals that left top-10" expiry statements (L6445–6467 and L6472–6491, the statements that write `decision_reason='expired: APPROVED combo fell out of hotset'`) → pinned rows are **not expired**.
2. Their `prev_hotset` entry is re-appended to `hotset_final` (L6251–6269) → `📌 [HOTSET-PIN] … pinned into hotset (fell-out APPROVED, ENFORCE=True)` (L6270), so decider's EXEC-BLOCK ("NOT in hot-set — bypass attempt blocked") passes. If no valid prev-hotset entry exists: `⚠️ … no pinnable prev-hotset entry — kept APPROVED only (not re-added)` (L6266) — pinned in DB but still EXEC-BLOCKable.
3. **Fail-safe:** whole block guarded (L6245–6273); any error degrades to flag-off (`_pin_ids=[]`, SQL byte-identical). Flag False today → only SELECT+log runs; rotation probe confirmed byte-identical with flag off (L6239–6240).

**Pin lifetime (what bounds the dwell — all three ceilings read directly):**

| Ceiling | Where | Effect |
|---|---|---|
| **Hard execution skip at 15 min** | `decider_run.py:6204–6216`: `if _sig_age_min > 15: SKIP … "too stale to execute"` (claim released, row → SKIPPED) | dwell beyond 15 min from row `created_at` **cannot fill** — this is the true executable ceiling |
| **DB cleanup at 1h** | `cleanup_stale_approved(hours=1)`, `signal_schema.py:3811–3831`, called at `decider_run.py:4650`; no `_pin_clause` | pinned row → EXPIRED, `executed=1`, ≤1h from `created_at` |
| **Blacklist expiry** | `signal_compactor.py:6206–6227` (no `_pin_clause`) | blacklisted token still dies |

So: **without the pin** an approved row dies in the same compaction cycle it falls out of top-10 (observed age at death: median 8.9 min, n=21 snapshot 23:00:42 UTC, min 1.2 / max 19.6, 20/21 ≤15 min); **with the pin** it stays decider-eligible until it fills or hits the 15-min skip — i.e. a residual executable window of roughly `15 − age_at_fellout` minutes (median ≈6 min), plus hotset membership for the EXEC-BLOCK fix. Note the pin does **not** bump `survival_rounds` (top10_combos is built at L6230, before the pin append) and does not change the top-10 selection itself: `hotset_final = hotset_final[:10]` runs at **L6186, before the pin block** — pinned entries are appended *after* the cap.

---

## 2. Event census (raw vs distinct — claim-hygiene §10)

Sources: `logs/archive/pipeline.log.20261119090701.gz` (covers 11-15 00:09 → 11-19 09:07, 552 lines) + live `logs/pipeline.log` (11-19 09:07 → now, 435 lines). Archive coverage is contiguous back to 11-07 and **zero `WOULD-PIN` lines exist before 2026-11-16 16:12:01** — shadow's first emission; last line 11-20 22:25:01. (Checkpoint's "433 lines" = live log at 22:16; 435 now.)

| | raw lines | distinct (token, direction, 10-min bucket) |
|---|---|---|
| **total** | **987** | **705** |
| 11-16 (from 16:12) | 75 | 55 |
| 11-17 | 233 | 177 |
| 11-18 | 173 | 125 |
| 11-19 | 195 | 141 |
| 11-20 (to 22:25) | 311 | 207 |

- Distinct **token:direction pairs: 119**; window 4.26 days → **166 distinct events/day**.
- Concentration: SOL LONG 154, SOL SHORT 103, BTC LONG 93, HYPE SHORT 57, BTC SHORT 54, ETH LONG 27, ETH SHORT 13 — **top 4 pairs = 404/705 = 57.3%**, top-7 = 71.1%; 61/119 pairs appear exactly once. (The same 4 majors the crash audit found dominating combo-stale deaths.)
- ⚠️ **Double-count hazard (sideways find, low severity):** `logs/signal-compactor.log` carries the *same* emission stream (archive segment md5-identical to pipeline.log's: `67a6e249…`). Counting both files doubles the census (987 → ~1,974). This readout counts pipeline.log only.

---

## 3. Counterfactual: would the pinned row have executed? (+60 min)

Join key: event (token, direction); window = [event_ts, event_ts+60min]; time anchors UTC (host TZ = UTC, verified `date`).

**(a) Real trade opened** — PG `brain.trades`, `status='closed' AND paper='f'`, `open_time` in window, same token+direction:

- **24/705 events converted (3.4%, Wilson 95% CI 2.3–5.0%)** → **15 distinct trades** (several events map to one trade), **7 distinct pairs** of 119 = 5.9% (BTC LONG, BTC SHORT, SOL LONG, SOL SHORT, HBAR LONG, RENDER LONG, ZORA LONG), realized pnl sum **+$0.20** (trade ids 16950, 16957, 16959, 16965, 16972, 16973, 16977, 16980, 16981, 16986, 16988, 16989, 16994, 17003, 17006).
- Per-day conversion: 11-16 1/55, 11-17 3/177, 11-18 10/125, 11-19 7/141, 11-20 3/207.
- Context: 68 real closed trades exist in the whole window — **15/68 = 22% of all executions occurred within +60 min after a WOULD-PIN event** for the same token:direction (the cohort sits on the tokens that actually trade). Longer window (+180 min): 59/705 events = 8.4% → 23 distinct trades.
- **Crucial caveat:** in every one of these 24 cases the pinned row was *already dead* when the trade fired (shadow mode) — the fill came from a *different/later* row of the same token:direction (`signal` ∈ jup_yolo_mirrored, bb-squeeze+, continuum±, warrior-sr-confirm+, ai-trader-pending). The pin would at most have changed *which row* executed and possibly earlier entry — it did not create these trades.

**(b) The signal row later executed/decided** — SQLite `data/signals_hermes_runtime.db`:

- **Coverage (stated as required):** the table is rolling and the compactor's `_purge_stale_unexecuted(2h)` (`signal_compactor.py:6785–6817`, runs hourly with `--purge-executed`) **deletes unexecuted death rows (incl. fell-out deaths) 2h after death**; `decision='EXECUTED'` rows purge at 1h (currently **0** present); zombie rows (`EXPIRED` + `executed=1`) are retained up to 14d (tier-2 archive, L6647–6655). Empirically `min(created_at)=2026-11-06`, n=12,692 rows at 22:45.
- Therefore the pin-candidate's own fate is directly observable for only **32/705 events (4.5%)** — all from the last ~2h before query. Live purge-drift proof: the `expired: APPROVED combo fell out of hotset` certificate count was **29 rows (expired_at 20:13–22:25) at 22:45, 21 rows (21:06–23:00) at 23:00:42** — identical to the crash audit's 47→14 purge drift.
- Of those 32 observable pre-existing rows: **0 executed within 60 min**. Deaths observed: 10 events `expired: APPROVED combo fell out of hotset` (the pin's own target), 5 `compaction_stale_10min`, 3 merge-window supersede, 3 `rr-engine-hard-block`, **4 events carrying `🚫 [EXEC-BLOCK] … NOT in hot-set — bypass attempt blocked` (leak class 2)**, 4 `blocked@approval:` gates, 2 `[BTC-CRASH] … BLOCKED`, 2 `already processed in this pipeline run`.
- Whole-window leak-class-2 evidence: **9 rows** `NOT in hot-set` SKIPPED, all tonight 20:54–21:53 (7 SOL SHORT, 1 SOL LONG, 1 BTC LONG) — approved-but-unpinned rows blocked at execution. The flip re-appends them into hotset.json so this block cannot fire.
- Repeated deaths of the same pairs are visible in the surviving window too (SOL LONG/SHORT fall-out deaths recur every few compaction cycles all evening).

**(c) Nothing** — **681/705 events (96.6%)**: no trade for that token+direction within 60 min; whatever row was pinned died without a fill (or the pair simply didn't execute).

---

## 4. Forward returns of the pinned cohort (`candles.db`)

Formula (as mandated): entry = OPEN of first `candles_5m` candle with `ts ≥ event_ts` (unix sec, `is_closed=1`); exit = close of the candle **12 bars after the entry candle** (≈+65 min from entry open); fwd1h = sgn×(exit/entry − 1)×100, sgn=+1 LONG / −1 SHORT.

**Coverage:** `candles_5m` window 2026-10-21 05:40 → 2026-11-20 22:50 (~30d rolling, 1,626,143 closed rows) — fully covers the event window. **701/705 events priced**; the 4 misses are right-censoring at the log's tail (BTC LONG, ETH LONG 22:20; SOL LONG/SHORT 22:00/22:10 on 11-20 — fewer than 13 forward bars exist yet), not token absence.

| cohort | n (priced) | mean fwd1h | median | win rate (fwd>0) | notes |
|---|---|---|---|---|---|
| **ALL distinct WOULD-PIN events** | 701 | **−0.053%** | **−0.010%** | **47.8% (335/701), Wilson 95% CI [44.1, 51.5]** | min −4.94, max +7.42 |
| later traded within 60 min | 24 | **+0.190%** | +0.190% | 58.3% (14/24), CI [38.8, 75.5] | permutation p=0.136 vs non-traded → **not significant** |
| did NOT trade within 60 min | 677 | −0.062% | −0.016% | 47.4% | |
| first event per distinct trade (dedup) | 15 | +0.063% | +0.101% | 53.3% | realized: +$0.20 |

**Reading:** the cohort is a coin flip around zero on a 1h horizon. The executed subset looks mildly better (+0.19% / 58.3%) but n=24 with a p≈0.14 and a CI spanning 39–76% — per the standing pattern rule this is **not claimed as an edge**. The pin therefore buys *eligibility hygiene*, not a profitable backlog; it also does not pin a demonstrably toxic cohort.

---

## 5. Risk analysis — what a flip actually changes

**Does it reduce top-10 turnover for fresh signals?** Not by eviction: the cap runs at L6186 *before* the pin append, so fresh top-10 ranking and turnover are untouched — pinned entries are *added* after the cap. The costs are downstream:

1. **hotset.json grows beyond 10.** Distinct would-pins per UTC hour (100 hours with ≥1 event): **mean 4.8, median 4, p95 11, max 16** (peak 2026-11-20 14:00 — mid-crash: APT/ARB/BTC/ETH/SOL … 16 pairs). At enforce, peak hours could see hotset ≈ 10+16 = ~26 entries (vs cap 10; file held 3 entries at 22:54 tonight).
2. **Decider pool ordering is not recency-weighted.** `get_approved_signals` (`signal_schema.py:3619–3674`) selects `decision='APPROVED' AND executed=0 AND created_at > now-24h AND conf ≥25` **`ORDER BY count DESC, max_conf DESC`** — a pinned (older) row with more merged rows/higher confidence ranks ahead of a fresher candidate. With DailyFillCap binding (crash day: engaged 12:07:46→end, 84 distinct ready candidates blocked), stale pinned rows can consume fill slots.
3. **Pinned-but-unexecutable rows are pure slot cost:** rows that fall out after 15 min (1 of 21 in tonight's snapshot) are pinned but will never fill (decider skip), yet still occupy hotset membership until the 1h cleanup.
4. **Execution suppression after a pin fills:** an executed row for token:direction suppresses fresh re-INSERT (`signal_compactor.py:5958–5966`) until the EXECUTED row purges (1h) — a pinned fill can delay a fresher signal on that pair by up to ~1h.
5. **Worst case is bounded and reversible:** even with zero gates, a pinned row dies by 15 min (exec skip) / 1h (cleanup) / blacklist; any pin-code exception degrades to flag-off (L6271–6273); revert = one constant line.

**Does it pin losers longer?** It pins *everything* longer by construction (median residual executable window ≈6 min, hard stop 15 min). The cohort's own fwd1h (−0.053% mean, 47.8% win, §4) says "losers" is not the right word — it's an **edgeless** cohort; the 15-min skip prevents a death spiral of long-dwell zombies.

---

## 6. Crash-window context (from `brain/verdicts/2026-11-20-crash-forensics-own-conclusions.md` — cited, not re-derived)

- **47 rows** carried `'expired: APPROVED combo fell out of hotset'` pre-purge (auditor exact-string count 16:50–16:57 UTC) — *"exactly this cohort"*; after the 17:00:03 hourly purge the count was **14** (K2 evidence; combo-stale 81→63 in the same purge).
- Crash funnel: **297 EXPIRED, 9 (3.0%) converted**; hotset-rotation deaths = 47 (post-purge 14) named as a starvation mode; DailyFillCap ENGAGED 12:07:46→end; **0 automated trades**; auditor extended test: blocked shorts ex1h −0.045% (n=189 dedup, 48% beat market) → **"blocked ≈ market."**
- K4 verdict: approvals *did* occur (approvals → fell-out deaths is the normal path), row counts overstate distinct opportunities (4 distinct tokens / 7 combos in the merge-window cohort; my pin census shows the same 4 majors = 57% of events).
- Reconciliation: my 11-20 census = 311 raw / **207 distinct** WOULD-PIN events vs the DB's 47 death certificates at 16:50 — expected divergence: the log dedups once per (pair, hour, process) and the DB purges certificates hourly; the log is the only durable cohort record (and it rotates into `archive/*.gz`).

---

## 7. What the flip buys / risks — one line each

**Buys:** (i) ~166 approved rows/day stop dying to rotation noise before the decider ever tries them — they get their remaining ≤15-min executable window; (ii) leak class 2 (approved-but-not-in-hotset EXEC-BLOCK, 9 rows tonight, 42+13 in the author's probe) is structurally closed; (iii) crash-day failure mode "approvals died at 8.9 min median for no edge reason" disappears from the death ledger.
**Risks:** (i) hotset membership above the 10-cap at peaks (~26 worst observed); (ii) stale pinned rows competing for cap-limited fills under non-recency ordering; (iii) ~1 pinned row/hour that is pinned-but-unfillable (>15 min); (iv) zero measured execution upside so far (0/32 observable rows executed; cohort fwd1h ≈ 0).

---

## 8. RECOMMENDATION FOR T

### **FLIP NOW — set `HOTSET_PIN_APPROVED = True` (line 4127), with the 7-day watch below.**

Numbers behind it:

1. **The leak is real and frequent:** 705 distinct rotation deaths in 4.26 days (166/day; 207 on crash day), plus 9 `EXEC-BLOCK NOT in hot-set` rows in a single evening; the independent crash audit confirms 47 approved-fell-out deaths on 11-20 — approvals are being thrown away before the decider can act on them.
2. **The risk is structurally bounded:** executable dwell ≤15 min (`decider_run.py:6204`), DB ceiling ≤1h (`cleanup_stale_approved`), blacklist path unpinned, append-after-cap so the fresh top-10 is never displaced, and any pin error degrades to flag-off. Revert = one line.
3. **The cohort is edgeless, not toxic:** fwd1h mean −0.053%, win 47.8% CI [44.1, 51.5] (n=701) — pinning it adds no systematic drag; the pin cannot turn this into a P&L lever either (set expectations: this is a correctness fix, not a throughput fix — D4 Batch-1 and the DailyFillCap are the throughput levers).
4. **"Flip after N more days of shadow" cannot answer the open question:** while shadow is on, pinned rows are *by design* never executed (0 attributable executions in 32 observable fates) — no amount of extra shadow measures pinned-row trade quality. The only way to learn that metric is to flip. Additional shadow days would only tighten an already-flat fwd1h estimate (CI already ±3.7pp).
5. **"Do not flip" is the option that keeps a known defect:** approvals continue to die at median 8.9 min of age with no edge justification, and the EXEC-BLOCK leak class stays open.

Risk-averse fallback if T wants it: flip 2026-11-27 (Friday review, alongside R1) — costs 7 days of ~1,160 further rotation deaths and yields only tighter cohort stats, not execution attribution.

### Monitor in week 1 (all cheap, all existing sources)

| # | Metric | Source | Expect / alert |
|---|---|---|---|
| 1 | `📌 [HOTSET-PIN] … pinned into hotset` vs `⚠️ … no pinnable prev-hotset entry` counts/day | pipeline.log | alert if degraded (⚠️) share >20% — those pins can still EXEC-BLOCK |
| 2 | hotset.json entry count (esp. >10) | `/var/www/hermes/data/hotset.json` `len(hotset)` | investigate if sustained >15 |
| 3 | `SKIP: … too stale to execute (>15min)` lines | pipeline.log/decider | rising count = pinned-but-dead slot cost |
| 4 | trades attributable to pinned rows (token:dir within +15 min after a 📌 line) → WR/net | PG `brain.trades` | vs 7d baseline WR 49.1% / +$0.54; any negative drift → revert flag |
| 5 | fresh-signal turnover (distinct token:dir entering hotset/day; PENDING→APPROVED conversions) | hotset.json cycle deltas + signals | must not drop vs pre-flip |
| 6 | `expired: APPROVED combo fell out of hotset` rows | signals DB (pre-2h-purge, or log) | should go ≈0 in compaction cycles (pin active) |
| 7 | Friday cadence: blocks:trades ratio & trades/day | `ceo_kanban.md` baselines 105.3:1 / 15.4 per day | pin should be neutral here; don't credit it with funnel recovery |

**Rollback:** `HOTSET_PIN_APPROVED = False` — one line, shadow logging continues; no schema, no other code touched by the flag.

---

## Appendix — queries/scripts executed this run (reproducibility)

| # | Question | Command/script | Result |
|---|---|---|---|
| A1 | raw WOULD-PIN lines | `grep 'WOULD-PIN' logs/pipeline.log` + `zcat archive/pipeline.log.20261119090701.gz \| grep -a` | 435 + 552 = 987 (identical duplicate stream in `signal-compactor.log`, md5-checked, excluded) |
| A2 | distinct events | `/tmp/pin_readout/extract.py` (regex ts/token/dir, dedup key = (TOKEN, DIR, 10-min bucket)) | 705 events, 119 pairs, 11-16 16:12→11-20 22:25 |
| A3 | trades ≤60 min | psql `brain`: `status='closed' AND paper='f' AND open_time>='2026-11-16'` then Python join on (token, direction, [t, t+60m]) | 24/705 events; 15 distinct trades; +$0.20; window total 68 real trades |
| A4 | signal-row fate | SQLite `signals_hermes_runtime.db`, rows same token:dir with created_at ≤ event and updated/expired in [t, t+60m] | observable for 32/705 (2h purge); 0 executed; states listed §3(b) |
| A5 | fwd1h | `/tmp/pin_readout/counterfactual.py` + `robustness.py` on `candles.db candles_5m` (entry open ≥ event ts; exit close idx+12; sgn-signed) | n=701/705 (4 right-censored); −0.053% / −0.010% / 47.8% [44.1,51.5]; traded n=24 +0.190% / 58.3%, perm p=0.136 |
| A6 | concurrency/turnover | `/tmp/pin_readout/risk_stats.py` (distinct pairs per UTC hour) | mean 4.8, median 4, p95 11, max 16 (11-20 14:00); 100 hours with ≥1 event |
| A7 | death age of pin cohort | SQLite snapshot 2026-11-20 23:00:42 UTC, `decision_reason='expired: APPROVED combo fell out of hotset'` | n=21 (was 29 at 22:45 — purge drift), min 1.2 / median 8.9 / mean 8.0 / max 19.6 min, 20/21 ≤15 min |
| A8 | crash-window numbers | read `brain/verdicts/2026-11-20-crash-forensics-own-conclusions.md` (K2/K4) | 47 → 14 post-purge; 297 EXPIRED / 3.0% converted; cap 12:07:46→end; blocked shorts ex1h −0.045% n=189 |

*Known mutable-source caveat: the signals table purges its own death certificates hourly (29→21 in 15 min, A7) — all fate numbers state their snapshot time; the pipeline.log census (A1/A2) is the durable record and rotates to `logs/archive/*.gz`.*
