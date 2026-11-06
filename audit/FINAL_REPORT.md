# Independent Audit — `backtest_atr60_momentum.py` (BTC ATR14 $60 event study)

**Auditor:** independent re-computation from raw `candles.db` (no code reused from the original;
my own indicator/event/outcome/statistics implementations in `audit/audit_check.py`,
scipy.stats for exact tests, bootstrap seeds `20261106+` ≠ original's 7/11, 20,000 rounds).

**Data pinned:** `/root/.hermes/audit/snap_*.npz` (snapshot 2026-11-06 05:03:30 UTC).
⚠️ `candles_1m` is a **live rolling 30-day window** (pruned at `price_collector.py:856-863`);
the DB advances every minute. The claim's exact window can no longer be reconstructed
(head pruned). Snapshot BTC: 42,807 bars, 2026-10-07 05:04 → 2026-11-06 05:03 UTC.

---

## 1. Per-claim results

| # | Claim (as stated) | Verdict | My independently computed numbers |
|---|---|---|---|
| 1 | 42,807 bars, 10-07 04:35 → 11-06 04:34 UTC, one 23,640 s gap, all else 60 s | **PARTIAL** (counts+gap confirmed; window not reproducible) | n = **42,807** ✓; **exactly 1** gap = **23,640 s** (2026-10-15 04:11→10:45 UTC) ✓; all other 42,805 gaps = 60 s ✓; OHLC violations 0, all `is_closed=1`, no dup ts (PK). Window: rolling → my snapshot 10-07 05:04 → 11-06 05:03; claim window (04:35→04:34) was valid only at run time (~04:35 UTC Nov 6) and is now unverifiable. Count is stable by construction: 43,200 − 393 missing = 42,807. |
| 2 | 201 raw crossings; 109 declustered (re-arm <54) | **CONFIRMED (exact)** | raw (`prev<60<=cur`, pure definition) = **201** ✓; hysteresis 0.9 → **109** ✓. Alternatives: hyst 0.95→137, hyst 0.833→93, cooldown 60 bar→105, cooldown 180 bar→73 (conclusions unchanged, see below). |
| 3 | 95 tradeable, 14 skipped, 48 LONG / 47 SHORT | **CONFIRMED (exact)** | 109 = **95** tradeable + **14** skipped (all MACD/RSI disagreement, **0** flat) + **0** dropped by the `i >= len-15` filter; **48 LONG / 47 SHORT** ✓. |
| 4 | \|fwd ret\| ev vs baseline: 60 m 0.413/0.248 +0.164 CI[+0.077,+0.264]; 240 m 0.792/0.494 +0.297 CI[+0.138,+0.476]; 1440 m 1.296/1.192 +0.105 CI[−0.169,+0.394] (n.s.) | **CONFIRMED (numbers)** / **interpretation misleading** | 60 m: ev **0.4127** vs base 0.2360 (their grid) / **0.2443** (all 42,792 bars) → diff **+0.168**, boot95 **[+0.081,+0.267]**, day-block [+0.104,+0.257], permutation p<1e-4, **circular-shift p=0.0007**. 240 m: ev **0.7890** vs base 0.5098/0.5071 → diff **+0.282**, CI **[+0.129,+0.452]**, circ-shift **p=0.004**. 1440 m: ev **1.2965** vs 1.2562/1.2286 → diff **+0.04…+0.068**, CI **[−0.182,+0.336]** = **not significant** ✓. Claim's baseline values lie inside my 60-grid-phase ranges (60 m 0.225–0.268; 240 m 0.474–0.547; 1440 m 1.143–1.303) — reproduced. **But**: ATR≥60-matched baseline (n=2,856, events excluded ±60) = **0.4376 / 0.8187 / 1.7204** → events are *equal or lower* (60 m diff −0.025 CI spans 0; 1440 m −0.42). Decomposition: ATR level alone explains **126 %** of the gap; cross-vs-state = **−0.044**. ATR-quartile table (monotone vol clustering): 0.1435 → 0.1987 → 0.2437 → 0.3913 %. |
| 5 | 15 m mean −0.048 %, WR 32.6 %, binom p 4.25e-04; 1440 m +0.059 %, WR 46.0 %, CI[−0.311,+0.428] | **CONFIRMED except p-value (wrong in claim)** | 15 m: mean **−0.0477 %**, WR **32.6 % = 31/95** ✓, but two-sided exact p = **9.246e-04**, not 4.25e-04 (script bug, §2.1). 1440 m: mean **+0.0588 %** ✓, WR **46.0 % = 40/87** (n=**87**, not 95), CI **[−0.318,+0.443]** ✓ includes 0. All 8 horizons: 30 m −0.036 (p=0.023), 60/120/240/480/720/1440 all n.s. → **no positive directional edge anywhere** ✓. Next-bar entry: 15 m shrinks to −0.022 (CI spans 0). |
| 6 | 18/95 (18.9 %) vs 80/510 (15.7 %); 14/18 in-dir p=0.0154; baseline 41/80 (51.2 %) | **CONFIRMED (event side exact; baseline phase-dependent but in range)** | events **18/95 = 18.9 %** ✓; in-direction **14/18**, one-sided exact p = **0.015442** ✓; baseline rate mine **17.8 %** (8 grid phases: **15.2–17.9 %** → claim's 15.7 % inside ✓), baseline in-dir **52.5 %** vs claim 51.2 % ✓ (both coin flip). Proper tests: **Fisher(event vs baseline in-direction) one-sided p = 0.0394**; big-move **rate** Fisher p = **0.77** (rates indistinguishable). Wick-based (high/low) touch: 17/95 events, 13/17 in-dir — same story. |
| 7 | 8 coins at ATR 0.076 % of price: SOL 49/47, SUI 40/46, TAO 54/46, PUMP 2/5, GALA 128/121, GMX 206/186, IMX 145/133, SAND 48/42; pooled 672/626 (51.8 %); all 24 h CIs include 0 | **CONFIRMED (7/8 exact, IMX ±1)** | at **0.076 %**: SOL **49/47** ✓, SUI **40/46** ✓, TAO **54/46** ✓, PUMP **2/5** ✓, GALA **128/121** ✓, GMX **206/186** ✓, SAND **48/42** ✓, IMX **145/134** (claim 145/133, ±1 = window drift). Pooled **672/1299 = 51.7 %**, one-sided p = **0.111** (claim 672/1298=51.8 %). **All 8 coins' 24 h direction-aligned bootstrap CIs include 0** ✓. Caveats: script default `--pct 0.077` does *not* reproduce (SOL 52/49 etc.) — claim requires explicit `--pct 0.076`; and **flat synthetic bars**: GMX 61 %, IMX 57 %, GALA 38 %, SAND 11 %, TAO 6 % of bars are O=H=L=C (tick-aggregator artifacts) → those coins' ATR/indicators are contaminated; PUMP n=7 → no power. |
| 8 | ATR matches talib (max diff 0); RSI to 1e-14; MACD hist <1e-10 after bar ~100; SMA-ATR 277 crossings, 28 % overlap | **PARTIAL** | ATR: **max abs diff = 0.000e+00** ✓ exact. RSI: **2.84e-14** ✓ (same order as claimed 1e-14). MACD hist: first valid bar 33 both ✓, but max\|diff\| over bars ≥100 = **4.52e-05**, first bar with diff <1e-10 = **180** (claim "<1e-10 after bar ~100" ✗); converges to ~1e-11 by bar 200 (warmup-only ✓), only **1 sign disagreement** in 42,807 bars (bar 42) → zero impact on events (first crossing at bar 304). Root cause: TA-Lib's internal MACD differs from its own `EMA(12)−EMA(26)` (max 1.247, converging at bar 174); script uses the standalone-SMA-seed convention. SMA-of-TR ATR: **277** raw crossings ✓; overlap = **57/201 = 28.4 %** of Wilder events also SMA events ✓ (Jaccard 13.5 %, SMA-side 20.6 %). |

**Reproduction of headline event-side numbers is exact** (201 / 109 / 95 / 14 / 48 / 47 / 18 / 14 / p=0.015442 / 277),
despite a 29-minute window shift — the claims are honest recomputations, not fabricated.

---

## 2. Bugs found (file:line = current working copy of `scripts/backtest_atr60_momentum.py`)

**2.1 Off-by-one in the two-sided binomial p-value — `:373` (was :351 in the version the claims were run on)**
```python
p_up = binom_p_ge(k, n_e)            # P(X >= k)
p_dn = binom_p_ge(n_e - k + 1, n_e)  # P(X <= k)   <-- actually computes P(X <= k-1)
p_two = min(1.0, 2 * min(p_up, p_dn))
```
Correct is `binom_p_ge(n_e - k, n_e)` (= P(X ≥ n−k) = P(X ≤ k)). Effect: reported two-sided p-values
are **understated ~2×**. Claim 5's 15 m p = 4.25e-04 → correct **9.246e-04** (scipy `binomtest(31,95,0.5)`
= 9.2464e-04; script formula = 4.24793e-04). Conclusion unchanged (still p<0.001) but every `p2s`
in `print_report` (`:374-379`) is wrong. *Severity: medium — inflates significance of all direction results.*

**2.2 Gap fallback can fabricate a 0 % return / distort horizons — `:206`**
```python
j = idx_map.get(target + 60) or idx_map.get(target - 60)
```
(a) `or` treats index 0 as falsy; (b) if `target` falls inside the 23,640 s gap it silently returns a
stale ±60 s bar (horizon no longer h minutes) or drops the horizon; (c) if the event bar is the last bar
before the gap, `target-60` lands **back on the event bar → 0 % return**. Latent for this dataset
(the gap-fallback fired only 3 times: 1 event at 240 m, 2 baselines at 60 m; the 0 % case did not trigger),
but it is a correctness landmine. *Severity: medium.*

**2.3 Silent tail drop — `:319`**: `if i >= len(ts) - 15: continue` drops events **without** counting them in
`n_skipped`. Here 0 events were dropped (109 = 95+14 holds), but the accounting is fragile. *Severity: low.*

**2.4 Horizon-dependent survivorship — `outcomes` `:196-213`**: events whose forward ts is beyond data end or
inside the gap silently vanish from that horizon: **n = 95 (15/60 m) → 93 (240 m) → 87 (1440 m)**.
Claim 5's "for the 95 events … at 1440 m" is really n=87 (its 46.0 % WR = 40/87 confirms the author's own
code dropped the same 8). Time-based, not outcome-based → mild bias (drops the most recent regime).
*Severity: low-medium (reporting honesty).*

**2.5 Baseline is a phase-dependent grid, not "every 60th minute" — `:312`**: `range(0, len(ts), 60)` samples by
**index**, so which bars are sampled depends on window-start phase **and** the 394-bar gap (post-gap the grid
shifts to a different minute-of-hour). Across the 60 possible phases: n = **478–556** (claim 510 ✓ in range),
60 m mean 0.225–0.268, 240 m 0.474–0.547, 1440 m **1.143–1.303**, touch-3 % rate **15.2–17.9 %** (claim 15.7 % ✓).
All claimed baseline values are achievable, but the baseline numbers carry ±5–10 % grid noise. Using **all bars**
removes the noise and *strengthens* 60/240 m slightly. *Severity: medium (fragile, unreported uncertainty).*

**2.6 Entry at the signal bar's own close — `:199` (`p0 = closes[i]`)**: the ATR cross requires that bar's
H/L/C, and the fill price is that same bar's close → zero-latency fill at the very close that generated the
signal. **No lookahead** (no future data used anywhere — verified: ATR/MACD/RSI/direction all use ≤ event close;
horizons exact-ts aligned; MFE/MAE/touch start at `i+1`), but optimistic. Entering at the next bar's close
changes 15 m from −0.048 (p=9e-4) to −0.022 (n.s.) — i.e. part of the 15 m "anti-edge" is entry-timing, not signal.
*Severity: low-medium.*

**2.7 Baseline/event sample overlap — `:312/:315`**: **551/556** baseline bars lie within 1,440 bars of an event
(overlapping outcome windows) and 1 bar is both event and baseline (index 30360). The two-sample bootstrap
(`:668-676`, `move_size_test`) assumes independence. In practice this is conservative here — day-block bootstrap
and a circular-shift null (preserves event clustering) both confirm 60 m/240 m significance — but the reported CI
is not the right CI in principle. *Severity: low.*

**2.8 `load_candles` (`:49`) does not filter `is_closed`**, and the fast collector marks the in-progress minute
`is_closed=1` (`price_collector.py:196`) → the newest bar can have partial OHLC. No impact here (all events >15
bars from the end), but it silently poisons "latest bar" logic elsewhere. *Severity: low.*

**2.9 Claim/code mismatch on cross-coin threshold — `:1127`**: `--pct` default is **0.077**, claim says **0.076**
(and only 0.076 reproduces the claimed counts). Reproduction requires the undocumented flag.
*Severity: low (reproducibility).*

**2.10 Post-hoc selection / multiple comparisons**: threshold $60 and the 30-day window were chosen *after*
observing the motivating ~6 % moves (docstring `:5-8`); the script then sweeps 6 thresholds × 12 direction variants
× 5 HTF rules × 6 entry schemes × 3 quiet settings × 8 horizons × 3 touch targets × 9 coins.
Claim 6's p=0.0154 → Bonferroni ×4 = **0.062**, ×8 = **0.123**; the correct event-vs-baseline Fisher p=0.0394 →
×4 = **0.158**. *The author's own "doesn't survive multiple comparisons" caveat is correct.*

**2.11 Script mutated during the audit**: 931 lines @04:51 (the version the claims were run on) → 958 (HEAD) →
**1,152 lines @05:26** (uncommitted +194-line `htf_trend_study`, a new "CEO hypothesis" study). Core functions
(`tv_atr`, `find_events`, `outcomes`, `collect`, binom formula) are unchanged across versions; my indicator
reimplementations match the script's `tv_atr`/`tv_rsi`/`tv_macd_hist` **exactly (max diff 0.0)**, so the claims
are attributable to the code I audited. *Severity: informational — but claims should be pinned to a commit.*

**No lookahead bias found** in signal construction or outcome measurement (the one timing optimism is §2.6).

---

## 3. Overall verdict on the researcher's conclusion

> "Volatility expansion after ATR14 1m crosses $60 is real and significant at 1-4 h; directional edge from
> MACD/RSI momentum direction is NOT supported; one positive BTC result at p=0.015 likely does not survive
> multiple comparisons and does not replicate cross-coin."

1. **"Directional edge NOT supported" — SOUND.** Reproduced independently: no horizon from 15 m to 24 h has a
   significant *positive* direction-aligned return; 15 m and 30 m are significantly *negative* (15 m correct
   p=9.25e-4, survives Bonferroni ×8 = 7.4e-3) — i.e. the evidence is actually *against* the MACD/RSI rule at short
   horizons, stronger than "no edge". Next-bar entry removes even that. The author understates this slightly
   (reports a p-value 2× too small due to bug §2.1).

2. **"p=0.015 doesn't survive multiple comparisons; doesn't replicate cross-coin" — SOUND.** Confirmed 14/18
   p=0.015442, Bonferroni kills it; the *proper* comparison (Fisher vs baseline direction share) is p=0.0394 →
   also killed by ×4; the big-move **rate** is statistically identical to baseline (Fisher p=0.77); cross-coin
   pooled 51.7 % p=0.11 with all 8 CIs covering zero. Exactly as concluded.

3. **"Volatility expansion is real and significant at 1-4 h" — NUMERICALLY TRUE, BUT MISLEADING AS AN EDGE.**
   The headline numbers reproduce (60 m +0.168 CI[+0.08,+0.27], 240 m +0.282 CI[+0.13,+0.45], 1440 m n.s.) and
   survive day-block bootstrap, permutation, a clustering-preserving circular-shift null (p=0.0007 / 0.004),
   alternative declustering rules, and Bonferroni over 8 horizons — so the *descriptive* statement is solid.
   **But it is volatility clustering, not an event edge**: conditional on the ATR *level* (ATR≥60, events removed),
   the cross predicts **nothing** — events 0.4127 vs state 0.4376 at 60 m, 0.7890 vs 0.8187 at 240 m, and
   **1.2965 vs 1.7204 at 1440 m (events lower)**; the ATR level explains **>100 %** of the event-vs-random gap,
   and within ATR≥60 the cross bar itself has *lower* subsequent |move| (0.398 vs 0.459). The result is the
   well-known fact that "high-volatility states stay high-volatility" (monotone ATR-quartile table), with a
   threshold ($60) and window chosen after seeing the motivating moves. It is not tradeable information.

**Bottom line: overall conclusion directionally SOUND (both negative findings hold up under adversarial
re-testing), with three qualifications an auditor should insist on:** (a) the "volatility edge" framing is
tautological — the cross itself adds zero information beyond the ATR level; (b) one reported p-value is wrong
2× (bug §2.1) and all reported p2s values are affected; (c) baseline numbers depend on an arbitrary index-grid
phase (±5–10 %) and horizon sample sizes silently shrink 95→87 — none of which flips a conclusion, but all of
which the original report presents as exact.

*Files: `audit/audit_check.py` (independent checker), `audit/audit_report.txt` (raw output),
`audit/snap_*.npz` + `audit/snapshot_meta.json` (pinned data).*
