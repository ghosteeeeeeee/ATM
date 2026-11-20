# Gate Registry — Hermes Hard-Veto Gates

**Source of truth:** CEO D2 (2026-10-12, gate-conundrum package, ALL GO).
**Policy:** New gates ship **shadow-first 14d** before hard-veto status (grade upgrades trade-level → counterfactual → shadow → live).
**Claim hygiene:** see brain/SOPs.md §10 — episode counts, first-seen dates, null-model check, direction-signed counterfactual required for any gate proposal.
**Maintained by:** upgrade implementer / signal analyst on every gate add/change. Update this file in the same commit as the gate.

## Columns

| Column | Meaning |
|--------|---------|
| Gate | Log tag / constant family |
| First seen | Date gate first observed live (or code first-seen if log unavailable) |
| Evidence grade | trade-level / counterfactual / shadow / live-n |
| n / effect | Sample and dollar or WR effect when known |
| Last verified | Date of last independent check |
| Notes | Scope, overrides, revert triggers |

## Active hard-veto / hard-block gates

| Gate | First seen | Evidence grade | n / effect | Last verified | Notes |
|------|------------|----------------|------------|---------------|-------|
| SHORT-CONTINUUM (BTC score > MAX sustained) | pre-2026-10-05 | live-n | 22,018 block lines / 1,646 eps (2wk, Oct 12 audit) | 2026-11-20 | Real #1 blocker by volume; hysteresis HYSTERESIS_MIN=30 wired (sustained-only block). Phase-2 demotion candidate (gate-conundrum). Re-measured NO-EDGE at 46d (n=1,093, ex4h +0.002) — see ratified classifications below |
| CONTINUUM-BULL | 2026-10-05 21:23 | live-n | 3.1k lines / 6d (D4 census) | 2026-11-20 | Blocks LONG when BTC continuum not bullish enough; young-gate retro entry per CEO D2. Re-measured NO-EDGE at 46d (n=2,362, ex4h −0.033) — shadow-first removal SHIPPED per CEO D2 GO(a) 2026-11-20 (see Nov 6 queue) |
| LONG-NEUTRAL-CHOP | 2026-10-11 04:15 | live-n (blocked-cohort unmeasured at ship) | — | 2026-11-20 | **Attacks best cohort** (chop-LONG +$3.28 / WR 53.7%). R1 shadow first-target. Remove Nov 6 if blocked cohort wins. Re-measured NO-EDGE at 46d (n=1,915, ex4h +0.059 — still a wash) |
| SHORT-RSI-HARD-FLOOR | 2026-10-12 00:33 (v1); value history: 45→35 (CEO 10-13) → **45 reverted 10-18** | trade-level | chop&lt;45: WR 36% −$4.56 (30d); trend side ≈ neutral | 2026-11-20 | **Stays for chop** (D6). Re-measured NO-EDGE at 46d (n=2,194, ex4h −0.005). PUMP_CHAIN sub-floor also 45 (reverted 10-21). Bear-structure relax = proposal only |
| PENALTY-BLOCK | 2026-10-06 | trade-level | 1.2k lines / 6d | 2026-10-09 | Penalty-gated execution fix; live in decider_run |
| PUMP-CHAIN-VEL (deadband −0.3%) | filter pre-Aug; deadband 2026-10-12 (D4) | shadow (validated reform) | POST-DEADBAND n=144 eps, ex4h −0.549%, p_day=0.015, OOS-stable (v2 deep dive) | 2026-11-20 | **Deadband self-validated** (CEO D2, 2026-10-30): remaining blocks are genuine decliners that underperform market strongly. Evidence: analysis/2026-10-30_shadow-redundancy-deepdive.md. Re-measured at 46d (n=164, ex4h −0.347, p_day=0.045) — probable worker, see ratified classifications |
| CONFLUENCE-GATE | long-standing | shadow | conf 80-89 ex4h −0.27% n=301 (expiry_shadow early) | 2026-11-20 | Highest-frequency block (~473/6h). Do NOT weaken (only gate proven helping per shadow-registry header). **Appended 2026-11-20 (CEO D4):** the Nov-19 46-day study re-measured CONFLUENCE-GATE-BLOCK as NO-EDGE (n=3,436, ex4h −0.063, p_tok 0.019 / p_day 0.045, neither clears Bonferroni; \|excess\|<0.10%) — old helping note kept as history, new evidence appended not deleted |
| BTC-CHOP-GATE | ~2026-10-04 (metric redefined 30m→5m slope) | counterfactual | 14 lines / 6h (D4) | 2026-11-20 | Threshold 0.05 (post b5006cd8 ratify). Re-measured NO-EDGE at 46d (n=869, ex4h +0.047 — non-replication holds) |
| HALL-SHAME (30d WR floor) | long-standing | trade-level | — | 2026-10-12 | Momentum exemption = proposal only (signal-starvation P1), not shipped |
| SHORT-NEUTRAL | long-standing | live-n | 74 events (post F1 capture) | 2026-10-04 | — |

## Young-gate watchlist (shadow-first clock)

Per CEO D2: any gate added after 2026-10-12 must accrue **14d shadow** before trusted as hard veto. On ship, add a row here with ship date; flip Evidence grade only after 14d review.

| Gate | Ship date | Shadow review due | Status |
|------|-----------|-------------------|--------|
| pump-chain+ LONG HIGH block | 2026-10-21 03:38 | 2026-11-04 | Collecting (commit c9092aea — committed 2026-10-21 03:37:59 UTC; registry had wrong day, fixed brain_auditor #76) |
| CHASE_RATIO_SHADOW (comment corrected 14d/Oct 27) | pre-2026-10-12 | 2026-10-27 | True, thresholds unchanged |

## Nov 6 removal-test queue (ratified 2026-10-30, CEO deep run 20261030T202502Z)

26d cluster-robust evidence (v2 shadow redundancy deep dive, analysis/2026-10-30_shadow-redundancy-deepdive.md): no economic edge AND another gate almost always blocks the same token+direction anyway. Removal predicted ≈ zero flow change. **No removal ships before the Nov 6 re-audit + CEO sign-off.**

| Gate | eps (26d) | solo10 | ex4h | Note | Disposition (2026-11-20) |
|------|-----------|--------|------|------|---------------------------|
| CONTINUUM-BLOCK | 1,984 | 13% | −0.043 | Fully redundant; robustly low solo across ±5/±10/±15min | **CEO D2 GO(a) 2026-11-20, shadow-first removal SHIPPED** (signal_compactor standalone-bypass leg; 📊 WOULD-BLOCK logs; review 2026-12-04; revert if admitted cohort underperforms). 46d study: NO-EDGE, n=2,831, ex4h +0.016 |
| CONTINUUM-BULL | 1,650 | 17% | +0.009 | Fully redundant (registry row above) | **CEO D2 GO(a) 2026-11-20, shadow-first removal SHIPPED** (signal_compactor standalone-bypass leg; 📊 WOULD-BLOCK logs; review 2026-12-04; revert if admitted cohort underperforms). 46d study: NO-EDGE, n=2,362, ex4h −0.033 |
| PRESERVE-SPIKE-BLOCK | 271 | 19% | +0.067 | Fully redundant; solo resolved 24.66%→19% with reparse frame | **HELD** — this study reclassified it MIXED/NS, n=79, ex4h −0.111 (helping direction) → not confirmed no-edge |

## Monitor-only harm candidates (no gate change before Nov 6)

Cluster-ns under the Oct-9 claim-hygiene standard — sign-consistent but not demonstrated. Graduate to the Nov 6 re-audit with 40+ days (CEO D3, 2026-10-30).

| Gate | eps (26d) | ex4h | p_w | p_tok | Note |
|------|-----------|------|-----|-------|------|
| SLOPE-FILTER | 287 | +0.342% | 0.0003 | 0.30 | Harm candidate only |
| OVERSOLD-SHORT | 649 | +0.152% | 0.003 | 0.19 | OOS-stable (+0.171/+0.141), cluster-ns |

## Ratified classifications — Nov-19 46-day usefulness study (CEO D4, 2026-11-20)

Source: `analysis/exports/nov19_gate_summary.tsv` (run-4, self-audit A1 re-coalesced) + `analysis/2026-11-19_gate-usefulness-deepdive.md`. Window 2026-10-04 → 2026-11-19 (46 days), 56 gates, cluster-robust (token + day clustered t-tests), Bonferroni p<0.0009. **Documentation ratification only — no policy, constant, or gate-behavior changes authorized by this section.**

**WORKS (keep):**
- **PUMP-CHAIN-RSI-MAX** — n=1,027, ex4h −0.190%, p_tok=0.012, p_day=0.005. **ONLY gate robust across all three baselines** (cross-mean / median / BTC).
- **LONG-RSI-CEILING** — n=989, −0.188%, p_tok=0.049. **Baseline-sensitive:** works under cross-mean/median, NOT under BTC — flag it.

**Probable workers (monitor):**
- **SPIKE-FILTER** — n=876, −0.157, p_tok=0.008.
- **PUMP-CHAIN-VEL** (post-deadband) — −0.347, p_day=0.045.

**NO-EDGE (27 gates = 82.4% of episodes / 85.8% of events) — efficiency-removal candidates pending shadow-first instrument.**

Top gates by episodes (n from the TSV): CONFLUENCE-GATE-BLOCK 3,436; CONTINUUM-BLOCK 2,831; CONTINUUM-BULL 2,362; SHORT-RSI-HARD-FLOOR 2,194; LONG-NEUTRAL-CHOP 1,915; LONG-NEUTRAL 1,791; SHORT-NEUTRAL 1,637; OVERSOLD-SHORT 1,446; RR-ENGINE 1,416; PUMP-CHAIN-SHORT-HIGH 1,236; BTC-CRASH 1,232; CTX-GATE 1,107; SHORT-CONTINUUM 1,093; PUMP-CHAIN-HIGH 966; LONG-RSI-BLOCK 921; BTC-CHOP-GATE 869.

State: "neither help nor hurt per block (|excess|<0.10%, p≥Bonferroni); removal case is efficiency/functional redundancy, NOT recovered PnL."

**Harm candidates — monitor-only, no gate change:**
- **SLOPE-FILTER** — +0.130, cluster-ns, direction consistent across 4 studies.
- **VOL-GATE-BYPASS** — +0.117, p_day=0.015 BUT flips to NO-EDGE when Oct 4–20 restored — period-dependent, do not act independently of the R1 dollar-closer.
- **MAXXED-BLOCK** — n=44, kill5 45% vs own 9% base rate.
- **CONFLICT-RESCUE-BLOCK** — n=19, too small.

### D7 operating statement (CEO D7, 2026-11-20)

"BLOCKS-SETUPS=0 under the reference baseline means: no gate harming by ≥≈0.23%/block (median MDE at n≥400, 46d window) is detectable — a detection-limit statement, NOT proof of absence. All no-harm claims must be stated with this limit. Detection limits do not block shadow-first removals (reversible, monitored); they DO block kill/harm conclusions without more data."

## Rules for editors

1. **Never remove a gate on intuition or a &lt;2wk window** (D6). Removals at Nov 6 re-audit or on pre-registered trigger.
2. **New gate PR must include:** first-seen plan link, episode-level counts (not raw log lines), null-model check for any "always/never" claim, direction-signed counterfactual, shadow plan (default OFF / shadow-log).
3. **Constants values** still require T/CEO instruction (hermes_constants DO-NOT-MODIFY). Registry is documentation only — it does not authorize value changes.
4. Update **Last verified** whenever a gate is independently re-measured.
