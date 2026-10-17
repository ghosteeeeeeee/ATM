# Current State — brain_auditor Captain Run Oct 17 13:40 UTC

**Last Updated: 2026-10-17 13:40 UTC**
**Updated by: brain_auditor — soak verification + ai-trader doctrine-drift find, 0 behavior changes**

## PIPELINE STATUS (13:40 UTC)

- **24h frozen (pre-pause cohort): 25T −$1.65 (28% WR)** | 1 open (BTC SHORT #16258 manual) | **7d 212T 34.4% −$2.86** | Health CRITICAL
- **Pipeline STOPPED** (vacation-guardrail since 04:08) + kill JSON live_trading=false — flat is the trade, correctly held. Auto-resume ~Oct 21. **Defeated-pause check PASS** (0 closes since 04:08).
- Regime: BTC SHORT_BIAS (15m/4h), vol LOW, AT EMA300, LEAN_BEAR. Entry 81522, SL 81766. HOLD; invalidation = 15m close >81592 w/vol.
- Exit signature: **7d HML 58T −$5.12 0%WR vs profit-trail 44T +$2.89 93.2%WR | ATR_SL now 75T −$0.14 near-flat (trail-arm timeouts converting bleeds)**
- **All 9 last-run changes HOLDING.** ai-trader drift guard now FUNCTIONAL (ai_trader_state writes rsi_at_pick — SEI pick 12:46 rsi=51.9; prior fail-open concern closed).

## ⚠️ THIS RUN'S FINDING — AI-TRADER DOCTRINE DRIFT (medium)

Pick reasoning calls SHORT 45-55 a "sweet spot" (SEI rsi 51.9) while decider_run.py:2098 blocks
exactly that band for all non-pump-chain (14d 9T 0W −$0.89). Manual HL path bypasses decider
gates — T's channel can enter what the signal channel refuses. **Creative (pre-registered, not
shipped): SHORT-midband ADVISORY in ai_trader_precheck (warn-only).**

## ⚠️ PRIOR RUN FINDING (11:46, still in force) — TRAIL-ARM-TIMEOUT CANDLE OOS (all 4 cohorts)

Same test class that killed universal MFE-CUT, now applied to the *signal-scoped* mechanism
(as-coded: still open at age≥T AND live_pnl <0.40% → close). `analysis/trail_arm_candle_oos_2026-10-17.py`.
**Units landmine: `pnl_usdt` = amount × unleveraged move; `pnl_pct` is LEVERAGED %. cf$ = amount × lp/100.**

| Cohort | T | fires (FK winners) | NET | fk % of winners | Verdict |
|--------|---|--------------------|-----|-----------------|---------|
| bb-squeeze LIVE | 60m | 20 (5) | **+$1.02** | 11.1% | **CONFIRMED — exit-ladder template** |
| pump-chain LIVE | 45m | 60 (21) | **−$0.13** | **36.8%** | wash — KEEP, "immune" claim RETRACTED |
| bb-bounce SHADOW | 55m | 33 (18) | +$0.31 | **41.9%** | **FLIP FAILS (fk bar 20%)** |
| ai-trader SHADOW | 55m | 3 (0) | +$0.26 | 0% | insufficient n — keep shadow |

- pump-chain prior "+$1.75 structurally immune" was selection-on-outcome: FOGO/AVAX/ADA/JUP were <0.40% at T=45m yet ended +4-6% unleveraged (slow grinders). Saves $3.18 ≈ costs $3.31 — net zero. No mechanism change (churn risk > $0.13/30d).
- bb-bounce: bounce winners run late (flat at 55m then trail). **Do NOT flip T=55 without redesign clearing fk≤20% on fresh candle OOS.**
- Peak-armed-guard idea tested-and-rejected: FKs never armed by T, guard wouldn't save them.
- Verdict file: `brain/verdicts/2026-10-17_trail-arm-candle-oos.md`. Constants comments updated (zero behavior).

## PRIOR RUN (11:05) — MFE-CUT FLIP BLOCKED (still in force)

Universal time+unrealized-pnl cut FAILed candle OOS (145 fk winners, net −$9.90/30d). Tier-2 pre-registration REVOKED. Signal-scoped only.

## LAST-RUN CHANGES — STATUS

| Change | Status | Evidence |
|--------|--------|----------|
| doji RE-KILL | HOLDING (frozen) | 0 trades since 20:30 Oct 16 |
| pump-chain+ dead-gap | HOLDING (frozen) | 0 trades since 01:39 |
| ai-trader drift guard | HOLDING | rsi_at_pick unverified (paused) |
| MFE-CUT shadow T=45/0.20 | COLLECTING / FLIP BLOCKED | candle OOS FAIL |
| bb-bounce trail-arm shadow T=55 | COLLECTING / **FLIP PATH FAIL** | candle OOS fk 41.9% |
| ai-trader trail-arm shadow T=55 | COLLECTING | 3 fires/30d hypothetical |
| pump-chain TAT live45 | KEPT — net≈0 wash | comment retracted, no code change |
| bb-squeeze TAT live60 | **CONFIRMED** | +$1.02 candle OOS |
| sweet-spot MIN 55 / SHORT midband / EXTREME 0.85 / SHORT floor-35 | HOLDING / UNVALIDATED | paused |

## ⚠️ OPEN (CEO-owned)

1. 🔴 **Exit-ladder candle backtest — STILL NOT COMMISSIONED (8th request).** Spec v2 ready: signal-scoped only; template = bb-squeeze T=60 (+$1.02, fk 11%); failure mode = slow-grinder FK (pump-chain T=45, fk 37%); units rule cf=amount×lp/100; bar fk≤20% AND net>0 on candle OOS.
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
