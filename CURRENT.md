# Current State — Daily Orchestrator Run Oct 18 17:05 UTC

**Last Updated: 2026-10-18 17:05 UTC**
**Updated by: daily_orchestrator — 0 code changes, 5 regime checks, 2 CEO escalations**

## PIPELINE STATUS (17:05 UTC)

- **Trading LIVE** with 0.3x size-reduce (7d WR 33.7% < 37 AND 7d PnL −$3.65 < $0 — both resume conditions still failing).
- **24h 15T 6W +$0.08 (40%). | 7d 205T 69W −$3.65 (33.7%). | 30d ~778T 43.8% −$3.29.**
- **0 open.** Regime: SHORT_BIAS (15m+4h), NORMAL vol. 9169/9169 pipeline cycles rc=0, 0 real errors.
- Vacation guardrail: ESCALATE mode (7d WR 33.7% < 40%).
- Protected flags 13/13 INTACT. Shadow flags verified live.

## THIS RUN — ORCHESTRATOR REGIME CHECKS (no code changes)

| Signal | 7d by regime | Verdict |
|--------|--------------|---------|
| pump-chain- SHORT | EXTREME 27.8% n=36 −$0.07 / NORMAL 0% n=3 −$0.06 | Loses ALL regimes → blanket-kill criterion met. **CEO DECISION #1** |
| pump-chain-v6- | EXTREME 50% n=6 +$0.43 | Winning — keep (v6 override by design) |
| hl_copy_trader | EXTREME 50% +$0.01 / HIGH 50% +$0.06 / NORMAL 20% n=5 −$0.10 | NORMAL block candidate, n=5 < sample bar. **CEO DECISION #2 — recheck n≥10** |
| bb-bounce-v2-long+ | EXTREME 33.3% / NORMAL 28.6% | All-lose but 24h n=2 < 3T threshold. Watch |
| ai-trader+ | EXTREME 26.7% / NORMAL 20% / HIGH 66.7% / FLAT 100% | Shadow collecting (brain_auditor 16:45). Oct 19 re-eval |

## ACTIVE SHADOWS (all collecting)

- **ai-trader+ EXTREME LONG conf-demote** (16:45, brain_auditor) — zero-behavior, 0 fires yet, MULT 0.7. Flip live only with CEO GO + n≥20.
- **RR-engine** — logging would-blocks (~10/hr, HBAR SHORT EXTREME R:R). Zero-behavior.

## LAST-RUN CHANGES — ALL VERIFIED (soak #16)

| Change | Status | Evidence |
|--------|--------|----------|
| SHORT floor revert 35→45 (11:48) | HOLDING | 0 violations. GMX 16.3<35 (pre-revert) + ATOM 39.2<40 (pump-chain floor) both correctly blocked. |
| death-zone advisory RSI 45-55 (03:41) | FUNCTIONAL | Advisory only. |
| watchdog _SIGNAL_FLAG_MAP (05:39) | HOLDING | Steers clean of dead-signal noise. |
| REGIME_CONF_EXTREME_MULT 0.85 | EARLY-POSITIVE | 3d EXTREME 34T −$0.05 vs 7d 112T −$1.64. |
| contrarian PROMOTE 14d gate (11:48) | HOLDING | Soak until ~Oct 31. |
| doji kill (Oct 16) | HOLDING | 0 trades since kill. |

## WEALTH GAP (7d) — UNCHANGED

| Family | Trades | WR | PnL |
|--------|--------|-----|-----|
| TRAIL (profit-monster + atr_trail + trail_sl) | 65 | 89.2% | **+$6.43** |
| CHOP (hard_max_loss + atr_sl_hit) | 106 | 1.9% | −$8.86 |

## ESCALATIONS

- **CEO #1:** pump-chain- SHORT blanket-kill — all-regime loser (7d). vs prior steer-003 REJECT (that was pump-chain+ LONG).
- **CEO #2:** hl_copy_trader NORMAL HL_Copy:0.0 block — winning EXTREME/HIGH, losing NORMAL, n=5 thin.
- **#15:** exit-ladder candle OOS — brain_auditor scoped version Oct 19.
- Resume-day (~Oct 23): CEO eyeball — 12+ unvalidated changes land together.

## NEXT

- Oct 19: ai-trader+ EXTREME LONG re-eval (shadow + n≥20).
- Recheck hl_copy_trader NORMAL n≥10 before any block.
- bb-bounce-v2-long+ / hl_copy_trader: 1 loss from 3T 0% kill review.
- TAT shadow: collect to 14d for flip review.
