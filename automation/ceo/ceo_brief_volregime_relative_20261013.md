# CONSULT — Are our fixed volatility-regime thresholds sound, or do we need relative regimes?

## What I need from you
OPINION ONLY — no edits, no subagents. T explicitly asked for this and is waiting.
Read the evidence, then answer the 4 questions at the bottom.

## The question T raised
"crypto already has a multi-year history — check/backtest to make sure our volatility
regimes make sense. We don't want to keep recalibrating as the market becomes more
volatile than we've seen so far."

## What I measured (evidence: brain/vol-regime-multiyear-audit-2026-10-13.md)
Local candles.db was too thin (BTC/ETH only 7 months), so I pulled Binance 1h klines
into a scratch DB (data/klines_multiyear.db): BTC/ETH 2017-08->2026-10 (9y),
DOGE 2019-07-> (7y), SOL 2020-08-> (6y). ATR(14)% computed on 1h — EXACT same basis
as classify_volatility(). Current thresholds are ABSOLUTE ATR%:
FLAT<0.48, NORMAL<1.0, HIGH<1.5, EXTREME>=1.5, MAXXED>=4.0.

FOUR FINDINGS (all from the data, not assumed):

1. Regime mix is ASSET-DEPENDENT, not universal. Same 1.5% threshold, different world:
   BTC 9y EXTREME 12.4% of hours | ETH 21.8% | DOGE 28.5% | SOL 40.3%.
   (FLAT/NORMAL/HIGH/EXTREME/MAXXED: BTC 19.8/48.1/18.9/12.4/0.8;
    SOL 1.8/23.6/30.4/40.3/3.8.) BTC median ATR 0.78% vs SOL 1.39%.
   Absolute thresholds encode ASSET BASELINE, not "unusual for this asset." Our live
   universe is alt-heavy -> 26% currently read EXTREME (asset mix, not market stress).

2. Cycle DRIFT — T's exact fear, CONFIRMED. EXTREME+MAXXED time-share by year on the
   SAME asset and SAME threshold: BTC 2017 55.5% -> 2023 1.5% -> 2026 1.8% (~30x).
   SOL 2020 84.5% / 2021 86.9% -> 2026 8.6%. DOGE 2021 66.7% -> 2023 15.3%.
   In a mania EXTREME swallows half the market; in a quiet year it is noise. Push the
   market beyond historical vol and EXTREME/MAXXED become the DEFAULT state and stop
   discriminating — the recalibration treadmill T wants to avoid.

3. SILENT — no alarm when the label stops meaning anything.

4. Right now every major is BELOW its own median (BTC 29th pct z=-0.54, ETH 33rd,
   SOL 32nd, DOGE 37th) yet SOL still reads HIGH — proof the thresholds track asset
   identity, not market conditions.

## My proposed shape (NOT implemented — needs your opinion + T sign-off + own-conclusions)
A. RELATIVE regime: percentile of ATR% vs the asset's OWN trailing window (~180d),
   so "EXTREME" always means "stormy FOR THIS ASSET" — stable across assets + cycles.
B. Keep MAXXED ABSOLUTE (>=4.0%) layered on top — the one thing that stays absolute,
   because the 2026-10-12 backtest showed >=4.0% is bad in BOTH directions (LONG 44.4%
   WR, SHORT 24.0% WR, independently repro'd). Absolute tail = real price violence.
C. DRIFT ALARM: alert when EXTREME's share of the live universe leaves its historical
   band — catches miscalibration and regime shifts instead of silently drifting.
D. Sparse-history tokens fall back to absolute (or pool to a peer group).

HONEST TRADE-OFFS I already see:
- Percentile regimes are SELF-REFERENTIAL: a calm asset's "EXTREME" can be a low
  absolute ATR -> wider real stops than expected, and the regime no longer implies
  absolute danger. Partially mitigated by keeping MAXXED absolute (B).
- BIGGEST RISK (my read): every existing regime-keyed override — SIGNAL_TYPE_OVERRIDES,
  VOL_PHASE_MULTS, the ~36 'EXTREME' string comparisons, the MAXXED tier — was
  calibrated on the OLD labels. Changing what "EXTREME" MEANS silently re-buckets all of
  them. This is the exact hazard you flagged when MAXXED was designed (2026-10-12: a
  naive relabel would unblock EXTREME restrictions). So this MUST be shadow-logged and
  diffed, never flipped.

## ROLLOUT I'd propose (staggered, per automatic-implementation skill)
1. Shadow: compute BOTH absolute and relative live, log would-be diffs >=7d, ZERO enforcement.
2. Diff the regime-keyed override behavior under both labeling schemes; enumerate every
   (signal,regime) pair whose effective block status would change.
3. own-conclusions verification on shadow results (out-of-sample: derive percentile bands
   on 2017-2022, validate 2023-2026 — per AGENTS.md THE-PATTERN, do NOT claim "relative
   is better" from one window).
4. T + CEO sign-off on the diff, then flip behind VOL_REGIME_MODE='absolute'|'relative'
   for one-line rollback.

## THE 4 QUESTIONS FOR YOU
1. Is relative-regime + absolute-MAXXED-tail the right shape, or would you rather keep
   absolute thresholds and just periodically re-tune the numbers (accepting the treadmill)?
2. What is the biggest risk you see in re-bucketing the existing regime-keyed overrides
   when "EXTREME" changes meaning? What would you require in the shadow diff before
   trusting it?
3. Should MAXXED stay ABSOLUTE (my recommendation) or also go relative?
4. Given the drift evidence, is doing NOTHING (keep absolute, no alarm) acceptable to
   you, or is the drift alarm the minimum viable change even if we defer the relative
   regime?

Answer with your opinion and reasoning. No edits.
