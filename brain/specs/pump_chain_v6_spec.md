# Pump-Chain V6 Spec — "Keep the Winners, Ditch the Losers" (REVISED)

**Date:** 2026-10-08 (rev1 — revised after independent audit)
**Status:** SPEC rev1 — audit fixes applied; awaiting approval before implementation
**Author:** Hermes analysis (data-driven, 260–304 closed trades, time-split validated)
**Skills followed:** `signal-lab` (thesis → entry → exit → backtest), `add-signal` (integration checklist), `own-conclusions` (independent audit)
**Independent audit:** round 1 `brain/verdicts/2026-10-08-pump-chain-v6-verdict.md`
(FIX SPEC FIRST, 10 changes — all applied in rev1); round 2 (re-audit of rev1)
`brain/verdicts/2026-10-08-pump-chain-v6-rev1-verdict.md` — **PASS, HIGH confidence**:
10/10 fixes CORRECT, all revised gate numbers reproduced exactly, zero disagreements.
Four non-blocking notes from the re-audit are folded into this document.

---

## 1. Executive Summary

Pump-chain's core thesis — capital rotates from leaders into laggards, and the chain
correlation is the alpha — **still works**. What failed in every previous version is the
*entry-timing gates* around it: overfit on tiny samples, data read from the wrong place,
or filters that reversed as the regime shifted.

V6 is a single clean signal (BOTH directions, one file). Gates were selected by one rule:
improve WR and PnL with the blocked basket net-negative — checked on the full sample and
on a **time-split robustness screen** (first/last 30% by open_time; NOT a true holdout —
both splits informed selection, disclosed per audit fix #9), with Fisher/Welch and
permutation significance.

**Revised gates (audit-fixed, both samples, p-values from `pump_chain_v6_rev1.py`):**

| Direction | Gate | FULL (hyphen n=260) | FULL (extended family n=304) | IS / OOS (robustness screen) |
|-----------|------|--------------------|------------------------------|------------------------------|
| **LONG** | block RSI<40 **or** momentum=flat | 43.7% +$2.59 → **52.9% +$5.35**; blocked 7W/27L −$2.76; Fisher p=0.002, perm p=0.0008 | → **59.7% +$7.26**; blocked 10W/32L −$3.44; Fisher p<0.001, perm p=0.0001 | IS 50.0% +$2.82 (p=0.026) / OOS 60.0% +$2.53 (p=0.031) |
| **SHORT** | block RSI<45 **or** momentum=flat | 50.4% −$0.52 → **53.5% +$1.40**; blocked 33W/37L −$1.92; Welch p=0.115, perm p=0.058 | same (underscore trades net-zero for SHORT) | IS +$1.18 / OOS kept +$0.22, blocked −$1.16 — directionally right, **not statistically significant** |

**Honest framing (audit fix #9):** the LONG gate is validated edge (survives multiplicity
haircut, permutation-verified, consistent within regimes, holds on the extended family
sample). The SHORT gate is a **correctly-hedged monitoring bet** — directionally right in
both splits but not distinguishable from random at current n. It ships under tighter kill
criteria, not as "validated."

**V6 does not replace the live `pump_chain_long` immediately** (§9): it runs in parallel
under `signal_type='pump-chain-v6'` with independent outcome stats; old variants retire
only after v6 proves itself live.

---

## 2. Why Every Previous Version Failed (Pitfall Register)

| Version | Claim | Delivered | Root cause | V6 fix |
|---------|-------|-----------|------------|--------|
| V1 | pure pump-flow momentum | 57.5% WR, losers > winners | No entry-timing gates | RSI/momentum gates |
| V2 spec | "93.5% WR verified" | ~45% WR live | Overfit on 73 in-sample trades | All claims time-split screened with p-values; min-n + kill criteria shipped with the spec |
| V4 | BTC oscillator block >80 | 15.4% WR −$1.51, NEVER_REENABLE | BTC-only indicator regime-shifted | **No BTC-score blocking in v6** |
| V5 | velocity + "block bottoming" | 33.3% WR −$0.42, killed 3× | (a) read wave_phase/momentum_state from the token's **last closed trade's metadata** — stale, cross-contaminated; (b) n=10 "90% WR" claim | All v6 gates computed from **live data at detection time**; no wave_phase blocking |
| V5 SHORT | accel/rising + BB blocks | breakeven | filters on 2-trade "0% WR" cells | v6 SHORT gates screened on n=141+ |

Audit-corrections to this table (fix #7 / claim 7): the "bottoming is now a winner band"
finding pools both directions — the win is entirely SHORT (77.8% +$1.40); LONG bottoming
is 50% WR −$0.12. The accurate v5 counterfactual: its bottoming block would have blocked
**breakeven** LONG trades, not winners. Still a reversal of v5's premise, but stated honestly.

Cross-cutting pitfalls fixed in V6:

1. **Confidence is not an edge.** 90+ bucket: n=155, 49.7% WR, −$0.03 (auditor-reproduced).
   Confidence = ranking only.
2. **Instant-chase execution loses.** LONG trades opened <2 min after signal: 32.7% WR,
   −$1.86 (n=55), sub-50% WR in all three time terciles; ≥2 min known-age: 60.0% +$4.03
   (Fisher p=0.0099). **Disclosure (fix #10):** staleness_minutes is NULL on 85/260 trades;
   NULL is its own "unknown" bucket, never counted as ≥2 min. → min-age guard (§6.5).
3. **Source-string zoo.** Fixed source strings only; chain evidence in `value` + logs.
4. **NULL metadata.** 39/260 NULL rsi_14 (momentum/z/wave never NULL). Gates fail open on
   missing features + DEBUG log — explicit decision, not accident.
5. **My own near-repeat of v5's sin (audit claim 10 — the fatal find).** rev0 computed the
   momentum gate from `candles_5m` (5 bars = 25-min velocity) claiming "zero calibration
   gap" to the historical `momentum_state`. The historical formula (`signal_schema._enrich_indicators`)
   uses **1-minute `price_history` bars** (5 bars = 5-min window). The two agree only 66.3%;
   the flat-block decision flips on 27% of historical trades. **rev1 computes momentum from
   1-minute bars with the exact historical formula** (§4, G4) and mandates a calibration
   check before enabling.
6. **Detection/execution gap:** v6 gates fire at detection; `decider_run.py` re-validates
   live RSI at execution (floors below). Min-age guard partially mitigates for LONG.

---

## 3. Thesis (signal-lab Step 1)

**Capital-rotation continuation:** when capital rotates from leaders into laggards
(pump-flow engine chain evidence: leader → follower lift), the follower's move is real
flow and continues — but only while the move is mid-cycle:

- **LONG while mid-RSI (40–70) with live momentum not flat.** RSI<40 = the pump never
  started or already died: 15.4% WR, −$1.01 (n=13). The old RSI>70 block is **dropped**
  (audit fix #2): the band is sign-unstable at the boundary (−$0.23..+$0.32), +PnL
  full-sample, and the CEO raised live `PUMP_CHAIN_LONG_RSI_MAX` 70→85 on 2026-10-07
  precisely because "old 70 threshold blocked profitable trades." The live 85 ceiling
  (inherited via substring matching) remains the operative overbought guard.
- **SHORT only when not already crushed (RSI≥45).** RSI<45 SHORT = shorting into
  oversold — the BANANA lesson, quantified: blocked basket −$1.92 (n=70).
  Floor is 45, not 40 (audit fix #3), matching the live `PUMP_CHAIN_SHORT_RSI_MIN=45`
  compactor block and `SHORT_RSI_HARD_FLOOR=45` exec floor — a v6 floor of 40 would have
  produced kept trades the pipeline blocks anyway.
- **`momentum_state='flat'` blocks LONG** (26.1% WR −$1.75, negative in all three time
  terciles). For SHORT it stays in the gate as low-cost hygiene (under the shipped
  floor-45: removes 26 trades at 46.2% WR, −$0.75 net — rev1-reaudit figure) but is
  **not claimed as validated SHORT edge** (audit claim 4: SHORT flat was +PnL in 2 of 3
  splits).

---

## 4. Entry Conditions (signal-lab Step 2) — exact, testable

Per pump-flow-engine recommendation (engine NOT modified):

```
G0  Engine gates:  phase confidence ≥ PUMP_FLOW_MIN_PHASE_CONFIDENCE
                   direction ∈ {LONG, SHORT} (WAIT ignored)
                   confidence ≥ PUMP_FLOW_MIN_CONFIDENCE (ranking floor, not edge)
G1  Freshness:     price_age_minutes ≤ PUMP_FLOW_MAX_PRICE_AGE
                   token_speeds.is_stale = false
G2  Risk:          not in LONG_BLACKLIST / SHORT_BLACKLIST; cooldown clear
G3  RSI gate:      RSI(14) at detection time from the SAME source as signal enrichment
                   (1-minute price_history / candles_1m — matches _signal_metadata)
                   LONG:  RSI ≥ 40          (block <40; no >70 block — see §3)
                   SHORT: RSI ≥ 45          (aligned with live floors)
                   missing RSI → fail open + DEBUG log
G4  Momentum gate: momentum_state = 5-bar velocity over 1-MINUTE bars using the EXACT
                   historical formula (signal_schema._enrich_indicators):
                   rising if vel > +0.1, falling if vel < -0.1, else flat.
                   Block 'flat' for LONG (validated) and SHORT (hygiene).
                   Missing data → fail open + DEBUG log.
                   ⚠ Calibration check before enabling (audit fix #1): recompute this
                   formula at the 175 historical pump-chain signal times and require
                   ≥75% agreement with stored metadata labels (auditor measured 77.1%
                   for the correct 1m formula vs 72.0% for the rejected 5m formula).
                   Below 75% → halt and re-audit. Do NOT ship on assertion alone.
```

Chain evidence logged + passed via `value` for audit — not a gate (no validated threshold).

---

## 5. Exit Plan (signal-lab Step 3)

**Explicit `SIGNAL_EXIT_CONFIG` entries are mandatory (audit fix #4)** — the rev0 claim
that v6 would inherit "existing routing" was FALSE: `_match_exit_config`
(position_manager.py:2751) was deliberately fixed 2026-09-30 to reject raw-prefix matches;
without explicit keys v6 would silently take the *default* exit path.

```python
SIGNAL_EXIT_CONFIG = {
    ...,
    'pump-chain-v6+': 'pump_exit',   # momentum exit works for pump-chain LONG
    'pump-chain-v6-': 'rr_engine',   # tighter SL for SHORT (CASHCAT −6.4% lesson)
}
```

`PROFIT_MONSTER_BYPASS_SIGNALS`: **no change needed** (audit fix — profit_monster already
matches v6 by substring `%pump-chain%`; rev0 mis-framed this as required). R:R floor via
existing rr_engine / ATR SL stack — unchanged.

---

## 6. Implementation Plan (add-signal checklist, audit-corrected)

### 6.1 New signal script — `scripts/signals/pump_chain_v6.py`
- One file, both directions. `SIGNAL_TYPE = 'pump-chain-v6'` (clean independent
  `signal_outcomes` stats for decay detector + kill criteria).
- `SOURCE_LONG = 'pump-chain-v6+'`, `SOURCE_SHORT = 'pump-chain-v6-'` — fixed strings.
- RSI + momentum computed from **1-minute data** (§4 G3/G4) via read-only connection,
  closed in `finally`. Staleness from `token_speeds` (read-only URI).
- `run()` with no params; price fetched once per cycle.

### 6.2 Constants — `hermes_constants.py`
```python
PUMP_CHAIN_V6_ENABLED = True          # master
PUMP_CHAIN_V6_PLUS_ENABLED = True     # LONG
PUMP_CHAIN_V6_MINUS_ENABLED = True    # SHORT
PUMP_CHAIN_V6_LONG_RSI_MIN = 40
PUMP_CHAIN_V6_SHORT_RSI_MIN = 45      # aligned with live SHORT_RSI floors (audit fix #3)
PUMP_CHAIN_V6_BLOCK_FLAT_MOMENTUM = True
PUMP_CHAIN_V6_MIN_AGE_MIN = 2         # LONG execution min-age (§6.5)
```
Plus the two `SIGNAL_EXIT_CONFIG` entries (§5). Existing PUMP_FLOW_* shared constants
reused. `STANDALONE_BYPASS_SIGNALS` += v6 sources (exact/strip matching confirmed —
`pump-chain-v6+` does not collide with the existing bare `pump-chain` entry).

### 6.3 Registration & enforcement — **BOTH volatility gates (audit fix #5)**
- `signals/__init__.py`: import + registry entry; not a slow signal.
- `signal_schema.py` `add_signal()` per-component checks + `is_component_disabled()`
  (constants added to ITS import block). **Corrected failure-mode note (fix #6):** that
  import block is wrapped in `try/except ImportError` that returns "not disabled" — a
  missing constant does NOT crash compaction (rev0 was wrong); it **silently allow-alls
  every component**, which is arguably more dangerous. Verify by grep after editing.
- `signal_compactor.py` `SIGNAL_SOURCE_WEIGHTS` += v6 (1.0).
- **`volatility_gate.py` AND `volatility_gate_v2.py`** `REGIME_SIGNALS` += v6 sources:
  `decider_run` uses `should_trade_v2`, which hard-SKIPs sources absent from its list —
  registering only in v1 would block every v6 trade in every regime.
  - LONG → NORMAL, HIGH, EXTREME (gate-applied HIGH kept = 14T 57.1% +$0.92 per audit —
    the gate, not the regime table, justifies keeping HIGH)
  - SHORT → NORMAL, EXTREME (HIGH is the confirmed SHORT bleed regime)
- **Inherited substring blocks (audit finding — accepted, documented):** ~15 live
  compactor/decider locations match `'pump-chain' in source` and WILL apply to v6 —
  notably the source-agnostic decider `SHORT_RSI_HARD_FLOOR=45` and the SHORT HIGH block
  (both consistent with the gates above). NOTE (rev1-reaudit): the compactor
  PUMP-CHAIN-SHORT-RSI-MIN block is exact-match on `'pump-chain-'` and will NOT inherit
  to v6 — v6's SHORT floor is protected by its own G3 gate + the decider hard floor, not
  inheritance; that compactor floor is also soft (BTC-bearish override). Before shipping,
  enumerate inherited matches (`grep -n "'pump-chain' in" *.py`) and confirm none
  conflicts with the gates above — MANDATORY because live code drifts (signal_compactor
  was modified during the re-audit itself).
- **Confidence multiplier quirk (rev1-reaudit):** `'pump-chain-v6+'` substring-matches
  the `('NORMAL', 'pump-chain-') = 1.2` volatility-gate-v2 entry, so v6 LONG would get the
  SHORT-side confidence boost in NORMAL regime (a boost, not a filter). Add explicit v6
  override entries in both gates' multipliers at implementation time.
- Not in `_DEAD_SIGNALS`; `validate_source()` check.

### 6.4 Known inherited blocks that intentionally apply to v6
Live floors already enforce parts of G3 at execution time (decider live-RSI hard floor
for SHORTs). V6's detection-time gates complement them (they keep garbage out of the DB
and hotset), they don't replace them.

### 6.5 Execution min-age guard (audit fix #7 — corrected premise + retry semantics)
Rev0 claimed a "2–5 min window" under `SIGNAL_STALENESS_MAX_AGE_MIN=5` — wrong: that
check has been **warn-only since 2026-09-04** (decider_run.py:3565–3571). The guard is
still implementable on its own evidence (p<0.01) with explicit semantics:
- For `pump-chain-v6+` only: if signal age < 2 min at decision time → **SKIP but leave
  the signal pending** (do NOT mark executed/consumed) so it is re-examined on a later
  cycle within a re-check window; if still alive at 2+ min, normal flow resumes.
- Interaction with price-drift checks: drift is measured vs detection price and grows
  while waiting — the skip path must not trip the drift block merely due to the wait.
- SHORT: no min-age (5m+ is the *best* SHORT band, 58.1% WR +$0.97 — age helps SHORTs).

### 6.6 Verification (add-signal Step 6)
py_compile all changed files → import-chain check (registry, both REGIME_SIGNALS,
is_component_disabled grep-verified) → `--dry` run → log check → pre-flight checklist →
**then bug_hunter on the diff, then own-conclusions re-check of the calibration script
output** (fix #1's ≥75% agreement gate) before the paper phase starts.

---

## 7. Tested and REJECTED (do not re-propose without new data)

| Candidate | Result | Verdict |
|-----------|--------|---------|
| Block LONG RSI>70 | sign-unstable at boundary (−$0.23..+$0.32); +PnL full-sample; contradicts CEO's 2026-10-07 70→85 raise; removal improves FULL/IS kept PnL (+$5.35/+$2.82 vs +$4.96/+$2.30) | **Rejected (audit fix #2)** |
| Block wave_phase='bottoming' (v5) | LONG bottoming = 50% WR −$0.12 (breakeven); the pooled "winner band" is SHORT-side only | Reversed premise |
| z-score filters (LONG <−1.5 / SHORT >+1.5) | blocks 0 LONG + exactly 1 SHORT trade (GMX −$0.01) — dead code | No |
| speed_percentile bands | sign flips across splits | No |
| volume_spike | IS strong, OOS sign-reverses | No |
| Confidence > threshold | 90+ = coin flip (n=155) | Ranking only |
| BTC oscillator block (v4) | 15.4% WR, NEVER_REENABLE | No |
| momentum gate from candles_5m (rev0) | different feature than validated: agree 66.3%, flat-rate 6.9% vs 26.9%, gate flips on 27% of trades | **Killed by audit claim 10** |
| SHORT floor at 40 (rev0) | kept 40–45 band can't execute anyway (live compactor floor 45); false stats | Raised to 45 |

**Statistical honesty (fix #9):** ≥12 candidate predicates were screened across splits —
the "OOS" numbers are a multi-split robustness screen, not a sealed holdout. LONG's
separation survives this treatment (permutation p=0.0001–0.0008; Fisher p≤0.035 in every
split, both samples). SHORT's does not reach conventional significance (permutation
p≈0.05–0.06 full, p≈0.14 OOS at the rev0 floor) — shipped as a monitored bet with its own
kill trigger (§9).

**Sample completeness (fix #8):** the LIKE-based family query excludes 44 legacy
`pump_chain` underscore trades (Sep 6–9; 42 LONG at 69% WR). rev1 validated gates on the
**extended family sample (n=304)** too — LONG gate strengthens (59.7% +$7.26, blocked
10W/32L −$3.44); SHORT unchanged. Extended-sample numbers are the primary table in §1.

---

## 8. Reproducibility

- `scripts/analysis/pump_chain_v6_rev1.py` — **the rev1 gate table in §1** (both samples,
  IS/OOS, Fisher/Welch + permutation)
- `scripts/analysis/pump_chain_v6_analysis.py`, `_round2.py`, `_round3.py` — rev0
  exploration (feature screens, terciles); superseded for gate numbers by rev1
- Auditor's independent scripts: `/tmp/audit_v6_part1..5.py` (session-temp; verdict
  `brain/verdicts/2026-10-08-pump-chain-v6-verdict.md` records all reproduced numbers)
- Data: PostgreSQL `brain.trades` (closed, pump-chain family, `_signal_metadata` attached)

---

## 9. Deployment & Kill Criteria (signal-lab Steps 5–6)

1. **Do NOT disable the current `pump_chain_long`** (`pump-chain+`): healthy at last check
   (14d ~22T ~54–59% WR ~+$2.0). V6 ships alongside under a new signal_type.
2. **Pre-enable gate:** the §4 calibration check (≥75% momentum-label agreement at
   historical signal times) — audited output, not asserted.
3. **Paper phase: 2 weeks.** Full pipeline; Layer-3 gates, regime routing (BOTH gates),
   min-age guard all live. Monitor `signal_outcomes` by `signal_type='pump-chain-v6'`.
4. **Kill criteria:** LONG — WR < 45% after 20 closed trades, or PnL < −$1.00 rolling 10,
   or decay_detector flag. SHORT — **stricter:** WR < 50% after 15 trades, or PnL < −$0.75
   rolling 10 (it ships unvalidated; it doesn't get 20 trades to prove itself).
   Kill = `PUMP_CHAIN_V6_ENABLED=False`; re-enable needs fresh backtest + CEO (v4/v5 precedent).
5. **Promotion:** ≥5 trades → self_learner tunes combo weights. If v6 ≥ 55% WR on 50
   trades → old `pump_chain_long` / `pump_chain_v5_short` flags go False with NEVER_REENABLE
   review if they can't beat v6.
6. **After commit: restart the pipeline** (detection-time filters need reload).
7. **bug_hunter on the implementation diff before commit** (add-signal Step 7 mandate);
   own-conclusions already run on the spec (this revision is its output).

---

## 10. Known Data Caveats (full disclosure)

- 39/260 NULL `rsi_14`; 85/260 NULL `staleness_minutes`; 0 NULL momentum/z/wave; 0
  fully-NULL metadata rows. Gates fail open on NULL + log.
- Even the correct 1m momentum formula reproduces stored labels 77.1% of the time at
  historical times (timing jitter between signal and enrichment) — hence the calibration
  threshold is 75%, not 100%; the gate trades the *stored-label* edge, and residual
  misclassification dilutes (never inflates) the measured effect.
- Calibration anchor set: the 175 hyphen-sample trades with non-NULL staleness
  (260 − 85); all 175 have 1m data available (re-audit verified). The 44 underscore trades
  all have NULL staleness and cannot serve as anchors.
- Window drift is real: several headline numbers moved 5–15% between the spec draft and
  the audit hours later. All rev1 numbers are as of 2026-10-08 and re-runnable.
