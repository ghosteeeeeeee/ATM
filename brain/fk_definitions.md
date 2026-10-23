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
