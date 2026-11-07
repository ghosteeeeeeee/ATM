# BRIEF: Bear-single-source ENFORCE flip — bar met early, concentration caveat (2026-11-06)

## Context (trust — from join run `shadow_tag_join.py` 2026-11-06T22:45:05Z, independent re-derivation PASS)
Your ruling (mover-census verdict 20261106T215910Z): "ship join builder early so the 11-10
bear-single-source flip can be read on data instead of defaulting to stay-blocked." Builder
shipped 11-06 (`14b1eeeb`/`20726e88`, selfcheck 29/29, ZERO trading-path files). The read is in:

**BEAR-SINGLE-SOURCE-SHADOW — registry bar: n≥20 token-days, WR≥55%, net≥+$1.00**
| limb | need | have | |
|---|---|---|---|
| n joinable (token-day dedup) | 20 | **34** | ✅ |
| WR of would-have-won | 55% | **79.4%** | ✅ |
| net @ $13.44, 0.09% RT fee | +$1.00 | **+$7.18** | ✅ |
→ **BAR MET on all three limbs, 4 days before its 11-10 date.**

**The caveat (why this consult exists):** day concentration — per-day net: 11-03 −0.66,
11-04 +0.07, **11-05 +7.90**, 11-06 −0.13. 29 of 34 token-days and the entire net land on
**11-05** (the post-crash bounce day). Breadth is real (30 distinct tokens, fwd range −5.15..+6.11,
median +1.93; LOO-by-token min +6.37) but the dollar edge is one episode — the exact
one-window class that killed the compaction-stale false positive (12h +$10.80 → 7d −$31.55).
Rate: 8.5 token-days/day → n ≈ 60+ by the scheduled 11-10 read with 4 more days of diversity.

**Other tags from the same run (for completeness):** SHORT-REGIME-EXEMPT bar NOT met (net −0.83,
1/3 positive days) · FLIP1-OVERRIDE NOT met (net −1.65, LOO −2.46) · VOLGATE/MAXXED n=0 —
and their darkness is now root-caused: VOLGATE = all 499 vol-gate blocks in 4d were LONG while
the shadow is SHORT-gated (arithmetic, premise refuted); MAXXED =20 SHORT blocks but the
regime read at probe time was LONG_BIAS (needs historical replay before 11-17).

## Question
1. **FLIP NOW** (`BEAR_SINGLE_SOURCE_SHORT_ENFORCE=True`, signal_compactor ~:3769-3790;
   revert = False) — literal pre-registered bar met, speed mandate, admission thesis? OR
2. **WAIT to 11-10** as scheduled — let the sample double (n≈60, ~5 more days) so the
   one-day concentration resolves before live? OR
3. **Modified now:** flip with a tripwire (e.g. re-evaluate at 11-10; if the post-flip
   realized fills contradict the counterfactual — net <0 over the first N — revert automatically
   with a pre-registered limb)?
State the ruling, the exact flag change, the tripwire (if any), and the registry text to write.
This is the ONE admission relaxation your mover-census verdict already authorized
("the one layer to give") — the only open question is WHEN, given the concentration.
