# CEO DECISION BRIEF — Shadow Redundancy Deep Dive v2 (corrected, external-audit ready)

Requested by T. Package: `analysis/2026-10-30_shadow-redundancy-deepdive.md` (v2, correction ledger included), engine `analysis/shadow_redundancy_deepdive_v2_2026-10-30.py`, raw `.out`, `analysis/exports/v2_*.tsv` (59,436 enriched events). Verification trail: v1 (7262794c) → own-conclusions verdict `brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md` (5ed3bcf8, ruled v1 NOT fit for external hand-off) → v2 corrections (0b02f4d5). 0 config changes at any stage.

## What the corrected 26-day shadow analysis found (Oct 4–30, cluster-robust standards)

1. **Cluster-robust WORKERS (2):** PUMP-CHAIN-RSI-MAX (n=1,087 eps, ex4h −0.136%, p_tok=0.011 p_day=0.040, solo 76%, OOS same-sign −0.085/−0.224) and **PUMP-CHAIN-VEL post-deadband** (n=144, −0.549%, p_day=0.015). The Oct-14 deadband (PUMP_CHAIN_VEL_30M_MIN=−0.3, your D4 of the Oct-12 package) SELF-VALIDATED: remaining blocks are genuine decliners and they underperform market strongly.
2. **Zero demonstrated harmful gates.** v1's SLOPE-FILTER "3rd replication" was pseudo-replication (token/day-clustered t-tests ns: p=0.20–0.30); now a monitor-only harm CANDIDATE along with OVERSOLD-SHORT (+0.152%, OOS-stable but cluster-ns).
3. **Three FULLY REDUNDANT gates:** CONTINUUM-BLOCK (1,984 eps, solo 13%), CONTINUUM-BULL (1,650, solo 17%), PRESERVE-SPIKE-BLOCK (271, solo 19%) — no economic edge (|ex4h|<0.05%) AND another gate almost always blocks the same token+direction anyway. Removal predicted ≈ zero flow change.
4. **26 NO-EDGE gates** incl. every volume giant (CONFLUENCE-GATE-BLOCK n=4,120 −0.040%; SHORT-CONTINUUM 1,962; SHORT-RSI-HARD-FLOOR 1,625 −0.012%; CTX-GATE 1,451) and LONG-NEUTRAL-CHOP (1,200, +0.014% — the patch-spiral gate remains a wash).
5. **Confluence-expired SINGLES are exactly zero** (80-89 band −0.0003%, n=11,944; 90+ +0.085%): the confluence wall neither costs nor protects on singles; its multi-source blocks skew negative. D3's question remains answered NO.
6. **BTC-CHOP-GATE non-replication stands** (+0.133%, positive both halves).
7. **Provenance gaps found by the auditor and fixed in v2:** recorder DB capture was only 33–43% for SHORT-RSI-HARD-FLOOR/SPIKE-FILTER/LONG-RSI-BLOCK/LONG-MIDBAND before the Oct-22 regex fix; Oct 11–12 outage (~4,500 events) recovered via full-log reparse; **pipeline.log archives were deleted, so Oct 4–10 (12,483 db-only events) is permanently unverifiable against raw logs.**
8. **t5_shadow unusable for verdicts:** 2.3% closure coverage AND join-selected (only signals that became live trades).
9. **R1 extended closer NOT built** — gate_shadow still closes via the weak follow-on-trade join (52% sign agreement with the audited engine; CI [0.48,0.57], 489 distinct trades). Dollar-denominated gate decisions remain impossible until it ships.
10. v2 did not re-run dollarization (v1's −$67/26d refused-opportunity was auditor-AGREEd in order of magnitude; flagged in report §6).

## Decisions requested (reply GO/NAY + reasoning per item)

D1. **Ratify the Nov 6 removal-test queue:** CONTINUUM-BLOCK, CONTINUUM-BULL, PRESERVE-SPIKE-BLOCK — priority candidates for removal at the re-audit (26d cluster-robust evidence of redundancy; predicted flow change ≈ zero). Alternatively approve an EARLIER shadow-first removal pilot: disable in shadow only (log would-blocks, let signals through to the weak closer) for 14d. No live loosening either way before your sign-off.

D2. **Record the deadband validation** in the R2 gate registry: PUMP-CHAIN-VEL deadband (Oct 14) = validated reform, evidence = this v2 package (p_day=0.015, OOS-stable). Registry entry only; no action.

D3. **Confirm monitor-only status** for the two cluster-ns harm candidates (SLOPE-FILTER +0.342% p_w=0.0003 but p_tok=0.30; OVERSOLD-SHORT +0.152% OOS-stable +0.171/+0.141) — no gate change before Nov 6; they graduate to the re-audit with 40+ days of data.

D4. **Retention + observability policy:** (a) restore durable retention for pipeline.log archives (current rotation deletes them; the Oct 4–10 tail is now permanently unverifiable — external auditors cannot check it); (b) add a health metric for gate_shadow capture rate (DB rows vs log lines, alert if <90% over 24h) so recorder gaps are never silent again (Oct-10 rotation bug + pre-Oct-22 regex both went unnoticed for days).

D5. **t5_shadow disposition:** retire the stream, or redesign its closure under the R1 extended closer when that ships? (Recommendation: retire the would_pnl join, keep the decision log for signal-side analysis only.)

D6. **Confirm external hand-off:** v2 package (report + engine + .out + v2_*.tsv + own-conclusions verdict) goes to the external auditor as-is; the correction ledger in the report documents every v1→v2 delta.

## Constraints honored
hermes_constants.py untouched by this work; CEO_PROTECTED_FLAGS intact; all claims cluster-tested per the Oct-9 claim-hygiene standard (D3 of the gate-conundrum package); the Nov-6 decision gate stands unless you rule otherwise in D1.
