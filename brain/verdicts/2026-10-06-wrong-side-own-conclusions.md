# Independent Verdict — Wrong-Side Chop Detector Plan (2026-10-06)

**Auditor:** Independent (fresh read, no priming — read plan, code, DBs, logs, ran chop detector myself)
**Plan under review:** `/root/.hermes/plans/wrong-side-chop-detector-2026-10-06.md`
**Data sources verified:** PostgreSQL brain DB, `data/continuum.db`, `data/candles.db`, `logs/pipeline.log`, `scripts/chop_detector.py`, `scripts/signal_compactor.py`, `scripts/decider_run.py`, `scripts/hermes_constants.py`

**Bottom line:** The plan's headline numbers do not reproduce from the databases. Its root cause (chop detector direction-blindness) is only half-true and did NOT cause today's losses — all 7 losing trades bypassed the chop detector entirely via `STANDALONE_BYPASS_SIGNALS`. The actual enabler of the losing LONGs was a bare-RECOVERY override bug in the BTC-CHOP-GATE and BTC-CRASH filters, which brain_auditor already found and fixed today — the plan is unaware of these fixes. The one verified kill (WR hard block on BTC SHORT) is in decider_run, not the chop detector, and blocking was not costly today (BTC went nowhere after both block windows).

---

## Claim-by-claim

### Claim 1 — Chop detector is direction-blind; blocks ALL momentum in CHOP; blocks winning SHORTs, allows losing LONGs

**Verdict: PARTIAL**

Evidence:
- `chop_detector.py` `should_trade_signal(signal_type, regime=None, token=None)` (line 577) has **no direction parameter** — direction-blind at that level: CONFIRMED.
- In CHOP, `momentum_allowed=False`, `mean_reversion_allowed=True` (lines 541–545) — blocks all MOMENTUM-class signals both directions: CONFIRMED. There is a token-trend-score bypass (lines 594–601, score ≥31 allows).
- **But the losing LONGs never touched this gate.** All 6 LONG signals (`bb-squeeze+`, `trend-ride+`) are in `STANDALONE_BYPASS_SIGNALS` (hermes_constants:2729, 2738). `signal_compactor.py` lines 1346–1348 skip the chop-detector check entirely for bypass signals. Log proof: `CONFLUENCE-GATE-PASS USELESS LONG: {bb-squeeze+} (NEUTRAL-relax: standalone bypass (bb-squeeze))`.
- **The system's dominant chop gate IS direction-aware.** `BTC-CHOP-GATE` (signal_compactor 1195–1271) has explicit direction logic: SHORT override when BTC is DECLINING or bear structure (lines 1230–1237), LONG override when bullish structure (1241–1252). During confirmed bear windows it would log `continuum says … allowing despite chop gate` for SHORTs — visible in logs at 00:00 (`[BTC-CHOP-OVERRIDE] FOGO SHORT pump-chain — BTC-exempt…`, `[TREND-ALIGN] BTC bearish → 1.40x`).
- **Empirically today the chop gates blocked mostly LONGs, not SHORTs.** `[CHOP]` blocks 2026-10-06: 6 ETH + 4 BTC, **all LONG momentum** (trendline_bounce_long). `BTC-CHOP-GATE` BLOCKED: 33 LONG (TRX/NEAR/BLUR/BABY/XPL/HYPE/HYPER) vs 5 SHORT (BIGTIME×3, LINK×2).
- SHORTs that died in the bear window were killed by **decider_run filters**, not the chop detector: EXEC-RSI-FLOOR/HARD-FLOOR (GOAT 02:17–02:27), BTC-CRASH gate (GOAT 02:21–02:26), LOSERS_HARD_BLOCK_WR (BTC 02:31–06:41), RR-ENGINE / HALL-SHAME / SHORT-REGIME-GATE / PUMP-CHAIN-VEL (FOGO/DYDX/CHIP/ADA/IO/IOTA at 00:00).

Confidence: HIGH.

---

### Claim 2 — The 6 LONG trades were all mean-reversion signals (bb-squeeze+, trend-ride+) ALLOWED in chop; the SHORT momentum that would have won was blocked

**Verdict: PARTIAL**

Evidence:
- **Signal facts CONFIRMED.** PostgreSQL (close_time > 2026-10-06 00:00): TURBO bb-squeeze+ LONG, IO trend-ride+ LONG, HBAR trend-ride+ LONG, POL bb-squeeze+ LONG, USELESS trend-ride+ LONG, SUPER trend-ride+ LONG, LTC pump-chain- SHORT. Ran `_classify_signal` myself: `bb-squeeze+ → MEAN_REVERSION`, `trend-ride+ → MEAN_REVERSION`.
- **"Allowed by chop detector" is causally wrong.** Both signals are standalone-bypass → the chop detector never evaluated them (see Claim 1). They were allowed by the bypass mechanism, not by the chop detector's mean-reversion policy. (`trend-ride+` would also be MEAN_REVERSION-allowed; `bb-squeeze+` bypasses regardless.)
- **"SHORT momentum that would have won were blocked" — NOT SUPPORTED by price data.** I queried candles.db for every blocked SHORT candidate and measured forward returns:

  | Blocked SHORT | Time | Blocker | Price +60m | Price +180m | Would have won? |
  |---|---|---|---|---|---|
  | LINK mtf_regime_trend_short | 00:39 | BTC-CHOP-GATE | −0.13% | −0.80% | Yes (small) |
  | AVAX warrior_sr_confirm_short | 23:36 | BTC-CHOP-GATE | +0.80% | +0.57% | **No** |
  | GOAT (RSI 25.4) | 02:17 | EXEC-RSI-FLOOR | −0.28% | +0.51% | Marginal |
  | GOAT (RSI 34.8) | 02:26 | EXEC-RSI-FLOOR | −0.64% | +0.31% | Marginal |
  | BIGTIME breakout_pullback_short | 14:23 | BTC-CHOP-GATE | +0.44% | +0.44% | **No** |
  | BTC continuum-trend- | 02:31 | HARD-BLOCK WR | −0.31% | −0.01% | ~Flat |
  | BTC continuum-trend- | 06:38 | HARD-BLOCK WR | +0.15% | +0.74% | **No** |

- **The one SHORT that actually executed (LTC pump-chain- at 03:29, confidence 99) LOST −5.57%** — price rose +1.11% raw (69.246→70.017 DB prices). Direct counter-evidence to "SHORTs would have won."

Confidence: HIGH.

---

### Claim 3 — Opposite side of every trade would have returned +9.85% vs actual −25.91% — a 35.76% swing

**Verdict: DISAGREE**

Evidence:
- **Actual total wrong.** Sum of DB `pnl_pct` for the 7 closed trades = **−29.37%** (−3.11, −3.57, −5.08, −5.98, −3.11, −2.95, −5.57). Plan says −25.91% — matches nothing (6-trade sum = −25.80; 7-trade = −29.37).
- **Mixed bases — the plan compares leveraged PnL against raw price moves.** "Actual" numbers are leveraged `pnl_pct` (leverage 3–5x per DB); "opposite" numbers are unleveraged raw price moves. E.g. TURBO: actual −3.11% (3x on −1.04% raw) vs plan's "opposite +4.45%".
- **Plan's own table contains errors:**
  - TURBO entry listed as 0.001100 — DB `entry_price` = **0.001062** (candles at open = 0.001061). This inflates TURBO's opposite from +1.04% to +4.45%.
  - USELESS opposite listed +1.30% — DB prices give +1.04%.
  - The table's own opposite column sums to **+11.15%**, not the headline +9.85%.
- **Consistent-basis recomputation from DB entry/exit prices:**

  | Token | Dir | Raw move | Actual pnl_pct | Opposite raw | Opposite @ same leverage (gross) |
  |---|---|---|---|---|---|
  | TURBO | LONG | −1.04% | −3.11% | +1.04% | +3.11% |
  | IO | LONG | −1.19% | −3.57% | +1.19% | +3.57% |
  | HBAR | LONG | −1.02% | −5.08% | +1.02% | +5.08% |
  | POL | LONG | −1.20% | −5.98% | +1.20% | +5.98% |
  | USELESS | LONG | −1.04% | −3.11% | +1.04% | +3.11% |
  | SUPER | LONG | −0.98% | −2.95% | +0.98% | +2.95% |
  | LTC | SHORT | +1.11% | −5.57% | −1.11% | −5.57% |
  | **TOTAL** | | | **−29.37%** | **+5.35%** | **+18.23%** |

- Even the +18.23% gross leveraged figure overstates realistic capture: opposite trades would exit via TP/trailing long before the same exit times (Oct 5 winners exited at +0.4% to +4.1%). The +9.85% headline is not reproducible on any consistent basis.

Confidence: HIGH.

---

### Claim 4 — BTC SHORT continuum-trend- conf=99% is killed every cycle by HARD-BLOCK WR=28.6% < 40%

**Verdict: PARTIAL**

Evidence:
- **Block mechanism CONFIRMED in logs:** `🚫 [HARD-BLOCK] BTC SHORT: WR=28.6% < 40.0% — BLOCKED` — 35 occurrences spanning **02:31:02–06:41:31** on 2026-10-06 (~every 48s pipeline cycle during that span — but not "every cycle" of the day; nothing before 02:31 or after 06:41).
- **Code confirmed:** decider_run.py:4217–4236 (`LOSERS_HARD_BLOCK_WR`, hermes_constants:382 = 40.0). The SQL computes **token-level 7d WR with NO direction filter** — 28.6% is BTC's overall 7d WR, not a SHORT-specific WR. The plan's framing implies SHORT-specific stats; it isn't.
- **Not the chop detector.** `continuum-trend-` is in `STANDALONE_BYPASS_SIGNALS` (hermes_constants:2786). Logs show it passing confluence every cycle: `✅ [CONFLUENCE-GATE-PASS] BTC SHORT: {continuum-trend-} (NEUTRAL-relax: standalone bypass (continuum-trend))`. The chop detector never blocked it; the kill is decider_run's LOSERS hard block.
- **"conf=99%" unverified** — no BTC SHORT trades exist in PostgreSQL to check confidence; plausible from signal logs but not confirmed.
- **Blocking was not costly today:** BTC at 02:31 ≈ flat (−0.31%/60m, −0.01%/180m); at 06:38 price rose +0.74%/180m — a SHORT there would have LOST.

Confidence: HIGH on mechanism; MEDIUM on "every cycle"/confidence details.

---

### Claim 5 — Chop detector's CHOP classification is marginal (votes: TREND=2, CHOP=3)

**Verdict: PARTIAL**

Evidence:
- **Ran `get_regime()` myself (2026-10-06 ~14:58):**
  ```
  regime: CHOP
  reason: CHOP: phase=quiet, vol=FLAT, btc_mom=+0.535%
  momentum_allowed: False
  votes: {'TREND': 4, 'CHOP': 3, 'CRISIS': 0}
  details: dir_outcome LONG wr=0.0 total=0 / SHORT wr=0.0 total=0; btc_mom +0.535% not flat; vol=FLAT; phase=quiet
  ```
  Vote counts are **TREND=4, CHOP=3** — not the plan's TREND=2/CHOP=3 (data has moved; plan quote used btc_mom=+0.458%).
- **The code is worse than the plan claims.** chop_detector.py lines 541–550: `elif votes['CHOP'] >= 3: regime='CHOP'` is evaluated **BEFORE** `elif votes['TREND'] >= 3`. With TREND=4 > CHOP=3 the regime is still CHOP — CHOP wins on ambiguity by code order, not by vote majority.
- **CHOP classification is currently WRONG given market data.** BTC continuum right now: state_score ≈ 99, linreg=LEAN_BULL, ema300=ABOVE, wyckoff=MARKUP — strongly bullish, not chop. Only vol=FLAT + phase=quiet voted CHOP; a +2 continuum-oscillator override gave TREND its 4 votes but the structure override (+5) didn't fire because phase=DECLINING isn't in the bullish phase set.
- **Two of four vote sources dead at classification time:** `get_directional_outcome` returned total=0 for both directions (signal_outcomes has data — 15 rows/24h, 160 LONG / 27 SHORT in 7d — but the 30-min window was empty). Classification currently rests on 3 inputs + overrides.

Confidence: HIGH.

---

### Claim 6 — The fix is to make the chop detector direction-aware (in bear chop, allow SHORT momentum)

**Verdict: PARTIAL — direction-awareness is fine, but this fix targets the wrong gate and would not have prevented today's losses**

Evidence:
- chop_detector.py is indeed direction-blind; adding direction logic is harmless. But **none of today's 7 losing trades would have been affected by Fix 1:**
  1. All 6 losing LONG signals (bb-squeeze+, trend-ride+) are standalone-bypass → never evaluated by the chop detector.
  2. LTC pump-chain- (the executed SHORT) is also bypass + MEAN_REVERSION → never evaluated.
  3. BTC SHORT continuum-trend- is bypass → killed by LOSERS_HARD_BLOCK_WR in decider_run, not the chop detector.
  4. The SHORT momentum blocked in the bear window died in decider_run filters (EXEC-RSI floors, BTC-CRASH, RR-ENGINE, HALL-SHAME) — addressed by the plan's Fix 2 and by pre-existing bear-structure overrides, not Fix 1.
- **Direction-aware bear overrides ALREADY EXIST in 4+ places:** signal_compactor 1230–1237 (BTC-CHOP-GATE SHORT override), 2905–2910 (pump-chain SHORT RSI override), 3592+ (SHORT-RSI-FLOOR override); decider_run 1936–1941 (EXEC-RSI-FLOOR override), 3390+ (BTC-CRASH override). Fix 1 partially duplicates this infrastructure.
- **The plan misses the actual root cause of the LONG losses** (see "Other findings" below): a bare-RECOVERY override bug that let SUPER LONG through two correct blocks. brain_auditor already fixed both instances today (2026-10-06) — signal_compactor:1242–1247 and decider_run:3387–3390. The plan appears written against pre-fix code and never mentions these fixes.
- Fix 2 (WR hard block bear override) targets the one verified kill (BTC SHORT) — directionally reasonable, though today's counterfactual shows the blocked BTC SHORT would not have won.
- Fix 4 (widen hard stop in chop) is directionally valid: hard stop is `CUT_LOSER_PNL = -1.00` on **price move** (position_manager:3386–3392, live_pnl on notional) — all 7 exits triggered at ≈ −1% raw price move, which is routine noise when BTC continuum score swings 0↔97 within hours. Note the plan mis-describes it as "-3% to -6% (3-5x leverage)" — that's the stored pnl_pct, not the trigger.

Confidence: HIGH.

---

## Independent investigation answers

1. **Is the chop detector ACTUALLY direction-blind?** At the `chop_detector.py` level: YES (no direction parameter anywhere in `should_trade_signal`/`get_regime`). At the system level: NO — the dominant gate (BTC-CHOP-GATE) is direction-aware via continuum overrides, and today's block logs were majority LONG (33 LONG vs 5 SHORT on BTC-CHOP-GATE; 10 LONG vs 0 SHORT on [CHOP]).

2. **Are the LONG trades ACTUALLY from mean-reversion signals?** YES — verified from PostgreSQL: 2× bb-squeeze+, 4× trend-ride+. Both classify as MEAN_REVERSION and both are standalone-bypass. But "allowed by chop detector" is the wrong mechanism — they bypassed it.

3. **Would SHORT momentum signals ACTUALLY have won?** Mostly NO. 1 small win (LINK, blocked at 00:39), 2 clear losses (AVAX 23:36, BIGTIME 14:23), marginal/flat (GOAT, BTC SHORT ×2). The only executed SHORT (LTC) lost −5.57%.

4. **Is the WR hard block ACTUALLY blocking BTC SHORT?** YES — 35 blocks 02:31–06:41, WR=28.6% < 40. But it's token-level 7d WR (no direction filter), it lives in decider_run (not the chop detector), and the blocked SHORT would not have won.

5. **OTHER filters contributing to the wrong-side problem the plan misses?** YES — see next section.

6. **Is the chop detector's CHOP classification correct?** NO. Currently CHOP with TREND=4 votes while BTC continuum is score≈99 / MARKUP / LEAN_BULL / ABOVE EMA300. Root defect: `CHOP >= 3` checked before `TREND >= 3` (code-order bias), plus 2 of 4 vote sources returning empty, plus structure-override phase set not covering DECLINING+LEAN_BULL+ABOVE.

## Other findings the plan misses (severity-ordered)

1. **🔴 bare-RECOVERY override bug — the actual enabler of SUPER LONG.** Full log chain at 01:48:00:
   ```
   🚫 [CONTINUUM-BLOCK] SUPER LONG — BTC bearish structure, blocking     ← correct block
   ✅ [CONFLUENCE-GATE-PASS] SUPER LONG: {trend-ride+} (standalone bypass)
   ✅ [BTC-CHOP-OVERRIDE] SUPER LONG — continuum says RECOVERY+LEAN_BEAR+BELOW, allowing despite chop gate   ← bug reopened it
   📊 [TREND-ALIGN] SUPER LONG: BTC bearish (score=7, bias=-0.86) → 0.60x   ← system KNEW it was bear
   ⚖️ [SCORE-FLOOR] SUPER LONG: multiplier product 0.0867 floored to 0.3    ← penalties survived via floor
   🚨 [BTC-CRASH] SUPER LONG BLOCKED — WARNING — MOMENTUM                 ← second correct block
   ✅ [BTC-CRASH-OVERRIDE] SUPER LONG — continuum says RECOVERY+LEAN_BEAR+BELOW, allowing despite crash filter  ← bug reopened it again
   EXEC: SUPER LONG @ $0.239600 conf=93%                                  → −2.95%
   ```
   Bare `RECOVERY`/`NEUTRAL` phase allowed LONG override despite full bear structure (LEAN_BEAR+BELOW). brain_auditor fixed both instances today (signal_compactor:1242–1247, decider_run:3387–3390) — the plan is unaware. If this fix regresses, the same loss recurs regardless of chop-detector changes.

2. **🔴 Score floor (0.3) lets structurally dead trades through.** SUPER's multiplier product was 0.0867 (every gate penalized it — TREND-ALIGN 0.6x, RR 0.7x, REGIME-CONF 0.5x, OSC 0.6x) yet the 0.3 floor + standalone-bypass at HOTSET-FINAL/PENDING/SAFETY guards kept it alive at conf=93. Consider making the floor regime-aware or honoring unanimous bear alignment as a block rather than a penalty.

3. **🟠 EXEC-RSI floors killed SHORTs during confirmed bear.** GOAT SHORT blocked 02:17–02:27 ("no bearish override") while continuum was RECOVERY/CALM+LEAN_BEAR/BEAR+BELOW+score<30 — the override condition was met but not active (override was removed by bf96d7cd and "RESTORED" 2026-10-06; the log proves it was inactive at 02:17). Also `fail-closed` "exec RSI unavailable" blocks (GOAT 02:20/02:25, BABY 02:31) — missing data = no trade, which during bear phases suppresses exactly the shorts the system wants.

4. **🟠 BTC-CRASH gate blocks SHORTs during crashes** (counterintuitive): `🚨 [BTC-CRASH] GOAT SHORT BLOCKED — WARNING — BTC_LEVEL/MOMENTUM` at 02:21–02:26. A BTC crash is the canonical SHORT condition; the crash gate + its (now-fixed) override chain suppressed shorts in the bear window.

5. **🟠 Normalization gaps in chop classification/bypass matching:**
   - `bb_squeeze+` (underscores) → **MOMENTUM** (default) while `bb-squeeze+` → MEAN_REVERSION. Underscore-variant source strings would be blocked in chop despite the hyphen variant being bypassed.
   - `mtf_regime_trend_short` → MOMENTUM and does NOT match bypass norm `mtf_regime_trend` (bypass entries 'mtf-regime-trend-' normalize with rstrip to 'mtf_regime_trend'; the `_short` suffixed signal string doesn't match). LINK SHORT was blocked at 00:39 partly for this reason despite mtf-regime-trend being a bypass-listed signal.
   - Signal-family default is MOMENTUM for unknowns — every unregistered source string gets chop-blocked.

6. **🟡 candles.db staleness during the losing window.** Log at 01:05: `USELESS: candles.db stale (3907s old) — falling back to Binance` — local candle data was >1h stale while the system opened losing LONGs. All price-dependent gates (RSI, spike filter, trend score, chop momentum) were running on stale/fallback data in exactly the window under investigation.

7. **🟡 Data inconsistency: IO trade pnl_usdt = 0.00 despite pnl_pct = −3.5731** (amount 11.10, leverage 3, raw −1.19% → expected ≈ −0.40 USDT). pnl_usdt appears unrecorded/zeroed for this row — affects any USDT-summing analysis (and the plan's totals).

8. **🟡 BTC-CHOP-GATE LONG clause asymmetry vs SHORT.** SHORT override includes structural bear "regardless of phase" (`_l2 in LEAN_BEAR/BEAR and _e2 == BELOW`), but LONG structural bull requires `_e2 in ('ABOVE','AT')` — ema AT is treated as bullish-transitional for LONG but the bear side has no AT equivalent. AT hysteresis (AT→ABOVE after 55min) can open LONG-allow windows inside bear structures.

9. **🟢 Plan date/scope imprecision:** "On 2026-10-06, the system executed 7 trades" — 3 of the 7 (TURBO, IO, HBAR) opened on 2026-10-05 (20:21–22:18) and only closed on 10-06. At their entry times the BTC continuum was **LEAN_BULL/ABOVE with score 44–100** — these LONGs were on the correct side at entry and lost only because BTC flipped bear at ~23:40. Only POL/USELESS/SUPER (opened 00:20–01:48) were opened into transitional/bear conditions. The plan's uniform "wrong side in bear chop" framing is inaccurate for half the book.

10. **🟢 The plan's continuum description is roughly accurate:** verified 01:50–04:00 = RECOVERY/CALM+LEAN_BEAR/BEAR+BELOW, score 0–28 (bear ✓); 02:00–04:00 bear ✓; 04:10–05:40 recovery ✓; 05:50–07:30 bear again ✓; 07:40+ strong bull ✓. Score does oscillate 0↔97+ within hours — "violent chop" descriptor is fair.

---

## Summary table

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | Chop detector direction-blind; blocks winning SHORTs, allows losing LONGs | PARTIAL | HIGH |
| 2 | 6 LONGs = mean-reversion allowed in chop; blocked SHORTs would have won | PARTIAL | HIGH |
| 3 | Opposite +9.85% vs actual −25.91%, swing 35.76% | **DISAGREE** | HIGH |
| 4 | BTC SHORT killed every cycle by HARD-BLOCK WR=28.6% < 40% | PARTIAL | HIGH/MED |
| 5 | CHOP classification marginal (TREND=2, CHOP=3) | PARTIAL | HIGH |
| 6 | Fix = direction-aware chop detector | PARTIAL (wrong gate; would not have prevented today's losses) | HIGH |

**Overall assessment of the plan:** The problem it describes (system on the wrong side, losing 7/7) is real — all 7 trades did hit `hard_max_loss`, total −29.37% pnl_pct. But the diagnosis is misattributed. The chop detector is a minor contributor: today it blocked 100% LONG momentum in its own logs, the losing signals bypassed it, and the one verified chop-adjacent kill (WR hard block) did not cost a winner. The plan's P0 fix would not have changed any of today's outcomes. Priorities the data actually supports: (a) keep the brain_auditor bare-RECOVERY fixes from regressing; (b) re-examine the score floor + standalone-bypass final guards that let unanimously-penalized trades execute at conf=93; (c) fix the normalization gaps; (d) widen the −1% raw hard stop in chop regimes (plan Fix 4 — the one fix with direct evidence behind it); (e) audit candles.db staleness. Before implementing Fix 1, the CEO desk should re-derive the opposite-side numbers on a consistent basis — the +9.85%/35.76% headline that justified the plan does not reproduce from the databases.
