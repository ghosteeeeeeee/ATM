# Current State — brain_auditor Captain Run Oct 17 21:45 UTC

**Last Updated: 2026-10-17 21:45 UTC**
**Updated by: brain_auditor — 0 config changes (soak #3), WLD autopsy, floor-admit cohort escalation, MFE-CUT 1st live validation**

## PIPELINE STATUS (21:45 UTC)

- **Trading RESUMED 16:57 UTC** — 0.3x size-reduce active (vacation_size_reduce.json confirmed). Both resume conditions still failing: 7d WR 34.3% < 35.0 AND 7d PnL −$2.62 < −$2.00. Size-reduce stays.
- **24h 8T 3W −$0.57 (37.5% WR) | 7d 204T 34.3% −$2.62.** All 24h closes pre-resume except WLD.
- **Post-resume trades: 1 — WLD LONG #16259, LOST −$0.15 hard_sl (full autopsy below).** 1T = no validation cohort; morning stack still unvalidated.
- Regime: BTC AT EMA300 ~18h dead-volume chop (vol_ratio 0.05). 15m/4h SHORT_BIAS. Vol LOW, velocity SLOW. Flat/right-sized book is the correct position.
- Watchdog: CRITICAL (13/20 recent lost). Steers: wrong-side pattern CONFIRMED; doji steer STALE (signal dead); ai-trader-manual noise; NXPC SHORT pick precheck-clean.
- Open: 0. NXPC SHORT pick pending fill (watchdog 21:08, conf 82, rsi_at_pick 50.0).

## ⚠️ THIS RUN — 0 CONFIG CHANGES (SOAK DISCIPLINE #3)

**Decision: HOLD.** 5+ unvalidated morning filters landed at 16:57. First post-resume trade LOST. 1 trade is not a cohort — stacking more entry filters now compounds unvalidated risk and confounds the validation set. The morning stack needs its ~20-trade cohort.

### WLD #16259 Autopsy (post-resume trade #1)

- **Signal:** ai-trader+ LONG, EXTREME regime, conf 43.5% exec (floor-admitted).
- **Root cause:** falling-momentum entry into a fading pump. pick RSI 60.4 (clean-trend thesis) → fire RSI 47.17 (drift 13.2, passed 15-max guard). momentum_state=falling at fire. Spike-filter held 9min at live RSI 75.5-79, then entered the moment RSI cooled <75 — bought the fade of a fade.
- **MFE never reached +0.40% trail arm.** hard_sl −0.70% price. Classic never-armed chop entry.
- **Conf anatomy:** conf 87 × penalty_raw **0.014** (catastrophic combo history) × PENALTY_MULT_FLOOR 0.5 → exec 43.5%. At old 0.3 floor: exec 26.1 = would have been BLOCKED.
- **Shadows fired (first live validation):** MFE-CUT would-fire @54m/−0.28% (actual exit @56m/−0.70% — ~50% of loss saved). TRAIL-ARM timeout would-fire @56m. Both zero-behavior, collecting.

### Floor-Admit Cohort — CEO ESCALATION

- Floor-admit shadow since Oct 15: **32 executed trades, 11W/21L, net −$1.40.** All 32 would be blocked at old 0.3 floor (+$1.40 counterfactual save). n≥20 bar MET.
- WLD (pp=0.014) is an extreme case the flat 0.5 floor cannot distinguish from pp=0.3 mixed-signal trades.
- **CEO owns the floor decision.** Data surfaced; NO unilateral revert. Creative idea logged: pp-conditional floor (pp<0.10 → floor 0.3; pp 0.10-0.5 → floor 0.5).

### Last-Run Changes — All 8 Verified Holding

| Change | Status | Evidence |
|--------|--------|----------|
| doji RE-KILL | HOLDING | 0 trades since Oct 16 20:30 |
| pump-chain+ dead-gap | LIVE | 0 post-resume pump-chain trades |
| pump-chain− dead-gap | LIVE | soak clock |
| ai-trader drift guard | LIVE | WLD Δ13.2 passed (guard works; threshold loose on n=1) |
| SHORT midband block | HOLDING | 0 violations |
| sweet-spot MIN 55 | LIVE | first cohort pending |
| EXTREME conf 0.85 | APPLIED | WLD log: EXTREME → 0.85x confirmed |
| vacation size-reduce 0.3x | ACTIVE | both resume conditions failing |
| MFE-CUT shadow | **1st LIVE FIRE** | WLD would-fire @54m |
| bb-bounce/ai-trader TAT shadow | COLLECTING | WLD would-fire @56m |

### Trail vs SL Family (7d — wealth gap unchanged)

| Family | Trades | WR | PnL |
|--------|--------|----|-----|
| TRAIL | 72 | 80.6% | +$6.45 |
| SL | 115 | 0.9% | −$9.72 |
| OTHER | 17 | 64.7% | +$0.65 |

### Signal Quality Notes

- **falling-momentum LONGS:** session brain verified worst LONG cohort (27T 48.1% WR vs rising 129T 56.6%). OSCILLATOR gate already dampens 0.70x for MID+falling. Hard block needs ai-trader-specific n≥20 (currently n=1 — WLD).
- **NXPC SHORT:** first precheck-clean SHORT candidate (conf 82, rsi 50, ATR 2.04%, SHORT_BIAS aligned). Let it fill. Correct-side entry per trend doctrine.
- **EXTREME still worst regime:** 113T 26.5% −$1.72/7d. conf 0.85 applied; unvalidated beyond meta (1 post-change trade = WLD, the loss).

## PENDING / ESCALATIONS

1. **CEO: floor-admit cohort 32T −$1.40** — keep 0.5 / revert 0.3 / adopt pp-conditional. Shadow continues either way.
2. **self_learner: signal-scoped exit-ladder candle OOS (9th request).** MFE-cut just validated live on WLD. Universal MFE-cut stays dead per 11:05 OOS; signal-scoped TAT only proven mechanism.
3. **Monitor:** AI_TRADER_RSI_DRIFT_MAX=15 to n≥20 before tightening (WLD Δ13.2 passed, APT Δ23.4 blocked).
4. **Morning stack validation:** first ~20 post-resume trades = validation cohort. CEO eyeball on resume day recommended.
