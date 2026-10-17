# Current State — brain_auditor Captain Run Oct 17 14:45 UTC

**Last Updated: 2026-10-17 14:45 UTC**
**Updated by: brain_auditor — EXIT-LADDER P0 CLOSED, 0 config changes**

## PIPELINE STATUS (14:45 UTC)

- **24h frozen (pre-pause): 25T −$1.57 (26.1% WR)** | 1 open (BTC SHORT #16258 manual, ~flat 11.3h) | **7d 212T 34.4% −$2.86** | Health CRITICAL
- **Pipeline PAUSED** (vacation-guardrail since 04:08) + kill JSON live_trading=false — flat is the trade. **Defeated-pause check PASS** (0 opens since 04:08). Auto-resume ~Oct 23 (rolling-7d aging math, 12:20 run).
- Regime: BTC SHORT_BIAS (15m/4h), vol LOW, market CALM, continuum AT. #16258: entry 81522, SL 81766 — HOLD (trend-aligned, tight SL caps risk).
- Exit signature 7d: **HML 58T −$5.12 0%WR | atr_sl 52T −$4.23 (ATR family 75T −$0.14 near-flat) | profit-trail 44T +$2.89 93.2% | atr_trail 23T +$4.09 82.6%**
- **ai-trader rsi_at_pick concern CLOSED** — field written (SEI pick 12:46 rsi=51.9); first-resume-pick verify pending.
- **SHORT floor-35 band HEALTHY** — since Oct 13: 27T −$0.06 37%WR; trigger (−$1.00) nowhere near; resets Oct 20.

## ⚠️ THIS RUN — EXIT-LADDER P0 CLOSED (8th request fulfilled)

brain_auditor ran the signal-scoped TAT candle OOS grid itself (self_learner undelivered
8×). Script `analysis/exit_ladder_tat_grid_2026-10-17.py`, verdict
`brain/verdicts/2026-10-17_exit-ladder-tat-grid.md`. 30d 782T, ARM 0.40 + creative
ARM=0.0 (underwater-only, never tested in 11:05 MFE grid):

| Family | Result |
|--------|--------|
| bb-squeeze LONG | **PASS all T∈[40,60] both ARMs** — live T=60 +$1.02 revalidated; T=55 delta $0.05 = noise, no churn |
| pump-chain− SHORT | **FAIL all 14 (T×ARM) cells** — exit-side dead end (underwater winners recover); entry-gap diffuse; only lever = CEO kill decision |
| pump-chain+ LONG | wash at live T=45; every T≥50 strictly worse (slow-grinder FKs) — keep |
| Progressive ladder | **FORMAL DEAD** — same root as MFE-CUT: fixed-time cuts cannot separate slow grinders from chop |

**TAT-eligibility meta-rule (pre-registered, reusable):** median winner hold < T <
median loser hold with ≥2× separation, THEN candle OOS fk≤20% ∧ net>0. Screen before
commissioning any future TAT shadow (bb-squeeze qualifies; pump-chain− fails premise).

## PRIOR RUN (11:05) — MFE-CUT FLIP BLOCKED (still in force)

Universal time+unrealized-pnl cut FAILed candle OOS (145 fk winners, net −$9.90/30d). Tier-2 pre-registration REVOKED. Signal-scoped only.

## LAST-RUN CHANGES — STATUS

| Change | Status | Evidence |
|--------|--------|----------|
| doji RE-KILL | HOLDING (frozen) | 0 trades since 20:30 Oct 16 |
| pump-chain+ dead-gap | HOLDING (frozen) | 0 trades since 01:39 |
| ai-trader drift guard | HOLDING | rsi_at_pick WRITTEN (SEI 12:46 rsi=51.9) — concern CLOSED |
| MFE-CUT shadow T=45/0.20 | COLLECTING / FLIP BLOCKED | candle OOS FAIL |
| bb-bounce trail-arm shadow T=55 | COLLECTING / **FLIP PATH FAIL** | candle OOS fk 41.9% |
| ai-trader trail-arm shadow T=55 | COLLECTING | 3 fires/30d hypothetical |
| pump-chain TAT live45 | KEPT — net≈0 wash | comment retracted, no code change |
| bb-squeeze TAT live60 | **CONFIRMED + REVALIDATED** | PASS all T∈[40,60] both ARMs, exit-ladder grid |
| sweet-spot MIN 55 / SHORT midband / EXTREME 0.85 / SHORT floor-35 | HOLDING / UNVALIDATED | paused |

## ⚠️ OPEN (CEO-owned)

1. ~~Exit-ladder candle backtest~~ **CLOSED this run** — grid complete, verdict `brain/verdicts/2026-10-17_exit-ladder-tat-grid.md`. Do NOT re-request. pump-chain− kill decision remains CEO-owned.
2. 🔴 **7d WR/PnL** — 34.7% / −$2.84. Vacation guardrail holds — correct.
3. 🟡 **ai-trader rsi_at_pick compliance** — verify first resume pick writes field.
4. 🟡 **#16258 SL/TP desync** DB vs PM — bug_hunter candidate.
5. 🟡 **dead-gap soak clock** — extend past Oct 17 on resume.
6. 🟡 **5+ unvalidated changes land together on resume (~Oct 21)** — CEO eyeball recommended.

## WATCHLIST (soak — do NOT stack new entry filters)

- MFE-CUT shadow — collecting, FLIP BLOCKED; would-fire data only
- bb-bounce trail-arm shadow — collecting, FLIP PATH FAIL at T=55 (keep for data, do not flip)
- ai-trader trail-arm shadow — collecting, low engagement
- ai-trader drift guard — verify rsi_at_pick on first resume pick
- pump-chain- HIGH_BLOCK + HARD_FLOOR=45 — holding
- CHASE_RATIO_SHADOW — soak to Oct 27
- volume-buildup− SHORT: 87.5%WR +$0.38, protect
- pump-chain+ : 14d #1 money maker, leave alone
- bb-squeeze TAT: CONFIRMED, candidate for any future exit-stack design

## KEY DATES

| Date | Item |
|------|------|
| Oct 20 | SHORT floor-35 trigger resets |
| ~Oct 21 | Vacation-guardrail auto-resume window |
| Oct 27 | CHASE_RATIO_SHADOW review |
| Oct 30 | bb-bounce shadow 14d review (note: flip path already fails OOS — review is data-only) |
| Nov 6 | Gate re-audit window opens |

## NEXT ACTIONS (on resume)

- Verify rsi_at_pick written by first ai-trader pick
- Grep `[SHADOW]` MFE-CUT + TRAIL-ARM lines — confirm collectors firing
- Extend dead-gap soak clock
- Monitor SHORT floor-35 trigger
- Do NOT flip MFE-CUT live; do NOT flip bb-bounce T=55 at T=55 — both candle-OOS failed
