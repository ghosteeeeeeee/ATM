# Independent Verdict — ROUND 2 (Revised Understanding Verification) — 2026-10-06

**Auditor:** Independent (fresh read + own test runs + own DB queries; verified at ~15:19–16:20 UTC 2026-10-06)
**Sources:** `scripts/chop_detector.py` (full), `scripts/signal_compactor.py` (1180–1379, 1930–2050, 2600–2729, 3360–3470, 4590s), `scripts/decider_run.py` (1920–1960, 3360–3410, 4200–4250), `scripts/hermes_constants.py`, `scripts/position_manager.py`, `scripts/btc_crash_filter.py`, `scripts/pnl_utils.py`, PostgreSQL `brain` DB, `data/continuum.db`, `data/candles.db`, `logs/pipeline.log`, git history.

---

## Claim-by-claim

### Claim 1 — "The chop detector voting bug (CHOP checked before TREND) is the highest-impact remaining fix — it currently classifies a strongly bullish market as CHOP."

**Verdict: PARTIAL**
**Confidence: HIGH**

Evidence:
- **Code-order bug CONFIRMED.** `chop_detector.py` lines 541–550: `elif votes['CHOP'] >= 3` is evaluated **before** `elif votes['TREND'] >= 3`. When both are ≥3, CHOP wins regardless of which leads. The only TREND rescue before that branch is line 536: `elif _continuum_voted and votes['TREND'] >= votes['CHOP']` — which requires the continuum *structural* override to have fired.
- **"Currently classifies a strongly bullish market as CHOP" is FALSE right now.** I ran `get_regime()` myself at 15:19:45:
  ```
  regime: TREND (continuum override)
  votes: TREND=8, CHOP=3, CRISIS=0
  reason: TREND (continuum override): btc_mom=+0.275%
  details: dir_outcome LONG wr=100 total=2 / SHORT total=0; vol=FLAT; phase=quiet
  ```
  BTC continuum at that moment: `CALM|BULL|ABOVE|score=99.85`. The bullish structural override (CALM+BULL+ABOVE → +5 TREND, `_continuum_voted=True`) fired and the line-536 branch classified TREND correctly.
- **But the bug DID misclassify a strongly bullish market as CHOP earlier today** — via a compound defect, not the vote order alone. At 08:52–08:57 and 14:58 BTC continuum was `DECLINING|LEAN_BULL|ABOVE|score=81→98`. `DECLINING` is **excluded** from the bullish phase set (line 524: RECOVERY/CALM/NEUTRAL only) while it **is included** in the bearish set (line 521). So `_continuum_voted` stayed False, and the CHOP-before-TREND order then produced CHOP. Log proof: `[CHOP] ETH LONG trendline_bounce_long: BLOCKED` at 08:52–08:57, `BTC LONG trendline_bounce_long` at 05:43–05:46 — during bullish structure. **The deeper bug is the bullish phase-set asymmetry; the vote order is the tiebreaker that turns it into a wrong CHOP.**
- **"Highest-impact remaining fix" is NOT supported by data:**
  - The chop detector's `[CHOP]` gate (signal_compactor 1343–1374) only evaluates **non-bypass** signals. All 7 losing trades on 10-06 were bypass signals — they never touched `get_regime()`.
  - Only **10 `[CHOP]` blocks** today (ETH/BTC `trendline_bounce_long`). I measured forward returns of blocked signals: ETH +180m **+0.04%**, HYPE +180m **−0.69%**, NEAR **−0.23%**, BABY **−1.84%**, XPL **−0.28%** — the blocked LONGs would mostly have lost.
  - The much bigger blocker — **`BTC-CHOP-GATE`, 39 blocks today** (signal_compactor 1194–1271) — **does not call `get_regime()` at all**. It uses BTC velocity flatness + `_classify_signal()`. Fixing the voting order does not touch it.
- Two of four vote sources are dead at classification time: `dir_outcome` returned total=0 for both directions in my run (needs ≥3 trades in a 30-min window to vote). Classification currently rests on vol + phase + btc_mom + overrides.

---

### Claim 2 — "The score floor 0.3 lets unanimously-penalized trades execute at conf=93."

**Verdict: AGREE (mechanism confirmed) — but the floor is not the root enabler**
**Confidence: HIGH**

Evidence:
- **Floor confirmed:** signal_compactor.py:2038–2049: `_mult_floor = 0.3`; `0 < product < 0.3` → floored to 0.3; `product ≤ 0` → score 0 (hard blocks preserved). SUPER log chain 01:48:00:
  ```
  [TREND-ALIGN] SUPER LONG: BTC bearish (score=7, bias=-0.86) → 0.60x
  [RR-ENGINE] SUPER LONG: RR PENALTY: R:R=0.95 grade=D → 0.70x
  [REGIME-CONF] SUPER trend_ride_long: HIGH → 0.50x
  [OSCILLATOR] SUPER: LOW+falling → 0.60x
  [SCORE-FLOOR] SUPER LONG: multiplier product 0.0867 floored to 0.3
  [HOTSET-FINAL-ADD] conf=88.0 score=23.40
  [DECIDER-LOOP] SUPER LONG conf=93.0 → EXEC @ $0.239600 → −2.95%
  ```
  Every gate penalized; the trade executed at conf=93. **Confirmed exactly as claimed.**
- **748 `[SCORE-FLOOR]` events today** (products 0.13–0.27): AVAX 0.256, RESOLV 0.27/0.22, BTC 0.175, MERL 0.221, CC 0.195, SAND 0.134/0.172, SOL 0.259/0.213, FOGO 0.202, SUPER 0.087… The floor fires constantly — penalty stacking routinely drives products below 0.3 and they are all resurrected at 0.3.
- **Root enabler is deeper than the floor:** the multiplier product is applied only to the **hotset ranking score** (line 2049: `final_score = score * _mult_adjusted`). **`final_confidence` — the field that gates execution — is never multiplied by the penalty stack.** SUPER: base conf 78 → +10 RSI sweet spot → 88 → decider conf=93. Even *without* the floor, score would be 78×0.0867=6.8 — and with hotsets currently holding only 1–2 entries, a score of 6.8 still makes top-10 and still executes at conf 93.
- **Minimum score threshold for hotset entry: THERE IS NONE.** Selection is `hotset_final[:10]` (top-10 by score, no absolute floor). The only execution gate is `MIN_EXEC_CONFIDENCE = 50` (decider_run.py:3202) applied to `final_confidence` — which ignores penalties entirely. A trade can be unanimously penalized, score near zero, and still execute at conf 90+.
- SUPER-class backtest (from commit cf4be820 message): **22T 45.5% WR −$0.57 over 7d → +$0.57 if blocked.** Blocking these trades flips the class from negative to positive.

---

### Claim 3 — "The bare-RECOVERY override bug is already fixed by brain_auditor today."

**Verdict: AGREE**
**Confidence: HIGH**

Evidence:
- **Both sites verified fixed in current code:**
  - signal_compactor.py:1241–1249 (BTC-CHOP-GATE LONG override): `(_p2 in ('RECOVERY','NEUTRAL') and _l2 not in ('LEAN_BEAR','BEAR'))` — bare RECOVERY/NEUTRAL now requires **non-bear linreg**. RECOVERY+LEAN_BEAR+BELOW matches no clause → gate blocks.
  - decider_run.py:3390–3392 (BTC-CRASH-OVERRIDE LONG): identical fix + structural bull any phase.
- **Commit confirmed:** `cf4be820` 2026-10-06 06:39:50 "signals: fix BTC override LONG bare RECOVERY/NEUTRAL hole (SUPER-class)", touching both files; diff shows the exact before/after.
- **Log verification:** pre-fix (01:57–02:50) XPL LONG and ZRO LONG repeatedly got `BTC-CHOP-OVERRIDE … RECOVERY+LEAN_BEAR+BELOW, allowing despite chop gate` — the bug live. **Post-fix (after 06:40): ZERO occurrences** of any `OVERRIDE … LONG` with `RECOVERY+LEAN_BEAR|RECOVERY+BEAR|NEUTRAL+LEAN_BEAR|NEUTRAL+BEAR`. All 66 post-06:40 LONG overrides are legitimate (BTC-exempt signal types, or LEAN_BULL/NEUTRAL-linreg structures).
- **Pipeline picks up fixes without restart:** hermes-pipeline runs as a systemd timer spawning fresh `python3` each minute (verified: service restarted 15:44:24, runs every 60s). Code changes go live on the next cycle.
- **Minor residual hole (not a regression):** bare `RECOVERY/NEUTRAL` + **NEUTRAL/other-non-bear linreg + ema=BELOW** still passes the override (`_l not in ('LEAN_BEAR','BEAR')` doesn't check ema). Narrower than the original bug but worth a follow-up.
- Pipeline restart caution (AGENTS.md) does not apply here — no long-lived process holds old code.

---

### Claim 4 — "BTC-CRASH gate blocks SHORTs during crashes when they should fire."

**Verdict: PARTIAL**
**Confidence: HIGH**

Evidence:
- **The gate CAN block SHORTs — design confirmed:** `btc_crash_filter.py` layers: price-crash layer sets `blocked_direction=''` (**all directions**, lines 558–563) during fast BTC dumps; momentum layer blocks SHORT when BTC rising (line 348–349); level layer blocks SHORT when BTC near session low (lines 405–407, bounce-risk logic). So yes, a BTC dump can emit `🚨 [BTC-CRASH] … SHORT BLOCKED`.
- **But the bear-structure override exists and fired in EVERY logged instance today:** decider_run.py:3395–3400 allows SHORT when `_p == 'DECLINING'` or `(CALM/RECOVERY + LEAN_BEAR/BEAR + BELOW)`. Log evidence — every SHORT block was immediately rescued:
  ```
  02:21:39 🚨 [BTC-CRASH] GOAT SHORT BLOCKED — BTC_LEVEL
  02:21:39 ✅ [BTC-CRASH-OVERRIDE] GOAT SHORT — CALM+LEAN_BEAR+BELOW, allowing
  02:26:35 🚨 [BTC-CRASH] GOAT SHORT BLOCKED — MOMENTUM
  02:26:35 ✅ [BTC-CRASH-OVERRIDE] GOAT SHORT — DECLINING+LEAN_BEAR+AT, allowing
  02:35/02:36/06:36/06:37 🚨 BTC SHORT BLOCKED — BTC_LEVEL → ✅ overridden (CALM/RECOVERY/DECLINING+LEAN_BEAR+BELOW)
  ```
  **Net suppression of SHORTs by this gate today: zero.** GOAT died later in EXEC-RSI-FLOOR (per round-1), not the crash gate.
- **Design tension remains:** blocking SHORTs during a crash contradicts the stated philosophy ("every dump is a SHORT opportunity"), and the level layer (block SHORT at session low) + price-crash layer (block all) are the counterintuitive parts. The momentum layer (block SHORT when BTC *rising*) is defensible V-reversal protection. Worth a policy decision, but it did not cost any trade today.

---

### Claim 5 — "The hard stop is -1% PRICE move, not -3% margin as originally claimed."

**Verdict: AGREE**
**Confidence: HIGH**

Evidence:
- **Constant:** hermes_constants.py:702: `CUT_LOSER_PNL = -1.00` (widened from −0.50 on 2026-10-01). Comment itself notes it governs position_manager's HARD_MAX_LOSS exit.
- **Trigger code:** position_manager.py:3386–3394: `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL_HERMES; if live_pnl <= HARD_MAX_LOSS_PCT → close "hard_max_loss"`. `live_pnl = compute_live_pnl(entry, cur, direction)` (line 2670) = **unleveraged raw price move** (pnl_utils.py:35–56: "Direction-aware, unleveraged (raw market return %)").
- **DB proof — exit_conditions store the raw move; pnl_pct stores the leveraged figure:**
  | Token | exit_conditions (raw) | pnl_pct (leveraged) | lev | raw×lev check |
  |---|---|---|---|---|
  | TURBO | hard_max_loss_pct=**−1.04%** | −3.1073 | 3 | −1.04×3 = −3.12 ✓ |
  | IO | hard_max_loss_pct=**−1.08%** | −3.5731 | 3 | −1.08×3 = −3.24 (exit px drift) ✓ |
  | SUPER | hard_max_loss_pct=**−1.05%** | −2.9459 | 3 | ✓ |
  | USELESS | hard_max_loss_pct=**−1.17%** | −3.1123 | 3 | ✓ |
  | POL | hard_max_loss_pct=**−1.21%** | −5.9828 | 5 | −1.21×5 = −6.05 ✓ |
- All 7 hard-stop exits fired at ≈ −1% **raw price move**. The plan's "−3% to −6%" describes leveraged pnl_pct, not the trigger. Original claim correctly revised.
- **Side finding:** position_manager.py:2672 fallback `live_pnl = pnl_pct` (when entry/cur missing) compares a **leveraged** DB pnl_pct against the **−1.00 raw** threshold — a unit-mismatch edge case that would exit early. Latent, not hit by these trades.

---

### Claim 6 — "TURBO/IO/HBAR were on the RIGHT side at entry (bull continuum) and lost because market flipped — not wrong-side entry."

**Verdict: AGREE (for these three tokens specifically)**
**Confidence: HIGH**

Evidence — I queried continuum.db at each entry time:
| Token | Entry (UTC) | BTC continuum at entry | Score |
|---|---|---|---|
| TURBO | 10-05 20:21:58 | DECLINING + **LEAN_BULL** + **ABOVE** | 77.8 |
| IO | 10-05 21:53:35 | DECLINING + **LEAN_BULL** + **ABOVE** | 99.9 |
| HBAR | 10-05 22:18:38 | DECLINING + **LEAN_BULL** + **ABOVE** | 99.5 |
- Structure was unambiguously bullish (lean bull, above EMA300, score 78–100). LONG was the correct side per structure. BTC flipped bear ~23:40; all three hard-stopped at −1% raw at 00:36–00:45.
- **Caveat 1 — scope:** this does NOT extend to the other three LONGs. SUPER entered RECOVERY+LEAN_BEAR+BELOW score **5.8** (clearly wrong side, enabled by the now-fixed override bug); POL entered DECLINING+LEAN_BEAR+AT score 50.2 (bear linreg); USELESS CALM+LEAN_BULL+AT score 48.9 (transitional). The revised claim is right about TURBO/IO/HBAR but the day's book was mixed: 3 right-side-flipped, 3 wrong/transitional-side.
- **Caveat 2 — the flip vindicated the stop:** forward returns after exit (candles.db, next 6h): TURBO min **−2.57%**, IO min **−2.52%**, HBAR min **−1.05%** below exit price. Only POL recovered (+2.61% after its exit). "Lost because market flipped" is true, but for these three the −1% hard stop **saved** money — widening it (plan Fix 4) would have increased these losses. Phase was also `DECLINING` at all three entries — the phase indicator was already warning even while structure said bull.

---

## Answers to the eight investigation items

1. **Voting bug (CHOP≥3 before TREND≥3):** CONFIRMED in code (lines 541/546). My live run: TREND=8, CHOP=3 → correctly TREND *because* the continuum structural override fired (CALM+BULL+ABOVE). The bug bites only when the structural override doesn't fire — i.e., when `phase=DECLINING` (excluded from the bullish phase set) despite LEAN_BULL+ABOVE. That's what happened at 08:52 and ~14:58 today.

2. **Current market classification:** BTC continuum = `CALM|BULL|ABOVE|score 99.85` (15:19) — strongly bullish. `get_regime()` = **TREND** (correct right now). Earlier today (08:52–08:57, ~14:58) the detector said CHOP during `DECLINING+BULL+ABOVE` score 81–98 — wrong then, correct now. The claim's "currently" was true at ~14:58, false at 15:19.

3. **Score floor / hotset threshold:** Floor at signal_compactor:2038–2049 (`_mult_floor = 0.3`). SUPER product 0.0867 → floored → executed conf=93 — **yes, confirmed**. **Minimum score threshold for hotset entry: none** — `hotset_final[:10]` top-10 by score only. Execution gate = `MIN_EXEC_CONFIDENCE=50` on `final_confidence`, which **never sees the penalty multipliers**. 748 floor events today.

4. **BTC-CRASH gate:** Price-crash layer blocks ALL directions; level layer blocks SHORT at session lows; momentum layer blocks SHORT on rising BTC. Counterintuitive parts exist, but decider_run's bear-structure override (3395–3400) rescued **every** SHORT block in today's logs (GOAT ×3, BTC ×4+). Net suppression today: zero.

5. **Hard stop semantics:** `CUT_LOSER_PNL = -1.00` applied to `compute_live_pnl()` = **unleveraged raw price move** (position_manager 3386–3394). DB exit_conditions confirm raw −1.04% to −1.21% at exit vs stored pnl_pct −2.9% to −6.0% (raw × leverage). **−1% PRICE move confirmed; −3% margin framing disproven.**

6. **Bare-RECOVERY fix:** Both sites fixed (signal_compactor 1241–1249, decider_run 3390–3392); commit cf4be820 06:39:50; **zero** post-fix `RECOVERY+LEAN_BEAR` LONG overrides in logs (vs XPL/ZRO firing the bug at 01:57–02:50 pre-fix). RECOVERY+LEAN_BEAR+BELOW no longer triggers the override. Residual hole: bare RECOVERY/NEUTRAL + non-bear linreg + ema=BELOW still overrides (no ema check on that clause).

7. **IO pnl_usdt=0.00:** DB row: `hl_notional_usdt = 0.1557`, `hype_realized_pnl_usdt = -0.001854`, `pnl_pct = -3.5731`. Guardian backfilled USDT PnL from HL ground truth on the **actual fill**: the live IO position was **$0.16 notional**, not $11–33. 0.1557 × −1.191% raw = −0.00185 USDT → rounds to **0.00** in `numeric(15,2)`. pnl_pct is correct (raw −1.191% × 3). **Root cause: order sizing/fill failure on Hyperliquid, not a PnL-math bug.** (TURBO's first 10-05 trade also mismatched: hl_notional 15.04 vs amount_usdt 22.10.)

8. **Signal classification gaps (my `_classify_signal()` runs):**
   | Input | Result | Problem |
   |---|---|---|
   | `bb-squeeze+` | MEAN_REVERSION | ✓ |
   | `bb_squeeze+` | **MOMENTUM** | underscore variant misses overrides/family → blocked in chop |
   | `trend-ride+` | MEAN_REVERSION | ✓ (explicit override) |
   | `trend_ride_long` | MEAN_REVERSION | ✓ (override added c285e79f, 10-05 21:44) |
   | `mtf-regime-trend-` | **MOMENTUM** | default; bypass-norm match saves it in the `[CHOP]` gate |
   | `mtf_regime_trend_short` | **MOMENTUM** | `_short` suffix → norm `mtf_regime_trend_short` ≠ bypass `mtf_regime_trend` → **chop-blocked** (GMT/MET 10-05) |
   | `continuum-trend-` | **MOMENTUM** | default; inconsistent with `continuum_trend_short` → MEAN_REVERSION |
   Unknown signals default to MOMENTUM (conservative) — every unregistered string gets chop-blocked. Normalization gaps CONFIRMED.

---

## NEW FINDINGS (missed by the revised understanding)

1. **🔴 Penalty multipliers never reach execution confidence — the score floor is a symptom, not the disease.** `final_confidence` (gates execution at ≥50) is built from raw signal confidence + additive bonuses (RSI sweet spot, hot rounds, CTX-GATE). The 26-factor penalty product only scales the hotset *ranking* score. SUPER executed at conf=93 with a product of 0.0867 because **nothing multiplies confidence down**. Even removing the 0.3 floor would not have blocked it (hotset holds 1–2 entries; score 6.8 still ranks). This is the actual mechanism that lets structurally dead trades fire, and it applies to all 748 floor events today.

2. **🔴 CONTINUUM-BLOCK ema-AT hole let POL LONG into bear structure.** signal_compactor:2642–2644: `_cont_bearish` requires `ema300_position == 'BELOW'`. POL entered 10-06 00:20 at `DECLINING+LEAN_BEAR+**AT**` score 50.2 — ema hysteresis "AT" meant `_cont_bearish=False`, `_cont_bullish=False` → fell through to the velocity fallback and passed. LEAN_BEAR+AT should count as bearish for LONG-blocking (mirror the fix that added AT as bullish for SHORTs).

3. **🟠 Chop detector's bullish phase-set asymmetry is the real trigger of "CHOP during bull market."** Line 521 bearish set includes DECLINING; line 524 bullish set excludes it. `DECLINING+LEAN_BULL+ABOVE` score 81–98 gets no structural vote → CHOP. Fix the phase set (or count linreg/ema regardless of phase) — higher leverage than the vote order alone.

4. **🟠 `dir_outcome` vote source is dead at classification time.** Both directions returned total=0 in my run (needs ≥3 outcomes in a 30-min window). The WR-degradation input almost never votes; regime rests on vol+phase+mom+overrides.

5. **🟠 IO live order filled at $0.156 notional (~1.4% of intended).** Beyond the accounting artifact, this means intended risk was never deployed and fills/sizing on HL need auditing. TURBO's first 10-05 trade also mismatched (15.04 vs 22.10).

6. **🟡 `BTC-CHOP-GATE` (39 blocks/day) is independent of `get_regime()`.** It uses velocity-flatness + `_classify_signal()`. Any chop-detector refactor leaves this gate untouched — yet it blocked the majority of signals today, including bypass-listed families whose underscore forms classify MOMENTUM (`oversold_bounce_long`, `warrior_sr_confirm_long`, `grind_accumulator_long`, `btc_pump_rider_long` — all blocked today, forward returns mostly negative, so the blocks were largely correct).

7. **🟡 Expectancy math (the profitability core):** since 10-03: **107 trades, 62 wins (57.9% WR), avg win +2.55% / avg loss −3.81% pnl_pct (USDT: +0.092 / −0.141)** → expectancy ≈ **−0.13% per trade** (≈ −$0.006/trade). Losses run **1.54×** wins. A 58% WR cannot carry a 1.54 loss/win ratio; need WR ≥ ~61% at current ratios, or cut avg loss to ≤ −2.5% pnl_pct, or widen winner trails (activation 0.40% is tight vs the −1% raw stop). Since 10-05: 40 trades, 20W, net **−$1.63**. The 7/7 day was regime-flip clustering (6 LONGs opened 20:21–01:48 into a ~23:40 flip), not uniformly wrong-side entries.

8. **🟢 Unit-mismatch edge case:** position_manager:2672 compares leveraged DB `pnl_pct` against the −1.00 raw threshold when prices are missing. Latent.

---

## Summary table

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | Chop voting bug = highest-impact fix; "currently" classifies bull as CHOP | **PARTIAL** — bug real, but currently TREND (8:3); blast radius limited to non-bypass momentum; BTC-CHOP-GATE (39 blocks/day) doesn't use get_regime(); deeper bug = bullish phase-set asymmetry | HIGH |
| 2 | Score floor 0.3 lets unanimously-penalized trades execute at conf=93 | **AGREE** — SUPER 0.0867→0.3→exec conf=93 confirmed; 748 floor events/day; but root cause is final_confidence never being multiplied by penalties; no min score threshold exists | HIGH |
| 3 | Bare-RECOVERY override bug already fixed by brain_auditor | **AGREE** — both sites fixed (cf4be820 06:39:50); zero post-fix violations in logs; pre-fix XPL/ZRO violations at 01:57–02:50 | HIGH |
| 4 | BTC-CRASH gate blocks SHORTs during crashes | **PARTIAL** — gate can block (price-crash=all dirs, level=SHORT at lows), but bear-structure override rescued every SHORT block today; net suppression zero | HIGH |
| 5 | Hard stop is −1% PRICE move, not −3% margin | **AGREE** — CUT_LOSER_PNL=−1.00 on unleveraged compute_live_pnl; DB exit_conditions show −1.04%…−1.21% raw vs −2.9%…−6.0% pnl_pct | HIGH |
| 6 | TURBO/IO/HBAR right side at entry, lost on flip | **AGREE** for these three — continuum LEAN_BULL+ABOVE score 78–100 at entry; but does not extend to SUPER (score 5.8 bear) / POL (LEAN_BEAR) / USELESS (transitional); stop exit was vindicated (price fell further after) | HIGH |

---

## HIGHEST-IMPACT FIX

**Gate execution on the penalty product — make `final_confidence` respect the multipliers (or hard-block below a product threshold).**

Evidence:
- SUPER-class 7d backtest (commit cf4be820): 22T 45.5% −$0.57 → **+$0.57 if blocked**. One fix flips a signal class from negative to positive.
- 748 `[SCORE-FLOOR]` events today — the system's own risk model (TREND-ALIGN bearish, RR grade D, REGIME-CONF penalized, OSC bearish) unanimously said "no" and execution said "yes at conf 93" **748 times**.
- The floor is cosmetic for execution: with 1–2-entry hotsets, even an unfloored score of 6.8 still executes at conf 93. **The fix must touch `final_confidence` (or add a product-threshold block), not just the score floor.**
- Suggested implementation: in the scoring pipeline, when `_mult_product < 0.15` (or when TREND-ALIGN penalizes against direction at ≥0.6x bearish), either (a) block the signal outright (like `product ≤ 0`), or (b) multiply `final_confidence` by `max(_mult_product, 0.3)` so `MIN_EXEC_CONFIDENCE=50` actually binds. Then independently backtest before enabling (per SOP).

**Runner-up fixes (in order):**
1. CONTINUUM-BLOCK ema-AT hole (LEAN_BEAR+AT must block LONGs) — direct POL-loss enabler, one-line fix.
2. Chop detector bullish phase set: include DECLINING (or drop phase gating on the structural override) + fix vote order (TREND before CHOP or compare counts) — cheap, fixes the "CHOP during bull" episodes, but modest direct P&L impact.
3. Normalization pass on `_classify_signal()` (hyphen/underscore/direction-suffix canonicalization) — closes the `bb_squeeze+` / `mtf_regime_trend_short` gaps.
4. Do NOT widen the hard stop based on today's data — TURBO/IO/HBAR/USELESS fell further after exit; only POL recovered. The loss/win asymmetry (1.54×) should be fixed on the **winner** side (trail activation 0.40% too tight vs −1% raw stop) or via entry quality, not by letting losers run further.

---

## PROFITABILITY ASSESSMENT

What the numbers say (all from PostgreSQL, run myself):
- Since 10-03: 107 closed trades, **57.9% WR**, avg win +2.55% / avg loss −3.81% (pnl_pct); USDT: +0.092 / −0.141 → **expectancy ≈ −0.13%/trade**. The system is a ~58% winner with 1.54:1 loss/win ratio — structurally slightly negative.
- Since 10-05: 40 trades, 50% WR, net **−$1.63**. The catastrophic-looking −24.6% pnl_pct day (10-06) = **−$0.73 real**, driven by 6 same-direction LONGs opened into a regime flip plus one wrong-side SUPER.

What it would take to become profitable:
1. **Stop the unanimous-"no" trades** (penalty-gated execution) — the commit's own backtest says this alone turns SUPER-class positive; extend to all product<0.15 classes and re-measure.
2. **Close the bear-structure ema-AT hole** so LONGs cannot open into LEAN_BEAR (POL-class losses).
3. **Restore loss/win ratio ≤ 1.2** — either raise winner capture (widen trail activation from 0.40%, or hold through the first pullback) or cut hard-stop depth below −1% raw where chop noise dominates (regime-aware stop, but *wider only in confirmed TREND*, not blanket). At 58% WR, breakeven requires loss/win ≤ 1.38; target 1.1–1.2 for real edge.
4. **Keep the bare-RECOVERY fix from regressing** — it is the only fix today with a clean before/after log proof; add a log-alert if `RECOVERY+LEAN_BEAR` LONG overrides ever reappear.
5. **Audit HL order sizing** (IO $0.16 fills) — real money isn't being deployed at intended size; all USDT-based analytics are distorted until fills match intent.
6. Regime-flip clustering control: 6 LONGs entered within 4h of each other all died on one BTC flip — a portfolio-level cap (max N concurrent same-direction new entries per regime window) would have capped the 10-06 damage at ~1/6.

Bottom line: the revised understanding is directionally right on 5 of 6 claims, and correctly walks back the original plan's misattributions. But it over-credits the chop detector voting bug (Claim 1) and under-credits the execution-side defect: **the system's penalty engine is advisory theater — it scores signals down and then executes them at full confidence anyway.** Fixing that, plus the two one-line structure holes (ema-AT bear, bare-RECOVERY kept fixed), is what moves expectancy positive. The chop detector is a classification-quality issue, not the profit lever.
