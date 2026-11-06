# Linreg Fade — Research & Diagnosis (2026-11-05)

**TL;DR:** The old linear-regression signals made no money (566 trades, 48.2% WR,
+$1.45 total) because regression was used as a *descriptive filter* ("is it a
trend?") instead of a *forecast* ("what happens next?"), with parameter churn
(18 variant sources), no IS/OOS discipline, and stop-based exits that kill
mean-reversion edges. A RenTech-style rebuild (one predictor → one target,
cleaned data, nonlinear decile transform, p-values, IS/OOS splits) found a real
edge: **fading the token's own 1m slope extreme at an 8h horizon**. SHORT side
validated: 1m Oct–Nov 2026 WR 53.9%, +0.154%/trade net, n=6142, positive in
every period slice (V8 exit structure). LONG side works only in up-regimes →
shipped with flag OFF.

Artifacts:
- `scripts/analysis/linreg_forecast_research.py` — univariate IC research (CLI: `--tf 1m|5m|15m [--slope W]`)
- `scripts/analysis/linreg_fade_backtest.py` — event-level backtest (CLI: `--tf ...`)
- Logs: `/tmp/linreg_research_1m_w{20,60}.log`, `/tmp/fade_1m_v8.log`, `/tmp/fade_15m_v8.log`
- New signal: `scripts/signals/linreg_fade.py`

---

## Part 1 — What we were doing wrong (old linreg signals)

Family = r2_trend_long/short/v2, r2_rev, tl_break, trendline_bounce,
slow_grind, grind_trend, grind_breakout, continuum_trend.

**Aggregate (PostgreSQL brain, all closed trades):**
`n=566, WR 48.2%, avg -0.0099%/trade, total +$1.45` — statistically zero edge
(after 0.09% round-trip fees, avg -0.01% is dead).

| # | Problem | Evidence |
|---|---------|----------|
| 1 | **Regression used as description, not prediction.** Every docstring says "R² trend confirmation" — R² answers "was it a trend?", never "what happens next?". No forward-return target anywhere. | `r2_trend_long.py` docstring; grep of all signal files |
| 2 | **Parameter churn = multiple testing.** 18 distinct variant sources (`r2-trend-long0..8`, `r2v2-long3..18`), most n=1–5 trades each. Each retune = a new suffix, never a validated hypothesis. | trades query: 18 distinct r2 variant strings |
| 3 | **Tiny samples, no significance.** Decisions on n=5–20 (grind-trend killed at n=14; r2v2-long3 kept at n=28). No p-values, no CIs, no IS/OOS split ever. | signal_outcomes table |
| 4 | **Hardcoded constants in signal files** (`R2_WINDOW=16`, `BASE_CONFIDENCE=65` inside `r2_trend_long.py`) — violates the no-magic-numbers rule; couldn't tune in place, so files were copied instead of tuned. | file headers |
| 5 | **Extra conditions added as decoration.** RSI bands, BB position, speed, accel, pre-move stacked on top of the slope — research shows R² IC≈0 and momentum flips sign IS→OOS; those conditions are noise-fitting. | IC table below |
| 6 | **Stop-based exits destroy mean-reversion.** 1:1.5 ATR stops need WR ≥46%; achieved 38–44% (V2/V6/V7 below). | backtest variants |
| 7 | **No regime awareness of the fade's beta.** Aug–Sep (up) LONG won / SHORT lost; Oct–Nov (down) flipped. Two regime gates tested (BTC 24h drift, system's own regime_4h) — **both failed OOS**; abandoned, not re-tuned. | V3/V4/V5 |

RenTech checklist mapping: target ✓(missing before) · nonlinear transform ✓(deciles) ·
clean data ✓(closed candles, winsorize, dead-token guards) · notice rubbish ✓(R²,
mom, atr_comp, dev_atr all called RUBBISH explicitly when IS/OOS sign flips).

## Part 2 — The research (what survived)

**Design:** target = forward return over H ∈ {1h,2h,4h,8h,16h}; predictor =
ONE of {linreg slope %, R², deviation-from-regression/ATR, volume z, momentum,
ATR compression, range position, residual z, slope/ATR}; cleaning = closed
candles, positive prices, 1/99 winsorize (inf-poisoning bug found & fixed);
IS = first 70% of time, OOS = last 30%, plus last-60d holdout; Spearman IC +
p-values; monthly sign stability; decile shape analysis.

**Verdicts (pooled IC, IS/OOS must share sign):**

| Feature | 15m (Aug–Nov) | 1m (Oct–Nov) | Verdict |
|---|---|---|---|
| slope_pct H8h | IS -0.040 / OOS -0.046, 4/4 months same sign | IS -0.025 / OOS -0.052 (w=60) | **CANDIDATE — the signal** |
| resid_z / dev_atr | flips sign at short H | stable negative small | weak/rubbish |
| r2 | IC ≈ 0, H16 flips | IC ≈ 0 | **RUBBISH (was our main old variable!)** |
| mom (4h ret) | IS -0.027 / OOS +0.005 flip | flip at H1/2/4h | **RUBBISH** |
| vol_z | stable negative small | flips at H8h+ | weak |
| rng_pos | stable negative | flips at short H | weak |
| atr_comp | flips | flips | **RUBBISH** |

**Shape (the nonlinear-transform step):** edge lives ONLY in the deciles.
15m OOS H8h: D1 (steepest fall) +0.07% vs D10 (steepest rise) −0.35%;
1m OOS H8h: D1 −0.17% vs D10 −0.48% (market fell −0.78% over the window —
fade-LONG selection alpha vs blind = +0.61%, fade-SHORT rides beta).

**Event backtest (entry = next bar open, trailing P10/P90 of the token's OWN
slope history, no lookahead, fees 0.09% RT, one position per token):**

| Variant (exit structure) | 1m SHORT | 15m LONG | 15m SHORT |
|---|---|---|---|
| V1 fixed 8h hold | **+0.203%/trade, WR 54.5%, n=6142** | +0.196%, WR 53.1%, n=7599 | -0.061% (up-regime drag) |
| V2 ATR SL1.5/TP2.25 | -0.090% (loses) | -0.025% (loses) | -0.058% |
| V6 production 2%/2%+trailing | -0.020% (flat) | -0.208% (loses) | -0.151% (loses) |
| V7 wide SL6 + trailing | — | -0.161% (loses) | -0.156% (loses) |
| **V8 wide SL6, NO trailing** | **+0.154%, WR 53.9%, IS+OOS+both months green** | +0.159% | -0.067% |
| V3 BTC-24h regime gate | — | OOS WORSE (-0.11 vs -0.06) | OOS WORSE (+0.23 vs +0.28) |
| V5 regime_4h gate | OOS WORSE (-0.17 vs +0.45) | OOS WORSE | OOS WORSE |

**Three hard-won conclusions:**
1. **The trailing stop is the edge-killer.** V6/V7 (any trailing) → WR 37–44%,
   all losers. V8 (identical, trailing off) → V1 numbers back. The 0.40%/1.20%
   trail arms after +0.4% and gets hit by noise before the 8h reversion plays.
2. **Regime gates don't work** with either proxy tested. Absolute PnL flips
   with market beta; selection alpha for fade-LONG is stable +0.26%/trade in
   ALL four period slices (15m IS/OOS) — but a directional book can't eat
   alpha without the regime. Both gate attempts documented and abandoned.
3. **The horizon is part of the variable.** H4h = rubbish (edge flips), H8h =
   validated (IC stable, deciles clear fees). 8h also equals the existing
   `UNIVERSAL_MAX_HOLD_MINUTES = 480` — production already hard-closes at 8h.

## Part 3 — What shipped

- `scripts/signals/linreg_fade.py` — 1m OLS slope (20 bars) vs trailing
  P10/P90 of the previous 4320 slopes (3 days), one variable, dead-token and
  staleness guards, 9h cooldown (mirrors the 8h hold).
- Flags: `LINREG_FADE_ENABLED=True`, `MINUS=True` (validated),
  `PLUS=False` (loses in down-regime — flip on when regime turns up).
- Layer 2 (`signal_schema.add_signal` + `is_component_disabled`),
  registry + slow set (`signals/__init__.py`), compactor weights.
- **Exit structure = part of the signal** (this is the lesson the old signals
  never learned): `decider_run.py` `linreg-fade` branch writes wide 6%/6%
  levels with a never-arming trailing activation; `position_manager.py`
  skips ATR level updates for `linreg-fade` sources (same skip mechanism as
  manual/CEO trades). Soft-trail (2h, losing-only, 0.6%) and weather-vane
  shield remain active as system safety nets — V9 measures their impact.

## Post-audit hardening (bug_hunter 2026-11-05: 1 CRITICAL + 5 HIGH found & fixed)

The first ship attempt was wiring-only — the audit proved the signal could
never trade and that 8 of ~10 production exit actors would still run on it:

| Finding | Fix |
|---|---|
| CRITICAL: 0/57 signals approved — not in `STANDALONE_BYPASS_SIGNALS` | Added `'linreg-fade'` (jup-liq pattern). All other gates (blacklist, regime, vol, speed, winrate) still apply; only the 2-type confluence requirement is waived — this is the intended 2-week observation mode. |
| HIGH: profit_monster trail (arms +0.40%, #1 exit in prod: 146 closes/14d) + T1/T2 tiers | `'linreg-fade'` added to `PROFIT_MONSTER_BYPASS_SIGNALS` |
| HIGH: cut_loser cuts −1.0…−3.0% before the 6% SL | Same list (cut_loser reads it) |
| HIGH: stale_exit (−1.0% after 8min) | Gated `not is_linreg_fade_pos` |
| HIGH: hard_max_loss floor — see below | **Kept on** — leverage pinned instead |
| MEDIUM: SL-zone tighten rewrote the wide SL mid-trade | Gated |
| MEDIUM: wave_turn / MFE-EXIT / 30min weather-vane shield / UGB-PT | Gated or covered by the bypass list |
| LOW: trades.signal could switch to signal_type form | Dual-form match (`linreg-fade` OR `linreg_fade`) at every site |

**hard_max_loss (Issue 4) — the guardrail stayed, leverage adapted:** the floor
is −4% *account* / leverage = −0.8% price at lev5, −4% price at lev1. Backtest:

| Variant | SHORT WR | SHORT avg | HML fires |
|---|---|---|---|
| V8 (no floor, reference) | 53.6% | +0.143% | — |
| **V10 floor −0.8% (lev5)** | **32.3%** | **+0.017%** | **63% of exits — EDGE DEAD** |
| **V11 floor −4% (lev1)** | **52.8%** | **+0.103%** | 13% — edge survives |

So `LINREG_FADE_LEVERAGE = 1` is pinned in decider_run.py: the account
guardrail is never exempted; the trade's leverage is set so the guardrail sits
at the level the structure was validated with (V11).

## Post-ship evaluation (2026-11-06 01:30 — real signals + CEO proposal tests)

**1. The first 78 real signals (all SHORT, as shipped):**
- `analysis/linreg_real_signal_replay.py` — replay through V8 structure:
  **WR 69.2%, avg +0.771%/trade, sum +60.17%, 0 SL hits (wide stop never
  touched), 3 TP, 75 time-exits** — BUT 75/78 signals are younger than 8h
  (median hold 319min, windows truncated) and Nov 5 was a dump day. Nov 6's
  8 signals already average −0.31%. Smoke test, not proof.
- shadow_trades (90 rows, per-engine counterfactuals): recorded old-engine
  outcome n=58 WR 74.1% avg +0.797%; **profit_monster trail + cut_loser
  BYPASSED 58/58** (fixes live in shadow); HML fired 8× — all 8 losers
  (avg −0.99%, confirms it only catches the fade's losers); ATR-engine
  counterfactual +1.92% avg — but that's 1 dump day vs the 3-month backtest
  where ATR exits LOSE (V2 −0.09%/trade); trust the longer sample.

**2. CEO proposal — "both sides, follow the trend via the system's own
regime gates" (`analysis/linreg_both_sides_regime_test.py`, gates
reconstructed from continuum.db BTC history, Aug 12 → now):**

| Cohort (event-level, V8 exits) | 1m (trading TF) | 15m full-sample | 15m OOS |
|---|---|---|---|
| A. current ship: SHORT only, ungated | **+0.248%/WR 54.9%** | −0.052% | **+0.305%** |
| B. both sides, ungated | −0.073%/WR 49.1% | +0.037% | +0.044% |
| C. both sides + system trend gates | −0.032%/WR 49.5% | +0.035% | +0.017% |

**Proposal rejected — it loses OOS on both timeframes.** LONG leg bleeds on
1m (Oct −0.29%, Nov −0.73%) and the system's gates don't rescue it (C still
negative on 1m; worse than A on 15m OOS). Why the gates don't line up with
the fade: measured BTC state by month — Aug score>60 only **2.0%** of the
time (SHORT gate inactive exactly when shorts lost −0.73%/trade), while the
Oct LONG block (bearish structure 43%) kept the *losing* LONGs (allowed
Oct LONGs avg −0.57%). Trend-followING itself was already tested in the
research: slope IC is negative (fade beats follow), momentum flips sign
IS/OOS → rubbish. LONG flag stays OFF until an up-regime validates it.

## Honest caveats

- 1m data spans only Oct 6 – Nov 5 2026 (a down regime); 15m spans Aug 7 –
  Nov 5 (both regimes). Crypto's constant pump/dump cycles recur, but a full
  bull-leg validation of the SHORT side does not exist yet.
- fade-SHORT in the recent window partly rides market beta (blind-short made
  +0.30%/8h OOS). fade-LONG has true selection alpha but negative absolute
  PnL in down regimes → flag OFF.
- Skill bar: SHORT side passes on 1m full-sample (WR 54.7% V1 / 53.9% V8,
  avg > 0.05%, n ≫ 20) and on 15m OOS; 15m full-sample SHORT fails (up-regime
  drag) — that's the regime story, not noise (p < 1e-10 throughout).
- Confluence gate applies (signal NOT added to STANDALONE_BYPASS) → trades
  only fire with a second source, which is the intended 2-week observation
  period before this signal carries weight on its own.
