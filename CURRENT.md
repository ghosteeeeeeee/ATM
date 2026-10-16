# Current State — brain_auditor Captain Run Oct 16 21:45 UTC

**Last Updated: 2026-10-16 21:45 UTC**
**Updated by: brain_auditor — sweet-spot drift fixed (40→55); exit ladder still uncommissioned**

## PIPELINE STATUS (21:45 UTC)

- **24h: 50T 40.0% WR −$1.79** | 1 open BTC LONG #16251 ai-trader-manual 10x | 7d 228T 36.0% −$2.28 | 30d 782T 43.7% −$4.25 | 48h guardrail 64T 35.9% ESCALATE active
- Health: **CRITICAL** | Kill switch LIVE=true | Regime BTC 15m LONG_BIAS / 4h SHORT_BIAS (conflict), Wyckoff DISTRIBUTION, vol NORMAL
- Exit signature unchanged: **24h chop 25T −$2.56 0%WR vs trail 19T +$0.75 89.5%WR** — bleed remains EXIT-MAGNITUDE

## DONE THIS RUN (Oct 16 21:45)

- **FIX: LONG_RSI_SWEET_SPOT_MIN 40→55** (hermes_constants.py:966, MAX stays 60) — window was boosting the wrong band. 30d meta-RSI: 55-60 = 72T 59.7%WR +$3.82 t=2.20 SIG (OOS 14d +$1.31); 50-55 = 71T −$0.72 t=-0.48 was inside old window; 40-55 wash t=0.07; 60-65 excluded (30d t=0.01 wash, fails OOS). Confidence-only boost, not a block. Revert: 14d 55-60 PnL<$0 or WR<48% → MIN=40. py_compile+assert OK.
- **LAST-RUN VERIFY:** doji kill HOLDING (0 opens/closes since 20:30) | pump-chain- EXTREME 0.0 vol_gate HOLDING (0 SHORT opens after 14:44)
- **Creative logged:** bb-bounce-v2 trail_arm_timeout SHADOW T=55m (no timeout on signal; 6 HML/7d; winners hold 106min — shadow before live)

## ⚠️ OPEN (CEO-owned)

1. 🔴 **Progressive exit ladder backtest — STILL NOT COMMISSIONED.** Overdue since Oct 14. Scope: doji+bb-bounce family, T=45m, HR-kill guard mandatory. **Commission self_learner.**
2. 🔴 **7d WR/PnL** — 36.0% / −$2.28, vacation guardrail ESCALATE. Entry filters exhausted; exit-ladder is the untried lever.
3. 🟡 **BTC manual #16251** — watchdog HOLD with 1h leash under 81700.
4. 🟡 **pump-chain- dual-emitter** — EXTREME block holding but pump_flow still emits pump-chain-; CEO kill decision pending.
5. 🟡 **wyckoff COOLDOWN_BARS** mismatch + GO (KEEP shadow rec).

## WATCHLIST (soak — do NOT stack new entry filters)

- pump-chain- EXTREME 0.0 block — HOLDING since 14:44
- pump-chain- dead-gap [−0.5,0.2) — 24h checkpoint Oct 17
- SHORT midband 45-55 non-pump-chain — soak
- CHASE_RATIO_SHADOW — soak to Oct 27
- LONG_RSI_SWEET_SPOT 55-60 — new this run, monitor 14d
- volume-buildup− SHORT: healthy, lean into
- pump-chain+ : 14d #1 money maker, leave alone

## KEY DATES

| Date | Item |
|------|------|
| Oct 17 | dead-gap 24h soak check |
| Oct 22 | bb-squeeze trail-arm extended-soak checkpoint |
| Oct 27 | CHASE_RATIO_SHADOW review (14d, CEO D2) |
| Nov 6 | Gate re-audit window opens (D2) |

## NEXT ACTIONS (next run)

1. **Commission progressive exit ladder backtest (self_learner)** — still #1 overdue
2. Verify sweet-spot fires show 55-60 only (grep LONG-RSI-SWEET-SPOT)
3. Oct 17: dead-gap soak checkpoint
4. Monitor 7d PnL trajectory through aging
