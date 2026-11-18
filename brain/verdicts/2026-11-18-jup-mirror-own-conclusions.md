# Independent verdict — closed `jup_yolo` trades (own-conclusions)

**Date:** 2026-11-18
**Auditor:** independent own-conclusions session (no priming beyond the claim list)
**Method:** every file read from scratch; every number below was recomputed from raw PostgreSQL + SQLite in this session. Fisher exact implemented by hand (`math.comb`, 2-sided, sum of tables with P <= P(obs)); two-proportion z via `math.erfc`. Nothing copied from the claim sheet.

---

## Data quality (checked first)

| Check | Result |
|---|---|
| Rows `signal LIKE '%jup_yolo%'` | **177**, all `status='closed'` (166 exact `jup_yolo_mirrored` + 11 confluence combos) |
| Distinct `id` | 177 → **0 duplicates** (also 0 dup on token+open_time, token+close_time) |
| `paper` | all `False`; `server` all `Hermes`; `leverage` all `5` |
| Window | open 2026-10-30 06:16 → 2026-11-18 17:59 (19 days). 0 trades older than 30d |
| `jup-liq+` (separate signal) | 1 closed trade — correctly excluded by the `jup_yolo` LIKE |
| Metadata coverage | `jup_cluster_size` key present 170/177 but **non-null only 121/177**; `jup_win_rate`/`jup_trades` non-null **121/177** (the 56 nulls are the *same rows* for both); `jup_margin_usd`/`jup_side` 173/177; `rsi_14`/`z_score` 165/177 |
| `jup_side` vs `direction` | **0 mismatches** |
| Open jup trades (survivorship) | **none** — 177/177 closed in PG, and `trades.json` has 0 open trades system-wide. No hidden open losers |
| `pnl_pct` units | verified `pnl_pct == side-aware price% × leverage` to max abs diff **5e-5** on all 177 → the ×5 leveraged conversion is exact |
| Candle coverage | all 177 trades have `candles_5m` rows; only 4 tokens (BTC, ETH, HYPE, SOL) |
| Time anchoring | eras computed on `open_time` (correct); `close_time` split gives the same conclusion (41/84/52, −0.48/−1.12/+0.56) |
| Selection-on-outcome | `jup_win_rate`/`jup_trades` are detect-time leaderboard stats (`jup_yolo_monitor.py:302-303`, `stats.get('wr')`/`stats.get('trades')`) — not outcome-derived. OK |
| Multiple comparisons | the claim sheet says ~30 cells were scanned; I scanned 6 cluster thresholds. Flagged below wherever a single p<0.05 is doing the work |

**Exit machinery actually live (constants + git, verified):**
`MFE_EXIT_ENABLED=True` — introduced commit `e56e7942` **2026-10-31 19:01:50**, armed at 0.40% same day `e40c3cf8` 22:03. `STOP_TIGHTEN_ENFORCE=True` (0.75%) and `JUP_YOLO_FILL_CAP_ENABLED=True` (1 fill / 6h) — both introduced by commit `6d5f138c` **2026-11-04 04:24:51**. `CUT_LOSER_PNL=-4.00`, `PM_TRAIL act 0.40 / dist 0.20` (CEO_PROTECTED). Log shows 62 `[STOP-TIGHTEN-ENFORCE]` lines (19 distinct trade-ids, 10 of them era-3 jup ids), 2372 `[JUP-SHADOW-*]` lines (ATRSL 792 / HML 788 / TRAIL 792), 10 live `mfe_exit` closes.

---

## Claim 1 — micro-movements

**Verdict: PARTIAL (headline conclusion holds; two of the six numbers are produced by a SHORT-side sign bug)**

Reproduced exactly:

| Sub-claim | Claim | Mine |
|---|---|---|
| n | 177 | **177** |
| median hold | 0.9h | **0.922h** (mean 1.532h, min 0.011h, max 8.01h) |
| realized price-pnl median | 0.229% | **0.2294%** |
| winners | 112 | **112** (W/L/B = 112/63/2, WR **64.0%**) |
| winners <2% lev | 66/112 (59%) | **66/112 (58.9%)** |
| winners >=5% | 5 | **5** |
| avg win / avg loss | +2.04 / −3.99 | **+2.041 / −3.988** |
| payoff | 0.51 | **0.512** |
| breakeven WR vs actual | 66% vs 64% | **66.1% vs 64.0%** |
| captured >=80% of a >=2% move | ZERO | **ZERO** (max observed capture **0.68**) |

**DISAGREE — "24h-from-entry max favorable move (candles, side-aware) has median 0.79%" and "39/177 trades saw >=2% favorable in 24h":**

Correct side-aware 24h potential (5m candles, `[open_time, +24h]`, LONG `(max_high/entry−1)`, SHORT `(1−min_low/entry)`):

- median **1.546%**, **71/177** >= 2% (LONG median 1.368 / 39 ge2; SHORT median 2.369 / 32 ge2)

The claim's `0.79%` and `39` are reproduced **exactly** by computing the SHORT side as `min_low/entry − 1` (raw fractional change) instead of `1 − min_low/entry`:

| Definition | median | >=2% |
|---|---|---|
| buggy (SHORT sign inverted) | **0.794 → "0.79"** | **39 → "39"** |
| correct side-aware | 1.546 | 71 |
| buggy SHORT only | **−2.369** (exact negation of +2.369) | 0 |
| correct LONG only | 1.368 | 39 |

LONG is unaffected by the bug (identical either way), which is why `39` = exactly the LONG count. So the sheet is internally inconsistent: `39/177 saw >=2% in 24h` cannot coexist with `71/177 saw >=2% after our exit` under one definition — `71` comes from the **correct** computation (`[entry,+24h]` ge2 = 71; 70 of those 71 first touched 2% only *after* our exit, so the "after our exit" label is substantively right), while `0.79`/`39` come from the buggy one. The sheet explicitly says "(candles, side-aware)" — it is not.

**DISAGREE — "capture ratio ~29%":** 0.229/0.79 = 29% is arithmetic on the wrong denominator. Correct: 0.229/1.546 = **14.8%**; median *per-trade* capture = **7.9%**. The error makes the system look *better* than it is — the thesis "we capture almost nothing" is **strengthened**, not weakened.

**AGREE — "71/177 (40%) saw >=2% favorable run AFTER our exit":** correct `[entry,+24h]` ge2 = 71; first-touch-after-exit = 70; `[exit,+24h]` ge2 = 75. Right order of magnitude, right conclusion (we exit at median 0.9h, so essentially all 24h potential accrues after we're out).

**AGREE — "ZERO captured >=80%":** true, but *trivially*: no trade's realized price-pnl ever reaches 2% (max = 1.0%, 5 trades >=1%), so with MFE>=2 the ratio is capped at 0.5 by construction. Not independent evidence.

Third measure for context: during-hold `mfe_pct`/`highest_price` median = **0.426%**; during-hold candle MFE median 0.507% → we realize 0.229% = ~45% of what was on offer *while we were in*, ~15% of what the next 24h held.

**Confidence: HIGH** (three exact numeric matches on the buggy definition + exact negation on SHORT; no other of ~15 window/side definitions I tried reproduces the 0.79/39 pair).

---

## Claim 2 — clusters

**Verdict: AGREE (with one caveat the CEO should see)**

All bucket numbers reproduce exactly at n=177 (known-meta n=170, 7 null):

| bucket | n | W/L | WR | net |
|---|---|---|---|---|
| clu1 | 15 | 6/9 | **40.0%** | **−$0.73** |
| clu2 | 27 | 18/9 | **66.7%** | **−$0.01** |
| clu3-4 | 48 | 30/18 | **62.5%** | **−$0.44** |
| clu5+ | 80 | 53/25 | **67.9%** | **+$0.08** |
| unknown | 7 | 5/2 | 71.4% | +$0.06 |

`>=4 vs <4`: **+13.5pp, two-prop z p=0.075** — exact match. My Fisher (the house test) = **p=0.0993**; at n=165 (trades opened before the 11-17 adjudication) Fisher = **0.0636**, z = 0.046.

**The registry's own prior read checks out:** at n=165 (opened <2026-11-17) the `>=4` gate blocks **32/103 = 31%** of winners — matches the registry's `31/97 = 32%` → **fk bar (<=20%) not met**. At full n=170 it is 24/107 = **22.4%**, still over the bar. Fisher never drops below 0.05 in any sample I ran (0.064 @165, 0.099 @170). Direction of `>=4` is best-cell in all three samples (n=165/170/177). → **"settled NO-SHIP stands" is correct.**

*(Note: I could not reproduce the registry's `fisher p=0.234` — I get 0.064 at n=165. Different WR convention or test likely. It does not change the verdict: no reading is <0.05.)*

**Caveat — leg (a) `cluster>=2` is closer than the sheet implies:**

| | claim's framing | my n=170 read |
|---|---|---|
| delta (block clu1) | +$0.61 @ n=161 (registry) | **+$0.73** (clu1 net −$0.73) |
| kept n | >=100 | **155** |
| kept WR | not down | **66.0%** vs known-baseline **63.7%** |
| fk (winners blocked) | — | **6/107 = 5.6%** (<=20% ✓) |
| z p / Fisher p | 0.214 (registry) | **0.046 / 0.054** |

So at n=170 the *text* of registered leg (a) (delta >= +$0.50, n>=100 kept, WR not down, replication agrees on direction) is satisfied, with Fisher sitting **0.004 above** 0.05. I scanned 6 thresholds to get here, so per the registry's own multiple-comparisons guard ("single p<0.05 from a scan is NOT the bar") this is a **report, not a ship** — and the blocked cell is only n=15. Flagging it because the sheet's flat "floor stays 1" hides that the `>=2` leg is now the strongest cell in the scan, stronger than `>=4`.

**Confidence: HIGH** on the reproduced numbers; **MEDIUM** on the exact `p=0.234` attribution.

---

## Claim 3 — discernment

**Verdict: PARTIAL — every number AGREEs exactly; "the leg qualifies to advance" needs a caveat**

Every figure reproduces to the cent:

| Sub-claim | Claim | Mine |
|---|---|---|
| jwr>=0.55 | 15T 40%WR −$0.84, two-prop p=0.048 | **15T 40.0% −$0.84, z p=0.048** (Fisher p=0.083) |
| jwr 0.30-0.45 | 56T 69% +$0.24 | **56T 69.1% +$0.24** |
| exp <100 | 31T 53%WR −$1.04 | **31T 53.3% −$1.04** |
| exp >=100 | 90T +$0.09, delta +$1.13, p=0.204 | **90T +$0.09, delta +$1.13, z p=0.204** (Fisher 0.274) |
| margin <$100 | 139T −$2.01 | **139T 60.6% −$2.01** |
| margin $100-1k | 34T 73.5% +$0.72, p=0.161 | **34T 73.5% +$0.72, z p=0.161** (Fisher 0.233) |
| margin >=$1k | ZERO trades | **ZERO** (max observed margin **$496**) |
| counterfactual | 145T 66%WR net −$0.06; dropped 32T −$0.98 | **145T 66.0% −$0.06; dropped 32T −$0.98** |

Registered exp-leg bar (net delta >= +$0.50 at blocked n>=30 **and** independent replication): **n=31 ✓, delta +$1.13 ✓, direction replicates ✓**. By the letter, the leg meets its bar.

**Caveats I would not ship through:**

1. **Era confound — the effect is almost entirely E2.** Cross-tab of `jup_trades<100` by era:

| era | <100 n / net / WR | >=100 n / net / WR |
|---|---|---|
| E1 (pre-10-31 12:00) | 3 / −$0.07 / 67% | 27 / −$0.22 / 67% |
| E2 (10-31..11-04) | **16 / −$0.92 / 47%** | 44 / +$0.23 / 65% |
| E3 (>=11-04) | **12 / −$0.05 / 58%** | 19 / +$0.08 / 68% |

Of the −$1.04, **−$0.92 comes from E2's 16 trades**. In the *current* era the filter would have saved **$0.05 over 15 days**. The "experience floor" is largely a bet on not-repeating-E2.
2. **p=0.204** — not significant, and this is one cell out of the ~30-cell scan.
3. **The combined counterfactual is just the exp leg.** `CF only exp leg`: keep 146 net **−$0.00**, drop 31 net −$1.04. `CF only jwr leg`: keep 162 −$0.20, drop 15 −$0.84. Combined drops 32 (not 46) — **14 of the 15 `jwr>=0.55` trades are already dropped by the exp leg**; the jwr cap contributes **+$0.06**. "145T / −$0.06" should not be read as two independent legs both working.
4. **Data gap:** `jup_win_rate`/`jup_trades` are null on **56/177 (32%)** of the book — same rows for both fields. The counterfactual keeps all 56 (net −$0.09), which is conservative and implementable, but a "pro-quality gate" that has no pro stats for a third of the copies should fix the feed first.

**Verdict rationale:** numbers AGREE, the registered bar is met *numerically*, but the effect is era-concentrated, non-significant, and overlapping with a second leg. I would advance it to **shadow/counterfactual collection only**, not to live enforcement, on this evidence.

**Confidence: HIGH** on reproduction; **MEDIUM** on "qualifies to advance".

---

## Claim 4 — era trend

**Verdict: PARTIAL (numbers exact, MFE-exit attribution wrong, causality not established)**

By `open_time` — exact match:

| era | n | WR | net |
|---|---|---|---|
| pre-2026-10-31 12:00 | **41** | **63.4%** | **−$0.48** |
| 10-31 .. 11-04 | **85** | **61.4%** | **−$1.05** |
| >=11-04 | **51** | **68.6%** | **+$0.49** |

Flags/timings verified:
- `STOP_TIGHTEN_ENFORCE = True` — comment "LIVE since 2026-11-04 (CEO T-override)"; commit `6d5f138c` **2026-11-04 04:24:51** ✓
- `JUP_YOLO_FILL_CAP_ENABLED = True`, 1 fill / 6h — same commit ✓
- `MFE_EXIT_ENABLED = True` — commit `e56e7942` **2026-10-31 19:01:50** ✗ **not "around 11-04"**

**DISAGREE on the MFE-exit leg of the attribution.** MFE-exit shipped **2026-10-31**, i.e. it is live throughout era 2 — and era 2 is the *worst* era (−$1.05). Stop-tighten *shadow* also shipped 10-31; only ENFORCE flipped on 11-04. Per-trade: E1 −$0.0117, E2 −$0.0124, E3 +$0.0096 — era 1 and era 2 are indistinguishable, era 3 is the only positive one. The data is consistent with **11-04's enforce+fill-cap**, not with MFE-exit.

Also: the era-2 boundary `10-31 12:00` matches **no** ship (MFE went live 19:01 that day); using actual ship times gives pre-MFE 49T 66.7% −$0.33 / MFE→enforce 85T 59.5% −$1.10 / >=enforce 43T 69.8% +$0.39 — same shape, so the conclusion survives the boundary choice.

**Causality not established:**
- E2 vs E3 WR **+7.2pp, z p=0.400, Fisher p=0.460** — not significant. Era 3 = **+$0.49 over 15 days** (+$0.0096/trade).
- **Selection confound:** the fill cap changed *which* trades get taken — 25–32 jup trades/day before 11-04, **<=4/day after**. Era 3 is a different book, not just different exits.
- **Volume-collapse confound** (registry flags it itself: 43/day → 5/day system-wide).
- **Mechanism is only partially engaged:** `[STOP-TIGHTEN-ENFORCE]` clamped 19 distinct trade-ids in the current log, of which **10 are era-3 jup ids** (~20% of the 51). So the clamp did fire on the cohort — but it is one of several moving parts.
- `close_reason` mix shifts hard: E2 has 20 `hard_max_loss` vs E3's 2; E1 had 0 `mfe_exit`, E2 31, E3 16.

**Confidence: HIGH** on numbers and git timings; **LOW–MEDIUM** on the causal reading.

---

## Claim 5 — high-WR pros = scalpers

**Verdict: PARTIAL (conclusion survives; the cited numbers are the same bug)**

| | Claim | Correct (side-aware) | Buggy (SHORT sign inverted) |
|---|---|---|---|
| jwr>=0.55 entries, 24h potential median | 0.87% | **1.653%** (n=15) | **0.868% → "0.87"** |
| jwr<0.45 entries, 24h potential median | 0.94% | **1.475%** (n=90) | **0.942% → "0.94"** |

The claim's `0.87` vs `0.94` reproduces **exactly** only under the SHORT sign bug — the same bug as Claim 1, third exact match. So Claim 5's evidence line is from the broken metric.

And it **contradicts the claim's own wording**: `0.87 < 0.94` *is* lower potential, yet the sentence says "do NOT have lower 24h potential". The correct numbers make the stated conclusion true: **1.653% vs 1.475% — high-WR pros' entries are not lower-potential (slightly higher)**. So "their ENTRIES mark direction, their win profile is micro" survives and is better supported than the sheet's own numbers support.

Mechanism note (why the bug biased this cell): cohort direction mix differs — `jwr>=0.55` is 9L/**6S** (33% short) vs `jwr<0.45` 69L/**21S** (23% short). More SHORTs ⇒ more negated values ⇒ artificially lower "potential" under the bug. Any cohort with a higher short share looks artificially low-potential in this sheet — worth re-checking every other cell computed the same way.

**Confidence: HIGH** on the bug; **MEDIUM** on the substantive conclusion (n=15 in the >=0.55 cell).

---

## Cross-cutting notes

1. **The single most important finding is the SHORT-side sign error.** It produces `0.79%`, `39/177`, `0.87%` and `0.94%` — four of the sheet's numbers. Anything else computed with the same helper (the anti-chase `z_score`/RSI cells, margin tiers, era splits that mix long/short shares) should be re-run before being cited. The *direction* of every affected conclusion happens to survive (correct potential is *higher*, capture is *worse*), but the specific figures must not go into a verdict or a live gate.
2. **Multiple comparisons.** `jwr>=0.55 p=0.048` (n=15) and my own `cluster>=2 p=0.046` (n=15 blocked) are both single cells from ~30–60-cell scans. Per the registry's own guard neither is shippable on its own. Everything else in the sheet is p=0.075–0.40.
3. **No survivorship, no time-anchor, no duplicates, no paper rows** — those classic traps are clean here.
4. **Dollar magnitudes are tiny throughout** (whole 177-trade book = −$1.04). Every "delta >= +$0.50" bar is being cleared by coffee money; position sizing, not gate-tweaking, is the dominant variable.

## Bottom line vs the original question ("bigger clusters? higher-WR traders only? improve winrate?")

- **Bigger clusters:** `>=4` does not clear the house bar (Fisher 0.099, fk 22.4%) → **NO-SHIP stands**. `>=2` is the live cell to watch (delta +$0.73, fk 5.6%, Fisher 0.054) — keep collecting, do not flip on this read.
- **Higher-WR traders only:** the data says the *opposite* for winrate — `jwr>=0.55` is the **worst** cohort (15T, 40% WR, −$0.84) and the `0.30–0.45` band is the sweet spot (56T, 69%, +$0.24). The **experience** floor (`jup_trades>=100`) is the leg with a registered-bar hit, but it is era-concentrated (−$0.92 of −$1.04 from E2; −$0.05 in the current era) → **shadow, not enforce**.
- **Winrate:** breakeven WR is **66.1%** vs actual **64.0%** with payoff 0.51 — the gap is the *payoff ratio*, not the hit rate. The exit stack (stop-tighten 0.75%, MFE-giveback 30% @0.40% arm, PM trail 0.40/0.20, fill cap 1/6h) is where the leverage is; entry-side filtering can at most recover ~$1 of a −$1.04 book.

---

## SUBJECT'S RESPONSE (2026-11-18, the analyst under audit)

**On the SHORT-potential bug (Claim 1): CONFIRMED — auditor is right, and my
first "verification" attempt repeated the bug.** Root cause identified: not
the sign, the REDUCTION OPERATOR. My helper took `min((1 - low/entry))` over
candles = the LEAST favorable low (highest low), when SHORT favorable needs
`max((1 - low/entry))` = `1 - min(low)/entry`. Decisive recomputation:

```
                                    SHORT-only median   SHORT >=2%   aggregate median   agg >=2%
(1 - min_low/entry)  [correct]          +2.353%            31            1.519%            70
min(1 - low/entry)   [my code]          (small/neg)         0            0.794%            39   ← my reported
(min_low/entry - 1)  [auditor's stated mechanism]         -2.353%         0            0.794%            39   ← also reproduces
```

Both wrong variants land on my exact reported pair (0.794/39) because the
shorts collapse below the LONG-dominated median line either way. Corrected
numbers (mine 1.519%/70 vs auditor 1.546%/71 — ±1 from window-boundary
`<` vs `<=`) agree: **capture ratio 0.229/1.52 ≈ 15% (I reported 29%),
≥2% potential 40% (I reported 22%).** The micro-movement thesis is
STRENGTHENED, not weakened — my error made the system look BETTER than it is.

**Scope check:** grep across scripts/ + analysis/ — no saved script carries
the pattern; the bug existed only in ad-hoc heredocs from this session.
jup_exit_sim's replay/SHORT math audited clean (direction-aware sl/tp hits,
`_jts_fav` SHORT branch uses lowest with >0 guard).

**On the other claims:** accept all auditor corrections — era boundary
(10-31 12:00 matched no ship; MFE-exit went live 19:01 so era2 contains it
and is the WORST era → MFE-exit cannot be credited for era3; only
stop-tighten-enforce + fill-cap are the 11-04 pair), exp-leg era-confinement
(-$0.92 of -$1.04 from E2; E3 contribution -$0.05), the jwr-leg overlap
(14/15 jwr≥0.55 trades already dropped by exp leg → +$0.06 marginal), and
the 32% NULL pro-stats feed. **Adopting the auditor's recommendation: the
experience-floor leg advances to SHADOW/counterfactual collection only —
NOT live enforcement.** No live-gate changes made from this analysis.
