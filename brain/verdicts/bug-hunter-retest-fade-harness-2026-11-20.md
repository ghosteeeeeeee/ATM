# BUG-HUNTER VERDICT — backtest_retest_fade harness (retest-fade evidence tables)

**Verifier:** agent-2 (bug_hunter), adversarial — no fixes applied, findings only
**Date:** 2026-11-20 07:2x UTC
**Target:** commit `315e576d` ("backtest harness: retest-fade evidence tables")
— `scripts/backtest_retest_fade.py` (317 lines, sole file in commit) +
`plans/2026-11-20_retest-fade-harness-output.txt` (gitignored, `.gitignore:142 plans/`, on disk) +
plan §7 `plans/2026-11-20_retest-fade-system-plan.md:155-229`
**Prior audit:** `brain/verdicts/1795152254-retest-fade-own-conclusions.md` (read first)
**Harnesses:** `/tmp/verify_rf.py`, `/tmp/verify_rf2.py`, `/tmp/rerun*.txt` — **zero production writes; no run_cycle run (backtest tool, not needed).**

---

## OVERALL VERDICT: **CONDITIONAL PASS — one HIGH finding (F-1)**

The three self-caught pre-commit bugs are **all genuinely fixed and complete**.
Scope, columns, cost arithmetic, pinned constants, and edges check out.
But the commit-message claim "confirmable levels (+3-bar swing confirmation = **the lookahead kill**)"
is **not fully true at the bar boundary**: >50% of "confirmable" episodes enter **on the very bar the swing
confirms**, before the level is knowable — and the resulting bias is **one-directional (inflates every row)**,
with **one LONG row flipping sign** under the strict causal model. Re-run after a +1-bar entry fix
before citing any col2/3/4 LONG number as lookahead-free.

## Verdict table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| A | Lookahead, every consumer | **FAIL (residual same-bar, HIGH)** — see per-consumer below | touch bar == confirm bar in **266/510 LONG, 243/449 SHORT** episodes; delay3→delay4 moves **all 16 rows down** (−0.3…−214 margin), 1 sign flip |
| A-ii | Adversarial: confirmable can't see future bars | **PASS (with boundary caveat)** | `/tmp/verify_rf.py`: swing@6 exists full / **absent when bar i+3 truncated**; min(touch−li)=3 for all real episodes, **0 touch before confirm bar**; synthetic delay3 earliest touch = li+3 |
| B | Column mapping col1-4 + cost arithmetic | **PASS** | `h2_h3:260-265` tuples exactly (0,F,F)(3,F,F)(3,T,F)(3,T,T); parsed committed output: **16/16 rows col4 = col3 − 1.9·n** (±0.05); 1.9 = (0.0009+0.0010)·100·10 ✓; costs-on-OPEN = pessimistic, ≤7.6 margin pts/row (F-9, LOW) |
| C | col2→col3 attribution | **PASS (measured)** | serialization is the *only* diff by construction; **576-bar OPEN-hold explains 1/150 (0.7%)**; 146 resolved-overlap + 3 same-bar dups (details below) |
| D | H1 correctness | **PARTIAL (3 findings)** | recorded breaks causally clean (0 of 147 in confirm window); but trend-gate skips/defers breaks (**40/147 delayed, med24h 0.44%→0.86%**), retest reference=anchor not lo, `touches`≠zone entries (F-3/F-4/F-5) |
| E | TRAIL proxy vs production `_lag_stop` | **PASS-with-bounds (10 named differences)** | list below; TRAIL ≠ production exit model in 8 ways, matches in 2 |
| F | Re-run determinism / py_compile / pinned constants | **PARTIAL** | py_compile OK; **two consecutive runs byte-identical**; committed constants `git show HEAD:` **byte-identical to disk**; **re-run ≠ committed output — data drift, not code** (rolling 90d window + in-place candle UPDATEs; F-2 MEDIUM) |
| G | Regression scope | **PASS** | commit = exactly 1 file (317+); no other scripts/ change in commit; **no imports of it anywhere**; (pre-existing *uncommitted* edits to 4 other scripts are unrelated — flagged, not part of this change) |
| H | Edge cases | **PASS** | `summ([])`→"n=0" (no div/0), run_h(sw=[])→n=0; H1 empty bucket "(none)"+`if retests` guard; swings bounded (first idx 6≥3, last ≤len−4); trend len == rows len (8640==8640); TP==stop impossible (assert); cluster-1 bucket exercised (n=62); `avail>=len` guard |

---

## A verdict: lookahead, per consumer (TOP PRIORITY)

Mechanics: `swings()` (L70-80) needs `rows[i±3]` → level knowable **only at the CLOSE of bar li+3**.

| Consumer | Verdict | Evidence |
|---|---|---|
| **Touch search** (L165,170) delay≥3 | **FAIL — same-bar residual (HIGH, F-1)** | start = `max(li+3, li+1)` = **li+3 inclusive** = the confirm bar itself; at fill time (intrabar, at zone price) the swing is **not yet confirmed**. **53% of confirmable episodes** enter on that bar (266/510 L, 243/449 S); **0** enter earlier (the audit's multi-bar killer IS dead). Strict model = start li+4: measured **all 16 rows move DOWN** (L g=1 0.4FIX +158.7→+33.8 = −79%; **L g=1 0.8FIX +93.1→−25.8 sign-flip**; S g=1 0.4FIX +351→+292; TRAIL rows −0.3…−194). Bias direction = **optimistic for every row**. Caveat: matches the audit's own "delay 3" convention (verdict §8), but the commit claims the *kill* |
| **col1 delay0** (L165,170) | PASS (by design) | touch from li+1 → 458/519 L and 425/461 S episodes enter ≤li+2; **documented** "as-simulated = lookahead levels" (docstring L19, col header L273) |
| **TRAIL** (L207-210, 216-219) `ti<=sj and sj+CONFIRM_DELAY<=i` | **PASS — clean, inclusive bound self-neutralizing** | fix from bug-2 present on both sides; pre-entry swings excluded (`ti<=sj`); tighten-only both sides (max for L / min for S). Residual `i==sj+3` application can't fire that bar (swing window guarantees `low[i]≥sv > sv·0.999` for L, `high[i]≤sv < sv·1.001` for S) — measured **0/988** cases; no +43k% artifacts (all sums ≤ ±1,430%) |
| **H1 break search** (L118-123) | **PASS empirically / structural gap noted** | clusters built from unconfirmed swings (L301, no delay) and search starts at `hi_i+1` (needs `hi_i+3`) → **structural 3-bar window**, but **0 of 147 recorded breaks** land in `[hi_i+1, hi_i+3]`; min gap hi_i+4 → all cluster levels confirmed before the recorded break. Window-specific, re-verify if data grows |
| **H1 trend gate** | PASS (closes ≤ i, gate bar is the break bar itself — break bar's close IS the trigger) | `trend[]` = EMA on closes (L63-66) |
| **H2/H3 gate** `trend[touch]` (L180) | **FAIL-lite — no cross-bar lookahead, but same-bar residual (LOW-MED)** | EMA uses closes ≤ touch bar; but entry is intrabar at the zone price while `trend[touch]` needs the touch bar's **close** → gate can use post-fill info. Flips vs strict prev-bar gate: **13/510 L, 18/449 S** episodes (2.5%/4%) |

**Adversarial case (A-ii) constructed:** 14 synthetic bars, swing-low@i=6 whose window needs rows[9];
prominence supplied by idx8. `swings(full)=[(6,99)]`; `swings(full[:9])=[]` → the level **does not exist**
until bar i+3. delay3: earliest touch = 9 (=li+3) — **never before**; delay0: touch = 7 (li+1) — col1's
documented lookahead. Conclusion: **no consumer reads bars past the confirm bar before entering — but the
confirm bar itself is used end-to-end (its low as touch, its close as gate) → one-bar-boundary leak.**

## C attribution: col2 (244) → col3 (94)

- **Serialization is the whole drop by construction**: col2/col3 differ only in `flat_only`; episode
  build identical; resolution independent of serialization (verified: my replica of `run_h` reproduces
  244→94 exactly on a snapshot matching the committed H3 rows, and `M.run_h` direct calls match the replica).
- **Exact decomposition of the 150 dropped** (H3 GATED 0.4 FIXED):
  - **146** — genuine overlap: skipped while an accepted **resolved** episode still holds the slot
    (blocker hold: STOP median **44 bars (11h)**, TP median **71 bars (17.75h)**; skip lag median 20 bars,
    p90 97)
  - **3** — same-bar duplicate entries (distinct swings, identical touch bar → stacked in col2, un-realizable)
  - **1** — the feared **576-bar (6-day) OPEN hold: counterfactual "OPEN doesn't hold" gives 95 vs 94 →
    it explains 1/150 = 0.7%**. (The single accepted OPEN here sits 12 bars from data end, so the cap
    barely bites on THIS window; structurally an OPEN mid-window would freeze 6 days — but it didn't matter.)
- Same pattern in the other two instrumented rows: H2 GATED 298→105 (OPEN-hold 1 of 193), H3 UNGATED
  449→165 (OPEN-hold 1 of 284). **Conclusion: the drop is touch-time clustering (~99%), not the OPEN cap.**
- Side note: the removed episodes average **+1.1…+1.8 margin/ep (positive)** vs kept ~+1.1 → sign-flip of
  H2 FIXED col2 (+156) → col3 (−52) is a composition effect of which wave-entry survives, not a computation error.

## E: proxy TRAIL vs production `_lag_stop` (auto_trader.py:431-615) — every difference

| # | Production `_lag_stop` | Proxy TRAIL | Direction |
|---|---|---|---|
| 1 | Structure = `structure_analysis` zigzag 0.6×ATR14, **15m (favorable) + 1h (adverse)** (L432-444) | own fractal detector (±3 bars, 0.25% prom, ≥6 gap), **15m only** | different levels entirely — audit SPEC SOUNDNESS #1 ("two level definitions coexist") applies inside the proxy too |
| 2 | **Adverse branch: RAISES stop to the 1h major invalidation line** (L591-610) | **no adverse handling — tighten-only from t0** | proxy stops out on pullbacks production would ride; production grants room proxy never does |
| 3 | Steps to **prev_val = one swing BEHIND** the newest (L573, L562-564) | trails to the **newest** confirmed favorable extreme (min/max over all post-entry swings) | proxy stop sits **closer to price** → earlier exits |
| 4 | **BE-cap** in profit (`_be`=entry±0.1%, L478-483) + **BE-LOCK at birth if in profit** (L507-511) | **no BE rule at all** | proxy gives back open profit to the original stop before first structure print; production locks BE first |
| 5 | **Birth re-anchor** of interior stop to 1h line (F-1, L486-559), F-4 caps price×1.05/0.95, F-3 breach guard | no re-anchor, no caps — t0 = level ± fixed 0.4/0.8% | different stop authority from bar 0 (audit should-have 13 unresolved) |
| 6 | Offsets = **±0.10×ATR15/ATR1h** (L575,583,599,606) | ±**0.1% fixed** (sv·1.001 / sv·0.999) | proxy buffer unresponsive to volatility |
| 7 | Cadence = **30-min cycle** (trade_watchdog.py:1296 "every ~30min", invokes run_cycle at :2244; config hermes-watchdog) with DB CAS + retry-next-cycle (L395-408) | stop moves **every 15m bar** (2×), applied inside the bar loop | proxy can catch moves the cycle would miss; production writes can miss-and-retry |
| 8 | Exit path = watchdog/quote hit-check; F-1 **TP suppression** for managed+stop (pm:643-658) | bar hi/lo intrabar, **STOP checked before TP** (conservative tie) | path differs; TRAIL's no-TP **matches** F-1 suppression ✓ |
| 9 | Guardrails: never-at-price, F-4 stale caps, CAS | none of these | proxy can model stops production would refuse to write |
| 10 | Regime: no longer selects anything (L443) | GATED rows add an EMA trend gate (separate concern, disclosed) | gate is extra, not a `_lag_stop` feature |

**Bound for the report:** TRAIL col = *closest available proxy* — it matches production only on
"tighten-only on favorable structure" and "no TP while managed". It does **not** reproduce adverse-raise,
one-behind lag, BE-lock/re-anchor, ATR buffers, 1h source, 30-min cadence, or stop authority.
The **FIXED (1.5% TP) columns have NO production counterpart while F-1 is open** (audit Blocker 1 unchanged).
Never state "TRAIL col = production exit model"; at most "TRAIL col ≈ production exit *shape*, ± 10 differences".

---

## FINDINGS (severity + line refs)

**F-1 | HIGH | Lookahead: confirmable columns enter on the swing-confirm bar**
`backtest_retest_fade.py:165,170` — `avail = li + delay` with `delay=3`, search includes bar `li+3`,
but the swing is knowable only at that bar's **close** (`swings()` needs `rows[i+3]`, L73-77).
**53% of confirmable episodes** (266/510 L, 243/449 S) touch exactly at `li+3` (0 earlier — the
multi-bar leak is dead; the boundary leak is not). Gate compounds it (L180, uses the same bar's close:
13 L / 18 S flips vs prev-bar gate). Strict `li+4` model: **every one of 16 rows moves down**
(−0.3…−214 margin pts), incl. **sign flip** H2 LONG 0.8% FIXED +93.1→−25.8 and −79% on
H2 LONG 0.4% FIXED. Bias = systematically **optimistic**; hurts LONG rows most (audit's known-fragile side),
shorts keep sign but lose 13-48% of FIXED sums. Commit message's "= the lookahead kill" overstates.
*Fix (for the owner, not applied): touch search starts at `li + CONFIRM_DELAY + 1`; gate uses `trend[touch−1]`; re-run all 4 columns.*

**F-2 | MEDIUM | Committed output is not byte-reproducible; no data fingerprint**
Re-run (`/tmp/rerun.txt`) ≠ `plans/...output.txt`; code is deterministic (rerun==rerun2, replica==`run_h`).
Mechanism proven: `data/candles.db` is a **live rolling 90-day window** (8,640 bars; window rolled
min 1787381100→1787382000 / max 1795156200→1795157100 between snapshot 06:24:49 and re-run; DB mtime
06:45:04 > file mtime) **plus in-place candle UPDATEs inside an unchanged ts range** (same window bounds +
same detector counts 520/469/148 while gated LONG col2 moved 303→298 between two runs → a close changed
→ EMA chain flipped). Effect: queued/gated columns drift ±1-5 episodes; output line 1 prints only **dates +
constant "8640 bars"**, hiding the shift — a later verifier sees a matching header and non-matching rows.
This is exactly the audit's reproducibility standard (#1). *Fix: print full min/max ts + hash of rows, or snapshot the rows used.*

**F-3 | MEDIUM | H1: trend-gate conditions break measurement on the gate (selection + late base)**
`h1():119-122` — `if not trend[i]: continue` skips non-trend bars entirely.
- **40/147 (27%) recorded breaks** have `b_g > b_any` → displacement measured from a **later, lower base**;
  selection effect: **med24h = 0.44% (any-break) vs 0.86% (gated-break)** — the published stat is ~2× the ungated one.
- Breaks occurring *only* in non-trend bars are never counted: **0 on this window** (structural, untested-outside).
- `P(≤−1%)` denominators (L147-148) count the **6 breaks lacking 24h follow-up as 0** (`.get("24h",0)`),
  biasing P **down** up to 6/62; medians (L144-146) exclude those same rows → **inconsistent denominators**.
- Survivorship: P's condition on *broken* supports — **147/148 broke** here so empirical leakage ≈0.7%, but
  **break rate per touch bucket is never printed** (bucket totals 62/23/63 vs broken 62/23/62 → ~100% in every
  bucket), so "N-touch supports break more" (frequency) is unanswerable from H1 — only P(displacement | break).

**F-4 | LOW-MED | H1 retest reference: anchor, not the broken level**
`h1():135-136` — break threshold = `lo×(1−BROKEN)` but retest = `hi ≥ anchor×(1−ZONE)`; reference mismatch
for spread clusters (chaining is unbounded downward by construction: `val ≥ lo×(1−CLUSTER_TOL)` each step;
**measured worst span 2.44% / 254 bars / 18 swings; 0 clusters >3% on this window**; 86/148 multi-swing).
For single-swing clusters (62) anchor==lo → test = zone re-entry at level×0.997 = **+0.2% recovery past the
break threshold** counts as "retest = no straight slice" — price never needs to touch the actual level.
Window also runs b+1..b+95 = **23h45m**, not 24h (L136 off-by-one). The headline 103/147 = 70% rides on this bar.

**F-5 | MEDIUM | `touches` counts swing-lows only; comment promises swings+zone entries; `zone_bars` dead**
`clusters():96-103` — comment (L96-97) says "swing-lows in cluster + bar-level zone entries" but
`c["touches"] = len(c["vals"])` (L98); `zone_bars` (L103) is **never read anywhere**.
Measured: **86/148 clusters** have in-zone bar visits > swing count; totals **2,766 in-zone bars vs 520 swings**;
worst cluster **184 in-zone visits bucketed as "13 touches"**. H1's 1/2/3+ buckets understate hammering by up
to an order of magnitude vs the CEO's "hammering the same support over and over" framing. If swing-only is
intended, the comment and the printed `touches` header are wrong.

**F-6 | MEDIUM | "TRAIL = production exit model" must be bounded (10 differences, list E above)**
No code defect in the proxy itself (trail logic is lookahead-clean, tighten-only, pre-entry exclusion
verified) — this bounds the *claim* the report may make. FIXED rows meanwhile have **no** production
counterpart under open F-1.

**F-7 | LOW | Costs charged on OPEN (unresolved) episodes — pessimistic**
`run_h():233-236` — both `if`/`else` branches are identical (dead branch); `(FEE+SLIP)·100·10 = 1.9`
margin/ep subtracted on every episode **including OPEN** (verified 16/16 rows: col4 = col3 − 1.9·n).
Bias = **understates net** (charges a round trip never executed; flips tiny-positive OPEN marks to losses in
col4 win%). Magnitude ≤4 OPEN ×1.9 = **≤7.6 margin pts/row** — negligible vs ±50…1430 sums; defensible as
"will pay to close", but state the direction. −1.9 arithmetic itself **correct** (0.19% × 10x).

**F-8 | LOW | Doc/impl and dead-code mismatches**
- `swings():71` docstring "each carries available_from = i + CONFIRM_DELAY" — **the tuple carries no such
  field**; every consumer must apply delay manually (they do — but the doc lies).
- `h1():115-116` `if not any(trend…): pass` — no-op.
- `trend_gate_report():282-286` docstring promises "episode counts gated/ungated" — body prints only the share.
- `run_h():156` param `style` unused; `h2_h3`/`trend_gate_report` param `cls` unused.
- `main():302-303` `datetime.utcfromtimestamp` DeprecationWarning (cosmetic, stderr only).

**F-9 | INFO | H2 label vs implementation**
`h2_h3():268` — rows labeled "bounce-LONGS at **hammered** support" but episodes are built from **every**
swing low (`sw_all`), not clusters (`cls` only feeds H1). Also entries are FADE/first-touch style, not the
plan §3.2 CONFIRM style (consistent with docstring "first-touch modeling", but §7's Blocker 2 stays open —
this harness reports FADE evidence only).

## The three self-caught bugs — verification

| Bug | Fix location | Verdict |
|---|---|---|
| SHORT touch-search skipping all shorts | `:171-174` dedicated SHORT branch (`high ≥ level×(1−ZONE)`), plus SHORT entry/stop/tgt `:182-186`, resolve `:204-214`, trail `:207-210` | **FIXED & COMPLETE** — H3 produces n=247-461 rows; all SHORT paths present symmetric to LONG |
| TRAIL ratcheting on pre-entry swings (+43k% artifacts) | `:209` and `:218` `ti <= sj` + value-guard (`sv<entry` / `sv>entry`) + tighten-only min/max | **FIXED & COMPLETE** — pre-entry excluded; no ratchet (stop can only tighten per side); all output sums ≤ ±1,430%; confirm-bar application self-neutralizing (0/988) |
| H2/H3 claiming the gate without applying it | `:180-181` `require_trend and not trend[touch]`, passed for **all four columns** `:265` | **FIXED & COMPLETE** — gated vs ungated differ everywhere (e.g., H3 FIXED0.4 col1 247 vs 460); gate applied identically across col1-4 |

## Repro evidence
```
python3 -m py_compile scripts/backtest_retest_fade.py        → OK
git show HEAD:scripts/backtest_retest_fade.py | diff - disk  → identical (pinned constants untouched)
git show HEAD --stat                                          → 1 file, 317 insertions; grep: no importers
python3 scripts/backtest_retest_fade.py > /tmp/rerun.txt      → ≠ committed output (F-2, data drift)
  (second immediate re-run)  /tmp/rerun.txt == /tmp/rerun2.txt → deterministic given identical rows
python3 /tmp/verify_rf.py, /tmp/verify_rf2.py                 → all measurements above
```

**Bottom line:** ship-quality as a *pinned evidence table generator* (scope clean, columns/costs exact,
three self-caught bugs genuinely fixed, edges safe), but **F-1 must land (+1 bar) and F-2 (data fingerprint)
before plan §7 cites any col2/3/4 row as "lookahead-free"** — and the report must carry F-3/F-5's H1 caveats
and F-6's bounded TRAIL-vs-production claim.

---

# ACCEPTANCE ROUND 2 — fixes F-1 / F-7 / F-2 (commit `3dceef49`, 2026-11-20 07:01)

Scope check: fix commit = exactly 1 file, 20 lines (14+/6−), 3 hunks (touch range, costs guard,
sha header). Pinned constants (L34-46) byte-identical to `315e576`. Later commit `9dd23fd`
touches only AGENTS.md/dsh-bundles (unrelated).

| Fix | Verdict | Evidence |
|---|---|---|
| **F-1** touch = `max(avail+1, li+1)` (L171) | **PASS (mechanics) + 1 residual** | OLD(delay4) ≡ NEW(delay3) episode-for-episode & margin-for-margin, 4/4 config cells, same snapshot; **col1 delay0 byte-identical old-vs-new** (unchanged by design ✓). Pure fix effect (queued/gross, current snapshot): LONG −100…−155 all down **incl. predicted sign flip 0.8FIX +105.5→−43.3**; SHORT FIXED −43/−49 (my table −59/−65, within drift); SHORT TRAIL +10.2/−6.8 (≈insensitive, my table −0.3/−17.3, sign = noise). Direction matches **7/8, 8th ≈ 0**. **Residual:** gate `trend[touch]` (L184) still uses entry-bar close — 2nd bullet of my prescription NOT applied (~13/510 L + 18/449 S flips, LOW-MED → v0.6 with F-3: `trend[touch−1]`) |
| **F-7** costs on STOP/TP only (L237-240), dead branch gone | **PASS** | Committed file verified **16/16 rows: col4 = col3 − 1.9×(STOP+TP)** exactly (e.g. +76.1 − 1.9×89 = −93.0; +46.7 − 1.9×60 = −67.3). OPEN free; ≤7.6 pts pessimism removed |
| **F-2** data-sha256[:12] over (ts, close) (L308-310) | **PASS (core) + 1 residual** | Two immediate runs **byte-identical** ✓; independent recompute = header value ✓. **My run ≠ committed file (20bd656714a8 vs b0d630140777) — data moved again: window rolled both ends +900 (now 1787382900→1795158000, new 15m bar landed post-their-run).** The hash now *proves* the cause = F-2 working as designed; byte-identity across time is unachievable on the live DB (the ask fails by environment, not by code). **Residual:** sha covers **(ts, close) only** — swings/touches/exits consume **high/low**; an HLC-repair would change results under an unchanged hash (full-row sha on this snapshot = 54198efec25b) → hash all 5 columns in v0.6 |

**Delta reconciliation (their reported vs mine):** their old→new col4
(−15.5 / +37.5 / +24.9 / +63.7) vs my like-for-like old→new on one snapshot
(**−12.7 / +40.4 / +27.9 / +66.6**) — matches within ±2.7 (drift) ✓.
Caveat for the record: my strict-model table was **queued/gross** (all rows down);**3 of 4 col4 rows moved UP** because col4 = flat+net and the entry shift
reshuffles serialization survivors (composition ±40-67) + F-7 (+1.9). "Signs
unchanged" ✓ true; "magnitudes shifted as predicted" is true for the **entry
component and sign-preservation only**, not for col4 magnitudes — don't cite
the latter without this caveat.

**F-3/F-4/F-5 deferral to v0.6: ACCEPTABLE — non-blocking.** They affect H1
claim interpretation only, not the H2/H3 money columns; §8 already records
the anchor-vs-lo inconsistency, the 90%>70% retest base rate, and the
header mislabel. Condition: **explicitly add F-3 and F-5 to the v0.6 backlog
line** (neither is visible in §8 text: F-3 = 40/147 gate-delayed breaks,
med24h 0.44→0.86, 6 no-follow-up counted as 0 in P; F-5 = touches=swings-only,
zone_bars dead, worst cluster 184 in-zone bars vs "13 touches") and keep H1's
"major break"/"no straight slice" out of settled claims until then.

**Heads-up:** §8's round-2 cell values are **PRE-fix** (its ranges cite
+139.4/+546.4 = the `315e576` output) — regenerate or annotate those cells
against the fixed harness; its structural findings (base rates, 73%
concentration, serialization driver) are robust to the fix.
