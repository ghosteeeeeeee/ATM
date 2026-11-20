# Frequency-Collapse Root Cause — Why live trades fell ~70%

**Date:** 2026-11-20 (queries run 05:08–06:50 UTC) · **Mandate:** CEO D3, checkpoint `20261120T050846Z-decision.md`
**Config/DB changes: NONE** · read-only analysis · query scripts in `/tmp/d3_freq/`
**Claim hygiene:** every number below comes from a query I ran this session; each series states its window, its n, and its weakness.

---

## 0. TL;DR (ranked answer in §6)

1. **The mandate's −72% is real but is two different collapses, not one.** 47.0/day (Sep-7 wk, n=329) → **14.1/day** (Nov-16 wk through Nov-20 06:02, n=60, 4.25 d) = **−70%**; trailing-7d n=110 = 15.7/day. (The engine's 13.2/day was a Nov-19 snapshot; same story.)
2. **~77% of the decline is the Nov-4 execution-side capital brakes** — `DAILY_FILL_CAP` (Cap D, 15 opens/24 h while fee-net<0) and Cap C (jup_yolo 1 fill/6 h), both shipped 2026-11-04. Daily trades fell 43.0/day (Oct 30–Nov 4, n=258) → **13.7/day** (Nov 5–19, n=205) = −68%, at exactly the moment the cap shipped, with emissions *flat-to-rising* across the boundary. n=11,765 `SKIP: DailyFillCap` log lines, 0 RELEASED lines.
3. **~15% is a genuine signal-emission decline** of −37% from early August to mid-October (2,446 → 1,542 inserts/day), caused by a cohort of high-volume generators going quiet (last-seen dates in §4.3).
4. **NOT the cause: gate blocks** (blocked-episode volume *rose* per day and per signal), **confluence** (CONFLUENCE-GATE-BLOCK *fell* 502→116/day), **the confidence floor** (**n=0** rejections observed), **SKIPPED decisions** (n=39 of 12,121 = 0.3%).
5. **The signal-side denominator was measurable after all** — see §2.1. Over the most recent comparable window it moved the *wrong way*: emissions **+48–50%** (two independent proxies) while trades fell **−51%**.

---

## 1. Data sources, exact coverage, and what is unrecoverable

| # | Source | Window (verified) | n | Notes / caveats |
|---|--------|-------------------|---|----------------|
| 1 | PostgreSQL `brain` `trades` (`status='closed' AND paper='f'`, weekly by `open_time`) | 2026-05-20 → 2026-11-20 06:02 | 6,534 | Complete. Source of truth. |
| 2 | `data/signals_hermes_runtime.db` **live `signals`** | `created_at` 2026-11-06 04:00 → 2026-11-20 06:45 | 12,121 | **Rolling ~14-d window**: `archive-signals.py` runs daily (`hermes-archive-signals.timer`, 04:00) and DELETEs rows older than `CUTOFF_HOURS_OTHERS=336`. |
| 3 | `archive/signals/signals_2026-{08,09,10,11}.jsonl.gz` | rows `created_at` 2026-07-20 → 2026-11-06 | 94,268 | **Holes:** 2026-08-20→09-22 (34 d), 09-26→09-30, 10-03→10-06, 10-08→10-10. Rows in the holes were **deleted before archiving** (dedup `DELETE … decision='PENDING' AND executed=0`, `signal_compactor.py:6744`), not never-created — proven by the `AUTOINCREMENT` id sequence (§2.1). File names are **not** the rows' month: `archive_month()` groups by run date because a `created_at` string trips the Unix-timestamp branch and falls back to `now()`. |
| 4 | `signals_archive_2026-04-16/21/28` (3 tables) | 2026-04-16 → 2026-04-28 | 168,501 | Out of window; ignored. |
| 5 | `brain/expiry_shadow.db` `events` | `created_at` 2026-09-24 21:45 → 2026-11-20 06:23; **`recorded_at` from 2026-10-09 00:48** | 63,723 | **Recorder shipped 2026-10-09** (commit `7f51dc6c`, "D3+D4 (CEO GO 00:45)"). Rows with `created_at` < 2026-10-09 are a **partial backfill** from whatever was still in `signals` at that moment: only 447 rows exist for 09-24→10-08 (297 + 58 + 92) and **zero** for 09-26→09-30 and 10-03→10-06. **Treat as complete only from 2026-10-09.** |
| 6 | `brain/gate_shadow.db` `events` | `blocked_at` 2026-10-04 11:07 → 2026-11-20 06:34 | 110,488 | **No rows for 2026-10-11** (full day). Per the Nov-19 deep-dive: pre-Oct-22 capture is 33–60 % for several gates and **12 gates are invisible to the recorder's emoji regex** (db=0). Block events are per (gate, dedup_key), so one signal can produce several. |
| 7 | `logs/pipeline.log` + 3 `logs/archive/pipeline.log.*.gz` | **2026-10-30 20:39:35 → now, continuous** | 7,233,357 lines | **Oct 4–30 raw logs deleted pre-rotator** — unrecoverable. Note: the brief said "Nov 7 → now"; it actually reaches Oct 30. |
| 8 | `logs/signal-compactor.log` + 2 archives | **2026-10-10 20:50 → now, continuous** | — | — |
| 9 | `logs/signals.log` | 2026-10-02 → now, **gap 10-14→10-21**, scan-count anomaly on 10-13 (2,260 scans vs 288/day) | — | Weak proxy only (§2.3). |
| 10 | `signal_history` | 2026-10-07 → 2026-11-20 | 26,015 | **Survivors only**: `survived=1` for 26,017/26,017 rows. Cannot be used as a rejection series. |
| 11 | `signal-purge.log` | 2026-08-02 → 2026-11-20 | 4,279 + 1,014 purge lines | Quantifies rows destroyed *without* archiving (§5). |

**Unrecoverable, stated plainly:**

- **Weekly emissions for 2026-08-20 → 2026-09-22** (the window that contains the Sep-7 anchor week). Only the 34-day aggregate survives: **78,115 inserts = 2,298/day**. No source splits it by week.
- **Per-source emission mix for anything after 2026-08-19** (same hole + the Oct-8 purge).
- **33,137 rows** deleted by `_purge_stale_unexecuted` (EXPIRED/SKIPPED, `executed=0`, >2 h) since 2026-10-08 — deleted, never archived.
- **17,949 rows** deleted by `_do_purge` (EXECUTED/FAILED, >1 h) since 2026-08-02 — deleted, never archived.
- **All gate blocks before 2026-10-04 11:07** and all events of the 12 regex-invisible gates.
- **All pipeline/compactor log evidence before Oct 30 / Oct 10** — including the whole late-Sep/early-Oct period (§4.4).
- `SKIP: DailyFillCap` counts are **log lines, not distinct candidates** (the decider runs every ~17–36 s, so one blocked candidate is re-logged many times).

---

## 2. The signal-side denominator (the measurement the deep-dive said was missing)

### 2.1 Primary: `signals`-table insertions, reconstructed from the id sequence

`signals.id` is `AUTOINCREMENT`; ids are consumed at insert and never reused, so **`max(id) − min(id)` counts inserts even for rows that were later deleted**. This survives the archive holes.

Cross-validation (complete weeks, no hole): observed rows vs id-span = 23,885 vs 24,421 (Aug-03 wk) and 21,561 vs 22,041 (Aug-10 wk) → the ~2.4 % difference is exactly the EXECUTED/FAILED rows `_do_purge` removes. **The id sequence is an unbiased insert counter.**

Independent cross-check for Oct 12 → Nov 20: `Σ id-delta` = 66,408 vs `expiry_shadow` total (57,727) + trades (867) + EXECUTED/FAILED purged ≈ 1,634/d × 39.25 d (64,100) → within 3.5 %.

### 2.2 Emissions by period (id-delta)

| Period | days | inserts | inserts/day | trades | trades/day | conversion |
|---|---|---|---|---|---|---|
| 2026-08-04 → 08-19 | 15.17 | 37,111 | **2,446** | 794 | 49.6 | **2.14 %** |
| 2026-08-20 → 09-22 *(hole)* | 34.0 | 78,115 | **2,298** | 1,516 | 44.6 | **1.94 %** |
| 2026-09-23 → 10-11 | 19.0 | 37,337 | **1,965** | 422 | 22.2 | **1.13 %** |
| 2026-10-12 → 11-04 | 24.0 | 37,002 | **1,542** | 680 | 28.3 | **1.84 %** |
| 2026-11-05 → 11-19 | 15.0 | 28,799 | **1,920** | 205 | 13.7 | **0.71 %** |

Weekly, full-coverage weeks only:

| week (Mon) | inserts | /day |
|---|---|---|
| 2026-08-03 | 24,421 | 3,489 |
| 2026-08-10 | 22,041 | 3,149 |
| 2026-10-12 | 8,958 | 1,280 |
| 2026-10-19 | 8,633 | 1,233 |
| 2026-10-26 | 12,543 | 1,792 |
| 2026-11-02 | 13,522 | 1,932 |
| 2026-11-09 | 14,671 | 2,096 |
| 2026-11-16 *(4.25 d)* | 8,058 | 1,896 |

### 2.3 Secondary proxy: compactor `Query: N combo_keys` (conf≥60, ≤10 min, deduped by combo_key)

From `signal-compactor.log`, sum per week: 65,046 (10-12) → 71,535 → 99,558 → 92,641 → 94,813 → 59,406 (11-16, 4.25 d).
Per day: **9,292 → 10,219 → 14,223 → 13,234 → 13,545 → 13,978 (+50 %)**.
Id-span per day over the same weeks: 1,280 → 1,233 → 1,792 → 1,932 → 2,096 → 1,896 (**+48 %**).
**Two independent emission proxies agree on direction and magnitude (+48–50 %).** The `Query:`/id-span ratio is stable at 6.5–7.4.

Tertiary, weak: `signals.log` "Found N groups from M signals" per confluence scan (every 5 min) → M/scan = 10.5 (Oct 22–25) vs 29.4 (Nov 9–19, 13 days) — same direction, but it is a *windowed* count (depends on signal lifetime), the log has a scan-count anomaly on Oct 13, and it is not an insert count. **Labelled weak, not used for any number in §3–§5.**

---

## 3. Weekly time series (all six required series)

Weeks start Monday. `–` = source does not reach that far back. † = partial week (Mon 00:00 → 2026-11-20 06:02, 4.25 d).

| week | (a) trades closed | (b) emissions (id-span) | (b′) compactor `Query:` hits | (c) confluence-expiry (`expiry_shadow`) | (d) conf-floor rejections | (e) gate-block episodes (60-min, per token+dir+gate) | (f) `expiry_shadow` SKIPPED |
|---|---|---|---|---|---|---|---|
| 2026-08-03 | 394 | 24,421 | – | – | – | – | – |
| 2026-08-10 | 424 | 22,041 | – | – | – | – | – |
| 2026-08-17 | 233 | 2,793 *(08-17→08-19 only; hole after)* | – | – | – | – | – |
| 2026-08-24 | 407 | **HOLE** | – | – | – | – | – |
| 2026-08-31 | 365 | **HOLE** | – | – | – | – | – |
| 2026-09-07 | **329** | **HOLE** (window avg 2,298/d) | – | – | – | – | – |
| 2026-09-14 | 205 | **HOLE** | – | – | – | – | – |
| 2026-09-21 | 121 | 2,895 *(09-23→09-25 only)* | – | 297 *(backfill)* | – | – | 0 |
| 2026-09-28 | 223 | 4,260 *(10-01→10-02 only)* | – | 58 | – | 423 *(recorder starts 10-04)* | 0 |
| 2026-10-05 | 127 | 9,040 *(partial)* | 7,463 *(from 10-10 20:50)* | 5,624 | 0 | 5,480 | 1,725 |
| 2026-10-12 | 201 | 8,958 | 65,046 | 7,762 | 0 | 4,285 | 2,355 |
| 2026-10-19 | 128 | 8,633 | 71,535 | 7,809 | 0 | 6,387 | 1,400 |
| 2026-10-26 | 242 | 12,543 | 99,558 | 10,890 | 0 | 9,389 | 1,944 |
| 2026-11-02 | 149 | 13,522 | 92,641 | 11,656 | 0 | 7,298 | 2,419 |
| 2026-11-09 | 111 | 14,671 | 94,813 | 12,652 | 0 | 8,300 | 3,137 |
| 2026-11-16 † | **60** | 8,058 | 59,406 | 6,958 | 0 | 5,545 | 1,139 |

**Episode definition check:** my 60-min coalesce per (token, direction, gate) reproduces `exports/nov19_weekly_funnel.tsv` to within snapshot drift — 423 / 5,480 / 4,285 / 6,387 / **9,389** (TSV 9,606) / 7,298 (7,933) / 8,300 (9,065) / 5,545 (5,582). Definition confirmed.

**(d) Confidence floor — full detail.** `MIN_EXEC_CONFIDENCE = 40` today; lowered from 50 by commit `bc0c72f0` on **2026-10-10** (so the brief's "No signals above **50** %" line has not existed since Oct 10; the line now reads 40 %).
- `🚫 [CONF-FLOOR]` per-signal rejection lines: **n = 0** across all 4 pipeline logs (2026-10-30 20:39 → 2026-11-20 06:15, 7.23 M lines).
- `No signals above 40 % confidence — skipping execution`: n = 10,765 — but this fires whenever `get_approved_signals(24h)` is *empty*, and with n=0 CONF-FLOOR lines it means **zero APPROVED rows, not "all below 40"**. It is an *empty-hotset* proxy, not a floor rejection.
- Its share of decider runs **fell**: 84.9 % (Oct 30–31, n=5,906 runs) → 58.0 % (11-02) → 36.0 % (11-09) → 42.8 % (11-16 †, n=10,745). Mean APPROVED rows/run rose 0.16 → 0.63 → 1.07 → 0.86.
**The confidence floor was not binding at any point in the observed window.**

**(f) SKIPPED / other decision reasons — live `signals` table (rolling 14-d window, 2026-11-06 → 11-20, n=12,121):**

| decision | n |
|---|---|
| EXPIRED | 12,062 |
| **SKIPPED** | **39** (0.32 %) |
| FAILED | 11 |
| PENDING | 4 |
| EXECUTED | 3 |
| APPROVED | 2 |

Grouped `decision_reason` (EXPIRED rows): `blocked@approval: <gate>` **6,652**; `compaction_stale_10min` **4,195**; `blocked@approval: confluence single-type` **1,148**; `expired: …` 36; `combo_key stale` 29. SKIPPED rows by reason: BTC-CRASH 21, EXEC-BLOCK 12, CTX-GATE 4, other 1.

**Instrumentation changes that invalidate reason-mix comparisons across their boundaries (disclosed, not hidden):**
- `blocked@approval:` first-seen **2026-10-29 04:05:41** (both `expiry_shadow` and archives) — before that date the reason simply did not exist. The "0 blocked@approval before the 10-26 week" in any weekly table is **instrumentation, not behaviour**.
- `combo_key stale:` first-seen **2026-10-30 08:36:12**.
- `compaction_stale_5min` → `compaction_stale_10min` switched **2026-08-06** (5-min last seen 03:34, 10-min first seen 10:53).

---

## 4. Decomposition — which lever moved with trades?

### 4.1 The two-step shape

Trades/day by period: **49.6** (Aug 4–19) → **44.6** (Aug 20–Sep 22) → **22.2** (Sep 23–Oct 11) → **28.3** (Oct 12–Nov 4) → **13.7** (Nov 5–19).

So: a ~50 % step down in late Sep/early Oct, a partial recovery, then a second ~51 % step down at Nov 4–5.

### 4.2 The Nov-4 step — execution side, not signal side

| | Oct 12 → Nov 4 | Nov 5 → Nov 19 |
|---|---|---|
| emissions (id-span) | 1,542/day | **1,920/day (+25 %)** |
| compactor `Query:` hits | — | (10-26 wk 14,223/d → 11-09 wk 13,545/d, −5 %) |
| trades | 28.3/day | **13.7/day (−51 %)** |
| conversion | 1.84 % | **0.71 % (−62 %)** |

Emissions did **not** fall. Conversion did. Mechanism, directly observed:

- **DailyFillCap (Cap D)** — `hermes_constants.py:6123 DAILY_FILL_CAP_ENABLED=True`, `DAILY_FILL_CAP_MAX=15`; shipped commit `e41faad2` **2026-11-04** ("CEO capital brake 20261104T172347Z"). First `SKIP: DailyFillCap` line **2026-11-04 17:51:31**; last 2026-11-20 03:27:31; **n = 11,765 lines**; **`DailyFillCap RELEASED` n = 0** — it has never released. Live state line at 2026-11-20 03:27:30 reads `15/15 opens, fee-net −0.15`.
- **Cap C** — jup_yolo 1 fill/6 h, same day (first `SKIP: Cap C` **2026-11-04 04:16:44**), **n = 18,957 lines** in Nov. jup_yolo_mirrored trades: 73/wk (11-02) → 20/wk (11-09) → 12/wk (11-16).
- Daily trades: Oct 30–Nov 4 = 258/6 d = **43.0/day** → Nov 5–19 = 205/15 d = **13.7/day** (−68 %). Observed rate ≈ the 15/day cap.
- Decider skip mix, Nov (n = 47,938 skip lines vs 638 entered): **Cap C 18,957 (39.6 %) + DailyFillCap 11,765 (24.5 %) = 64 % of all skips**. For Oct 30–31 (n = 602 skipped / 108 entered) DailyFillCap was 0.

*Adversarial notes:* (i) the SKIP counts are line-instances, not distinct candidates; (ii) two other changes shipped 2026-11-04 (`ICHIMOKU_LONG_BYPASS_ENABLED=False`, Cap B PG-leak fix) — but confluence-single-type blocks **fell** after the 11-02 week (640 → 683 → 359 → 333/wk), so the bypass disable does not explain the step; (iii) correlation of ship-date + magnitude + explicit per-candidate SKIP lines + zero releases is strong but is still not a randomised counterfactual.

### 4.3 The emission decline — which generators stopped

Last-seen dates from the full insertion record (n = 106,404 archived + live rows). Sources with last-seen ≤ 2026-08-19 may have continued into the unrecoverable Aug 20 – Sep 22 hole; they are therefore **bounded as "stopped by Sep 23"**, not pinpointed. Sources with last-seen *after* the hole are exact.

| source | n | last seen | | source | first seen |
|---|---|---|---|---|---|
| zscore-rising- | 5,180 | 2026-08-04 | | pump-chain+ | 2026-10-02 |
| zscore-rising+ | 5,070 | 2026-08-06 | | volume-buildup-, pump-chain-v6+, ema-reclaim-long | 2026-10-12 |
| vel-hermes- | 1,987 | 2026-08-04 | | **jup_yolo_mirrored** | **2026-10-30** |
| tl_break_long | 4,489 | 2026-08-07 | | **linreg-fade-** | **2026-11-05** |
| ma100-cross | 948 | 2026-08-07 | | **atr-trend-** | **2026-11-06** |
| hzscore± / range_breakout± | 4,246 | 2026-08-12 | | | |
| range_finder± | 2,238 | 2026-08-16 | | | |
| ct-hot+ | 1,581 | 2026-08-17 | | | |
| bb_bounce+ / tl_break_short | 5,610 | 2026-08-19 | | | |
| accel-300- | 3,677 | **2026-09-24** (exact) | | | |
| bb-bounce-short | 2,519 | **2026-10-18** (exact) | | | |

Net: a large mid/late-August cohort went quiet and was only partly replaced by a smaller, later cohort — hence 2,446 → 1,542 inserts/day (−37 %) by Oct 12–Nov 4, then a recovery to 1,920/day once jup_yolo/atr-trend/linreg-fade arrived.

**Trade-side corroboration (PG `trades.signal`, weekly top):** Aug-31 wk `bb_bounce_v2_long` 56 / `ema300_dip` 55 / `accel_300_v3_long` 37 → Sep-7 wk `pullback-entry-` **47** / `pump-chain-` 42 / `pump_chain` 40 → Sep-14 wk `pullback-entry-` **65** (then absent) → Sep-28 wk `bb-squeeze+` 55 → Oct-12 wk `pump-chain±` 65 → Oct-26/11-02 wk `jup_yolo_mirrored` 66 / **73** → Nov-09 wk `ai-trader-pending` 30 / `atr-trend-` 26 → Nov-16 wk `atr-trend-` 14 / `jup_yolo_mirrored` 12. The trade book rotated with the generator book; `pullback-entry-` alone contributed 112 trades in the Sep-7 + Sep-14 weeks and then disappeared.

### 4.4 The late-Sep / early-Oct conversion dip — real, not attributable

Conversion 1.94 % → **1.13 %** (Sep 23 – Oct 11) → 1.84 % (Oct 12 – Nov 4). n = 422 trades over 19 d; the neighbouring windows imply ~686, so the deficit is ~38 % (Poisson σ ≈ 26) — **not noise**. It then recovered, so it contributes almost nothing net (−0.05 log-points, §5).

**No instrument covers it**: `gate_shadow` starts Oct 4, `expiry_shadow` Oct 9, `signal_compactor.log` Oct 10, `pipeline.log` Oct 30, and `signals.log` has a hole Oct 14–21. Git shows a dense run of gate/filter changes Oct 11–12 (LONG-NEUTRAL-CHOP, mid-band block, BB-SQUEEZE RSI max, HIGH-70+ LONG block, `SIGNAL_EXPIRY_MINUTES 5→15`) but **I cannot attribute the dip to any of them from data** — and most of them shipped *after* the dip began. Stated as unexplained.

---

## 5. Quantified decomposition of the mandate's −70 %

Anchor: Sep-7 week **47.0/day** (n=329) → Nov-5–19 **13.67/day** (n=205). `ln(13.67/47.0) = −1.235`.

`trades = emissions × conversion`, so:

| component | log-share | attribution |
|---|---|---|
| **Nov-4 capital brakes** (conversion 1.84 % → 0.71 %, `ln = −0.948`) | **−0.948 → 77 %** | Cap D + Cap C |
| **emissions** (Sep-7 wk E → 1,920/day) | **0 % … +25 %** (E = 1,900 → −1 %; E = 2,298 → +15 %; E = 2,600 → +25 %) | generator attrition (§4.3) |
| intermediate conversion wiggle (Sep 23 → Nov 4) | **≈ +4 %** | unexplained (§4.4), nearly cancels |

The 77 % figure is **anchor-independent**: it is the Oct 12–Nov 4 → Nov 5–19 conversion step and does not use the unrecoverable Sep-7 emission rate.

**Robustness to the denominator choice.** Using the deduped compactor `Query:` hits instead of id-span: conversion 0.31 % (10-12 wk) → 0.10 % (11-16 wk) = **−68 %**; id-span conversion 2.24 % → 0.74 % = **−67 %**. Same answer.

**Block volume, corrected.** The deep-dive's "4.3k–9.4k episodes/week flat" is reproducible (4,285–9,389 for full weeks) but *per day* it rose: **783 → 612 → 912 → 1,341 → 1,043 → 1,186 → 1,305/day** (Oct-05 → Nov-16 wk). Per *emission* it is roughly flat: 0.48 / 0.74 / 0.75 / 0.54 / 0.57 / 0.69 episodes per insert. Raw gate events/day: 1,630 → 3,085. **Gates did not tighten; block:trade worsened 12:1 → 130:1 because trades fell.**

**Confluence, corrected.** `CONFLUENCE-GATE-BLOCK` fell from 3,515/wk (10-26) to 813/wk (11-09) — **502 → 116 per day, −77 %**. Confluence *loosened* over the window; it cannot be the declining lever.

---

## 6. Ranked answer

| # | Lever | Share of the −70 % | Confidence | Basis |
|---|---|---|---|---|
| **1** | **DailyFillCap (Cap D, 15/day) + Cap C, shipped 2026-11-04** | **~77 %** | **HIGH** | Ship date = step date; n=11,765 + 18,957 named SKIP lines; 0 releases; observed 13.7/day ≈ 15 cap; emissions +25 % across the boundary; conversion −62 %; skip-mix 64 % of all Nov skips. Not a randomised test, but four independent lines agree. |
| **2** | **Signal-emission decline (generator attrition), −37 % Aug → mid-Oct** | **0–25 %** (15 % at the window-mean anchor) | **MEDIUM** | Id-sequence insert counts are unbiased and cross-validated to 3.5 %, but the 34-day hole containing the anchor week prevents weekly resolution, and post-Aug source mix is unrecoverable. |
| **3** | **Late-Sep/early-Oct conversion dip (1.94 % → 1.13 %)** | net **≈4 %** (large gross, then recovered) | **LOW on mechanism, HIGH on existence** | n=422 vs ~686 expected (p≪0.001 by Poisson), but **zero log coverage** for the period. |
| **4** | Gate blocks | **0 (wrong sign)** | HIGH | Episodes/day +67 %; per-emission 0.48–0.79 flat; CONFLUENCE-GATE-BLOCK −77 %/day. |
| **5** | Confidence floor (MIN_EXEC_CONFIDENCE) | **0** | HIGH | `CONF-FLOOR` lines **n=0** (Oct 30 → Nov 20, 7.23 M lines); empty-hotset share *fell* 84.9 % → 42.8 %. |
| **6** | SKIPPED decisions | **0** | HIGH | n=39 of 12,121 rows (0.32 %), Nov 6 → Nov 20; expiry_shadow SKIPPED *rose* 1,725 → 3,137/wk. |

**The single measurement that would firm this up:** re-run the exact `SKIP: DailyFillCap` / `Decider Done: N entered | M skipped` counters with a **distinct-candidate key** (token+direction+signal_id) and hold `DAILY_FILL_CAP_ENABLED=False` for 48 h in shadow-first fashion (the `automatic-implementation` pattern), comparing trades/day and conversion against the 13.7/day baseline over the same emissions level. That converts the 77 % attribution from a strong temporal+magnitude argument into a controlled one, and it also prices in the §4.4 gap if run while emissions are at their current ~1,900/day.

---

## 7. Reproducibility

All query scripts: `/tmp/d3_freq/` — `load_signals.py` (archives + live table → `signals_all.db`), `weekly.py` (emissions + expiry reason mix), `master.py` (the §3 table), `logs_weekly.py` (log markers), `eps.py` (60-min episode definitions), `daily_ids.py` (daily id-delta series), `pipeline_all.log` (concatenated pipeline logs, 7,233,357 lines).
Key one-liners:

```sql
-- trades (PG brain)
SELECT date_trunc('week', open_time)::date, COUNT(*) FROM trades
WHERE status='closed' AND paper='f' GROUP BY 1 ORDER BY 1;

-- expiry_shadow weekly
SELECT date(created_at,'weekday 0','-6 days') wk, decision, COUNT(*) FROM events GROUP BY 1,2;

-- gate_shadow weekly events
SELECT date(blocked_at,'weekday 0','-6 days') wk, COUNT(*) FROM events GROUP BY 1;
```

Known limits: §1 (coverage) and §5 (anchor sensitivity).
