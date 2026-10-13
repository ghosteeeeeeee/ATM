# Volatility Regime Multi-Year Audit (2026-10-13)

## Question (T)
Do the fixed ATR% regime thresholds (FLAT<0.48, NORMAL<1.0, HIGH<1.5, EXTREME>=1.5,
MAXXED>=4.0) hold up against crypto's multi-year history, or will they need constant
recalibration as the market grows more volatile than we've seen?

## Data
Local candles.db is a ROLLING WINDOW — BTC/ETH only 2026-03-17->now (7mo), 2 tokens >1yr.
Insufficient for multi-year validation (AGENTS.md API-allowed case). Pulled Binance 1h
klines into scratch DB data/klines_multiyear.db (NOT live candles.db):
  BTC 2017-08-17->2026-10-13 (80,140 rows, 9y)  ETH same 9y
  SOL 2020-08-11-> (6y)                          DOGE 2019-07-05-> (7y)
ATR(14)% computed on 1h — EXACT same basis as classify_volatility().

## FINDING 1 — Regime mix is asset-dependent, NOT universal
Same thresholds, wildly different meaning:
  BTC 9y: FLAT 19.8 NORMAL 48.1 HIGH 18.9 EXTREME 12.4 MAXXED 0.8
  ETH 9y: FLAT  7.8 NORMAL 40.5 HIGH 28.5 EXTREME 21.8 MAXXED 1.4
  DOGE   : FLAT  3.5 NORMAL 34.1 HIGH 30.3 EXTREME 28.5 MAXXED 3.6
  SOL    : FLAT  1.8 NORMAL 23.6 HIGH 30.4 EXTREME 40.3 MAXXED 3.8
BTC median ATR 0.78% vs SOL 1.39%. Absolute thresholds encode ASSET BASELINE,
not "unusual for this asset." SOL is structurally parked in HIGH/EXTREME even
when calm relative to its own history. Live universe is alt-heavy -> 26% EXTREME.

## FINDING 2 — Fixed thresholds DRIFT in meaning across market cycles (T's fear, CONFIRMED)
EXTREME+MAXXED time-share by year (same 1.5% threshold, same asset):
  BTC: 2017 55.5% -> 2023 1.5% -> 2025 2.7% -> 2026 1.8%   (~30x swing)
  ETH: 2017 61.2% -> 2023 1.2% -> 2026 5.6%
  SOL: 2020 84.5% -> 2021 86.9% -> 2026 8.6%               (~10x swing)
  DOGE:2021 66.7% -> 2023 15.3% -> 2026 10.7%
In a mania year EXTREME swallows half the market; in a quiet year it's a rounding
error. If the market exceeds historical vol, EXTREME/MAXXED become the DEFAULT
state and lose all discriminating power — every signal looks "stormy." This is the
recalibration treadmill T wants to avoid.

## FINDING 3 — It is SILENT (no drift detection)
Nothing alerts when the label stops discriminating. The 26%-EXTREME live reading is
a symptom of the alt-heavy universe (Finding 1), NOT of market stress.

## FINDING 4 — Right now every major is BELOW its own median (market is calm)
  BTC 0.57% NORMAL 29th pct z=-0.54 | ETH 0.82% NORMAL 33rd z=-0.48
  SOL 1.11% HIGH 32nd z=-0.51 | DOGE 0.99% NORMAL 37th z=-0.37
All below median, yet SOL still reads HIGH. Proves the thresholds measure asset
identity, not market conditions.

## RECOMMENDED DIRECTION (needs T + CEO sign-off; NOT implemented)
Move to RELATIVE (per-asset rolling) thresholds + add a DRIFT ALARM:
  regime = percentile of ATR% vs that asset's OWN trailing window (e.g. 180d),
  -> stable meaning across assets and cycles; a "storm" is always "stormy FOR THIS ASSET."
  + Drift alarm: alert when EXTREME share of universe leaves its historical band
  (catches both miscalibration AND regime shifts instead of silently drifting).
Trade-offs: percentile regimes are self-referential (a calm asset's "EXTREME" can be
a quiet absolute level -> wide absolute stops in reality); needs per-asset history
sparse tokens fall back to absolute. Keep MAXXED as ABSOLUTE tail backstop
(verified bad both dirs in 2026-10-12 backtest) layered on top.
This is a CHANGE TO LIVE TRADING -> requires independent backtest (own-conclusions)
+ CEO approval before any code. No code touched in this audit.
