# Independent Verification: `jup_yolo_mirrored` detect-time RSI >= 55 block rule

**Date:** 2026-11-14
**Question (pre-registered):** Would blocking `jup_yolo_mirrored` entries whose detect-time RSI (metadata `rsi_14`, fallback `rsi_detect`) is >= 55 have improved results over the trailing 30 days?
**Method:** Own-conclusions. All SQL and statistics written from scratch against the live DB. Fisher exact implemented by hand with `math.comb` (hypergeometric), cross-checked against `scipy.stats.fisher_exact`. Welch t-test computed by hand (Welch–Satterthwaite df), p-value from t survival function, cross-checked against `scipy.stats.ttest_ind(equal_var=False)`. Both cross-checks matched to 6 decimals.
**PnL field:** `pnl_usdt` (unleveraged) everywhere. `pnl_pct` never used.

## Delta convention (stated explicitly)

```
sum_blocked = Σ pnl_usdt of trades the rule would block
delta       = total_after_block − baseline_total = −sum_blocked
```
Blocking a cohort that sums to −$1.35 saves +$1.35. **Bar 1 requires delta >= +$0.50.**

---

## 1. Data verification (run first)

```sql
-- metadata availability for jup_yolo_mirrored, trailing 30d
SELECT
  count(*) AS n_all,
  count(*) FILTER (WHERE _signal_metadata ? 'rsi_14') AS has_rsi_14,
  count(*) FILTER (WHERE NOT (_signal_metadata ? 'rsi_14') AND _signal_metadata ? 'rsi_detect') AS only_rsi_detect,
  count(*) FILTER (WHERE NOT (_signal_metadata ? 'rsi_14') AND NOT (_signal_metadata ? 'rsi_detect')) AS neither,
  count(*) FILTER (WHERE signal_rsi_14 IS NOT NULL) AS has_col_signal_rsi
FROM trades
WHERE signal='jup_yolo_mirrored' AND status='closed'
  AND close_time >= now() - interval '30 days';
-- result: 156 | 145 | 0 | 11 | 145
```

Schema confirmed: `_signal_metadata` is **jsonb** (not text — a `<>''` predicate errors out; first probe hit this).

```sql
SELECT min(close_time), max(close_time), count(DISTINCT id), count(*)
FROM trades WHERE signal='jup_yolo_mirrored' AND status='closed'
  AND close_time >= now() - interval '30 days';
-- 2026-10-30 06:27:08 .. 2026-11-14 11:34:27 | 156 | 156
```

## 2. Cohort extraction (exact SQL)

```sql
SELECT id, token, direction, pnl_usdt, open_time, close_time, mfe_pct, volatility_regime,
  COALESCE(_signal_metadata->>'rsi_14', _signal_metadata->>'rsi_detect') AS rsi_detect,
  CASE WHEN _signal_metadata ? 'rsi_14' THEN 'rsi_14'
       WHEN _signal_metadata ? 'rsi_detect' THEN 'rsi_detect'
       ELSE 'MISSING' END AS rsi_src
FROM trades
WHERE signal='jup_yolo_mirrored' AND status='closed'
  AND close_time >= now() - interval '30 days'
ORDER BY close_time;
```

Analysis (Fisher/Welch/halves): `/tmp/opencode/jup/analyze.py` against `/tmp/opencode/jup/jup_cohort.tsv`.

**Rule as evaluated:** blocked = `rsi >= 55.0` where rsi = `rsi_14` else `rsi_detect`. Rows with **neither key are KEPT** (cannot be shown to be >=55 → conservative for a block rule; they are not silently dropped).

## 3. Headline numbers (n=156)

| Cohort | n | net pnl_usdt | wins | WR | zero-pnl |
|---|---|---|---|---|---|
| Full baseline | 156 | **−$1.07** | 96 | 61.54% | 5 |
| Blocked (rsi>=55) | **50** | **−$1.35** | 28 | 56.00% | 1 |
| Kept (rsi<55 or null) | **106** | **+$0.28** | 68 | 64.15% | 4 |

- `delta = −sum_blocked = +$1.35`
- WR excluding zero-pnl rows (alternative convention): baseline 63.58% (96/151), kept 66.67% (68/102) — bar 3 holds either way.
- Blocked RSI range: 55.06 .. 80.49. Near-threshold band (50 ≤ rsi < 55): 13 trades (would-be borderline if threshold moved).

## 4. Pre-registered ship bars

| # | Bar | Result | Verdict |
|---|-----|--------|---------|
| 1 | net delta >= +$0.50 | **+$1.35** (sum_blocked = −$1.35) | **PASS** |
| 2 | blocked n >= 30 | **n = 50** | **PASS** |
| 3 | kept WR >= baseline WR | **64.15% >= 61.54%** (+2.61 pp; also holds excl. zeros: 66.67% vs 63.58%) | **PASS** |
| 4 | blocked net negative in both time-halves | half1 **−$0.88** (n=23), half2 **−$0.47** (n=27) — same sign | **PASS** |

Time-halves: full cohort ordered by `close_time`, split at median close_time **2026-11-02 13:48:39** → half1 = 2026-10-30 06:27 .. 2026-11-02 13:48 (n=79), half2 = 2026-11-02 15:11 .. 2026-11-14 11:34 (n=77). Kept halves: +$0.23 / +$0.05.

Sensitivity (split blocked cohort at its **own** median 2026-11-02 19:07): h1 −$0.98 (n=26), h2 −$0.37 (n=24) — same sign, bar 4 robust to split choice.

## 5. Significance tests (reported honestly)

| Test | Statistic | p-value | Significant at 0.05? |
|------|-----------|---------|----------------------|
| Fisher exact, 2-sided, WR blocked vs kept (28/50 vs 68/106) | odds 0.7112 | **p = 0.379252** | **No** |
| Welch t-test, per-trade pnl_usdt blocked vs kept | t = −1.5600, df = 89.28 | **p = 0.122304** | **No** |

Hand implementations matched scipy exactly (`fisher_exact` p=0.379252; `ttest_ind(equal_var=False)` p=0.122304).

Fisher 2-sided method: hypergeometric `P(X=x) = C(r1,x)·C(n−r1,c1−x) / C(n,c1)` over all tables with `P <= P(observed)` (tolerance 1e-9), support `[max(0, c1−(n−r1)), min(r1, c1)]`.

**Neither difference is statistically significant.** The WR gap (56.0% vs 64.15%) and the pnl gap (−$0.027/trade vs +$0.003/trade) are directionally consistent with the rule helping but rest on n=50 with small dollar magnitudes. Bar 4's same-sign halves are the only consistency evidence available in-window.

## 6. Direction split of blocked cohort

| Direction | n | net pnl_usdt | WR |
|-----------|---|--------------|-----|
| LONG | 31 | −$1.10 | 54.8% |
| SHORT | 19 | −$0.25 | 57.9% |

Both sides negative → the blocked cohort's losses are not driven by one direction. Rule is not a hidden direction bet.

## 7. Collision check — is a jup-scoped rule necessary?

SQL (separate cohort, no jup rows):
```sql
SELECT id, signal, direction, pnl_usdt, close_time,
  COALESCE(_signal_metadata->>'rsi_14', _signal_metadata->>'rsi_detect')::numeric AS rsi
FROM trades WHERE status='closed' AND close_time >= now() - interval '30 days'
  AND (signal LIKE '%atr-trend-%' OR signal LIKE '%bb-squeeze+%')
ORDER BY close_time;
```
Overlap with jup cohort: **0 ids** (signal values are disjoint by construction; no double counting possible).

| Signal cohort | n (30d) | RSI range | Blocked (rsi>=55) | sum_blocked | **delta if blocked** | blocked halves | bar1/bar4 if global |
|---|---|---|---|---|---|---|---|
| `atr-trend-` | 21 | 57.6 .. 100.0 | **21 of 21 (100%)** | +$0.05 | **−$0.05** | +$0.11 / −$0.06 (opposite) | FAIL / FAIL |
| `bb-squeeze+` (+1 combined) | 57 | 0.0 .. 75.0 | 46 | +$0.02 | **−$0.02** | +$0.70 / −$0.68 (opposite) | FAIL / FAIL |

- `atr-trend-` fires **exclusively** at RSI >= 55 — a global rule would annihilate 100% of it while it is net positive, and would "lose" money (delta negative).
- `bb-squeeze+`: blocking rsi>=55 saves −$0.02 (i.e., loses money), halves flip sign, though its blocked WR (56.5%) is below its kept WR (81.8%) — dollars and WR disagree there.
- **Conclusion: YES, the jup-scoped rule is necessary.** The identical non-scoped rule fails bar 1 AND bar 4 on both non-jup signals.

## 8. Sanity / double-counting

- 156 rows, **156 unique ids → 0 duplicates**. Halves partition exactly: 79 + 77 = 156; blocked halves 23 + 27 = 50.
- Zero id overlap between jup cohort and collision cohorts (78 unique collision ids, none is a `jup_yolo_mirrored` row).
- All 156 jup trades opened in the window are `status='closed'` — no open/partial rows excluded, none counted twice.
- `pnl_usdt` nulls: 0.

## 9. Data-quality surprises

1. **"Trailing 30 days" contains only ~15 days of data.** `jup_yolo_mirrored` closes start 2026-10-30. The 30d filter is honest but the effective window is 15.2 days — OOS-consistency evidence (bar 4) covers ~7.6 days per half, not 15.
2. **11/156 (7%) rows carry neither `rsi_14` nor `rsi_detect`** — and the fallback helps: `only_rsi_detect = 0`, so the fallback never fires. The same 11 rows are also NULL in the `signal_rsi_14` column (145 populated). Missing rows are scattered 2026-11-03 → 2026-11-14 (not a startup artifact), net −$0.06, 7 wins. Primary treatment: kept. Sensitivity on the 145 RSI-present rows only: blocked 50 / −$1.35, kept 95 / +$0.34, delta **+$1.35 unchanged**, kept WR 64.21% >= baseline 61.38% → bars unaffected.
3. **Dollar magnitudes are tiny.** The entire 156-trade cohort nets −$1.07; the rule's full benefit is +$1.35. Bar 1 clears its $0.50 gate by 2.7x, but economically this is coffee money — position sizing, not edge size.
4. **No statistical significance** (Fisher p=0.38, Welch p=0.12). Ship bars do not require it, but any claim of "proven edge" would be overreading this.
5. **`atr-trend-` has RSI floor 57.6** — that signal's RSI is structurally always >=55, so the same numeric threshold means something completely different per signal. Strong argument for signal-scoped thresholds generally.
6. 5 zero-pnl rows treated as losses in WR; bars hold under either convention.
7. One probe failed initially: `_signal_metadata` compared as text errors (`invalid input syntax for type json`) — it is jsonb. Anyone copying queries should use `?` / `->>` operators, not string predicates.

## 10. VERDICT

# **PASS**

All 4 pre-registered bars hold:
1. delta = **+$1.35** >= +$0.50 ✅
2. blocked n = **50** >= 30 ✅
3. kept WR **64.15%** >= baseline WR **61.54%** ✅
4. blocked net in both halves: **−$0.88 / −$0.47**, same sign ✅

P-values reported honestly: Fisher 2-sided **p = 0.379** and Welch **p = 0.122** — both **not significant**. The bars as registered do not gate on significance, but the effect should be treated as directionally supportive and statistically unconfirmed at n=50 over a 15-day effective window.

Collision check: rule must remain **jup-scoped** — the identical non-scoped rule fails bar 1 and bar 4 on both `atr-trend-` (delta −$0.05, would block 100% of the cohort) and `bb-squeeze+` (delta −$0.02).
