# INDEPENDENT VERDICT — MFE/MAE 8h analysis (own-conclusions audit)

**Auditor:** independent (own-conclusions) · **Date:** 2026-10-26 · **Auditor run time:** ~21:50–22:00 UTC
**Claims audited:** `reports/20261026-mfe-mae-8h-verdict.md` + `reports/20261026-mfe-mae-8h-last100.md`
**My code (written from scratch, does NOT import theirs):** `analysis/audit_own_mfe_mae.py`
**Method note:** I read their report + script only to enumerate the claims and (after computing my own numbers) to audit definitions. Every number below comes from my own script or raw SQL. I ran 3 cohort variants:
- **FULL (n=99 analyzed):** my current last-100 at run time.
- **MATCHED (n=95):** dropped the 4 oldest trades (an earlier, incorrect attempt to reproduce their skip set — kept here only to show drift).
- **CLEAN (n=88):** only trades whose 8h window has fully elapsed at my run time (`AUDIT_MIN_WINDOW_AGE_S=32400`), all with 100% candle coverage.

## Critical caveat on comparability: the cohort is a moving target

Their run was at **~21:23 UTC**; mine at **~21:50–22:00 UTC**. New trades closed in between, shifting the last-100 window. Their cohort = last-100 as of 21:23 (newest = DOT opened 19:39). My FULL cohort = last-100 as of ~21:50 (DOT opened 19:39 was still in it, but BLUR/INJ/ALT windows were further along). So **exact integer equality is impossible**; I compare against direction and magnitude of drift. Where their number falls inside my range across cohorts, that is a pass.

**The single most important structural finding (affects every claim):** their 4 "skipped" trades were **not data gaps** — they were the 4 **newest** trades whose 8h windows had **not finished elapsing** when the script ran. Verified minute-exact below (claim 1). Consequently ~10 further recent trades were **included with truncated windows** (51–99% coverage), which biases MFE / MAE / fav_after downward for the newest trades.

---

## Claim 1 — 96/100 analyzable, 4 skipped (DOT/BLUR/INJ/ALT), median coverage 100%

**Verdict: PARTIAL** (counts reproduce; the *reason* is mislabeled)

Evidence:
- Their raw output: `DOT 1m=104 cov=22%, BLUR 1m=218 45%, INJ 1m=236 49%, ALT 1m=239 50%`, plus "1 trade at 51% (RENDER)".
- My raw SQL of trade open times: **ALT opened 17:23:38, INJ 17:27:36, BLUR 17:44:33, DOT 19:39:40** (all 2026-10-26) — these are exactly the 4 newest trades of their cohort, in exactly the order their skip list prints (open_time DESC).
- Elapsed window minutes at their run time: ALT 3h59m = **239 min** (= their 239 candles), INJ 3h56m = **236**, BLUR 3h38m = **218**, DOT 1h44m = **104**. Every single "insufficient candle" count equals the **minutes the window had been open**. Coverage of the *elapsed* portion is 100% in all four cases.
- Conclusion: **zero evidence of candle-data loss.** These are windows-in-progress, not a data-quality skip. RENDER (51%) was the razor-edge case that passed the 50% threshold and was included with a half-window.
- Median coverage 100%: **AGREE** (FULL p50=100%, CLEAN min=100%).
- My FULL run independently skipped the same DOT trade (cov 27–28%, 131–132 candles = its elapsed window) — same phenomenon, reproduced.

Confidence: **HIGH**

Notes: This is not a arithmetic error, but it materially misleads the reader — it converts a *recency/truncation* artifact into an apparent *data-coverage* problem. The correct filter is "drop trades whose 8h window has not fully elapsed," which the report did not apply (it kept ~10 partial-window trades and flagged only RENDER). See NEW-1.

---

## Claim 2 — 94 exits inside window: 52 profitable, 42 stopped-out

**Verdict: AGREE**

Evidence:
- FULL: 97 in-window exits (2 held past 8h) → **53 profitable / 44 negative** (price-based).
- CLEAN: 86 in-window exits (2 held past 8h) → **50 / 36**.
- Their 94 = 96 analyzed − 2 held; my 53/44 vs their 52/42 differs by exactly the extra low-coverage trades I included. Ratios 55.3/44.7 (theirs) vs 54.6/45.4 (mine FULL) — indistinguishable.
- Definition check: they split on `fav_at_exit` sign (gross price move), not net PnL. Net-of-fees positive count is **51** vs 53 price-positive in FULL — 2 flips from fees. Worth knowing, not an error.
- "2 held past 8h": reproduced exactly in all my runs.

Confidence: **HIGH**

---

## Claim 3 — Bigger move after exit: 70/94 @T=0.3 (74%), 61/94 @T=0.5; winners giving up ≥0.3pp 44/52; stopped losers ≥+0.3/1.0/2.0% = 26/42, 18/42, 10/42

**Verdict: AGREE** (numerically); one code-level claim in the method is wrong but immaterial here

Evidence:
| threshold | theirs | mine FULL | mine CLEAN |
|---|---|---|---|
| T=0.2 | 76/94 (81%) | 78/97 (80%) | 69/86 (80%) |
| **T=0.3** | **70/94 (74%)** | **71/97 (73%)** | **63/86 (73%)** |
| T=0.5 | 61/94 (65%) | 62/97 (64%) | 55/86 (64%) |
| winners ≥cap+0.3pp | 44/52 | 45/53 | 42/50 |
| winners ≥cap+1.0pp | 24/52 | 25/53 | 23/50 |
| losers ≥0.3 / 0.5 / 1.0 / 2.0% | 26 / 23 / 18 / 10 (of 42) | **26 / 23 / 18 / 10** (of 44) | 21 / 18 / 14 / 9 (of 36) |

- The loser-tier **numerators reproduce exactly** (26/23/18/10) — only the denominator differs by the 2 extra losers in my larger cohort. That is as close to an exact reproduction as this drifting cohort allows.
- The 74% headline is stable at **73%** on both my FULL and CLEAN cohorts — robust to the recency-truncation issue.

**Method flaw (no numerical impact):** their text says fav_after uses "candles STARTING at/after exit (straddle candle excluded → conservative)". In code, `exit_t = ep(close_time)` **truncates** to the second, so a candle whose start is up to 59s before the exit (1m) or up to **5 min before** the exit (5m table is in the union) is retained — the straddling candle is *not* excluded, and it can carry pre-exit price action. I implemented a genuinely-strict variant (ceil exit time to the next full minute, 1m primary only) and compared: **0 trades flip classification at T=0.3, and every tier count is identical** (strict vs loose). So the bias the code actually carries is real but happened to be zero-effect on this dataset. The description is wrong; the numbers are not.

Confidence: **HIGH**

---

## Claim 4 — Median foregone 1.83pp (p75 2.81, p90 4.08); foregone gross $19.15 vs realized $0.75 → gap $18.40 (amount_usdt as notional)

**Verdict: PARTIAL** (median/p75/max + dollars AGREE; p90 does not reproduce; notional claim CONFIRMED)

Evidence:
- FULL (n=71 early group): **p50 1.81pp, p75 2.81pp, p90 3.64pp, max 13.24pp**; foregone **+$19.31** vs realized **+$0.79** → gap **$18.52**.
- CLEAN (n=63): p50 1.80, p75 2.81, p90 3.64, max 13.24; $16.95 vs $1.18 → gap $15.77.
- Their p90 = **4.08pp**; mine = **3.64pp** in both runs. 4.08 corresponds to the GRASS 10-23 14:51 trade in their worst-15 list (missed +4.08pp) sitting at rank index 63 of 70; in my 71-member group that rank is a 3.64pp trade. This is a **single-trade tail-ranking difference**, not a computational disagreement — but their p90 should be treated as ±0.5pp, not as a stable statistic.
- Max 13.24pp (GRASS) reproduces **exactly** in every run.
- **Notional claim verified independently:** across the cohort, `|pnl_usdt − fav_exit×amount_usdt|` median **$0.002**, max **$0.06**. So `amount_usdt` IS the notional position size (incl. leverage), and `pnl_pct` is ROI on margin (move × leverage). Their dollar math is dimensionally correct. (Cross-checked: DOT SHORT lev5, move +0.2386%, amount 11.10 → implied $0.0265 vs recorded $0.03 ✓; LTC SHORT lev5, move −0.7637%, amount 22.10 → −$0.169 vs −$0.17 ✓.)
- **Caveats they state, and I confirm:** foregone is **gross of fees**, realized is **net**, and foregone assumes capturing the *entire* post-exit extreme. So $18.40 is an upper bound on the gap. Comparing gross to net inflates the gap by both legs' fees (roughly 0.05–0.10% × notional × 2 × ~70 trades ≈ small but not zero at these sizes).
- Realized figure drifts with cohort membership ($0.75 / $0.79 / $0.92 / $1.18 across my runs) — it is the least stable number in the report.

Confidence: **HIGH** on median/p75/max/dollars, **LOW** on p90

---

## Claim 5 — Exit census: profit-monster-trail 40 (37 wins, +$2.37), hard_max_loss 11 (0, −$1.36), atr_sl_hit 10 (−$0.59), ugb_pt 9 (+$0.24), trail_arm_timeout 9 (−$0.20)

**Verdict: AGREE**

Evidence (FULL, n=99):
| exit rule | theirs | mine FULL | mine CLEAN (n=88) |
|---|---|---|---|
| profit-monster-trail | 40 / 37w / +$2.37 | **40 / 37w / +$2.37** | 39 / 36w / +$2.32 |
| hard_max_loss | 11 / 0w / −$1.36 | 12 / 0w / −$1.67 | 9 / 0w / −$1.07 |
| atr_sl_hit | 10 / 0w / −$0.59 | **10 / 0w / −$0.59** | **10 / 0w / −$0.59** |
| ugb_pt | 9 / 6w / +$0.24 | 10 / 7w / +$0.28 | 7 / 6w / +$0.26 |
| trail_arm_timeout | 9 / 2w / −$0.20 | 10 / 2w / −$0.20 | **9 / 2w / −$0.20** |

- profit-monster-trail and atr_sl_hit reproduce **exactly** in FULL. The +1 in hard_max_loss/ugb_pt/arm-timeout is exactly the three partial-window trades (BLUR HML −$0.31, INJ ugb_pt +$0.04, ALT arm-timeout −$0.06) that their run skipped and mine included. 40+11+10+9+9 = 79 of their 96; my FULL sums to 82 for the same five rules (+3) — perfectly explained.
- Full 15-row census also matches on the tail rules (hard_sl 4, stale_exit 2, atr_trail 2, rr_engine 2, UNIVERSAL_MAX_HOLD 2, and the 1s).

Confidence: **HIGH**

---

## Claim 6 — For the 64 trades with MFE≥0.8%: MAE-to-peak p50/p75/p90 = 0.57/1.17/1.62% (max 4.76%); 24/64 hit own SL first, 13/64 hit HML first, 36/64 survivable to peak under both

**Verdict: PARTIAL** — the MAE percentiles AGREE; the SL/HML attribution is **definition-dependent and one half of it is unsound**

Evidence — MAE percentiles AGREE:
- FULL cohort (n=65): first-touch **p50 0.57 / p75 1.15 / p90 1.62 / max 4.76**; last-touch p50 0.57 / p75 1.17 / p90 1.62 / max 4.76.
- CLEAN cohort (n=59): p50 0.47 / p75 1.09–1.17 / p90 1.62 / max 4.76.
- Their 0.57 / 1.17 / 1.62 / 4.76 sits squarely inside my range. **AGREE.**
- Independent raw-SQL spot check of the max: **ZRO SHORT 2026-10-23 11:22**, 480/480 candles, MFE +3.37%, MAE_8h 4.76%, MAE-to-peak **4.76%**, peak 19:18 — **MATCHES their spot check exactly.**

Evidence — the kill attribution is the problem:
- Their raw counts reproduce: FULL gives SL 25 / HML 14 / survivable 36 (of 65); subtracting my extra trade → **24 / 13 / 36 on 64 — exact match.**
- **But 24+13+36 = 73 ≠ 64.** The SL and HML kill sets **overlap by 9–10 trades**; their own script computes two independent boolean counts and never resolves which stop actually fires first. My explicit first-killer attribution (FULL, close-time SL): **SL-first 19, HML-first 8**, overlap 10. So "24 would hit own SL **first**" overstates SL-first kills by ~5; the honest sentence is "24 exceed their SL distance and 13 exceed the HML cap, with 9–10 exceeding both."
- **Bigger issue — the SL distances are not the stops that were in force.** `trades.stop_loss` is rewritten continuously while a trade is open (`_persist_atr_levels`, `_persist_sl` in position_manager; `compute_atr_sl_tp` re-anchors to peak when in profit **and to current price when in loss**). Verified in data: **57–63 of 59–65 cohort trades are `atr_managed`**, and `atr_sl_hit` trades in the wider 30d set show close-time SL distances as low as **0.006%**. The close-time `stop_loss` is a snapshot of the *trailed* stop at exit — for a stopped trade it sits mechanically at the exit price, i.e. near the adverse extreme. Using it as "the trade's stop" in a pre-peak MAE comparison therefore inflates SL-kill counts.
- Alternative using the **initial** SL (`sl_distance` column, uniformly **0.015 = 1.5%** on every cohort trade): **SL-kill 10/65, SL-first 0/65, HML-first 14, survivable 51/65.** With a 1.5% initial stop, the HML (0.8% price at 5x) *always* kills first — which is exactly the report's own "at 5x, HML caps the stop at 0.8% — anything wider is dead code" conclusion, but arrived at from the opposite direction.
- So "36/64 survivable to peak under both" ranges **36 (exit-snapshot stop) → 51 (initial stop)** depending purely on which stop definition you use. The report presents one number without the caveat. The truth about live behavior sits between the two: the ATR stop chases price during drawdowns, so a real ATR-managed trade gets stopped quite early in any sustained adverse move — meaning the *pessimistic* end is arguably closer to reality, but "24 SL-first" is not a defensible point estimate either.

Confidence: **HIGH** on the MAE percentiles; **HIGH** on the contamination finding; the correct survivable count is genuinely definition-dependent.

---

## Claim 7 — Max leverage keeping HML intact: p50 → 7x, p75 → 3.4x (4/1.17), p90 → 2.5x

**Verdict: AGREE**

Evidence:
- FULL: 4/0.57 = **7.0x**, 4/1.17 = **3.4x**, 4/1.62 = **2.5x** — arithmetic exact.
- CLEAN: 8.6x / 3.7x / 2.5x (shifts because p50/p75 move on the smaller cohort; p90 stable at 2.5x).
- `CUT_LOSER_PNL = -4.00` confirmed in `hermes_constants.py` line 735.
- I verified the live HML threshold is genuinely `CUT_LOSER_PNL / leverage` in price terms: position_manager line 3708 `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL_HERMES / _hml_lev`.
- **Sideways finding:** the ATR vol-floor refinement (`HML_VOL_ATR_MULT = 0.5`, constants line 736) **can never take effect** — the code caps the vol floor at the account limit and then re-compares it to the same account limit (`if _hml_vol_floor < _hml_account_cap: _hml_vol_floor = _hml_account_cap` followed by `if _hml_vol_floor < HARD_MAX_LOSS_PCT`), so the threshold always stays at −4%/lev. That is inoperative dead code (documented intent: widen HML in EXTREME regimes). **No impact on this report** (their 4/lev formula matches actual behavior), but it is a live-system defect worth a ticket — the EXTREME-regime widening brain_auditor shipped 2026-10-08 does not actually widen anything.

Confidence: **HIGH**

---

## Claim 8 — Time from open to 8h-peak: p50 ≈ 278 minutes

**Verdict: AGREE**

Evidence: FULL **271m** (first-touch), CLEAN **260m**, my other runs 251–280m. Their 278m sits inside that band. p75 ~397–406m vs their 403m, p90 436–440m vs their 436m — all reproduce.

Confidence: **HIGH**

---

## Claim 9 — Scenario on the whole 64-cohort: actual +$1.68 vs SL 0.80% +$9.61 (23 stopped), SL 1.17% +$12.95 (15), SL 1.62% +$16.35 (6)

**Verdict: AGREE numerically / PARTIAL as a policy estimate** (they already label it an upper bound)

Evidence (my independent recompute of the same rule: ride to 8h peak if MAE-to-peak ≤ W, else stop at −W, gross of fees):
| SL | theirs | mine FULL (n=65) | mine CLEAN (n=59) |
|---|---|---|---|
| actual (net) | +$1.68 | +$1.72 | +$1.94 |
| 0.80% | +$9.61 / 23 stops | **+$9.52 / 24** | +$9.58 / 19 |
| 1.17% | +$12.95 / 15 | **+$13.15 / 15** | +$12.29 / 13 |
| 1.62% | +$16.35 / 6 | **+$16.55 / 6** | +$15.39 / 5 |

- Stop counts reproduce exactly at W=1.17 (15) and W=1.62 (6) in FULL; W=0.80 differs by 1 (my extra cohort trade). Dollar figures within $0.05–0.60. **Reproduced.**
- Scenario logic is sound as stated. Additional caveats beyond theirs, all pushing the same direction (upward bias):
  1. Non-stopped trades are assumed to capture the **exact peak high/low** — impossible in practice (they say "upper bound").
  2. It ignores that today's profit-monster trail (0.20% distance, arms at +0.40%) would exit most winners well before an 8h peak — the scenario is not "the same trades with wider stops," it is "different exit rule entirely."
  3. **Intra-candle stop ambiguity:** a candle containing both the peak and an adverse W-move is scored as stopped even if the adverse leg came *after* the peak. My last-touch MAE variant shifts W=0.80 to 24–25 stops / +$9.31–9.52 and W=1.17 to 16 stops / +$12.90. Small.
  4. Gross-of-fees scenario vs net-of-fees "actual" row — mixing bases (they disclose this).

Confidence: **HIGH** on reproduction, **MEDIUM** on the numbers being decision-useful

---

## Claim 10 — Outliers are real: GRASS 2026-10-21 12:38 LONG post-exit +12.5% entry-based; WLD 2026-10-23 14:36 SHORT +10.07%; both 480/480 candles

**Verdict: AGREE**

Evidence (my own raw 1m queries, independent code path):
- **GRASS LONG 10-21 12:38**, exit 14:01 (atr_sl_hit, capture −0.73%): **480/480 1m candles, 0 gaps >1min** in the window. MFE **+12.50%**, best candle **19:31** — 5.5h *after* our exit. MAE 0.95% (worst 14:00). fav_after strict = +12.50% = loose = +12.50%.
- **WLD SHORT 10-23 14:36**, exit 15:16 (profit-monster-trail, capture +0.95%): **480/480 candles, 0 gaps**. MFE **+10.07%**, best candle **22:33** — 7h after exit. MAE 0.47% (worst 14:38).
- Both extremes occur hours after the exit, in candle-dense regions — **not data gaps, not candle-boundary artifacts.** The moves are real.

Confidence: **HIGH**

---

## Claim 11 — Split-half: older 34/47, newer 36/47

**Verdict: AGREE**

Evidence: FULL **35/48 vs 36/49**; CLEAN **31/43 vs 32/43**. Both halves land at 71–74%. The phenomenon is present in both halves in every cohort I tested, with the same near-equal split. Their 34/47 vs 36/47 reproduces modulo cohort membership.

Confidence: **HIGH**

---

# NEW ISSUES (not disclosed, or under-disclosed, in the report)

**NEW-1 — [MEDIUM→HIGH] Recency truncation, mislabeled as data coverage (claim 1).** The 4 skips are windows-in-progress (proven minute-exact), and ~10 further trades with 51–99% windows were silently *included* with truncated MFE/MAE/fav_after. Effect on the headline 74% is negligible (73% on a clean fully-elapsed cohort), but effect on per-trade MAE and the MFE≥0.8% cohort membership is not zero (cohort 64 → 59 when I drop partial windows; MAE p50 0.57 → 0.47). **Fix:** filter `open_time <= NOW() - 8h` at the top; do not use a coverage threshold as a proxy.

**NEW-2 — [HIGH] Claim 6 uses trailing-contaminated stop distances.** `trades.stop_loss` is rewritten by the ATR manager throughout a trade's life (57–63/65 cohort trades `atr_managed`; live `atr_sl_hit` distances down to 0.006%). Using the close-time value as "the trade's stop" overstates pre-peak SL kills: with the initial 1.5% stop the split becomes SL-first **0**/HML-first **14**/survivable **51**. See claim 6.

**NEW-3 — [MEDIUM] "SL first / HML first" is not actually computed.** The two kill counts overlap by 9–10 trades; 24+13+36 ≠ 64. True first-killer attribution on my FULL cohort is SL-first ~19, HML-first ~8. The report should either report the overlap or attribute first-killer.

**NEW-4 — [LOW] Straddle-candle description is wrong in code.** `ep(close_time)` truncates to the second, so the candle containing the exit is retained in `fav_after` (up to 5 min of pre-exit action from the 5m table). Described as "straddle excluded → conservative"; it is in fact mildly anti-conservative. Measured impact on this dataset: **zero** (0 flips at T=0.3, identical tier counts). Latent, not current.

**NEW-5 — [LOW] Dead code, two places.** (a) `analysis/mfe_mae_8h.py` line 176 loads `candles_5m.db` into `db5m` but never uses it (harmless). (b) **Live trading defect:** `HML_VOL_ATR_MULT` vol-floor in position_manager (lines ~3747–3759) can never alter the HML threshold — it is capped to the account limit and then re-compared against that same limit. The EXTREME-regime HML widening shipped 2026-10-08 is inoperative. No effect on this report's math (their 4/lev formula matches actual behavior), but it should be ticketed.

**NEW-6 — [LOW] Union-of-series is safe but unverified by them.** I checked 5m-vs-1m feed agreement across ~8,500 buckets: **44–53 disagreements (0.6%)**, max MFE effect **0.04pp**. Union is fine here. Their "min/max over the union can only widen toward the true extremes" holds only because the feeds agree to 0.6%; if a 5m feed ever diverged, the union would silently ingest bad extremes. A cheap assertion would harden it.

**NEW-7 — [LOW] p90 is not a stable statistic at n≈70.** Their foregone p90 = 4.08pp; mine = 3.64pp in every run — a one-trade rank flip at the 90th percentile, not a computational disagreement. Report p90 with a ±1-trade caveat or drop it.

**NEW-8 — [LOW] "3 reproducible runs" proves determinism, not stability.** The cohort is re-selected by `NOW()` on every run, so rerunning hours later yields a *different* last-100 with different answers (their own note admits ALT's candle count drifts). Reproducibility claims should be made against a pinned trade-id list. Related: `pnl_pct` semantics are inconsistent in the DB (RENDER records `pnl_pct` = raw price move while peers record move×leverage) — unrelated to these claims, but a data-hygiene flag.

---

# Bottom line

The core findings of the report **survive independent reproduction**: ~74% of in-window exits are followed by a materially bigger move, the loser-continuation tail (26/42 ≥0.3%, 10/42 ≥2.0%) reproduces **exactly**, the outliers are real, the MAE-to-peak percentiles and the "HML caps you at 0.8% price at 5x → ≤3x leverage to survive the p75 ride" conclusion are correct, and the dollars are dimensionally sound (`amount_usdt` confirmed as notional).

The two things I would not let through unamended: **claim 1's framing** (recency truncation presented as data loss, with ~10 partial-window trades silently included) and **claim 6's SL attribution** (trailing-contaminated stop distances, an uncomputed "first" label, and an overlap that makes 24+13+36≠64). Neither overturns the report's recommendation — the coupled CUT_LOSER + wider-SL shadow trial — but claim 6's survivable count should be quoted as a **36–51 range**, not the single number 36.
