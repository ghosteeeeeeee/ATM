# CEO DECISION BRIEF — GATE USEFULNESS DEEP DIVE (T: "THIS IS VERY IMPORTANT")

Requested by T, marked high-priority. Window Oct 4 → Nov 19 2026 (46 days, shadow + live). Package: `analysis/2026-11-19_gate-usefulness-deepdive.md` (corrected revision with §10 correction ledger), engine `analysis/gate_usefulness_deepdive_2026-11-19.py` + `.out` (run-4), self-audit `analysis/gate_usefulness_selfaudit_2026-11-19.py` + `.md` (**6/6 PASS on final build**), exports `analysis/exports/nov19_*` (events TSV = 83,593-row snapshot of record), independent verdict `brain/verdicts/2026-10-19...` → correct: `brain/verdicts/2026-11-19-gate-usefulness-own-conclusions.md`, auditor working code `/tmp/oc_nov19/`. Lineage: Oct-8 gate audit (55 gates, dual-verified) → deadlock-thesis kill (10-12) → conundrum package D1-D6 (10-12, your ALL-GO) → shadow redundancy v2 (10-30, your 6/6) → THIS. **0 config changes at any stage; DO-NOT-MODIFY and protected flags intact throughout.**

## T's three complaints — all verified (own-conclusions C1 AGREE)

1. **Frequency collapse CONFIRMED:** 47.0 trades/day (Sep-7 week) → 13.2/day (current) = **−72%**.
2. **Long WR below coin-toss CONFIRMED:** LONG n=729, WR **46.4%**, net **−$6.89** (since Oct 4).
3. **Not profitable CONFIRMED:** SHORT n=318, WR 48.7%, net −$1.71. Both directions negative.

## Headline findings (46 days, 56 gates, cluster-robust, Bonferroni 0.0009)

- **USEFUL (2):** **PUMP-CHAIN-RSI-MAX** (n=1,027, excess4h −0.190%, p_tok=0.012 p_day=0.005) — the ONLY gate robust under all three baselines (cross-mean/median/BTC); **LONG-RSI-CEILING** (n=989, −0.188%, p_tok=0.049; baseline-dependent — see caveat).
- **BLOCKS-SETUPS (0)** under the reference baseline — **but power-limited: median MDE 0.227% at n≥400; a gate harming +0.15%/block would be undetectable.** This is a detection-limit statement, not proof of absence.
- **USELESS (27 no-edge gates = 82.4% of episodes / 85.8% of events of all block volume):** CONFLUENCE-GATE-BLOCK (3,436 eps −0.063), CONTINUUM-BLOCK (2,831), CONTINUUM-BULL (2,362), SHORT-RSI-HARD-FLOOR (2,194 −0.005), LONG-NEUTRAL-CHOP (1,915, still a wash), LONG/SHORT-NEUTRAL, OVERSOLD-SHORT, **RR-ENGINE (1,416 −0.048)**, **BTC-CRASH (1,232)**, CTX-GATE (LLM), BTC-CHOP-GATE (869, non-replication holds), SHORT-CONTINUUM, PUMP-CHAIN-HIGH/SHORT-HIGH, LONG-RSI-BLOCK, et al. — |excess|<0.10%, p≥Bonferroni: they neither help nor hurt per block.
- **MIXED/watch (20):** VOL-GATE-BYPASS (+0.117, p_day=0.015 — but flips to NO-EDGE when Oct 4-20 restored: period-dependent), SPIKE-FILTER (−0.157, p_tok=0.008 — probable worker), SLOPE-FILTER (+0.130, cluster-ns, harm direction now consistent across FOUR separate studies), PUMP-CHAIN-VEL post-deadband (−0.347, p_day=0.045), MAXXED-BLOCK (kills big moves at 45% vs own tokens' 9% base rate, n=44), CONFLICT-RESCUE-BLOCK (n=19, too small).
- **FUNNEL:** blocked episodes steady 4.3k–9.4k/week while trades halved twice (242→53/wk); ratio 21:1 → **93.5:1**. Consistent with UPSTREAM starvation (signal volume/confluence/confidence) but NOT proven — the signal-side denominator was never measured (see D3 below).
- **Big moves:** 164 blocked episodes printed dir-MFE≥10% (three cases blocked by FOUR gates each: BLUR +32.9%, CASHCAT +22.1%, NXPC +29.6%); but blocked-set averages ≈ market — concrete misses exist, class claim doesn't hold.
- **Robustness:** coalescing flips 1–2/20; OOS flips 9/20; WORKS pair same-sign both halves.

## Verification trail (why you can trust these numbers)

- **Independent own-conclusions verdict:** `brain/verdicts/2026-11-19-gate-usefulness-own-conclusions.md` — C1/C5/C6 AGREE, C2/C3/C4/C7/C8 PARTIAL; **all 8 defects corrected** (§10 ledger): two-run splice fixed, 99%→82.4%, RR-ENGINE's 3,402 events restored (emoji-parser gap), survivorship/baseline/power limits disclosed, C3 starvation claim softened, C7 prune narrative retracted (routine 30d incremental retention, no mass delete; ALL 24,699 pre-horizon events were lookahead at run — guard fixed them).
- **Self-audit 6/6 PASS** on final build (independent re-coalescing, raw-log line checks, SQL-baseline to 4dp, sign consistency, dedup, MFE checks) — it also caught 3 of its own bugs AND an engine case-sensitivity regression mid-correction (BTC-CHOP 868→210 biased subset → fixed, restored n=869).
- **Data caveats:** candles_5m has 30d rolling retention (pre-Oct-21 values non-regenerable — exports are the snapshot of record); raw pipeline logs Oct 4–30 deleted (rotator now retains going forward); 8 gates invisible to the gate_shadow recorder's regex (its emoji set lags the log format).

## Decisions requested (reply GO/NAY + reasoning per item)

D1. **External hand-off:** package is corrected + self-audited 6/6 — confirm it goes to the external auditor as-is (T's stated next step).

D2. **Nov-6 removal queue — now overdue:** your Oct-30 D1 ratified CONTINUUM-BLOCK / CONTINUUM-BULL / PRESERVE-SPIKE-BLOCK as removal tests "at the re-audit"; Nov 6 has passed and this 46-day study supersedes it (both gates confirmed NO-EDGE, CONTINUUM pair solo 13–17% = functionally redundant). Options: (a) GO removals under shadow-first (disable, log would-blocks, 14d, per the automatic-implementation pattern); (b) hold until the R1 dollar-closer exists (your standing position); (c) set a new date. Which?

D3. **Commission the frequency-collapse root-cause analysis** (T's complaint #1): signal emissions/week (the missing denominator), confluence-expiry rates/week (expiry_shadow has 63k events), confidence-floor rejections/week — all derivable from existing data, none measured yet. This answers WHY trades halved while block volume stayed flat.

D4. **Ratify the registry entries:** PUMP-CHAIN-RSI-MAX = WORKS/triple-baseline keeper; LONG-RSI-CEILING = WORKS-reference (baseline-sensitive flag); SPIKE-FILTER + PUMP-CHAIN-VEL = probable workers (monitor); the 27 no-edge gates = efficiency-removal candidates pending D2's instrument. Update brain/gate_registry.md accordingly.

D5. **Harm candidates:** SLOPE-FILTER (4-study direction, cluster-ns), VOL-GATE-BYPASS (p_day=0.015 but period-dependent), MAXXED-BLOCK (extreme tail-kill, n=44) — monitor-only until the R1 extended closer (still unbuilt — your Oct-12 D1 GO; the built-in closer remains the weak 52%-agreement join)? Or commission R1 now as the missing instrument for dollar-level tail/removal decisions?

D6. **Data retention:** extend candles_5m retention beyond 30d (older analyses become unverifiable — this study already lost Oct 4-20 values) and fix the gate_shadow recorder's emoji set (8 gates currently db=0)? Both are observability-only.

D7. **Detection-limit acceptance:** BLOCKS-SETUPS=0 means "no harm ≥0.23%/block detectable at n≥400" — do you accept this as the operating statement (documented in registry), or require longer windows before trusting any no-harm claim?

## Constraints honored
hermes_constants.py untouched; no gate removed/relaxed; all claims cluster-tested per brain/SOPs §10 claim-hygiene standard; every number traceable to .out sections or TSV columns; correction ledger documents every v1→v2 delta.
