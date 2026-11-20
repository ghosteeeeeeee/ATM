# === INDEPENDENT VERDICT — retest-fade HARNESS (2026-11-20) ===

**Auditor:** agent-3 (own-conclusions, fresh eyes; no trust in prior analyses — every
number below re-derived from candles.db by my own scripts)
**Targets:** plan `plans/2026-11-20_retest-fade-system-plan.md` (§7 treated as claims),
evidence `plans/2026-11-20_retest-fade-harness-output.txt`, code
`scripts/backtest_retest_fade.py`, prior verdict `1795152254-...own-conclusions.md`
**My scripts:** `/tmp/audit_main.py` (H1 re-derivation, engine re-implementation,
economics, concentration, limit-sensitivity), `/tmp/audit2.py` (gate swap vs shipped
`structure_json`, H1 base-rate controls, top-k concentration), pinned data snapshot
`/tmp/snap15m.pkl` (8640 × 15m bars, 2026-08-22 07:00 → 2026-11-20 06:45)

**Re-run status:** first harness re-run reproduced the committed output
**byte-identically**. Then I discovered `candles_15m` is a **rolling 90-day window
(8640 bars, front bars drop as new ones append)** — min-ts slid from 08-22 04:45 to
08-22 07:00 within minutes. On the slid window: **65/99 output lines differ, max cell
drift 42.4pp (H3 GATED SHORT0.4FIXED col1 +546.4 → +504.0), but 0 sign flips in all
64 cells, H1 table identical, claim-5 violation count identical (17/32)**. All my
analysis below is pinned to one snapshot so it is internally consistent.

---

## Claim 1 — H1 "retest-of-broken-support within 24h = 70% (103/147) supports no-straight-slices"
**Verdict: PARTIAL (number reproduces exactly; interpretation weak)**
**Evidence:** my own-code H1 re-derivation on the snapshot: **103/147 = 70% ✓ exact**,
bucket table also exact (1-touch n=62 med24h +0.86%, 2 n=23 +0.97%, 3+ n=62 +0.64%).
Selection concerns tested and **do not bite**: 148 clusters, **147 eventually closed
below thr, 0 clusters broke only during non-trend bars (nothing skipped), 1 never
broke**; 6 breaks have truncated 24h windows. But:
- **Definition-sensitive:** retest = high ≥ anchor×(1−ZONE) → 70%; high ≥ anchor →
  **58%**; high ≥ anchor×(1−BROKEN) → 77%; high ≥ break-thr → 84%. Horizon curve:
  4h 54% → 12h 66% → 24h 70% → 48h 78% → 96h 80%.
- **Base-rate control kills the S/R-specific reading:** after ANY generic 0.5% red
  bar (no level involved), P(≥0.2% bounce within 24h) = **111/123 = 90%** — *higher*
  than the 70% support-retest rate. Coming back to a broken level within 24h is what
  price does anyway; supports actually retest LESS than generic bars bounce.
- Break sample itself is well spread (147 breaks / 48 half-days; top-3 half-days = 15%).
**Confidence: HIGH** on numbers, **HIGH** that "no straight slices" as EVIDENCE is
base-rate-inert as computed.
**Notes:** break-vs-retest anchors are inconsistent in the code (break vs `c["lo"]`,
retest vs `c["anchor"]`) — worth pinning. Header says "confirmed 1h-down proxy" but
the gate is 15m EMA80/320 — label wrong, not numbers.

## Claim 2 — hammered (3+) supports do NOT break more majorly (med24h 0.64% vs 0.86%;
## P(≤−2%) 8% vs 19%) — thesis "eventually breaks majorly" NOT supported
**Verdict: AGREE (with power caveat — and the data if anything leans the other way)**
**Evidence:** all three cells reproduce exactly (0.64/0.86, 8%/19%, n=62/62).
Crash-tail test: 1-touch 12/62 vs 3+ 5/62 ≤−2% — Fisher one-sided
**P(3+ ≥ 1-touch major-break rate) = 0.983** (no support for the thesis);
the reverse direction P = **0.058** (3+ if anything breaks *less* majorly, borderline).
Median-difference permutation p = 0.62 (not significant). Deeper: **median 24h
displacement after a confirmed-downtrend support break is POSITIVE in every bucket**
(+0.64 to +0.97%) — breaks bounce at the median; P(≤−2%) is 8–19% in all buckets.
So "usually in a major way" is not merely unsupported — it is contradicted at the
median by this detector. Confidence: **HIGH** on reproduction, **MEDIUM** on the
3+vs1 difference itself (n=62/62, underpowered to detect <~15pp differences).
**Notes:** claim's own numbers are honest; the CEO thesis line should be recorded
as TESTED-AND-NOT-SUPPORTED by H1.

## Claim 3 — H3 GATED: every col4 negative (−56..−150) while col1/col2 strongly
## positive (+214..+546) → touch-fade short edge does not clear costs/serialization
**Verdict: PARTIAL (signs exactly right; quoted col1/col2 range wrong; cost model
is decisive but NOT the whole story — concentration and exit model are bigger)**
**Evidence (snapshot):** col4 = −77.5 / −150.0 / −56.5 / −131.0 ✓ all negative,
range matches "−56 to −150" ✓. col1/col2 all positive ✓ but the actual range is
**+139.4 to +546.4** (col2 TRAIL0.8 = +139.4; there is no +214 lower bound).
Per-episode gross edges (col3, price%/RT): **FIXED 0.4% +0.109%, FIXED 0.8% +0.116%,
TRAIL 0.4% +0.007%, TRAIL 0.8% −0.001%**. Breakeven **total RT cost = 10.9bps**
→ **breakeven slip = +1.9bps over the 9bps taker fees**; at fees-only the row is
**+18% margin sum instead of −75.7%**; at a maker-assisted ~6bps RT (entry IS a
resting limit at the zone edge; TP is a limit) → **≈ +46%**. So col3→col4 sign is
literally 100% the 0.19% cost assumption — but the gross itself is thin (11bps),
**73% concentrated in the top-3 half-days** (top episode = 44% of net), longest
same-outcome run = 11. And the **TRAIL rows (the shipped-exit proxy) are ≈0 gross
(+5.6 / −5.8) — no cost model rescues them** (F-1 TP-suppression re-verified live at
`position_manager.py:655 hit = None` for managed+structure_governed).
**Confidence: HIGH.**

## Claim 4 — H2 bounce-longs: gated col3/col4 all negative → not viable net
**Verdict: AGREE (conclusion holds; but the harness does not test what its label says)**
**Evidence:** gated col3 = −61.6/−185.4/−86.3/−190.3, col4 = −261.1/−411.5/−242.1/−363.2
— all negative ✓. Long gated gross is **negative BEFORE costs** (−0.059%/ep, FIXED 0.4)
→ dead at any cost, not a cost artifact. **Finding:** H2's header says "at hammered
support" but `h2_h3` receives `cls` (clusters) and **never uses it** — episodes are at
ALL swing-lows. I tested the label's actual claim (3+-touch clusters only): col3
n=31 **+12.4 gross, col4 −46.5 net** — still net-negative, conclusion unchanged,
but n collapses to 31. Confidence: **HIGH**.

## Claim 5 — gated < ungated in EVERY row (gate as specified removes profit,
## consistent with prior audit)
**Verdict: DISAGREE as stated (17 of 32 rows violate); right for fade-shorts gross only**
**Evidence:** violations of "gated < ungated": **17/32** (same count on the committed
parse and on my snapshot). Breakdown: **H3 col1-col3: gated < ungated in 12/12 ✓**
(the prior audit's FADE warning holds for gross rows: gate removes +718pp queued /
+52pp flat from the short side). But **H2: 14/16 rows gated > ungated** (the gate
*improves* longs almost everywhere — it removes losing longs) and **H3 col4: 3/4
rows gated > ungated** (gated less negative because ungated pays 1.9 margin/episode
on more episodes — the gate reduces cost drag). Confidence: **HIGH**.
**Notes:** plan §7 should restate claim 5 as "gate removes fade-short GROSS profit
(12/12) but improves longs (14/16) and slightly improves net shorts (3/4)".

## Claim 6 — self-caught bugs (SHORT touch-search, TRAIL pre-entry ratchet,
## gate-not-applied) fixed pre-commit; committed code/output reflect the fixes
**Verdict: AGREE**
**Evidence:** commit `315e576d` message documents all three as caught pre-report and
states "the committed output is post-fix". Code inspection of the committed file
(clean worktree for that path):
- SHORT touch-search: `run_h` L173 `rows[i][2] >= lval*(1−ZONE)` searches swing-HIGHS,
  starts after the swing bar — correct fade geometry ✓.
- TRAIL pre-entry ratchet: L209/L218 `ti <= sj and sj + CONFIRM_DELAY <= i` — only
  post-entry, already-confirmed swings ratchet; no lookahead, no pre-entry pin ✓.
- Gate applied: L180-181 `if require_trend and not trend[touch]: continue`; in the
  output **gated n < ungated n in all 32 rows** (a not-applied gate would show equality) ✓.
- Sign/behavioral checks: run_h re-implementation in my scripts reproduces printed
  col3 sums to ±0.1 (engine independently verified).
Confidence: **HIGH**.

---

## Standalone adversarial findings (not claims, but they matter)

1. **The GATE measured is not the gate specified.** Spec §3.4 = shipped 1h+4h
   `structure_detail` states; harness uses 15m EMA80/EMA320. Agreement at the 1,443
   decision times (auto_trader.db `structure_json`, 2026-10-22 → 11-20): **373/1443 =
   26%** (confusion: EMA-down & not-shipped-down = 1,052 bars). EMA down-share 84% vs
   shipped 1h+4h-AND-down share 13% — **the harness gate is ~6× more permissive**.
   Gate swap on the SAME covered episodes (155 shorts, 0.4% FIXED, flat, gross):
   EMA n=52 +155.5 | shipped-AND n=13 +55.0 | shipped-OR n=44 +101.6
   (net at 0.19%: +56.7 / +30.3 / +18.0). A shipped-state gate behaves differently —
   it admits ~1/4 as many trades — so "GATED" rows are not counterfactuals of what
   would ship. (Also: the covered 30-day window nets **+56.7** vs full-window
   **−75.7** → the positive gross lives entirely in the recent slide = G1 regime risk.)
2. **col2→col3 drop = serialization alone, NOT the walk limit.** Same limit on both
   cols (576 bars). Attribution run: SHORT0.4FIXED queued +356.9 (n=244) → flat
   +102.9 (n=94) = **29% retained; 61% of episodes dropped as overlapping**. Limit
   sensitivity (detector untouched): **3-day ≡ 6-day IDENTICAL** (every row, n and
   sums); 2-day differs trivially (+97.0 vs +102.9, n=95). The 6-day limit is not a
   factor; flat-only serialization is the whole col2→col3 drop — consistent with the
   prior audit's execution-model finding, which ranks FIRST.
3. **Episode independence is the biggest unaddressed statistical problem:** col3
   gross +102.9% where **top-3 half-days = +75.0 (73%)**, top-3 episodes = +45 (44%),
   longest same-outcome run = 11; col2 top-3 half-days = 59%. Effective independent
   units ≈ 1–2 trend phases, not 94 episodes. Every headline sum should be read as
   one-episode-block CIs (prior audit's should-have, still open).
4. **Reproducibility requires a pinned window.** Live harness re-run reproduced
   byte-identically at one moment; after the 90-day roll, 65/99 lines drift (max
   42.4pp on lookahead col1; 0 sign flips; H1 identical). For v0.6: print the data
   window (first/last ts + row count) in the header and archive a snapshot, or the
   tables can never be re-verified exactly.
5. **Cost-model summary (breakeven per RT, snapshot):** gated shorts FIXED ≈ 10.9–11.6bps
   total-cost breakeven (≈ +2bps slip over taker fees) — the 19bps assumption flips
   them; TRAIL shorts breakeven is ~0 (dead at fees); longs are gross-negative
   (dead at anything). The chosen 0.19% is defensible-taker, but sign hangs on
   ±2bps; the standing resting-orders/fill-quality round decides it.

---

## DOES THE DATA BACK THE STRATEGY?
**NOT YET — proceed to shadow-mode only after one spec revision.**

Why not YES: after realism (confirmable levels + one-position serialization +
shipped-exit proxy + costs) the *only* cell family with real gross is
**FIXED-TP fade-shorts** (+84…+103 gross, 11bps/ep, 73% from 3 half-days), and the
FIXED exit does not exist in production for managed trades (F-1 re-verified:
`hit = None` suppresses the TP — the shipped TRAIL proxy makes ≈0 gross on the same
episodes). Bounce-longs are gross-negative (thesis long side dead). The gate tested
is not the shipped gate (26% agreement). And "no straight slices" at 70% is
base-rate-inert (generic bounce control 90%).

Why not NO: the short-side diagnosis is honest and reproducible; flat/gated
FIXED-shorts are positive gross in every configuration; the trend-gate direction for
shorts behaves as the prior audit predicted; the harness fixed exactly the defects
it claimed (claim 6 all AGREE). The thesis's "eventual major break" is refuted, but
the *fade-the-failed-retest* half of the thesis survives — shorts-first, as mandated.

Shadow-mode (entries OFF, counterfactuals logged) is only worth running on the
REVISED spec: shipped-state gate + a decided exit model + a stated fill model —
otherwise the counterfactuals answer a question no shipped system will ask.

## GAPS RANKED (for v0.6)
**BLOCKER**
1. **D1 exit model unresolved — now data-driven:** same episodes, same detector:
   FIXED gated flat shorts +84…+103 gross vs TRAIL **+5.6/−5.8 ≈ 0 gross**. Decide
   (CEO + bug_hunter): carve a fade-target out of `structure_governed` (touches F-1,
   still open) or accept that under shipped exits there is no edge to ship. Nothing
   else matters until this is answered.
2. **Ship-gate validity:** re-run all GATED rows with actual `structure_json`
   1h/4h states (AND as spec'd; OR as sensitivity) — 26% agreement / 84% vs 13%
   down-share means the current GATED rows are not the shipped counterfactual.
3. **Episode independence:** block-based (half-day/phase) CIs on every table; top-3
   half-days = 73% of the headline edge — n=94 is not 94 trials.
4. **Fill model in the cost column:** breakeven slip +2bps; resting-limit entry
   (the entry already IS a zone-edge limit) + limit TP would model ~6bps RT and flips
   every FIXED short row positive — but only if D1 says FIXED. This is exactly the
   standing resting-orders round.
**SHOULD**
5. Pin the data window in the harness header (rolling 90d drift: 65/99 lines, max 42pp).
6. Retest claim: report with the generic-bounce control and the definition range
   (58–84%); stop presenting 70% as S/R-specific.
7. Fix claim 5 (17/32 false) and claim 3's range (+139…+546) in plan §7.
8. H2 label/code mismatch: `cls` unused in `h2_h3` — either gate episodes to
   hammered clusters (my run: n=31, +12.4 gross / −46.5 net) or retitle the section.
9. Drop bounce-longs from v0.6 scope (gross-negative before costs; shorts-first).
10. F-9: any fade armer must flock `pending_orders.json`; reach-gap (prior claim 16)
    still needs its new rule — both remain open standing constraints (not re-verified
    this round; F-1 code re-verified live).
**NICE**
11. Pin break/retest anchors consistently (break uses `lo`, retest uses `anchor`);
    6 truncated retest windows; count "retest then resume down" splits.
12. Correct the H1 header ("1h-down proxy" = 15m EMA80/320); delete the duplicated
    identical cost branch in `run_h` (dead code, harmless).

## THE ONE CHANGE
**Resolve D1 — put the fade edge through the real exit path (carve-out vs
re-run-through-structure-governed) — before touching anything else.** It moves gross
by ~100pp (+103 → +5.6), ~20× the cost model's swing (~+122pp on the net but only if
FIXED survives) and 100× the walk-horizon lever (≈0pp). **Conditional on D1 =
FIXED carve-out, the best of your five candidates is the resting-limit fill model in
the cost column** (breakeven slip +2bps; ~6bps RT → every gated FIXED short row nets
positive). Shipped-state gate is the best *honesty* fix (must happen for shadow
validity but reduces n rather than creating edge); shorter horizon is a non-factor
(3d≡6d); selective-quality entries are untestable on a sample whose 73% comes from
3 half-days; dropping the new-entry strategy for ladder re-cross-wait entries is the
right fallback **only if D1 goes against the carve-out** — then the shipped exits
kill this edge and the ladder path inherits the infrastructure that already works.
