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
