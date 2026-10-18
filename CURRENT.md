# Current State — brain_auditor Captain Run Oct 18 08:35 UTC

**Last Updated: 2026-10-18 08:35 UTC**
**Updated by: brain_auditor — 0 config changes, soak #12, arm-registration-gap finding**

## PIPELINE STATUS (08:35 UTC)

- **Trading LIVE** with 0.3x size-reduce (7d WR 34.5% < 37 AND 7d PnL −$2.90 < $0 — both resume conditions still failing).
- **24h 11T 5W +$0.18 (45.5%). | 7d 203T 70W −$2.90 (34.5%). | 30d 778T 43.8% −$3.29.**
- **2 open:** HYPE SHORT volume-buildup- (+0.05%, 0.3h), PUMP SHORT ai-trader- (−0.12%, 0.3h) — both aligned SHORT_BIAS/SHORT_BIAS — HOLD.
- Vacation guardrail: ESCALATE mode (48h WR ~38% < 40%).

## THIS RUN — 0 CONFIG CHANGES, SOAK #12

**NEW FINDING: ARM-REGISTRATION GAP.** 28T/14d atr_sl_hit reached MFE≥0.40 (avg 0.83%, hold 70m) with `trailing_activated=FALSE`, net −$1.62. Concentrated: pump-chain- 12T −$0.55, pump-chain+ 6T −$0.58. Hypotheses: (a) candle-MFE vs live_pnl price-source mismatch, (b) spike-between-poll missed arm, (c) trail-subsystem flag desync. **Delegated: bug_hunter zero-behavior close-time instrumentation (escalation #16).** Enables or kills ATR-normalized arm threshold idea with data.

**WATCHDOG STEER TRIAGE (08:26 steers):**

| Steer | Verdict | Detail |
|-------|---------|--------|
| 001 losing streak 13/20 | AGED-OUT | Window straddles Oct 16-17 pre-fix losses; 24h healed +$0.18. Size-reduce covers. |
| 002 PUMP+HYPE cluster | ALIGNED | Both SHORT in dual SHORT_BIAS — no action. |
| 003 wrong-side trades | VERIFIED-STRUCTURAL | 48h LONG 38T −$1.99 vs SHORT 15T +$0.10. LONG-SHORT-BIAS block shadow-falsified Oct 15. Macro REDUCE + size-reduce deployed. No new filter passes bars. |
| 004 pump-chain+ disable | REJECTED | 14d 51T +$1.65 39.2% net-profitable. 4-loss streak below bar. Dead-gap band soaking. |
| 005 ai-trader+ streak | MONITOR→Oct 19 | EXTREME band improved to 15T 33.3% −$0.04. Advisory live. |

## LAST-RUN CHANGES — ALL VERIFIED (soak #12)

| Change | Status | Evidence |
|--------|--------|----------|
| watchdog _SIGNAL_FLAG_MAP fix (05:41) | PASS | Dead-signal steers gone from steer list |
| bb-bounce TAT backfill (07:45) | FLIP BLOCKED | Single-condition: 7/7 eligible winners degraded (100% FK). Dual-condition (MFE<0.20∧pnl<−0.2%) = restructure candidate, needs OOS |
| MFE-CUT shadow | COLLECTING | 0 fires (structural: only collects on signals without live TAT) |
| TAT shadow fires | 1 | BANANA counterfactual −0.50% vs −2.24%. Flip needs ≥15 + dual-condition redesign |
| doji / dead-gap / drift / EXTREME 0.85 / sweet-spot / midband | HOLDING | 0 violations |
| SHORT floor-35 | HOLD | −$0.12 vs −$1.00 trigger (resets Oct 20) |
| death-zone advisory | SHIPPED | Non-blocking |

## WEALTH GAP (7d) — UNCHANGED

| Family | Trades | WR | PnL | Signature |
|--------|--------|-----|-----|-----------|
| TRAIL (profit-monster + atr_trail + trail_sl) | 64 | 89.1% | **+$6.36** | armed, held, won |
| HML | 53 | 0% | −$4.71 | MFE 0.113%, hold 28m |
| atr_sl_hit | 50 | 2% | −$3.98 | MFE 0.430%, hold 58m |

Exit-magnitude remains THE lever. Entry-filter family exhausted.

## ESCALATIONS

- **#15:** exit-ladder candle OOS for dual-condition TAT still needed (self_learner undelivered 8+).
- **#16 (NEW):** arm-registration-gap instrumentation — bug_hunter, zero-behavior close-time debug log.

## NEXT

- Re-eval ai-trader+ death-zone/EXTREME Oct 19.
- Floor-35 daily check until Oct 20 reset.
- TAT dual-condition OOS design before any flip.
- Protected flags 13/13 INTACT.
