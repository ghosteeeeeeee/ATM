# Current State — brain_auditor Captain Run Oct 18 16:45 UTC

**Last Updated: 2026-10-18 16:45 UTC**
**Updated by: brain_auditor — 1 shadow ship, 0 live filters**

## PIPELINE STATUS (16:45 UTC)

- **Trading LIVE** with 0.3x size-reduce (7d WR 33.7% < 37 AND 7d PnL −$3.65 < $0 — both resume conditions still failing).
- **24h 15T 6W +$0.08 (40%) — HEALED. | 7d 205T 69W −$3.65 (33.7%). | 30d ~778T 43.8% −$3.29.**
- **0 open.** Regime: SHORT_BIAS (15m+4h), BTC below EMA300 366min, NORMAL vol, DECLINING.
- Vacation guardrail: ESCALATE mode (7d WR 33.7% < 40%).
- **Current pick: ACE SHORT @ 0.152, conf 74, RSI 56.7** — correct side, all gates pass.

## THIS RUN — 1 SHADOW SHIP

**ai-trader+ EXTREME LONG conf-demote SHADOW** (AI_TRADER_EXTREME_LONG_SHADOW_ENABLED=True, MULT=0.7).
- 14d EXTREME LONG: 14T −$0.61 28.6% WR = worst ai-trader+ cohort
- HIGH: 7T +$0.03 71.4% | NORMAL: 4T −$0.05 50.0% — regime is the separator
- Zero-behavior: logs would-demote conf to hotset metadata
- Flip live only with CEO GO + n≥20 + winner-impact check (Oct 19 re-eval)

## LAST-RUN CHANGES — ALL VERIFIED (soak #16)

| Change | Status | Evidence |
|--------|--------|----------|
| SHORT floor revert 35→45 (11:48) | HOLDING | 0 violations. HBAR SHORT won +$0.07 at RSI 54.45. |
| death-zone advisory RSI 45-55 (03:41) | FUNCTIONAL | Advisory only. 2 in-band trades since (both small losses). |
| watchdog _SIGNAL_FLAG_MAP (05:39) | HOLDING | Steers clean of dead-signal noise. |
| REGIME_CONF_EXTREME_MULT 0.85 | EARLY-POSITIVE | 3d EXTREME 34T −$0.05 vs 7d 112T −$1.64. |
| contrarian PROMOTE 14d gate (11:48) | HOLDING | Soak until ~Oct 31. |
| doji kill (Oct 16) | HOLDING | 0 trades since kill. |
| ai-xlm shadow (16:45 this run) | COLLECTING | Zero-behavior, first fires pending. |

## WEALTH GAP (7d) — UNCHANGED

| Family | Trades | WR | PnL |
|--------|--------|-----|-----|
| TRAIL (profit-monster + atr_trail + trail_sl) | 65 | 89.2% | **+$6.43** |
| CHOP (hard_max_loss + atr_sl_hit) | 106 | 1.9% | −$8.86 |

## WATCHDOG STEER TRIAGE

| Steer | Verdict | Detail |
|-------|---------|--------|
| 001 losing streak 13/20 | AGED-OUT | 24h healed +$0.08 40%WR. |
| 002 wrong-side trades | VERIFIED-STRUCTURAL | Trail vs chop unchanged. LONGs 48h 19T −$1.54 16.7% vs SHORTs 9T +$0.41 44.4%. |
| 003 pump-chain+ disable | REJECTED | 14d 51T +$1.65. EXTREME habitat +$2.14. |
| 004 ai-trader+ streak | MONITOR→Oct 19 | Shadow now collecting counterfactual data. |

## ESCALATIONS

- **#15:** exit-ladder candle OOS (self_learner undelivered 10+). brain_auditor runs scoped version Oct 19 if still undelivered.
- Resume-day (~Oct 23): CEO eyeball — 12+ unvalidated changes land together.

## NEXT

- Oct 19: ai-trader+ EXTREME LONG re-eval (shadow data + n needs 20+).
- TAT shadow: collect to 14d for flip review.
- Protected flags 13/13 INTACT.
