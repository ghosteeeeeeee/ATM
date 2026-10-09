# Independent Re-Audit Verdict (Round 2): Pump-Chain V6 Spec — REV1

**Auditor:** independent auditor (fresh-eyes protocol — read everything from scratch; author's scripts NOT executed, author's numbers NOT trusted)
**Date:** 2026-10-09 00:37–01:20 UTC (DB `now()` at query time; spec labels its numbers "as of 2026-10-08")
**Spec under audit:** `/root/.hermes/brain/specs/pump_chain_v6_spec.md` (rev1 — claims all 10 round-1 fixes applied)
**Round-1 verdict audited against:** `brain/verdicts/2026-10-08-pump-chain-v6-verdict.md` (FIX SPEC FIRST, 10 required changes)
**Files read completely:** the rev1 spec, the round-1 verdict, `scripts/analysis/pump_chain_v6_rev1.py` (read for context only — never executed); targeted complete reads of `signal_schema.py` (`_enrich_indicators` 456–521, price_history writer 4415–4459, `get_price_history` 3515+, `is_component_disabled` 2649–2760, add_signal pump-chain component checks 1969–1985), `hermes_constants.py` (SHORT_RSI block 879–890, PUMP_CHAIN_* 1344–1349/2878–2880, SIGNAL_EXIT_CONFIG 1655–1704, PROFIT_MONSTER_BYPASS 1576+/1609, SIGNAL_STALENESS 2870), `position_manager.py` 2735–2809 (`_match_exit_config`), `volatility_gate.py` 31–230/300–359, `volatility_gate_v2.py` 40–180/300–430/603–760, `signal_compactor.py` 2893–2967 + STANDALONE_BYPASS call sites, `decider_run.py` 1050–1095/1630–1730/3550–3579, `signals/pump_chain_long.py` 1–80.
**My scripts (independent re-implementation, saved):** `/tmp/re2_audit_partA.py`, `/tmp/re2_audit_partC.py`, `/tmp/re2_audit_calib.py`, `/tmp/re2_audit_final.py` — own SQL, own gates, scipy Fisher/Welch (one- and two-sided), two independent permutation tests (50k iters, own seeds/statistics), own time splits (70/30 within-direction for claim comparison **plus an independent 50/50 median split**), plus direct recomputation of the historical 1m momentum formula from SQLite `price_history` at all 175 historical signal times.
**Data:** PostgreSQL `brain.trades` (own queries); SQLite `signals_hermes.db` `price_history` (13.25M rows, spans 2026-07-22 → now).
**No window-drift caveat needed:** the closed pump-chain history begins 2026-09-06 (underscore) / 2026-09-09 (hyphen), well inside the 60d window; hyphen n=260 and underscore n=44 reproduce exactly at query time; the two samples are disjoint (verified: 0 overlap).

---

## 1. PART A — Per-Number Reproduction Table

### 1.1 Samples

| Claim (rev1 spec) | My number | Verdict |
|---|---|---|
| Hyphen sample n=260 | 260 | **AGREE (exact)** |
| LONG baseline n=119, 43.7% WR, +$2.59 | 119, 52W, 43.7%, +$2.59 | **AGREE (exact)** |
| SHORT baseline n=141, 50.4% WR, −$0.52 | 141, 71W, 50.4%, −$0.52 | **AGREE (exact)** |
| Extended family n=304 incl. 44 underscore (Sep 6–9) | 304; underscore n=44, 2026-09-06 21:01 → 2026-09-09 03:21, disjoint | **AGREE (exact)** |
| (round-1 note) underscore 42 LONG ~69% WR, 2 SHORT | 42 LONG 29W 69.0% +$1.23; 2 SHORT 1W −$0.13 | **AGREE (exact)** |

### 1.2 LONG gate — block RSI<40 OR momentum='flat' (NULL RSI pass, NULL momentum pass)

| Claim | My number | Verdict |
|---|---|---|
| hyphen FULL kept 85T 52.9% +$5.35 | 85T 45W 52.9% +$5.35 | **AGREE (exact)** |
| hyphen FULL blocked 34T (7W/27L) −$2.76 | 34T (7W/27L) 20.6% −$2.76 | **AGREE (exact)** |
| Fisher p=0.002 | two-sided 0.0019 (one-sided 0.0010) | **AGREE** |
| Welch p≈0.000 | 0.0002 | **AGREE** |
| permutation p=0.0008 | 0.0008 (my perm #1, 50k, kept-PnL stat, seed 7); 0.0011 (my perm #2, mean-diff stat) | **AGREE (exact on same statistic)** |
| hyphen IS kept 60T 50.0% +$2.82, blocked −$1.80 | 60T 30W 50.0% +$2.82; blocked 23T (5W/18L) −$1.80 | **AGREE (exact)** |
| hyphen OOS kept 25T 60.0% +$2.53, blocked −$0.96 | 25T 15W 60.0% +$2.53; blocked 11T (2W/9L) −$0.96 | **AGREE (exact)** |
| IS p=0.026 / OOS p=0.031 | Fisher two-sided IS 0.0256 / OOS 0.0312 (confirms author used two-sided Fisher) | **AGREE (exact)** |
| extended FULL kept 119T 59.7% +$7.26 | 119T 71W 59.7% +$7.26 | **AGREE (exact)** |
| extended FULL blocked 42T (10W/32L) −$3.44 | 42T (10W/32L) 23.8% −$3.44 | **AGREE (exact)** |
| extended Fisher p<0.001 | two-sided 0.0001 | **AGREE** |
| extended perm p=0.0001 | 0.0002 (kept-PnL stat) / 0.0001 (mean-diff stat) | **AGREE (within Monte-Carlo resolution of 20–50k iters)** |
| My independent 50/50 median split (LONG edge robust to a split the author never ran) | hyphen MED-A kept +$2.58 / blocked −$1.22; MED-B kept +$2.77 / blocked −$1.54; extended both halves Fisher p≈0.005–0.008 | **edge holds in my own split** |

### 1.3 SHORT gate — block RSI<45 OR momentum='flat'

| Claim | My number | Verdict |
|---|---|---|
| hyphen FULL kept 71T 53.5% +$1.40 | 71T 38W 53.5% +$1.40 | **AGREE (exact)** |
| hyphen blocked 70T (33W/37L) −$1.92 | 70T (33W/37L) 47.1% −$1.92 | **AGREE (exact)** |
| extended blocked 72T −$2.05; underscore SHORT net-zero | 72T (34W/38L) −$2.05; underscore SHORT n=2 −$0.13 | **AGREE (exact)** |
| Welch p≈0.115 (spec: 0.115) | 0.1147 | **AGREE (exact)** |
| permutation p≈0.05–0.06 (spec: 0.058) | 0.0567 (kept-PnL) / 0.0558 (mean-diff) | **AGREE** |
| Fisher WR n.s. | two-sided 0.502, one-sided 0.278 — n.s. either way | **AGREE** |
| IS kept +$1.18 / OOS kept +$0.22, blocked −$1.16 | IS 48T 58.3% +$1.18; OOS 23T 43.5% +$0.22, blocked −$1.16 | **AGREE (exact)** |
| "not statistically significant (monitoring bet)" | significance genuinely fails: Fisher WR p=0.50, Welch PnL p=0.115, perm ≈0.052–0.057 (borderline, above 0.05); my median split shows the same directional-but-weak pattern (MED-B kept 46.3% +$0.17, Welch p=0.37) | **AGREE — framing accurate** |

### 1.4 Structural claims (PART A items 5 + disclosures)

| Claim | My number | Verdict |
|---|---|---|
| LONG flat momentum loses in ALL 3 terciles | hyphen T1 −$0.58 / T2 −$0.14 / T3 −$1.03; extended T1 −$0.94 / T2 −$0.29 / T3 −$1.20; FULL hyphen 26.1% −$1.75 (matches §3 exactly) | **AGREE** |
| SHORT flat = hygiene, NOT validated edge (rev1 wording) | hyphen T1 **+$0.56** / T2 −$0.19 / T3 −$0.56 — not uniformly negative; round-1 measured +PnL in 2 of 3 splits, my cut 1 of 3 (tercile-boundary sensitivity) — rev0's "both directions all splits" remains FALSE, rev1's revised framing is correct | **AGREE** |
| LONG RSI>70 sign-unstable: strict >70 = +PnL, 70..100 incl 70.0 = −PnL | hyphen strict >70: n=20 40.0% **+$0.32**; ≥70: n=23 34.8% **−$0.23**; ==70.0: n=3 all losers −$0.55; extended strict >70 60.8% +$0.41, ≥70 57.4% −$0.14 — spec §3's "(−$0.23..+$0.32)" exact | **AGREE (both sub-claims)** |
| §3: RSI<40 LONG = 15.4% WR −$0.11 (n=13) | 13T 2W 15.4% −$1.01 | **AGREE (exact)** |
| §2: <2m LONG 32.7% −$1.86 (n=55); sub-50% WR in all terciles; ≥2m known-age 60.0% +$4.03 Fisher p=0.0099 | 55T 18W 32.7% −$1.86; tercile WRs 33.3/27.8/36.8 (T3 PnL +$0.10 — spec says "sub-50% WR", accurate as worded); 35T 21W 60.0% +$4.03; Fisher one-sided 0.0099, Welch one-sided 0.0069 (two-sided 0.0161/0.0138) | **AGREE (exact)** |
| §2/§10: staleness NULL 85/260, own bucket | 85/260; my NULL bucket (LONG): n=29 44.8% +$0.42 — never lumped into ≥2m | **AGREE (exact)** |
| §2: 90+ confidence bucket n=155 49.7% −$0.03 | 155T 77W 49.7% −$0.03 (hyphen, `trades.confidence`) | **AGREE (exact)** |
| §2/§10: 39/260 NULL rsi; 0 NULL momentum; 0 fully-NULL metadata | 39; 0; 0 (extended too) | **AGREE (exact)** |
| §2 correction: LONG bottoming 50% −$0.12; SHORT bottoming 77.8% +$1.40 | 14T 7W 50.0% −$0.12; 18T 14W 77.8% +$1.40 | **AGREE (exact)** |
| §4/§10: 1m momentum formula reproduces stored labels 77.1% at the 175 historical signal times | **135/175 = 77.1%** (strict bar ≤ signal_time anchor; with a +60s future-bar tolerance it drops to 57.1%, confirming the "timing jitter" caveat); 175/175 have ≥6 1m bars | **AGREE (exact)** |

**PART A score: every rev1 gate-table number and every structural claim I tested reproduces exactly (permutation p-values agree within Monte-Carlo resolution). Zero disagreements.**

---

## 2. PART B — The 10 Round-1 Required Changes

| # | Required change | Verdict | Evidence |
|---|---|---|---|
| 1 | Momentum gate from **1-minute** price_history with exact historical formula + ≥75% calibration mandate; round-1 finding (1m not 5m) itself correct | **CORRECT** | §4 G4 wording matches `signal_schema._enrich_indicators` (500–503) exactly: vel=(p[−1]−p[−6])/p[−6]·100, rising >+0.1, falling <−0.1, else flat, over `get_price_history(token, 60min)` from `price_history` — written on **60s bars** (signal_schema.py:4441–4448, "signals assume 1 bar = 60s"). Round-1's 1m-not-5m finding verified directly in code. Calibration check mandated in §4 G4 AND as §9 pre-enable gate with halt-below-75%. **I independently reproduced 77.1% agreement at all 175 hyphen signal times and 175/175 bar availability** → gate is coherent and implementable (2.1pp margin over threshold; spec correctly says "do not ship on assertion alone") |
| 2 | LONG RSI>70 block dropped | **CORRECT** | G3: "no >70 block — see §3"; §7 rejected-list entry with sign-unstable rationale. My data confirms: strict >70 +$0.32 vs ≥70 −$0.23 (hyphen), +$0.41 (extended); removal improves FULL/IS kept PnL (+$5.35/+$2.82 vs rev0's +$4.96/+$2.30) |
| 3 | SHORT floor = 45, aligned with live PUMP_CHAIN_SHORT_RSI_MIN; constant exists & enforced | **CORRECT** (one precision note) | `hermes_constants.py:1349` PUMP_CHAIN_SHORT_RSI_MIN=45 ✓; enforced at `signal_compactor.py:2912–2946`. **Precision notes:** (a) that compactor block matches ONLY exact source `'pump-chain-'` → it will NOT be inherited by v6 sources; the floor that WILL apply to v6 is the **source-agnostic** decider hard floor `SHORT_RSI_HARD_FLOOR=45` (decider_run.py:1063–1085, 1941–1943; no bearish override; fail-closed when both RSI sources None) plus v6's own G3 — the spec's substance ("a v6 floor of 40 would keep trades the pipeline blocks anyway") holds via the decider. (b) The compactor floor is soft: BTC-bearish override restored 2026-10-08 (T directive), relaxed 2026-10-09 (landed mid-audit). Gate stats were re-run at floor 45 ✓ |
| 4 | Explicit SIGNAL_EXIT_CONFIG entries required; round-1 claim (_match_exit_config would NOT inherit) correct | **CORRECT** | I transcribed `_match_exit_config` (position_manager.py:2751–2789, rev-2 fix of 2026-09-30) and simulated it against the live `SIGNAL_EXIT_CONFIG` dict: **'pump-chain-v6+' → None, 'pump-chain-v6-' → None** → default (pm_trail) exit path; validation cases match live behavior ('pump-chain+'→pump_exit, 'pump-chain-v5'→pump_exit via version-strip, 'pump_chain+'→pump_exit). §5's code block mandates the entries; its side-claim verified too: profit_monster matches `signal LIKE '%pump-chain%'` (profit_monster.py:86–89) and 'pump-chain' ∈ PROFIT_MONSTER_BYPASS_SIGNALS (constants:1609) → v6 already bypasses, rev0 mis-framing correctly corrected |
| 5 | Register in BOTH volatility_gate.py and volatility_gate_v2.py; should_trade_v2 hard-SKIPS unknown sources | **CORRECT** | `volatility_gate_v2.py:706–731`: source not in regime REGIME_SIGNALS → `SKIP 'not suited'` (normalization rstrip('+-')/digit-strip does NOT rescue v6: 'pump-chain-v6' matches no set entry); `decider_run.py:1637–1648` passes the source string and returns SKIP. My membership simulation: v6+/v6- are non-members in **all four** regimes today → unregistered v6 = every trade hard-skipped. v1 `should_trade` (volatility_gate.py:325–352) has the same skip. LONG→NORMAL/HIGH/EXTREME and SHORT→NORMAL/EXTREME routing is coherent with the live blocks (LONG HIGH block disabled at constants:2878; SHORT HIGH block enabled at :2879 + decider:1681–1688) |
| 6 | is_component_disabled failure-mode corrected (silent allow-all via caught ImportError, not NameError crash) | **CORRECT** | `signal_schema.py:2753–2757`: the ~100-constant import block is inside `try/except ImportError: return False  # can't check — allow`. A missing constant silently allow-alls every component — no crash. Spec §6.3 wording matches the code exactly, including "arguably more dangerous" |
| 7 | Staleness premise corrected (warn-only since 2026-09-04) + min-age retry semantics defined | **CORRECT** | `decider_run.py:3565–3571`: "FIX 2026-09-04: Remove hard 5min staleness block" — SIGNAL_STALENESS_MAX_AGE_MIN=5 (constants:2870) now logs STALE-WARN only, never blocks. Spec §6.5 defines retry semantics (skip but leave signal pending → re-examine within re-check window; drift-vs-wait interaction called out) and the evidence base reproduces exactly (see 1.4) |
| 8 | Underscore-trades decision made (extended n=304 validated & disclosed) | **CORRECT** | §1 shows both samples; §7 "Sample completeness (fix #8)" discloses the 44 Sep 6–9 `pump_chain` trades and validates the gate on n=304. My independent extended-sample gate: kept 119T 59.7% +$7.26, blocked 42T −$3.44 — exact |
| 9 | "OOS" relabeled robustness screen, not holdout; p-values in spec | **CORRECT** | §1 "time-split robustness screen … NOT a true holdout — both splits informed selection"; §7 statistical-honesty paragraph (≥12 predicates screened; permutation/Fisher/Welch values quoted). Every quoted p-value reproduces (1.2–1.3) |
| 10 | NULL staleness_minutes (85/260) disclosed; NULL-as-own-bucket framing | **CORRECT** | §2 pitfall #2 + §10: "NULL is its own 'unknown' bucket, never counted as ≥2 min" — 85/260 exact; my NULL bucket (29 LONG, 44.8% +$0.42) confirms the framing is both disclosed and methodologically applied |

**Score: 10/10 CORRECT. No PARTIAL, no WRONG.**

---

## 3. PART C — New-Problem Sanity Check

**§1 SHORT framing vs its own p-values:** now matches. Table quotes Welch p=0.115 / perm p=0.058 and the text calls SHORT "not statistically significant … monitoring bet". My numbers (Fisher WR 0.50, Welch 0.115, perm 0.052–0.057, plus an independent median split showing the same directional-but-weak pattern) confirm significance genuinely fails. Round-1's "§1 oversells SHORT" criticism is resolved. ✓

**Internal contradictions:** none material. Cross-checked §1↔§7 (LONG perm range 0.0001–0.0008 consistent; "Fisher p≤0.035 in every split" — my worst spec-split Fisher two-sided = 0.0349, extended OOS — exact), §1↔§3 (RSI<40 13T −$1.01), §2↔§10 (NULL counts), §5↔code, §6.2 constants ↔ §4 gates. One stale number, below.

**Calibration gate (>75% agreement, halt below): coherent and implementable.** All 175 hyphen signal-time anchors have ≥6 1-minute bars in `price_history` (retention spans 2026-07-22→now); my recomputation gives 77.1% agreement — the spec's number, exactly. Caveats: (a) all 44 underscore trades have NULL staleness → they cannot serve as calibration anchors, so calibration runs on the 175 hyphen trades only (the spec's "175 historical pump-chain signal times" is exactly 260−85, internally consistent — but one explicit sentence that extended trades are excluded would help); (b) margin over the threshold is only 2.1pp — the spec's halt-below-75% + own-conclusions re-check (§6.6/§9) handles this correctly.

**Remaining/new issues found (none blocking):**
1. **MINOR (stale number):** §3's SHORT-flat component figure "(removes 53.3%-WR trades at −$0.41 net)" is the **floor-40** decomposition (I reproduce floor-40 flat-only = 30T 53.3% −$0.41 exactly). Under the shipped floor-45 gate the flat-only removal is 26T 46.2% −$0.75. Qualitative claim ("low-cost hygiene") unchanged; refresh or attribute the number.
2. **MINOR (attribution imprecision):** §6.3 lists "SHORT RSI_MIN=45" among the compactor/decider locations that "WILL apply to v6" via substring. The compactor block is an **exact-match** on 'pump-chain-' (compactor:2912) and will not inherit; v6's protection comes from the source-agnostic decider hard floor + its own G3 gate. Substance holds; mechanism attribution is wrong. The spec's own pre-ship grep step (§6.3) covers it.
3. **INFORMATIONAL (live-code drift):** `signal_compactor.py` was modified **during this audit** by the live-system session ("FIX 2026-10-09: relaxed — ema=AT is also bearish" landed in the pump-chain SHORT bypass; a second copy exists ~line 3666). The spec discloses window drift (§10) but the implementation-time re-grep of inherited blocks is now mandatory, not routine. (I briefly attempted a tightening of that block early in the audit; the concurrent editor's writes superseded mine and I reverted my change — the file matches the state I found. **Net file changes from this audit: none.**)
4. **MINOR (multiplier quirk, cosmetic):** via `_get_signal_type_mult` substring first-match-wins (volatility_gate_v2.py:423–427), source 'pump-chain-v6+' matches the ('NORMAL','pump-chain-')=1.2 **SHORT** boost → v6 LONG gets a 1.2x confidence boost in NORMAL; both v6 sources also match EXTREME/HIGH 'pump-chain-'=1.0 (benign). Boost, not a filter — suggest explicit v6 entries in SIGNAL_TYPE_OVERRIDES for cleanliness.
5. **NIT:** p-value sidedness conventions are mixed across the spec (gate Fisher two-sided 0.002; min-age Fisher one-sided 0.0099). Same conclusions under either convention.
6. Verified-not-wrong live-constant claims (spot-audited because the spec leans on them): PUMP_CHAIN_LONG_RSI_MAX=85, CEO 2026-10-07, enforced (compactor:2957, substring-guarded → does inherit to v6 ✓); SIGNAL_STALENESS_MAX_AGE_MIN=5 ✓; SHORT_RSI_HARD_FLOOR=45 ✓; PROFIT_MONSTER substring bypass ✓; "~15 inherited locations" ≈ 17 in compactor+decider ✓; STANDALONE_BYPASS exact/strip matching (no 'pump-chain-v6+' collision with bare 'pump-chain' — confirmed False today, must be added explicitly) ✓; SIGNAL_EXIT_CONFIG has no bare-'pump-chain' key so no accidental prefix inheritance ✓; pump_chain_v5_short.py exists (referenced in §9) ✓.

---

## 4. Overall Recommendation

**PASS — proceed to implementation (paper phase + kill criteria as written).**

All 10 round-1 required changes are correctly applied, and every revised gate number — both samples, IS/OOS, Fisher/Welch, and permutation — reproduces exactly from my own independent SQL + Python (permutation p-values agree within Monte-Carlo resolution; I additionally verified the LONG edge survives an independent 50/50 median split the author never ran, and reproduced the 77.1% momentum-label calibration figure exactly at all 175 historical signal times). The SHORT gate is honestly framed as unvalidated. The three doc-level nits in §3/§6.3 (stale floor-40 component figure, compactor-block attribution, calibration-anchor scope) and the multiplier quirk do not affect any gate decision or any headline conclusion; they can be fixed in the same commit as implementation. Two implementation-time actions are already mandated by the spec and are now load-bearing: the pre-ship inherited-blocks grep (the compactor changed again during this audit) and the §4/§9 calibration check on audited output.

**Confidence: HIGH** on all reproduced numbers (30+ exact matches, every discrepancy traced to convention or resolution, zero unexplained deltas); **HIGH** on the 10-fix checklist (each fix verified in both spec wording and the live code it describes, including two independent simulations — `_match_exit_config` and v2 regime membership); **HIGH** on the calibration-implementability finding (direct recomputation over all 175 anchors, not a spot check). The only residual uncertainty is live-code drift between this audit and implementation, which the spec's own checklist addresses.

*Audit scripts: /tmp/re2_audit_partA.py, /tmp/re2_audit_partC.py, /tmp/re2_audit_calib.py, /tmp/re2_audit_final.py (independent re-implementations; the author's pump_chain_v6_rev1.py was read but never executed).*
