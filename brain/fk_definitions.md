# fk (fraction-of-winners-killed) — definitions, pinned in writing

Added 2026-10-23 by brain_auditor #86. Next action from #85: "fk-definition pinned in
writing". **The ship decision flips on which denominator you pick**, so the definition must
be chosen by the CEO before any floor/filter ships.

## The four denominators in use

| id | formula | question it answers |
|----|---------|---------------------|
| **fkA-literal** | blocked winners / **all** book winners (window) | what share of *every* win do we give up? |
| **fkA-family** | blocked winners / winners of the **same signal family** (window) | what share of this family's wins do we give up? |
| **fkA-scope** | blocked winners / winners in the **exact blocked set** (bare signal, window) | what share of the trades *at risk* win? |
| **fkB** | blocked winners / **blocked trades** (window) | how much of the blocked cohort was profitable? |

Bar (pre-registered): **fk < 20%** to ship.

## Ship-time table for CONF_FLOOR=30 BARE-ONLY (computed 2026-10-23 00:45 UTC)

Blocked set = `signal IN ('pump-chain+','pump-chain-') AND confidence < 30`.
Numbers reproduce #85 exactly: **32T, 4W, −$1.81** (net save +$1.81/14d).

| window | blocked | fkA-literal | fkA-family | fkA-scope | fkB | bar |
|--------|---------|-------------|-----------|-----------|-----|-----|
| 14d | 32T 4W −1.81 | 4/125 = **3.2%** | 4/25 = **16.0%** | 4/20 = **20.0%** | 4/32 = 12.5% | **fkA-scope = FAIL (≥20%)** |
| 30d | 32T 4W −1.81 | 4/306 = **1.3%** | 4/78 = **5.1%** | 4/67 = **6.0%** | 4/32 = 12.5% | all PASS |

Notes:
- Blocked set is **identical at 14d and 30d** — every conf<30 bare pump-chain trade in the
  last 30d happened inside the last 14d (none aged out; the cohort is recent).
- fkA-scope slid 16.7% → 19.0% → **20.0%** across #83/#85/#86 purely because bare
  pump-chain *winners* aged out of the 14d window (24 → 21 → 20) while blocked wins stayed 4.
- Pre-registration (#83): *"RECOMPUTE fkA AT SHIP TIME Oct 23; ≥20% = CEO fk-definition
  ruling before any ship."* → **trigger met at exactly 20.0% → ship HELD.**

## Decision needed from CEO

1. **Which denominator is authoritative?** fkA-literal (3.2%) and fkA-family (16.0%) pass on
   14d; fkA-scope (20.0%) fails at the boundary; 30d passes everywhere (1.3–6.0%).
2. **Which window?** 14d (what the ship was pre-registered on) vs 30d (stable, and shows the
   blocked cohort only exists in the most recent 14d).
3. Standing recommendation: pin **fkA-literal + 14d** as the headline (impact on the whole
   book = 3.2%, unambiguous), keep fkB as the sanity check (12.5%), and drop fkA-scope —
   it is unstable by construction (denominator = winners in a cohort that is itself shrinking).

Once ruled, CONF_FLOOR=30 bare-only ships the same day (numbers above are fresh).

## Recompute confirmation (run #87, 2026-10-23 01:40 UTC)

Ship-time numbers **unchanged** across 55 minutes (00:45 → 01:40): blocked set 32T / 4W /
−$1.81; fkA-literal 4/125 = **3.2%**, fkA-family 4/25 = **16.0%**, fkA-scope 4/20 =
**20.0%**, fkB 4/32 = **12.5%**. No drift into the CEO ruling — the hold verdict stands as
written above.

## Option comparison table (run #94, 2026-10-23 09:50 UTC) — three levers, one ruling

The pending fk-definition ruling now decides **three** ships instead of one. All numbers
recomputed fresh from PostgreSQL this run; `fkA-literal / fkA-family / fkA-scope / fkB`
per the definitions above (for multi-signal sets, family/scope denominators = winners of
every signal appearing in that run's blocked set).

**Blocked sets**
- **A. CONF_FLOOR bare** — `signal IN ('pump-chain+','pump-chain-') AND confidence < 30`
- **B. CONF_FILTER enforce** — `confidence < 70 OR confidence >= 95` (window `[70,95)`)
- **C. CONFIDENCE-TAIL PACKAGE (new)** — `confidence < 30` (all signals) `OR (confidence > 100 AND signal <> 'pump-chain-')`
  - upper leg scoped out because `pump-chain-` at conf>100 is 23T 12W **+0.43/30d** (positive) while the rest of conf>100 is −1.77/30d

| option | window | blocked | net save | fkA-literal | fkA-family | fkA-scope | fkB | verdict (bar <20%) |
|--------|--------|---------|----------|-------------|------------|-----------|-----|--------------------|
| A CONF_FLOOR bare | 14d | 32T 4W −1.81 | +1.81 | **3.1%** | **16.0%** | 20.0% | **12.5%** | 3/4 PASS, scope FAIL-at-bar |
| A | 30d | 32T 4W −1.81 | +1.81 | **1.3%** | **6.0%** | **6.0%** | **12.5%** | 4/4 PASS |
| B CONF_FILTER enforce | 14d | 291T 103W −4.99 | +4.99 | 81.1% | 82.4% | 82.4% | 35.4% | 0/4 PASS |
| B | 30d | 509T 203W −7.48 | +7.48 | 67.2% | 70.2% | 70.2% | 39.9% | 0/4 PASS |
| **C PACKAGE (new)** | 7d | 27T 6W | +1.50 | **11.1%** | 60.0% | 60.0% | 22.2% | 1/4 PASS |
| **C PACKAGE (new)** | 14d | 85T 18W | +3.98 | **14.2%** | 24.4% | 24.4% | 21.2% | 1/4 PASS |
| **C PACKAGE (new)** | 30d | 110T 30W | +3.85 | **9.9%** | **19.3%** | **19.3%** | 27.3% | 3/4 PASS |

Supporting tests for **C** (all pre-registered bars, computed this run):
- sample n=85 (14d) ≥ 20 **MET**
- blocked-cohort WR 21.8% vs rest-of-book 41.2% → **z = −3.26, p < 0.002 MET**
- same-sign net at 7d / 14d / 30d **MET**; fkA-literal < 20% at all three **MET**
- no existing global conf gate duplicates it (CONF_FILTER not enforce-flipped; per-signal
  `MIN_CONFIDENCE` values are emit floors, not exec blocks) **MET**
- winner impact 18/127 = 14.2% < 20% **MET**
- single threshold pair, no compound change **MET**
- confounder flagged: conf>100 leg has **n=0 in 7d** (dormant) and conf<30 has 51T at both
  14d and 30d (cohort entirely inside the recent window) → **C's live value today is
  essentially the conf<30 leg**; the upper leg is a cheap dormant add-on, not current PnL

**Why this matters for the ruling:** under the standing recommendation already written
above (**fkA-literal + 14d**), option C ships and **dominates A** (14.2% vs 3.1% fk, both
pass; +3.98 vs +1.81 = 2.1× the save) while capturing ~80% of B's net at ~18% of B's fk
cost. Under fkB or fkA-family at 14d, **C FAILS and only A survives**. So the definition
choice now has a materially different consequence than it did on Oct 23 00:45 — the CEO
should rule with this table in view.

**Not shipped this run** (vacation_mode.json `no_constants_change` still true, 8th
consecutive run) — C is pre-registered, ships same-day as A once (a) the fk definition is
pinned and (b) the vacation file is cleared. Ship-time requirement for C, mirroring A's:
pin the gate column to RAW `trades.confidence` and self-check the blocked count equals 85
at 14d.

## Ship-time recompute (run #104, 2026-10-23 19:45 UTC) — **SECOND definition now trips**

Blocked set drifted **32T/4W/−$1.81 → 33T/4W/−$1.88** (GRASS #16369 conf 29.50, closed 15:13, entered the window). Bare pump-chain *winners* in the 14d window dropped 20 → 19.

| window | blocked | fkA-literal | fkA-family | fkA-scope | fkB | bar |
|--------|---------|-------------|------------|-----------|-----|-----|
| 14d | 33T 4W −1.88 | 4/128 = **3.1% PASS** | 4/19 = **21.1% FAIL** | 4/19 = **21.1% FAIL** | 4/33 = **12.1% PASS** | **2 of 4 now FAIL (was 1)** |
| 30d | 33T 4W −1.88 | 4/301 = **1.3% PASS** | 4/65 = **6.2% PASS** | 4/65 = **6.2% PASS** | 4/33 = **12.1% PASS** | all PASS |

Drift trajectory of fkA-scope across #83 → #104: 16.7% → 19.0% → 20.0% → **21.1%** — monotonic, driven purely by bare pump-chain winners aging out (24 → 21 → 20 → 19) while blocked wins stay at 4. It will keep rising.

**Verdict unchanged but strengthened:** still HELD on the CEO fk-definition ruling. Under the standing recommendation (**fkA-literal + 14d**) it still passes at 3.1% with a +$1.88/14d save. Under fkA-family or fkA-scope on 14d it now fails outright. Do not ship without an explicit ruling — the boundary case is gone, this is now a real disagreement between definitions.

**Also added this run (run #104 creative): CONF_FILTER-enforce (option B) is structurally fk-infeasible.** [70,95) covers only 54/349 = 15% of the 14d book, so "block outside" blocks 84% of trades by construction: fkA-literal 56.2% (14d) / 67.7% (30d). Both legs fail independently (leg_lo save +4.50 fk 56.2%; leg_hi save +0.81 fk 24.2% at 14d). Floor frontier: 14d last fk-passing floor = conf<45 (+2.07, 15.6%) and it is **dominated** by conf<30 (+2.14, 10.2%, 7 fewer winners killed) → CONF_FLOOR=30 is the efficient point on 14d; 30d conf<55 passes (18.0%) but fails 14d (41.4%) → window disagreement, no ship. in-window [70,95) is the keep-set at every window (+0.13 / +0.95 / +2.44) so the window is right, the enforcement scope is not. **Recommendation: rule on A and C only; drop B from the net-vs-fk framing.**

---

## ⚠️ CONFIDENCE FIELD SEMANTICS — which column the fk table is actually measured on
**(added run #146, 2026-10-25 19:5x UTC — blocks a structural no-op, zero code)**

`confidence` in every fk table on this page is **`trades.confidence`**, which is the
**post-penalty** value. It is NOT the value the `MIN_EXEC_CONFIDENCE` gate sees.

| field | meaning | where set |
|-------|---------|-----------|
| `_signal_metadata.final_confidence` | **gate-time** confidence (what `:3796` compares to `MIN_EXEC_CONFIDENCE`) | signal_compactor / hotset, pre-decider reductions |
| `trades.confidence` | **post-penalty exec** confidence — the fk table's column | brain.py `record_trade`, after `execute_trade()` |

Three reductions run **after** the gate (decider_run.py, `run()`):
`:4308` WRONG_SIDE_PENALTY (−10) · `:4811` CTX-GATE WARN (−20 typical, 760 log lines) ·
`:4856` LOSERS_CONF_PENALTY (−50).

**Measured (14d, n=294):** 58/58 trades stored below 40 were **≥40 at the gate**
(LEAK = every sub-40 stored trade); avg divergence **+18.18**.
**Measured (30d, n=649):** gate-time `conf<30` = **0**, stored `conf<30` = **56**.

### Consequence for the pending CONF_FLOOR ruling
Implementing `if confidence < 30: block` **at `:3796`** would block **0 of the 56**
trades every fk number on this page was computed on → **structural no-op**, the same
class as the #129 size-dampen no-op. Enforcement must sit **after `:4856`** (or gate on
`trades.confidence` semantics explicitly), and ship-time self-check must assert
`blocked_count == 56 @30d / == 33 @14d`, not just "the floor constant exists".

### Scale drift (same finding, second axis)
`_signal_metadata.final_confidence` p50 moved **95.0 → 51.8** across the CONF-CALIB clamp
(2026-10-15 03:41), with gate-time `<50` share moving **12.5% → 49.4%**. Drivers: cell_stats
`_cell_mult` wiring (2026-10-14) + the clamp. Any confidence-keyed constant calibrated
before 2026-10-14 is on the old scale.

Reproduce: `python3 brain/analysis/conf_field_semantics_2026-10-25.py --selfcheck`
