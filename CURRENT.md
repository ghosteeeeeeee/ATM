# Current State — brain_auditor Run Oct 19 19:45 UTC

**Last Updated: 2026-10-19 19:45 UTC**
**Updated by: brain_auditor #25 — 1 bugfix (size-reduce auto-clear aging guard)**

## PIPELINE STATUS (19:45 UTC)

- **Trading LIVE** with 0.3x size-reduce (7d WR 33.8% < 37 AND pnl −$4.13 < $0). **⚠️ Auto-clear aging guard SHIPPED this run: WR path now requires pnl_7d ≥ −$2.00. Size-reduce will NOT auto-clear Oct 20 via aging artifact (WR would hit 37.2% on denominator change while book still −$2.60). Clears only on genuine healing (WR≥37 ∧ PnL≥−$2) or profitability (PnL≥$0). Staged-lift escalation still CEO.**
- **24h 17T 8W −$0.38 (47.1% WR healed). | 7d 201T 33.8% −$4.13. | Never-armed chop 127T −$9.95 vs trail 68T +$6.07 (7d wealth gap $16.02).**
- **0 open — flat.** 6 quiet hours. Transition posture: 19:06 watchdog 15m+4h both LONG_BIAS (regime-flip #2 attempt; first flip 12:36 reversed <2h), but continuum BELOW + alt tape still SHORT-bias. PONS/INJ SHORT picks unfilled (no forced entries).
- **Vacation mode ACTIVE** — shadow-first, no enforcement flips. Lifts when T returns.
- Protected flags 13/13 INTACT (verified this run: LIVE_TRADING=True, PM_TRAIL 0.40%/0.20%).

## THIS RUN — brain_auditor #25

**1 bugfix: vacation_guardrail auto-clear aging-artifact guard.**
- Before: `(wr_7d >= 37 or pnl_7d >= 0)` — Oct 13 cohort (56T −$1.53, 25% WR) ages out Oct 20, inflating WR 33.8→37.2% on denominator change while book still −$2.60 → old OR would full-size (3.3× risk step) a bleeding system.
- After: `((wr_7d >= 37 and pnl_7d >= -2.00) or pnl_7d >= 0)` — clear only on genuine healing or profitability. py_compile OK, 7-case sim ALL PASS. Timer applies on next 30-min tick.
- pump-chain− kill watch RE-AFFIRMED: 14d +$0.07 razor-thin (57T 24.6% WR); pre-block EXTREME trades aging out will pull to wash. Auto-kill when 14d PnL < $0 with n≥20.

**WATCHDOG STEERS BOTH AGED:**
- 001 wrong-side 7 losses = morning ARB/DOGE/LDO cluster pre-EXTREME-block (09:41). Block is the systemic fix; 0 wrong-side trades since.
- 002 ai-trader+ streak = same pre-block cluster; 0 post-block trades.

**LOSING AUTOPSY 24h: 9 losers −$0.72, ZERO new patterns, max −$0.26, 5/9 shadow-covered.**

**LAST-RUN VERIFY all PASS:** signal_reporter flips ✓ (0 trades since blocks) | precedence fix ✓ | death-zone advisory ✓ (firing on PONS RSI 51.1) | SHORT floor-45 ✓ | doji kill ✓ | pp-cond ✓ | all shadows collecting ✓.

## PREVIOUS — brain_auditor #24 (18:40 UTC)

**0 config changes** (vacation mode + soak #24; all candidates fail bars or already shipped).

**signal_reporter vacation violation: RATIFY both flips — do not revert.**
- b0a2467d 09:41: ai-trader+ EXTREME→0.0 (30d 15T 26.7% −$0.71), ai-trader- EXTREME→0.0, manual NORMAL→0.0
- f56927c5 15:51: pump-chain+ NORMAL 0.5→0.0 (all-time 8T 12.5% −$0.45; EXTREME habitat 97T 44.3% +$4.01 preserved)
- Rationale: data-backed 30d windows, already live, 0 trades since either block, reverting = churn. Collateral: EXTREME demote shadow STARVED (re-eval moot). CEO actions when T returns: formal ratify; retire/repurpose starved shadow; decide signal_reporter vacation scope (regime-blocks shadow-only?).

**EXIT-STACK SCORECARD (run #19 pre-registered creative, DELIVERED):**

| Cohort (7d) | n | PnL | Lever | Blocked on |
|---|---|---|---|---|
| Never-armed chop (MFE<0.40) | 88 | **−$8.29** | exit-ladder (entry filters EXHAUSTED) | self_learner candle-OOS (P0, 10+ requests) |
| Armed-then-reverse (MFE≥0.40, SL exit) | 27 | −$1.31 | ARM-BE shadow / EXTREME BE-ratchet (38/50 EXTREME @14d) | CEO ratify + v6 exit-stack integration |
| Trail family (winners) | 56 | **+$5.93** | DO NOT TOUCH | — |

**LOSING AUTOPSY 24h: 8 losers, ZERO new patterns** — ai-trader mid-RSI LONGs ×3 (advisory+demote shadow cover), ME stale (TAT 2nd live would-fire), ARB floor-admit (pp-cond cover), BTC/LTC variance. 5/8 shadow-covered.

**LAST-RUN VERIFY all PASS:** vacation_guardrail precedence ✓ | SHORT floor-45 ✓ | ai-trader EXTREME block ✓ (0 trades since 09:41) | pump-chain+ NORMAL block ✓ (0 since 15:51) | death-zone advisory ✓ | doji kill ✓ | pp-cond 665+ events ✓ | ARM-BE collecting (0 fires = legit, 0 armed trades) | MFE-CUT/TAT collecting ✓ | protected 13/13 ✓.

## PREVIOUS — brain_auditor #23 (16:45 UTC)

- ai-trader+ TAT-eligibility screen = FAIL (winner med hold > loser med hold = impossible T) — idea formally dead, verdict written.
- Dual-condition TAT OOS = FAIL (n=4 <15, net −$0.06) — flip path closed.
- EXTREME demote shadow re-eval: KEEP (n=16<20, fk 75% fails bar) — now moot (starved by hard block).
- Sideways-URGENT: signal_reporter vacation violation flagged (this run: RATIFY).

## PREVIOUS — brain_auditor #22 (14:38 UTC)

- Regime flip (12:36 LONG_BIAS) reversed <2h — bounce-in-downtrend, STRONG_DOWN restored. n=1 natural experiment closed.
- EXTREME confidence inversion pre-registered (n=16, below bar).

## ACTIVE SHADOWS

- pp-conditional penalty floor — 665+ events / 64+ would-blocks, CEO resume-day decision
- ARM-BE stop — collecting (0 fires, code PM:3679)
- MFE-CUT / bb-bounce TAT — collecting (ME 2nd live would-fire validated)
- ai-trader+ EXTREME LONG conf-demote — STARVED by hard block (CEO: retire or repurpose)
- contrarian PROMOTE — collecting (14d span gate)
- wyckoff shadow — collecting
- RR-engine would-blocks — ~10/hr

## NEXT

- **Size-reduce auto-clear BLOCKED by aging guard (this run)** — stays until 7d PnL ≥ −$2.00 with WR≥37, or PnL≥$0. Staged-lift decision still CEO.
- **pump-chain− kill watch: auto-kill when 14d PnL < $0 with n≥20** (currently +$0.07, pre-block EXTREME aging out pulls toward wash).
- **CEO return: ratify signal_reporter flips; ARM-BE v6 review; staged-lift decision; signal_reporter vacation scope.**
- P0: self_learner exit-ladder candle OOS (blocks chop −$9.95/7d fix).
- Oct 21: pp-cond floor flip surface (n≥20 met).
- Regime-flip watch: if BTC holds LONG_BIAS >4h = real reclaim; if reverses = bounce #2 confirmed.
