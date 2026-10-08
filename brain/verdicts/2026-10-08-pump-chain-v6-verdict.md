# Independent Audit Verdict: Pump-Chain V6 Spec

**Auditor:** independent auditor (fresh-eyes, own-conclusions protocol — no priming, read everything from scratch)
**Date:** 2026-10-08 (DB `now()` = 2026-10-08 23:0x UTC)
**Spec under audit:** `/root/.hermes/brain/specs/pump_chain_v6_spec.md`
**Files read completely:** the spec, `scripts/analysis/pump_chain_v6_analysis.py`, `pump_chain_v6_round2.py`, `pump_chain_v6_round3.py`, `scripts/signals/pump_chain_long.py`, `scripts/signals/pump_chain_v5.py`; plus targeted reads of `hermes_constants.py`, `signal_schema.py`, `signal_compactor.py`, `volatility_gate.py`, `volatility_gate_v2.py`, `decider_run.py`, `position_manager.py`, `monte_carlo_gate.py`, `signals/__init__.py`, prior verdict `2026-09-09_pump-chain-v2-verdict.md`.
**Data queried myself:** PostgreSQL `brain.trades` (own SQL, not the authors' scripts), SQLite `signals_hermes.db` (price_history), `candles.db` (candles_5m/1m), `signals_hermes_runtime.db`.
**My scripts (independent re-implementation, saved in /tmp):** `audit_v6_part1.py` … `audit_v6_part5.py`. None of the authors' scripts were executed; every number below comes from my own queries/code (scipy-based Fisher/Welch tests + 20k-iteration permutation tests).

---

## 1. Per-Claim Verdicts

| # | Claim | Verdict |
|---|-------|---------|
| 1 | Full 60d sample: n=260, 47.3% WR, +$2.07; LONG n=119 43.7% +$2.59; SHORT n=141 50.4% −$0.52 | **AGREE** (exact), with a sample-completeness caveat |
| 2 | LONG gate: kept 66 (56.1% +$4.96), blocked 53 (15W/38L −$2.37), improves in IS and OOS | **AGREE** (exact; permutation-verified) |
| 3 | SHORT gate: kept 86 (53.5% +$1.54), blocked 55 (25W/30L −$2.06), OOS improvement weak | **AGREE** (exact; weakness confirmed and quantified) |
| 4 | momentum_state='flat' loses in BOTH directions and ALL three time splits | **PARTIAL** — true for LONG; FALSE for SHORT (flat is +PnL in 2 of 3 SHORT splits) |
| 5 | Confidence not predictive: 90+ bucket ~155 trades ~50% WR, PnL ≈ ±$0 | **AGREE** (n=155, 49.7% WR, −$0.03) |
| 6 | LONG <2min: 32.7% WR n=55 (−$1.86), losing in all three terciles; ≥2min better | **AGREE with caveats** (numbers exact; "all terciles" true by WR but T3 PnL is +$0.10; +$4.45 figure lumps NULL-staleness trades into ≥2m) |
| 7 | wave_phase='bottoming' is a WINNER band (65.6% +$1.28 n=32); v5 filter would block winners | **PARTIAL** — pooled number exact, but the win is entirely SHORT (77.8% +$1.40); LONG bottoming is 50% WR −$0.12, so the v5 (LONG-only) counterfactual is "blocks breakeven trades", not winners |
| 8 | z-score filters block ZERO trades in 60d (dead code) | **AGREE (nitpick: off by one)** — LONG z<−1.5 blocks 0; SHORT z>+1.5 blocks exactly 1 trade (GMX, −$0.01). Economically dead code |
| 9 | 39/260 rows have NULL rsi_14 | **AGREE** (exact 39/260; momentum_state/z/wave_phase never NULL; 0 rows with fully-NULL metadata) |
| 10 | Historical momentum_state = 5-bar velocity "from 5m candles" → computing v6's gate from candles_5m = "zero calibration gap" | **DISAGREE — the spec's central implementation claim is false.** Historical formula used **1-minute** price_history bars (5 bars = **5 min**); candles_5m gives 5 bars = **25 min**. Empirically the two formulas agree only 66.3% of the time; flat-rate 26.9% vs 6.9%; the flat-block gate decision flips on **47/175 (27%)** of historical trades |

---

## 2. My Reproduced Numbers (all from my own queries)

### Claim 1 — sample (window: DB now − 60d; closed; `signal LIKE '%pump-chain%'`; metadata NOT NULL)
```
FULL   n=260  123W/137L  WR=47.3%  PnL=+$2.07
LONG   n=119   52W/67L   WR=43.7%  PnL=+$2.59
SHORT  n=141   71W/70L   WR=50.4%  PnL=-$0.52
```
Exact match. **Caveat (my finding):** 60d also contains **44 literal `pump_chain` (underscore) trades** (Sep 6–9; 42 LONG at 69.0% WR +$1.23, 2 SHORT −$0.13; all with metadata) that the `LIKE '%pump-chain%'` pattern does not match. (`LIKE '%pump_chain%'` cannot be used to fix this — `_` is a LIKE wildcard and matches the hyphen rows too; must use `position('pump_chain' in signal) > 0`.) Extended sample = **n=304, LONG n=161 50.3% +$3.82, SHORT n=143 50.3% −$0.65**. The spec neither includes nor justifies excluding these.

### Claims 2–3 — gates (my re-implementation; NULL rsi → fail-open; NULL momentum → pass)
```
LONG gate (block RSI<40 or >70 or flat):
  FULL : baseline n=119 43.7% +$2.59 → kept n=66 (37W/29L) 56.1% +$4.96 | blocked n=53 (15W/38L) 28.3% -$2.37
         Fisher(WR kept>blocked) p=0.002 ; Welch(PnL) p=0.0035
  IS   : baseline 41.5% +$0.79 → kept 52.2% +$2.30 | blocked 36 (10W/26L) -$1.51   (p_wr=0.022, p_pnl=0.044)
  OOS  : baseline 48.6% +$1.80 → kept n=20 65.0% +$2.66 | blocked 17 (5W/12L) -$0.86 (p_wr=0.033, p_pnl=0.014)
  Permutation (20k random blocks of same size): real gate beats 99.6% (FULL), 95.5% (IS), 98.7% (OOS) of random blocks.
SHORT gate (block RSI<40 or flat):
  FULL : baseline n=141 50.4% -$0.52 → kept n=86 (46W/40L) 53.5% +$1.54 | blocked n=55 (25W/30L) 45.5% -$2.06
         Fisher p=0.22 (WR not significant) ; Welch p=0.027 (PnL)
  IS   : baseline 55.0% +$0.25 → kept 61.5% +$1.60 | blocked 48 (23W/25L) -$1.35
  OOS  : baseline 39.0% -$0.77 → kept 34 41.2% -$0.06 | blocked 7 (2W/5L) -$0.71 ; Welch p=0.059; permutation p≈0.14
```
All spec figures reproduce exactly. Extended-sample caveat: with the 44 underscore trades added (they mostly get blocked — 32 of 44, and those were 72% winners), the LONG blocked basket becomes n=85 **44.7% WR** −$2.40 and the WR separation weakens (Fisher p=0.089; PnL improvement still solid, Welch p=0.004). Component decomposition (my finding): the SHORT gate's edge is carried almost entirely by the RSI<40 block (blocked n=27 −$1.78); the flat block removes 30 trades at **53.3% WR** (−$0.41) and only 4 OOS trades.

### Claim 4 — flat momentum
```
LONG  flat: FULL 23T 26.1% -$1.75 | T1 -$0.43 | T2 -$0.59 | T3 -$0.73   → loses in all 3 splits ✓
SHORT flat: FULL 36T 52.8% -$0.19 | T1 +$0.06 | T2 +$0.10 | T3 -$0.35   → POSITIVE in T1 and T2 ✗
```
"Both directions, all three splits" is true only for LONG. Moreover, blocking flat alone for SHORT keeps a *worse* basket (kept 46.6% −$1.29 vs blocked 48.3% −$0.42, full sample) — consistent with the spec's own §7 note, but it means the SHORT flat rule is noise inside the combo, not validated edge.

### Claim 5 — confidence
```
conf>=90: n=155  77W  WR=49.7%  PnL=-$0.03     (spec said 50.3% — trivial window drift, same conclusion)
conf<90 : n=105         WR=43.8%  PnL=+$2.10   (Fisher conf90+>conf<90: p=0.21, n.s.)
60-70 bucket: n=16 +$0.15 (positive, tiny n) ; 70-80 bucket: n=74 +$3.13 (the real positive bucket)
```
AGREE. Side note: `round2.py` prints these buckets under the label "flow_score" while actually querying the `confidence` column — cosmetic script bug; interpretation in the spec is correct.

### Claim 6 — instant-chase execution
```
LONG with staleness present: n=90 (of 119!) 43.3% +$2.17
  <2m : n=55 (18W/37L) 32.7% -$1.86          ← exact match
  >=2m(known age): n=35 (21W/14L) 60.0% +$4.03
  Fisher(>=2m ><2m) p=0.0099 ; Welch p=0.0069
Terciles within the <2m group: 33.3% / 27.8% / 36.8% WR — all <50% ✓, but PnL by tercile: -$0.57 / -$1.39 / +$0.10 → T3 is marginally POSITIVE.
```
The spec's "+$4.45 / ~50%+" for ≥2min = **all non-<2m LONGs including 29 NULL-staleness trades** ((52−18)/64 = 53.1%, +$4.45) — NULL staleness is "unknown", not "≥2min". Direction of conclusion unchanged, but 29/119 LONG trades (and 85/260 overall) have NULL staleness_minutes — a missing-data caveat the spec does not disclose. My tercile cut differs from the spec's (28.6/30.8/36.4 — they likely terciled differently); by WR my cut agrees, by PnL the third tercile is +$0.10.

### Claim 7 — wave_phase
```
Pooled (hyphen sample): bottoming n=32 65.6% +$1.28   ← exact match to spec
  LONG  bottoming: n=14 (7W/7L) 50.0% -$0.12
  SHORT bottoming: n=18 (14W/4L) 77.8% +$1.40
Per-split pooled: T1 66.7% +$0.21 | T2 83.3% +$0.14 | T3 64.7% +$1.10
```
The headline number pools both directions. Since v5 was a LONG-only signal, the correct counterfactual is the LONG basket: 14 trades, breakeven. "v5's filter would block winners" overstates — it would block ~breakeven trades (LONG), while the "winner band" claim is true only for SHORT. (Extended sample pooled: n=35 68.6% +$1.45 — same story.)

### Claim 8 — z-score
```
LONG  z<-1.5: would block 0 trades
SHORT z>+1.5: would block 1 trade (GMX 2026-09-23, z=+2.22, pnl=-$0.01)
NULL z_score: 0 rows
```
"Zero" is literally off by one; economically dead code — AGREE.

### Claim 9 — NULL metadata
```
n=260 : NULL rsi_14=39 ✓ | NULL momentum_state=0 ✓ | NULL z_score=0 | NULL wave_phase=0
        NULL staleness_minutes=85 (undisclosed in spec) | fully-NULL metadata rows=0
```

### Claim 10 — momentum formula (the decisive test)
Code: `signal_schema._enrich_indicators` (lines 450–515) computes `momentum_state` as 5-bar velocity over `prices = get_price_history(token, 60 min)` → the `price_history` table, which is written on **60s bars** (signal_schema.py:4435–4437: "price_history: write on MINUTE boundaries only … signals assume 1 bar = 60s"). RSI in metadata likewise comes from **candles_1m** (line 473). The spec's quoted thresholds (rising >+0.1, falling <−0.1, else flat, 5-bar) are correct — but the **bar is 1 minute, not 5**. Spec G4 says compute from `candles_5m` ⇒ 25-minute velocity.

Empirical recomputation at the175 historical signal times (signal_time ≈ open_time − staleness):
```
Historical formula (1m, 5-min window):  agreement with metadata label 77.1%
Proposed 5m formula (5m, 25-min window): agreement with metadata label 72.0%
Two formulas agree with EACH OTHER:      66.3%
Flat-rate:  1m formula 26.9% (47/175)  vs  5m formula 6.9% (12/175)
Flat-block gate decision differs: 47/175 trades (27%)
LONG gate with metadata labels: blocked 19 flat trades (26.3% WR, -$1.32)
LONG gate with 5m-computed labels: blocked only 4 flat trades (25.0% WR, -$0.62)
```
**Conclusion: "zero calibration gap" is false.** The validated flat-block edge (blocking ~$1.3 of losers across ~19 LONG trades) largely evaporates under the spec's proposed implementation, because a ±0.1% threshold over 25 minutes is almost never met. One of the two shipped gates would be a near no-op while claiming validated backing.

---

## 3. Statistical-Rigor Audit of the Spec

**Legitimate:** the IS/OOS split is genuinely time-ordered (first/last 30% by `open_time`), no label leakage in the split mechanics; sample is closed-only with **zero open pump-chain trades pending** (checked — no right-censoring); the spec discloses NULL rsi, discloses SHORT weakness, ships kill criteria, and lists rejected candidates (§7) — good practice against silent re-proposals.

**Not legitimate (must be corrected in the spec's wording):**
1. **The "OOS" is not held out.** `round3.py` evaluated every candidate predicate on IS, OOS **and** FULL simultaneously, and the spec's own selection rule ("must improve in full AND OOS, blocked basket net-negative") used the OOS to choose the gates. The last 30% participated in selection. Call it a *multi-split robustness screen*, not out-of-sample validation. True holdout = pick on IS, evaluate once on OOS.
2. **Multiplicity.** ≥12 candidate predicates were screened across splits (round2 tested z, speed, volume, confidence, flow; round3 tested 6+6 RSI/momentum combos). LONG's full-sample separation (Fisher p=0.002, permutation p=0.004) survives a Bonferroni-style haircut; SHORT's does not (Fisher p=0.22 full, Welch p=0.059 / permutation p≈0.14 OOS).
3. **Sample adequacy.** OOS LONG kept = n=20; OOS SHORT blocked = n=7. The spec admits SHORT OOS is weak — my numbers show it is *not statistically distinguishable from random* (14% of random 7-trade blocks do as well). LONG is adequate; SHORT is a monitoring bet, exactly as §8 says — but §1's table presentation oversells it.
4. **Band instability at boundaries.** LONG RSI>70 flips sign with an off-by-one: strict `>70` = n=20 40.0% **+$0.32**; `70≤RSI<100` = n=23 34.8% **−$0.23**; RSI exactly 70.0 = n=3, all losers. The spec quotes BOTH "+$0.32" (§7) and "33.3% −$0.52" (§3) without reconciling — an internally inconsistent presentation of a noise-level band.

---

## 4. Integration-Point Verification (vs actual code)

| Spec says | Reality | Verdict |
|---|---|---|
| `signal_schema.add_signal` component checks needed for v6+/- | ✓ Per-component checks exist in the claimed pattern (pump-chain+ at :1970, pump-chain- at :1978) | CORRECT |
| `is_component_disabled()`: add constants to ITS import block, "missing this = NameError kills ALL compaction" | ⚠ The import block is inside `try/except ImportError: return False`. A missing constant **silently allows ALL components** (guard disables itself) — it does NOT crash compaction. Advice stands; stated failure mode is wrong (silent fail-open is arguably more dangerous) | PARTLY WRONG |
| `volatility_gate.py` REGIME_SIGNALS += v6 | ⚠ There is a **second, enforcement-side copy** in `volatility_gate_v2.py:45`. `decider_run` uses `should_trade_v2`, which **SKIPs any signal not in its REGIME_SIGNALS** ("not suited for regime"). Adding only to volatility_gate.py would hard-skip every v6 trade in every regime. The spec's §6.3 names only the v1 file | CRITICAL OMISSION |
| `signal_compactor.SIGNAL_SOURCE_WEIGHTS` += v6 (1.0) | ✓ exists (`('pump-chain','pump-chain+')=1.2` currently) | CORRECT |
| `STANDALONE_BYPASS_SIGNALS` += v6+/- needed | ✓ correct — matching is exact/strip-based; `'pump-chain-v6+'` does not match the existing `'pump-chain'` entry (digit-stripping quirk documented at compactor:4260) | CORRECT |
| `PROFIT_MONSTER_BYPASS_SIGNALS` += v6 | ⚠ Redundant: profit_monster matches by substring `signal LIKE '%pump-chain%'`, and `'pump-chain'` is already in the tuple — v6 sources **already bypass**. Harmless, but mis-framed as required | MINOR ERROR |
| §5: v6+ "routes into the existing pump_exit / v6- into rr_engine (existing routing)" | ❌ **FALSE.** `SIGNAL_EXIT_CONFIG` has no v6 keys, and `_match_exit_config` (position_manager.py:2751, deliberately fixed 2026-09-30 to prevent raw-prefix matches) does NOT match `'pump-chain-v6+'`/`'pump-chain-v6-'`. They fall through to the **default exit path**. Explicit `SIGNAL_EXIT_CONFIG` entries are mandatory; §6.3's checklist omits them | SPEC BUG |
| (not mentioned) | ❌ **Undisclosed inherited blocks:** ~15 compactor/decider locations match `('pump-chain' in source or 'pump_chain' in source)` and will silently apply to `pump-chain-v6±`: SHORT HIGH block (enabled — consistent with spec), **SHORT RSI_MIN=45 compactor block (enabled — conflicts with spec's SHORT floor of 40)**, LONG RSI 35/85 block (enabled, redundant), dead-hours blocks (currently inert, lists empty), BTC-chop exemptions, rescue paths. The 19 kept SHORT trades at RSI 40–45 (63.2% WR +$0.48) **cannot execute** under the live 45 floor | CRITICAL OMISSION |
| §8 monitors `signal_outcomes` by signal_type | ✓ table exists in `signals_hermes_runtime.db` with `signal_type`; `signal_decay_detector.py` exists | CORRECT |
| New signal_type is safe from monte_carlo_gate | ✓ `MC_MIN_TRADES=10` → new types allowed | CORRECT |
| Not a slow signal (same cost class as pump_chain_long) | ✓ `pump_chain_long` is not in `_SLOW_SIGNALS` | CORRECT |

**Min-age guard vs staleness ceiling (spec §6.4):** the premise is factually wrong. `SIGNAL_STALENESS_MAX_AGE_MIN=5` has been **WARN-ONLY since 2026-09-04** (decider_run.py:3565–3571: "Remove hard 5min staleness block … conditions will be verified"). There is no hard 5-minute ceiling, so the "window is 2–5 min" framing is invented. The guard is still implementable, but the spec must define **retry semantics** (a <2min skip must re-examine the signal later, not mark it executed/skipped-and-done) and consider interaction with the price-drift check (drift vs detection price grows with waiting). Evidence base: 55 trades, p<0.01, but with the NULL-staleness/tercile caveats from Claim 6.

**Fail-open safety:** acceptable for RSI (39/260 unknown; downstream 35/85 LONG floor and 45 SHORT floor also fail open when compactor RSI missing — small exposure; the 40–45 SHORT band is actually +EV in this sample, +$0.48). Fail-open on missing candles is fine mechanically — but under the 5m formula the flat gate is nearly a no-op anyway (6.9% flat-rate), so fail-open is moot until Claim 10 is fixed.

**Pitfall-register fact checks (§2):** V5 reading "last closed trade's metadata" ✓ confirmed in `pump_chain_v5.py:155–187` (`ORDER BY close_time DESC LIMIT 1`); V5 "90% WR claim was n=10" ✓ consistent with v5's own docstring; V4 "BTC oscillator block, 15.4% −$1.51, NEVER_REENABLE" ✓ consistent with hermes_constants:1864 + v4 docstring; V2 "93.5% on 73 in-sample" ✓ consistent with `2026-09-09_pump-chain-v2-verdict.md` (73-trade baseline 57.5%, in-sample 93.5%); V1 "57.5% WR" ✓ (same baseline); "source-string zoo" ✓ confirmed in DB (`ADA(1.73x),ZRO(1.52x)),pump-chain+` etc.) and in `pump_chain_long.py:229–230`; CASHCAT "−6.4% with pump_exit" ✓ matches SIGNAL_EXIT_CONFIG comment. §8's "pump_chain_long 14d 22T 59.1% +$2.21" reproduced as 13W/22T at author time (now 24T 54.2% +$1.99 — window drift). **One unverifiable item:** no repo artifact for the exact V2 "93.5% verified" wording beyond the prior verdict (the v2 spec file itself is gone) — consistent, not independently confirmable.

**Additional spec-internal contradiction found:** §3 claims LONG RSI>70 = "33.3% WR −$0.52" while §7 claims the same blocked basket is "+$0.32". My resolution: the band is sign-unstable at the RSI=70 boundary (−$0.23 to +$0.32) — it is **not** a validated loser band. Critically, the CEO raised live `PUMP_CHAIN_LONG_RSI_MAX` 70→85 on **2026-10-07** with the note *"Old 70 threshold blocked profitable trades."* Shipping an RSI>70 detection block in v6 re-introduces, under a new name, a filter the CEO killed one day earlier. Removing the >70 rule improves the LONG gate's kept PnL in FULL (+$5.35 vs +$4.96) and IS (+$2.82 vs +$2.30), costing only −$0.13 in OOS — i.e., the rule is cherry-picked from the one split where it helps.

**Regime evidence check (§6.3):** baseline LONG PnL by regime: EXTREME +$3.66 (n=80), HIGH −$0.41 (n=32), NORMAL −$0.66 (n=7) — "EXTREME carries all PnL" ✓ directionally (magnitude differs from spec's +$3.03; drift). With the gate applied, HIGH kept = 14T 57.1% +$0.92 — the gate, not the regime table, justifies keeping HIGH. Gate holds within regimes (EXTREME kept +$4.16 vs blocked −$0.50; HIGH kept +$0.92 vs blocked −$1.33).

---

## 5. Required Changes Before Implementation (ordered)

1. **Fix the momentum gate's data source (claim 10).** Either compute momentum_state from `price_history` 1-minute bars (exact historical formula, zero gap is then true) or re-run the round3-style validation with 5m-computed labels. Under the 5m formula the flat gate blocks 4/19 of the validated trades — do not ship it as "validated".
2. **Drop the LONG RSI>70 block** (band is +PnL full-sample, sign-unstable, and directly contradicts the CEO's 2026-10-07 PUMP_CHAIN_LONG_RSI_MAX=85 decision).
3. **Resolve the SHORT floor conflict:** either raise the spec's SHORT gate to ≥45 (align `PUMP_CHAIN_V6_SHORT_RSI_MIN` with live `PUMP_CHAIN_SHORT_RSI_MIN=45`) or explicitly document that kept-trade stats include 40–45 RSI trades the compactor will block.
4. **Add explicit `SIGNAL_EXIT_CONFIG` entries** ('pump-chain-v6+' → pump_exit, 'pump-chain-v6-' → rr_engine) — the "existing routing" claim is false.
5. **Register in BOTH `volatility_gate.py` and `volatility_gate_v2.py` REGIME_SIGNALS** — v2's should_trade_v2 hard-SKIPs unknown sources.
6. **Correct §6.3's `is_component_disabled` failure-mode claim** (silent allow-all via caught ImportError, not a NameError crash).
7. **Correct §6.4's staleness premise** (5-min ceiling is warn-only since 2026-09-04) and define min-age retry semantics.
8. **Decide on the 44 `pump_chain` underscore trades** — include them (n=304) or justify exclusion; note they flip some per-band signs (e.g., LONG RSI>70 becomes 60.8% +$0.41).
9. **Re-label "OOS" honestly** as a time-split robustness screen (both splits were used in selection); keep the permutation/Fisher p-values in the spec instead of point estimates only.
10. **Disclose NULL staleness_minutes (85/260)** and restate the min-age evidence with NULL as its own bucket.

---

## 6. Overall Recommendation

**FIX SPEC FIRST — do not implement as written; do not reject.**

The core of v6 is sound: the LONG gate's edge is real, permutation-verified (p≈0.004 full / 0.013 OOS), consistent within regimes, and its blocked basket is genuinely net-negative. The SHORT gate is a correctly-hedged monitoring bet. But two of the spec's load-bearing claims are false as implemented: the momentum gate would be computed from a *different feature* than the one validated (claim 10 — flat-rate 6.9% vs 26.9%), and the exit routing it assumes does not exist. Combined with the undisclosed inherited substring blocks (SHORT RSI 45 floor), the missing v2 REGIME_SIGNALS registration, and the RSI>70 rule contradicting the CEO's day-old decision, implementing per the current spec would produce a signal that is neither the backtested one nor safely integrated. After the 10 changes above (a small spec revision, not a redesign), proceed to implementation with the paper phase and kill criteria as written.

**Confidence level: HIGH** on all reproduced numbers (8/10 claims matched exactly; every discrepancy traced and explained); **HIGH** on the claim-10 formula finding (direct code path + empirical recomputation at 175 historical signal times); **MEDIUM-HIGH** on integration findings (single-pass code reading across compactor/decider/position_manager; the two critical items — v2 REGIME_SIGNALS skip and exit-config non-match — were re-verified by tracing the exact matching code).

*Audit scripts: /tmp/audit_v6_part1.py … part5.py (independent re-implementation; authors' scripts were not executed).*
