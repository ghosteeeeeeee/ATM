# Independent Verdict: Signal Habitat Filters Plan

**Date:** 2026-10-08
**Auditor:** Independent subagent (own-conclusions, fresh read)
**Subject:** `/root/.hermes/plans/signal-habitat-filters.md` (v3)
**Data source:** PostgreSQL `brain`.`trades`, 30-day window (Sep 8 – Oct 8 2026), `close_time > NOW() - INTERVAL '30 days'`, `status='closed'` — queried directly, not taken from the plan.

---

## OVERALL VERDICT: PARTIAL (directionally plausible, materially overstated, not safe to implement as written)

The headline totals are real and several habitat cells reproduce exactly. But: two key table rows for pump-chain- cannot be reconciled with the database (they inflate the "profitable habitat" side), the filter-impact math is wrong by ~2.3x, the entire pump-chain- edge lives in ONE week and **reverses sign in the two most recent weeks**, none of the win-rate differences are statistically significant, one of the three proposed filters is already live, and another directly contradicts a live filter (SHORT_CONTINUUM) without acknowledging it. The plan's code snippet would crash on missing BTC score (29% of pump-chain- trades).

---

## 1. pump-chain-: "works when BTC bullish (60-62% WR), fails when bearish (20-40% WR)"

=== INDEPENDENT VERDICT ===
Claim: pump-chain- SHORT works in bullish BTC (60-62% WR), fails in bearish BTC (20-40% WR)
Verdict: PARTIAL
Evidence:
- Reproduced cells (exact match to plan): bullish EXTREME 8T 62.5% +$0.36; strong_bear EXTREME 30T 40.0% +$0.15; bearish EXTREME 18T 38.9% -$0.44; neutral EXTREME 14T 50.0% -$0.56; strong_bear HIGH 5T 20.0% -$0.58. ✔
- **UNREPRODUCIBLE rows**: plan claims strong_bull HIGH **n=18** 61.1% +$0.53 and strong_bull EXTREME **n=28** 60.7% +$0.15. Actual (score>80): strong_bull HIGH **n=5** 60% +$0.48; strong_bull EXTREME **n=5** 40% **-$0.19**. Only **10** pump-chain- trades have score>80 in the window — the plan's two rows claim 46. The plan's cell table sums to 121 trades but only 96 scored trades exist → internally impossible. No alternate bucketing (score≥60/≥70, btc_regime field, alternate windows 14/21/25/35/45d, hype_realized_pnl column) reproduces these rows. The error inflates exactly the side the plan calls the "habitat".
- Directional trend exists but weak: score<40 = 60T **40.0% WR** -$0.55; score≥40 = 36T 52.8% -$0.16; score≥60 = 21T 57.1% **+$0.56**. Fisher exact p=0.29 (<40 vs ≥40), p=0.21 (<40 vs ≥60); Mann-Whitney on PnL p=0.23. **None significant at 0.05.**
- All SHORTs (30d) agree in direction: score≥80 = 52.2% WR +$0.35 (best band); 20-40 = 39.7% -$1.67; 40-60 = 40.0% -$1.95. So the thesis direction is supported in aggregate — but confounded by time (see §6).
Confidence: HIGH
Notes: The threshold choice of 40 is poorly supported: the **kept** band 40-60 is the worst per-dollar (-$0.72); only ≥60 is positive. A 60 threshold would fit this window better — which is exactly the in-sample tuning trap the plan's own Risk 3 warns about.

---

## 2. Filter 1 impact: "block BTC<40 → block 41 trades (-$1.58), keep 54 (+$1.04), net +$2.62"

=== INDEPENDENT VERDICT ===
Claim: Blocking pump-chain- when BTC score<40 improves PnL by +$2.62/30d
Verdict: DISAGREE
Evidence (computed directly):
- Actual blocked set: **60 trades, -$0.55** (not 41/-$1.58), and it contains **24 winners** (40% WR) — not "41 losing trades".
- Actual kept set: 76 trades (36 scored + 40 fail-open NO_SCORE), **+$0.32** (not 54/+ $1.04).
- **True improvement = +$0.55**, not +$2.62. The plan's own arithmetic also double-counts (improvement from removing a -$1.58 set is +$1.58, not +$1.58+$1.04).
- No window (14/21/25/35/45d), threshold (20-70 sweep), or PnL column (pnl_usdt / hype_realized_pnl_usdt) reproduces "41 trades / -$1.58".
- **Instability — the edge is one week and it has already flipped sign.** Weekly blocked-set PnL: Sep-14 wk -$0.04 (3T) | **Sep-21 wk -$1.51 (22T)** | Sep-28 wk **+$0.70 (22T)** | Oct-05 wk **+$0.30 (13T)**. In the two most recent weeks, blocking BTC<40 would have **cost** ~$1.00. On a 14d window the blocked set is **+$0.92** — the filter would have destroyed $0.92 of profit. Bootstrap 95% CI of the 30d improvement: **[-$2.48, +$3.26]** — includes large harm.
- **The "habitat" is not actually profitable:** kept scored trades (score≥40) = 36T **-$0.16**. The filter's only positive kept mass is the 40 NO_SCORE trades (+$0.48, 65% WR) — all from the first week, when btc_score was recorded for only 28% of trades. The projection relies on fail-open trades from a different era.
- Confounder: the last week (Oct-05) had **zero** score≥40 pump-chain- trades; all 13 scored trades were <40 (+$0.30). The claimed habitat has stopped producing signals entirely.
Confidence: HIGH

---

## 3. bb-squeeze+: "works in NORMAL (80-83% WR), fails in HIGH with certain BTC conditions"

=== INDEPENDENT VERDICT ===
Claim: bb-squeeze+ has a NORMAL-volatility habitat at 80-83% WR; failure cell is strong_bull+HIGH
Verdict: PARTIAL
Evidence:
- The plan's 7 table rows reproduce **exactly** (bullish NORMAL 5T 80% +$0.51; bullish HIGH 5T 80% +$0.23; bearish HIGH 5T 80% +$0.16; strong_bull NORMAL 6T 83.3% +$0.08; strong_bull HIGH 17T 47.1% -$0.13; neutral HIGH 7T 71.4% -$0.18; strong_bear HIGH 5T 60% -$0.23). ✔
- But "works in NORMAL 80-83%" is cherry-picked: overall NORMAL = 18T **66.7%** +$0.25, and **neutral NORMAL = 0/4, -$0.46 — the worst cell in the whole table sits inside the proposed preferred habitat**.
- "Fails in HIGH" is not general: 3 of 5 HIGH cells are positive; only strong_bull+HIGH is clearly negative (17T -$0.13). Fisher exact strong_bull-HIGH vs other-HIGH: **p=0.18 — not significant**.
- Plan's "Option A keeps 21 NORMAL trades (+$0.88)": actual NORMAL = 18T +$0.25. Wrong.
Confidence: HIGH

---

## 4. bb-squeeze+ filter proposals (three mutually inconsistent versions)

=== INDEPENDENT VERDICT ===
Claim: Block bb-squeeze+ in EXTREME volatility (code sample) / block strong_bull+HIGH (Option A) / require NORMAL (Option B)
Verdict: PARTIAL — and the code-sample version is **already live**
Evidence:
- The plan's **code sample blocks EXTREME** — but the data section identifies strong_bull+HIGH as the failure cell; the three options are never reconciled.
- **The EXTREME block already exists and is live**: `BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED = True` (hermes_constants.py:2883, set 2026-10-02), enforced in `decider_run.py:1704-1709`, with the identical numbers (12T 50%WR -$0.15) in the comment. Implementing the plan's code sample adds **$0.00** of new value.
- Option A (strong_bull+HIGH): improvement +$0.13 on 17T, p=0.18 — noise-level. Option B (NORMAL only): keeps 18T +$0.25, blocks 51T -$0.30, improvement +$0.30 — but keeps the 0/4 -$0.46 neutral-NORMAL cell.
Confidence: HIGH

---

## 5. mover+: "loses money in all conditions, block it"

=== INDEPENDENT VERDICT ===
Claim: mover+ loses in all conditions; disabling yields +$1.00
Verdict: PARTIAL
Evidence:
- "All conditions" is false as stated: NORMAL vol = **2T, 100% WR, +$0.15**; NO_SCORE = 6T 83.3% WR. The plan's table silently omits the NORMAL row while citing n=23 (its rows only sum to 21).
- Every BTC band is negative in dollars (-$0.12 to -$0.59) and total is -$0.89 on 23T (all-time: 23T since Sep 9 — the signal is young, not "broken for months").
- Statistically it is **not** a proven loser: t-test vs 0 p=0.36; binomial WR>50% p=0.34. With n=23 neither "loses in all conditions" nor its reversal is established.
- Blocking yields **+$0.89**, not +$1.00, and "block 23 losing trades" mislabels 13 winners as losers.
- **Already done**: `MOVER_PLUS_ENABLED = False` has been live since 2026-10-07 (hermes_constants.py:3370, brain_auditor kill), enforced in signal_schema.py:1711 and trade_watchdog.py:58. The plan re-proposes an existing state as new work.
Confidence: HIGH

---

## 6. Total impact: "+$3.64 (from -$1.17 to +$2.47)"

=== INDEPENDENT VERDICT ===
Claim: Proposed filters improve 30d PnL by +$3.64
Verdict: DISAGREE
Evidence:
- Current 30d totals reproduce exactly: pump-chain- -$0.23, bb-squeeze+ -$0.05, mover+ -$0.89 → **-$1.17** ✔
- Recomputed projection with the plan's own code-sample logic (block pump-chain- <40 fail-open; block bb-squeeze+ EXTREME; disable mover+): pump-chain- → **+$0.32**, bb-squeeze+ → **+$0.10**, mover+ → $0.00 → total **+$0.42**.
- **True improvement: +$1.59, not +$3.64** — the plan overstates by ~2.3x, and its projected endpoint (+$2.47) is wrong.
- This is a best-case static backtest on one 30d window in which the pump-chain- component has already flipped sign in the most recent two weeks (§2). Realized improvement could plausibly be negative.
Confidence: HIGH

---

## 7. Statistical and data-quality issues (plan's Risk section — verified, and worse than stated)

=== INDEPENDENT VERDICT ===
Claim: Risks are small samples, regime change, overfitting, BTC gaps (mitigated by fail-open)
Verdict: DISAGREE (mitigations insufficient)
Evidence:
- **BTC score gaps**: 40/136 = **29.4%** of pump-chain- trades have no btc_score; 159/832 (19%) overall. Coverage is **time-clustered**: week of Sep 7 = 60/215 (28%), later weeks ~99% (constants file itself notes "only available since Sep 12"). The habitat cells therefore compare "scored recent era" vs "unscored early era" — the NO_SCORE pump-chain- trades (+$0.48, 65% WR) are the best-performing group and pass the filter untouched. The gap is not missing-at-random; it's a regime.
- **Significance**: every key win-rate comparison is non-significant (p=0.18–0.29); bootstrap CI on the flagship improvement spans -$2.48 to +$3.26. With 15 mined cells from 136 trades, extreme cells (20% WR on n=5) are expected noise.
- **Multiple consumers, inconsistent semantics**: metadata btc_score (0-100, continuum-derived, written signal_schema.py:2241) is read three ways: plan uses 20/40/60/80 zones, OSCILLATOR_MULTS uses 30/70 zones (hermes_constants.py:1306), SHORT_CONTINUUM uses a single 60 cutoff on continuum.db state_score. The compactor itself sources it from two places (speed_data vs _btc_ctx_cached, signal_compactor.py:1953-1957). Calling it "reliable" (claim 5) is overstated — it is available 71-81% of the time, era-dependent, and semantically inconsistent across the codebase.
Confidence: HIGH

---

## 8. Conflict with the live SHORT_CONTINUUM filter (unaddressed by the plan)

=== INDEPENDENT VERDICT ===
Claim: (implicit) the BTC-score filter is compatible with the current system
Verdict: DISAGREE — it directly contradicts a live filter
Evidence:
- `SHORT_CONTINUUM_FILTER_ENABLED = True` (hermes_constants.py:1355) blocks **all SHORTs when BTC score > 60** (SCORE_MAX raised 40→60 by CEO 2026-10-06) unless z=STRONG_NEG — rationale: "Best SHORT state = extreme bearish (score<5). Neutral/other lose."
- The plan wants pump-chain- allowed **only when score ≥ 40**. Combined, the two filters would permit pump-chain- SHORTs only in the 40-60 band (+ STRONG_NEG exception) — **the single worst band in the data (-$0.72 / 15T)** — while jointly blocking both <40 (plan) and >60 (continuum), i.e. the +$0.56 ≥60 band and the -0.55 <40 band.
- Per this 30d window the live SHORT_CONTINUUM logic looks backwards for pump-chain- (it blocks the profitable ≥60 band and permits the bleeding ≤60 bands). Either the continuum analysis or the habitat analysis is wrong — or both are fitting noise. The plan never mentions this collision.
Confidence: HIGH

---

## 9. Implementation approach (plan §Implementation vs reality)

=== INDEPENDENT VERDICT ===
Claim: Add `check_signal_habitat()` to signal_compactor.py + constants + vol-gate overrides
Verdict: DISAGREE (as written it is buggy, incomplete, and partly redundant)
Evidence:
- **Crash bug**: `if btc_score < PUMP_CHAIN_MINUS_BTC_SCORE_MIN` raises `TypeError` on `None` in Python 3 — and 29% of pump-chain- trades have no score. The stated fail-open intent (Risk 4) is not implemented in the sample code.
- **STANDALONE_BYPASS leak**: signals on the bypass path skip signal_compactor entirely — this is precisely why the existing pump-chain/bb-squeeze blocks were duplicated into decider_run.py (comment at decider_run.py:1670). The plan targets only the compactor; its filter would leak through the same hole previous fixes had to plug.
- **Exact-match misses combos**: `signal_name == 'pump-chain-'` ignores combo trades (`pump-chain-,rs-r61`, `pump-chain-,r2-trend-short4`, etc. — 6 in window) and is inconsistent with the existing `'pump-chain' in bare_source` matching used by every neighboring block (signal_compactor.py:2890-2914).
- **Vol-gate item incoherent**: `('pump-chain-': {'BEARISH_BTC': 0.0})` — volatility_gate_v2 SIGNAL_TYPE_OVERRIDES is keyed `(vol_regime ∈ NORMAL/HIGH/EXTREME/FLAT, signal)` with substring match (volatility_gate_v2.py:292-427). 'BEARISH_BTC' is not a vol regime; the structure is wrong; it would never match. (The plan half-admits this.)
- **Redundancy**: the bb-squeeze EXTREME block and the mover+ kill are already live (§4, §5). Of the three "proposals", only the pump-chain- BTC gate is genuinely new — and it is the one with the sign-flipping weekly evidence (§2).
- **Process**: hermes_constants.py line 2 says "DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!" — the plan proposes constants edits without noting this requirement.
- Positive: the plan's Testing Strategy (shadow mode first, gradual rollout) is sound and matches repo norms. It should be the *only* part of the implementation that survives review.
Confidence: HIGH

---

## Bottom line

| Claim | Verdict | Key number |
|---|---|---|
| pump-chain- habitat by BTC zone | PARTIAL | 5/7 cells exact; 2 "strong_bull" rows unreproducible (n=18/28 claimed vs n=5/5 actual) |
| Filter 1 impact +$2.62 | DISAGREE | Actual +$0.55; blocked set 60T not 41T; 24 winners blocked |
| bb-squeeze+ NORMAL habitat | PARTIAL | Cells exact, but overall NORMAL 66.7% not 80-83%; worst cell (neutral NORMAL 0/4) is inside the habitat |
| bb-squeeze EXTREME block | PARTIAL | Already live since 2026-10-02; adds $0.00 |
| mover+ always loses | PARTIAL | All BTC bands negative, but NORMAL +2T, statistically indistinguishable from 0; already disabled 2026-10-07 |
| Total +$3.64 | DISAGREE | Actual recomputed: +$1.59 best-case, ~2.3x overstated, edge reversed in last 2 weeks |
| BTC score "reliable" | DISAGREE | 29% missing for pump-chain-, time-clustered, 3 inconsistent consumers |

**Recommendation: do NOT implement as proposed.** Before any BTC-score gate: (1) reconcile with the live SHORT_CONTINUUM filter — they currently point in opposite directions and combined they trap pump-chain- in its worst band; (2) re-run the habitat analysis on a per-week basis — the filter has been net-negative for two consecutive weeks; (3) if pursued at all, run the plan's shadow-mode phase with a `None` guard, `in`-source matching, and a decider_run.py twin, and judge it on out-of-sample weeks only.

**Context:** the sibling analysis of the same day (`brain/lessons/2026-10-08-winning-dna-failure.md`, independent-auditor DISAGREE, 3 failed attempts at mining pre-entry "winning DNA") shows this codebase is currently in a high-variance mining phase. This plan shows the same signature: many small cells, cherry-picked habitat rows, one irreproducible table, and impact math that shrinks ~2.3x under independent recomputation.

*All numbers above were recomputed directly from PostgreSQL on 2026-10-08; no figure was taken from the plan without verification. Working queries exported to /tmp/hab_trades.csv; test script /tmp/hab_stats.py.*
