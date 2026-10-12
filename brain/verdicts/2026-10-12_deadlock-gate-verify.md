# Adversarial Verification — "Deadlocked Gate Stack" Claims (2026-10-12)

**Auditor:** independent (nothing trusted; every number below re-derived from raw logs / brain.trades / candles_5m with my own code in `/tmp/audit/`).
**Data frozen at:** 2026-10-12 19:28 UTC (`pipeline_current_snapshot.log` — the live log grows; all log counts are as of this snapshot).
**Evidence files (all in `/tmp/audit/`):** `parse.py` (block/pass parser), `c1c2.py/.out` (census + pincer + nulls), `c3456.py/.out` (chop/RSI/forward-returns/cohorts), `attacks.py/.out` (same-token pairs, permutation tests, timezone), `rsi_check.py/.out` (independent candle-computed RSI), `extra.py/.out` (timeframe ID, regime splits), `blocks.tsv` (123,359 parsed block lines), `episodes.tsv` (13,669 coalesced), `passes.tsv` (201,507 ✅ lines), `trades.tsv` (1,338 live closed trades since 09-01).

**Parser scope (fixed once, applied everywhere):** a block line requires the `🚫` marker + `[GATE]` + token + `LONG|SHORT` (a `TOKEN:DIRECTION` form included). `[rr-engine] SHADOW BLOCK` lines (2,407) contain no 🚫 and are excluded by construction. Exact duplicates on (ts, gate, token, direction) are merged (handles the archive 10-02→10-03 overlap and double-timestamp PENALTY-BLOCK lines). Episodes = per (gate, token, direction) coalescing with gap > 60 min.

---

## C1 — BLOCKER CENSUS: **KILLED (not reproducible; window-fraud on one gate, threshold mislabels on another)**

Claimed table vs my independent parse (09-29 00:00 → 10-12 23:59; log coverage actually starts 09-29 03:23):

| Gate (claimed) | claimed hits | my raw lines | my episodes | first seen | days active |
|---|---|---|---|---|---|
| SHORT-RSI-HARD-FLOOR | 1,340 | **1,517** | **89** | **2026-10-12 00:33** | **<1 day** |
| PUMP-CHAIN-SHORT-HIGH | 552 | 5,397 | 510 | 09-29 08:51 | 10 |
| HALL-SHAME (SHORT) | 319 | 2,580 (S) + 3,992 (L) | 234 S + 352 L | 09-29 03:37 | 14 |
| CONTINUUM-BULL | 254 | 5,969 | 590 | 10-05 21:23 | 8 |
| CONTINUUM-BLOCK (LONG) | 1,302 | 14,623 | 1,401 | 09-29 03:24 | 13 |
| LONG-NEUTRAL | 705 | 13,488 | 1,233 | 09-29 03:24 | 14 |
| LONG-NEUTRAL-CHOP | 389 | 1,218 | 151 | **2026-10-11 04:15** | **2 days** |
| LONG-RSI-BLOCK | 203 | 7,642 | 1,180 | 09-29 04:20 | 14 |
| PENALTY-BLOCK | 166 | 3,468 (L+S) | 455 | **2026-10-06 18:32** | 7 |
| SHORT-NEUTRAL | 192 | 9,525 | 875 | 09-29 03:26 | 14 |

**Actual top blockers (raw lines / episodes):** SHORT-CONTINUUM 22,018/1,646 · CONTINUUM-BLOCK 14,623/1,401 · LONG-NEUTRAL 13,488/1,233 · SHORT-NEUTRAL 9,525/875 · LONG-RSI-BLOCK 7,642/1,180 · CONTINUUM-BULL 5,969/590 · PUMP-CHAIN-SHORT-HIGH 5,397/510 · PUMP-CHAIN-SHORT-RSI-MIN 5,278/567 · HALL-SHAME 6,572/586 · SHORT-RSI-FLOOR 2,439/392 · **SHORT-RSI-HARD-FLOOR 1,517/89**.

Why the census fails under every parser choice:
1. **SHORT-RSI-HARD-FLOOR is a <24-hour-old gate** (first line 2026-10-12 00:33, "blocked at approval … < 45"). Presenting it as the #1 SHORT blocker "over ~2 weeks" is a window artifact. Its predecessor SHORT-RSI-FLOOR (threshold drifted 50→40→45 during the window — verified in message text and consistent with hermes_constants comments) did 2,439 lines / 392 episodes over 13 days; even merging the family gives 3,956/481, still behind SHORT-CONTINUUM/CONTINUUM-BLOCK/NEUTRAL.
2. Claimed numbers match neither raw lines nor 60-min-coalesced episodes for any gate (closest: CONTINUUM-BLOCK episodes 1,401 vs claimed 1,302 — 7% off; everything else is 2–30× off). Per-minute re-logging inflates raw lines ~9× (123,359 lines → 13,669 episodes), so a census must state which unit it used; this one can't be reconciled with either.
3. **Mislabels:** PENALTY-BLOCK fires at `exec_conf < 50%`, not "conf<40%". HALL-SHAME fires on BOTH sides (it's the 30d-WR hall of shame for either direction), not a SHORT-side gate. LONG-NEUTRAL-CHOP and PENALTY-BLOCK are brand-new filters being counted as if they had 2 weeks of history.

**Verdict: KILLED.** Do not use this census for anything. Correct census = the table above (files: `c1c2.out`).

---

## C2 — THE PINCER: **statistic reproduces (even higher than claimed) but the NULL KILLS it — the "deadlock" narrative is refuted**

**Reproduction:** 328/329 hours (99.7%) in log coverage had ≥1 block episode on BOTH directions (claim: 324/329, 98%). Avg distinct gates per both-blocked hour = **12.45** (claim 6.2 — their narrower gate scope). So the raw stat is real.

**Null models (my code, `c1c2.out`):**

| Null | Expected both-blocked hours | Observed |
|---|---|---|
| N1: keep each hour's block count, sample direction iid at global mix (52.2% SHORT) | **329.0 / 329 (100.0%)** | 328 (99.7%) |
| N2: Monte-Carlo permutation of direction labels across all 123,359 block-line instances (200 trials) | **329.0 / 329 every trial** | 328 |
| N3: same at episode level (13,669 episodes, 41.5/hour, 51/49 mix) | **328.9 / 329 (100.0%)** | 328 (99.7%) |

With ~375 block lines/hour (~42 episodes/hour, ~21 per direction), P(an hour has zero SHORT-block episodes) = e^−20.2 ≈ 5×10⁻⁷. The observed statistic is not merely compatible with the null — it is **1 hour below** what pure direction-coin-flipping predicts. "98% of hours have both directions blocked" carries zero information about a deadlock; it is a restatement of the fact that ~20 gate families evaluate ~80–100 tokens every minute.

**Attack (a) — per-minute re-logging / same tokens?** Re-logging inflates lines 9×, but the conclusion is unchanged at episode level (328/329). Same-token detail: **316/328 both-blocked hours (96.3%) contain ≥1 token blocked LONG *and* SHORT in the same hour** (top: BTC itself 194h, CHIP 82h, APT 59h, INJ 57h). Avg **31.3 distinct tokens** blocked per both-blocked hour. So "both blocked" mostly means the same liquid tokens are perpetually in some gate's blocked state in both directions simultaneously — the signature of always-on thresholds, not of a directional pincer.

**Attack (b) — did anything pass?** **326/328 both-blocked hours (99.4%) had ≥1 ✅ gate-pass on LONG and ≥1 on SHORT.** There is no hour in the window where either direction was actually shut. A "deadlock" that passes signals in both directions in 99.4% of hours is not a deadlock.

**Attack (c) — executions:** 347 live trades opened in the window; **343/347 (98.8%) opened during a "both-blocked" hour** (vacuously, since 99.7% of hours are), and **168/328 (51.2%) of both-blocked hours produced ≥1 execution**. The claim's "135 live trades in 10-02→10-08" does not reproduce under any convention: 174 opened [10-02, 10-08), 185 opened [10-02, 10-09), 187 closed in that window.

**Narrative kernel that survives (weakly):** the *specific* claimed pairing is only intermittently true. In BEAR hours (CONTINUUM-BLOCK fired; 170 hours), the SHORT side's top blockers were SHORT-NEUTRAL 62%, PUMP-CHAIN-SHORT-HIGH 61%, and **SHORT-RSI-FLOOR only 49%**. In BULL hours (51), top LONG blockers were PUMP-CHAIN-RSI-MAX 84%, CTX-GATE 80%, LONG-NEUTRAL 76%, LONG-RSI-BLOCK 59%. The gates do co-fire by BTC state, but every gate family also fires in most *other* states on some token — the co-firing is not distinguishable from base rates.

**Verdict: KILLED as evidence of deadlock.** The gate stack is permeable in both directions at all times; the hour-level co-block stat is statistically vacuous.

---

## C3 — CHOP CONCENTRATION: **CONFIRMED (the concentration); "chop trades lose" KILLED**

Trades = live closed, opened 09-29→10-12 (n=347). Chop = |BTC 30m velocity| at open hour computed from candles_5m (6×5m close ratio — the same definition the PUMP-CHAIN-VEL gate logs).

| Threshold | Chop n / WR / net$ / net% / mean% | Trend n / WR / net$ / net% / mean% |
|---|---|---|
| 0.2% | 247 / 48.6% / **+$0.69** / +68.66 / +0.278% | 100 / 53.0% / $0.00 / +9.43 / +0.094% |
| **0.3%** | **290 (83.6%) / 50.0% / +$0.59 / +75.64 / +0.261%** | 57 / 49.1% / +$0.10 / +2.45 / +0.043% |
| 0.5% | 313 / 49.8% / +$0.80 / +93.48 / +0.299% | 34 / 50.0% / −$0.11 / −15.39 / −0.453% |

- **Concentration: CONFIRMED.** 83.6% of trades open in chop at 0.3% (claim 86% — same picture; the few-point gap is velocity anchoring, not substance).
- **"Chop trades lose": KILLED at every threshold.** Chop trades are net **positive** in dollars (+$0.59) and percent (+75.6 pct-units, mean +0.261%/trade); trend trades are ~flat (+$0.10). The earlier refutation holds.
- **Where the losses actually are:** direction split at 0.3% — chop **LONG** n=231, WR 53.7%, **+$3.28 / +109.6 pct-units** (the system's best cohort); chop **SHORT** n=59, WR 35.6%, **−$2.69 / −33.9 pct-units**. Trend LONG −$0.48; trend SHORT +$0.58. The bleed is **shorting into flat markets**, not "chop" per se.
- Regime by continuum log-state at open hour: LONG trades in bear-state hours n=88 net −$0.11; bull-state n=49 +$0.81; **no-continuum-fire hours n=136, WR 58.1%, +$2.10** — the profit engine is longs in unremarkable hours, which the stack does permit.

---

## C4 — RSI FLOOR EVIDENCE: **direction weakly CONFIRMED; claimed magnitudes and "≥45 PAYS" KILLED; evidence column itself unreliable**

Constants comment (hermes_constants.py:905): "30d SHORT RSI<45 = 114T 34.4%WR −$5.52 vs ≥45 = 246T +$3.53". Independent re-derivation from brain.trades:

**Stored `entry_rsi_14`, window 09-07→10-07 (the claimed 30d):**

| band | n | WR | net$ | net% |
|---|---|---|---|---|
| <40 | 100 | 46.0% | −2.88 | −83.7 |
| 40-45 | 38 | 44.7% | −1.75 | −31.6 |
| 45-55 | 81 | 49.4% | +0.21 | +14.7 |
| 55-65 | 39 | 48.7% | −0.01 | +3.8 |
| 65+ | 43 | 48.8% | −1.63 | −59.7 |
| **<45 total** | **138** | **45.7%** | **−4.63** | |
| **≥45 total** | **163** | **49.1%** | **−1.43** | |

The claimed split (114/246 trades, −$5.52/+$3.53) does not reproduce. **The ≥45 side is not profitable: it nets −$1.43.** Where "+$3.53" likely came from: `entry_rsi_14` is **missing for exactly the 65 trades of 09-08→09-11** (feature_recorder outage, verified day-by-day) and that RSI-less cohort netted **+$3.68 at 63.6% WR** — because the whole week 09-07→09-12 was profitable for shorts (n=123, WR 62.6%, +$2.37), not because of RSI. Imputing that cohort into ≥45 manufactures a profitable ≥45 cell. Period confound.

**Independent RSI — recomputed from raw candles_5m** (Wilder RSI-14 on the last *closed* 5m candle at trade open; window 09-12→10-07 where candles exist; n=230 of 241):

| band | n | WR | net$ | mean% |
|---|---|---|---|---|
| <40 | 63 | 36.5% | −3.77 | −1.60% |
| 40-45 | 45 | 42.2% | −0.60 | −0.20% |
| 45-55 | 84 | 41.7% | −1.98 | −0.76% |
| 55-65 | 28 | 60.7% | +1.56 | +1.25% |
| 65+ | 10 | 80.0% | +0.35 | +1.31% |
| **<45 vs ≥45** | 108 vs 122 | **38.9% vs 49.2%** | **−4.37 vs −0.07** | |

Permutation tests (one-sided, H1: <45 worse): **pnl_usdt diff −$0.0399/trade, p=0.038** (calc-RSI) / −$0.0318, p=0.083 (stored RSI); pnl_pct p=0.084 / 0.097. So: shorting oversold **does** underperform by ~4–10 WR points and ~$3–4/30d — real but **borderline significant and half the claimed magnitude**, and the "≥45 is a money-maker" half of the justification is **false**.

**Evidence-column reliability finding (sideways, important):** `entry_rsi_14` correlates only **r = +0.33** (mean |Δ| = 12.9 RSI points) with actual 5m Wilder RSI at trade open — the best of 5m/15m/1h attempts (15m r=0.19, 1h r=−0.01). The codebase itself flags it "DRIFT-E unreliable" (hermes_constants.py:1389). **Constants comments derived from entry_rsi_14 cohorts should be treated as unaudited.**

**Regime split (decisive, feeds C6):** the <45 bleed is **entirely a chop phenomenon**: chop RSI<45 shorts n=86, WR 36.0%, **−$4.56**; chop ≥45 n=103, WR 49.5%, −$0.63. **Trend** RSI<45 shorts n=22, WR 50.0%, **+$0.19**; trend ≥45 WR 47.4%, +$0.56. Post-10-07 (floor live): only 13 RSI-recorded SHORT trades total, 1 below 45 — the gate binds hard; the bypass cohort is too small to judge.

---

## C5 — PINCER COST: **KILLED — no meaningful missed edge in trend blocks**

Method: coalesced episodes; entry = open of first 5m candle with ts ≥ block_ts; fwd 4h = direction-signed (close at +4h / entry − 1); excess vs cross-sectional mean of ALL tokens with a complete 4h window at the same timestamp, direction-signed (LONG: fwd − market; SHORT: −fwd + market). Bootstrap 95% CIs (1,000 resamples).

| Cohort | episodes (covered) | mean excess4h [95% CI] | WR(excess>0) |
|---|---|---|---|
| **TREND-blocked (|vel|≥0.3%)** | 2,448/2,452 (99.8%) | **+0.0075% [−0.041, +0.061]** | 49.6% |
| CHOP-blocked (|vel|<0.3%) | 11,164/11,217 (99.5%) | **−0.0198% [−0.044, +0.005]** | 48.8% |
| CONTINUUM-BLOCK (LONG), trend | 323 | +0.033% [−0.083, +0.144] (raw fwd −0.53% — blocked longs fell WITH the market) | 52.6% |
| SHORT-RSI-FLOOR family, trend | 124 | **+0.148% [−0.086, +0.390]** | 56.5% |
| CONTINUUM-BULL / SHORT-CONTINUUM (block shorts), trend | 318 | −0.075% [−0.218, +0.058] (blocking shorts in BTC-strength helped) | 52.2% |
| TREND, deduped per (token,direction) | 1,735 | +0.013% [−0.044, +0.075] | 49.9% |

- Trend-blocked signals show **zero relative edge** (CI ±0.05%). At the live position size (~$11/trade), 2,448 trend episodes × 0.0075% ≈ **$2 of total missed edge over two weeks. Economically nothing.**
- Chop-blocked signals show slightly **negative** excess — blocking chop is mildly *good*.
- Only the SHORT-RSI-FLOOR family has a positive point estimate in trend (+0.15%/episode, = ~$0.02/signal at current size) — directionally interesting for C6, **not significant**.
- Survivorship/coverage: only 2 blocked tokens (CASHCAT, USELESS) lack candles in trend; ~15 in chop (mostly recent episodes censored by the 4h lookahead at the data edge). Coverage99.5–99.8% — no material censoring.

---

## C6 — TRADE-LEVEL vs COUNTERFACTUAL: **conflict is real but explained; neither side justifies confident claims**

**CONTINUUM-BLOCK (LONGs):** trade-level, LONGs that entered during bear-state hours (the bypass/override survivors): n=88, WR 47.7%, net −$0.11 (vs no-continuum-hour longs: n=136, WR 58.1%, +$2.10). Counterfactual (C5): trend-blocked LONGs excess +0.03% ≈ 0. No conflict once you note both are absolute-vs-relative: in falling markets any long prints negative dollars, and the blocked ones fell exactly with the market. **The gate neither demonstrably earns its keep nor demonstrably costs anything.** Selection caveat: bear-hour entrants are STANDALONE_BYPASS/override survivors, unrepresentative of all hypothetically-blocked longs — the counterfactual (all blocked tokens) is the better estimator here, and it says ≈0.

**SHORT-RSI-FLOOR/HARD-FLOOR (SHORTs):** genuine tension — trade-level <45 shorts **lose** (WR ~39–46%, net −$3.7..−$4.6/30d), while the C5 trend-block counterfactual says blocked trend shorts carried **+0.15% excess** (would have won). Resolution, in order of importance: (1) **regime mix** — the trade-level bleed is entirely chop shorts (C4 split: chop <45 = −$4.56; trend <45 = +$0.19), and the floor fires mostly in chop (357 of 481 floor episodes are chop); the counterfactual's positive subset is the 124-trend-episode minority. (2) **measurement basis** — 4h markout vs realized SL/TP/trailing PnL with fees; a blocked short that would have been stopped out looks different in the two ledgers. (3) **selection** — post-10-07 only bypass trades reach <45 (n=1); pre-10-07 the <45 cohort (n=138) was a normal mixed population, so the pre-period evidence is NOT bypass-contaminated. Bottom line: the two evidence bases measure different populations in different regimes and are both individually uncertain (n small, CIs wide). They do not jointly support "the gate prints money" nor "the gate is a disaster."

---

## ATTACK-VECTOR LEDGER (all checked)

- **Timezone:** DB session `Etc/UTC`, `now()` returns UTC; timestamp columns are naive but server-UTC. Spot-check: 40/40 random window trades have same-token log activity within ±2 min of DB `open_time`. No offset. Log and DB are aligned.
- **Log rotation gaps:** none. 329 consecutive hours (09-29 03:00 → 10-12 19:00), every hour has ≥4,900 lines. The two archives **overlap** (archive2 starts 10-02 20:24, archive1 ends 10-03 01:52) — deduped by (ts, gate, token, direction), so no double counting. Nothing before 09-29 03:23 exists; any "09-29" census starts at 03:23.
- **pnl_pct convention (2026-08-21):** all windows used here start ≥09-07 — entirely post-boundary (leveraged). No mixing possible.
- **Per-minute re-logging:** quantified — 123,359 lines = 13,669 episodes (89% repeats). Every claim reported at both granularities; C1 census differs by ~9× depending on unit (this is why the circulated census is unusable without a stated unit).
- **Null model (C2):** three independent nulls, all put expected co-blocking at 100%; observed 99.7% is *below* null. Statistic discarded.
- **Survivorship:** candles DB starts ~09-12; the 123 SHORT trades of 09-07→09-12 (net +$2.37, WR 62.6%) are outside candle coverage and excluded from the independent-RSI window — this exclusion removes a *profitable* short period and therefore biases the post-09-12 short picture *worse*, i.e., against the gate if anything. Blocked-token candle coverage 99.5–99.8%.

---

## WHAT THE DATA SUPPORTS

### (1) Structural complaints that SURVIVE adversarial testing
1. **All "block hit" counts in circulation are garbage.** Raw lines overstate episodes ~9×; the circulated census is irreproducible, mis-windows a 19-hour-old gate as a 2-week #1 blocker, and misstates thresholds (PENALTY-BLOCK fires at <50%, not <40%). Any gate-health dashboard must count **episodes with explicit first-seen dates**.
2. **The evidence columns behind gate constants are shaky.** `entry_rsi_14` correlates r≈0.33 with actual 5m RSI at entry (codebase already calls it DRIFT-E-unreliable), and `entry_rsi_14` has a 4-day hole whose profitable cohort appears to have been imputed into the "≥45 pays +$3.53" claim. Constants comments citing cohort stats need re-derivation from candles before they justify threshold changes.
3. **The short side bleeds in chop regardless of RSI** — chop SHORTs: WR 32–36%, net −$2.7 to −$4.6 across every threshold and RSI source tried. This is the system's real loss engine and it survives every attack.
4. **RSI<45 shorts do underperform ≥45 shorts** (WR ~39–46% vs ~47–49%; permutation p≈0.04–0.08 one-sided, consistent across two independent RSI derivations) — weak-to-moderate, direction-consistent evidence. But the effect is **chop-specific** (trend <45 shorts were net positive, n=22).
5. **The stack's regime gates blanket-fire on ~80–100 tokens at all times** (SHORT-CONTINUUM + CONTINUUM-BLOCK + NEUTRAL gates alone: 60k+ lines, ~4,700 episodes). Whatever their individual merit, they make any aggregate "blocked" metric meaningless and they make per-token block-state a near-constant.

### (2) Complaints REFUTED
1. **"The stack is deadlocked / pincer-blocked in both directions."** The 98–99.7% hour-level co-block stat is exactly what a direction-coin-flip null predicts (nulls: 100.0%; observed 99.7%, i.e. one hour *below* null). Passes occur in **99.4%** of those hours on both directions; **51.2%** of both-blocked hours produced an execution; **98.8%** of all window trades opened during "both-blocked" hours. There was no hour in the window where either direction was actually shut.
2. **"Trades only happen during chop — and chop trades lose."** Concentration true (83.6%); the losing part false: chop trades net **+$0.59 / +75.6 pct-units** at every threshold tried, and chop LONGs (+$3.28, WR 53.7%) are the best cohort in the system.
3. **"The deadlock has a meaningful cost / missed edge."** Trend-blocked episodes: excess +0.008% [−0.041, +0.061] ≈ **$2 total over two weeks** at live sizing. Chop blocks are mildly *profit-saving* (excess −0.020%). The pincer-cost claim is economically dead.
4. **The specific claimed magnitudes:** the census table (C1), "135 trades 10-02→10-08" (actually 174/185/187 by convention), "avg 6.2 gates/hour" (12.45 with all gates), and "RSI≥45 = +$3.53" (actually −$1.43).

### (3) SHORT-RSI-HARD-FLOOR specifically: **KEEP for chop — NEEDS-MORE-DATA for trend; fix the evidence comment**
- **Keep floor=45 in chop.** Chop <45 shorts: WR 36%, net −$4.56/30d across both RSI derivations; C5 chop-block excess slightly negative (blocking helps). Blocking oversold shorts in flat markets is correct and is the one short-gate with real trade-level backing.
- **Do not trust it (yet) in trend.** Trend <45 shorts: no bleed (trade-level +$0.19, n=22); blocked trend shorts show +0.15% excess point estimate (n=124 episodes, CI [−0.09, +0.39] — includes zero). The blanket gate is at best neutral and at worst forgoes ~0.15%/signal in trend; sample too small to decide. If any change is made, make the floor **chop-conditional** (or allow the bear-structure override that SHORT-RSI-FLOOR already has — 1,470 `✅ [SHORT-RSI-FLOOR-OVERRIDE]` passes in the window — which HARD_FLOOR denies by design). Do not remove it outright.
- **Correct the justification** (flag only; file is DO-NOT-MODIFY): "30d SHORT RSI<45 = 114T 34.4%WR −$5.52 vs ≥45 = 246T +$3.53" does not reproduce. Real numbers (stored RSI, same window): <45 n=138, 45.7%WR, −$4.63; ≥45 n=163, 49.1%WR, **−$1.43**. Independent candle-RSI (09-12→10-07): <45 WR 38.9% net −$4.37 vs ≥45 WR 49.2% net −$0.07, permutation p=0.038. The gate's *direction* survives; its stated magnitude and its "≥45 is profitable" half do not.

**Sideways finding for review (severity: medium):** `LONG-NEUTRAL-CHOP` (live since 10-11, "BTC BELOW EMA300 = chop, no trend") blocks LONGs in chop — but chop is exactly where the system's long profits come from (C3: chop LONGs +$3.28/2wk, WR 53.7%, the best cohort). Watch its blocked-cohort forward returns closely; on current evidence it is aimed at the profitable side of the book.
