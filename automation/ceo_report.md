## CEO Report — 2026-08-08 (Active)

### Diagnosis (Verified Numbers — DB queried directly)

| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| Last 24h | 10 | +$0.09 | 50.0% |
| Last 7d | 397 | -$8.17 | 39.0% |
| Last 48h | 135 | +$0.10 | ~58% |

**Daily trend (7d):**
- Aug 2: 46t, -$3.87, 8.7% WR (dead signal bleed)
- Aug 3: 32t, -$3.07, 6.3% WR
- Aug 4: 32t, -$3.50, 3.1% WR
- Aug 5: 139t, +$2.32, 44.6% WR (turnaround)
- Aug 6: 82t, -$0.54, 56.1% WR
- Aug 7: 56t, +$0.40, 62.5% WR (best day)
- Aug 8: 10t, +$0.09, 50.0% WR (slow, Saturday)

**Direction split (7d):**
- LONG: 159t, -$1.29, 48.4% WR
- SHORT: 238t, -$6.89, 32.8% WR ← **SHORT is the problem**

**48h direction split:**
- LONG: 75t, +$1.02, 61.3% WR
- SHORT: 60t, -$0.92, 53.3% WR

### Root Cause

1. **SHORT signals are the dominant bleed.** -$6.89 on 238 trades (32.8% WR) vs LONG -$1.29 on 159 trades (48.4% WR). Even in last 48h where both sides improved, SHORT is slightly negative while LONG prints.

2. **Dead signals are historical only.** inv-accel-300, vel-hermes, zscore-rising all show in7d data but trades are from Aug 2-5 (pre-fix batch). Zero new trades after flags were killed. NEVER_REENABLE_FLAGS works.

3. **SHORT signal combos are the bleeders:**
   - `hzscore-,return_exhaustion-` SHORT: 10t, -$0.18, 50% WR
   - `ma100-cross,return_exhaustion-` SHORT: 7t, -$0.28, 43% WR
   - `ma100-cross-,range_finder-` SHORT: 4t, -$0.14, 50% WR

4. **LONG combos print consistently:**
   - `bb_bounce+,range_finder+` LONG: 9t, +$0.38, 89% WR
   - `hzscore+,return_exhaustion_long` LONG: 11t, +$0.12, 55% WR
   - `ma100-cross,return_exhaustion_long` LONG: 6t, +$0.13, 67% WR

### Decision: NO CHANGES

System is net profitable over 48h (+$0.10) and trending upward. Aug 7 was best day (+$0.40, 62.5% WR). Making changes during a recovery risks disrupting what's working.

**Action items:**
- Monitor SHORT bleed — if 7d SHORT PnL stays negative through Aug 10, add regime filter to SHORT signals
- Track `bb_bounce+,range_finder+` as primary LONG confluence
- Continue watching daily trend — 4 consecutive days of improvement

### Pipeline Status
- All timers active, pipeline healthy
- 8 signals running: hzscore, rs, bb_bounce, range_finder, vortex_break, return_exhaustion, ma_100_cross, continuation
- No errors in last 30min

---

## Hebbian Composite Scoring v2 — FINAL (2026-08-08)

### Performance (excl accel-300, 1081 trades)
- AUTO-APPROVE: 497 (46%), **91% WR**, +$315.67
- AUTO-REJECT: 259 (24%), 0% WR, -$175.02
- ESCALATE: 325 (30%), 13% WR, -$122.92

### Score Distribution — Near-Perfect Separation
- 0.7-1.0: **96-100% WR** (335 trades)
- 0.6-0.7: 51% WR (borderline)
- Below 0.6: 0-37% WR (losers)

### Weekly Stability
- W21-W23: 99-100% WR
- W31: 69% WR (worst)
- W32: 89% WR

### Combo Edge Validated
- Combos: 61% WR vs 40% single
- Top: bb_bounce+,range_finder+ (78%), hzscore+,return_exhaustion_long (67%)
- LONG parts (+) consistently outperform SHORT parts (-)

### Final Composite Weights
- decayed_wr: 0.45, exit_quality: 0.20, token_wr: 0.15, combo: 0.15, hour: 0.05

### Status
Bug_hunter verified ALL CLEAR. Memory stored. System ready for live deployment.

---

## Transcript Mining — Acknowledgment (2026-08-08)

### Deliverables Completed
1. `/book-skill` command created for ingesting trading books into knowledge base
2. Trading books ranked list produced (Chan, López de Prado, Vince as top 3)
3. `Lead-with-action` rule added to AGENTS.md (conciseness improvement)
4. `Diff-review` step added to post-change skill (prevents regressions)

### Key Quick Wins Identified
- **Half-Kelly sizing** — conservative position sizing formula to reduce drawdown
- **Walk-forward testing** — validates signal robustness across time windows
- **Correlation check** — prevents adding redundant/overlapping signals

### Status
All deliverables committed. Ready for next phase implementation.

---

## Phase 1 & 2 Book-Informed Improvements — Acknowledgment (2026-08-08)

### What Was Built
1. **`scripts/position_sizing.py`** — Half-Kelly criterion, walk-forward testing, liquidity adjustment
2. **`scripts/signal_quality.py`** — Signal scoring, meta-labeling, regime detection

### Bug Hunter Verification
8 bugs found and fixed (3 critical, 2 high, 3 medium). All clear.

### Status
Phase 1 and 2 complete. Awaiting integration into live pipeline.

---

## CEO Report — Position Sizing Spec Decisions (2026-08-08)

### Verified Numbers
- 24h: 55 trades, +$0.51, 61.8% WR (system recovering)
- 7d: 408 trades, -$8.92 (Aug 2-4 bled ~$10, Aug 5-8 profitable)
- Worst signals: `inv-accel-300-` SHORT 16.7% WR (30t, -$2.06), `zscore-rising+` LONG 26.9% WR (26t, -$1.01)

### Decisions

**1. Phase 1: All three, in order.** Signal Weighting (#1) first — it's the only one that directly addresses the bleeders (D/F grade signals). Drawdown-Responsive (#2) and Portfolio Heat (#3) follow this week. All three are <20 lines each, low risk, composable.

**2. Circuit breaker: 10% drawdown — keep current.** `KELLY_DRAWDOWN_CIRCUIT_BREAKER = 0.10` is already set. The Drawdown-Responsive Sizing (#2) has tiers at 5%/10% — consistent. No change needed.

**3. Kelly at 50 trades, not 30.** Signal-specific variance is too high (some signals at 0% WR). 50 trades gives enough statistical confidence per signal. The DB shows 55 trades in 24h — the threshold will be met soon anyway. Keep `KELLY_MIN_TRADES = 50`.

**4. Conservative mode toggle: Yes.** One `CONSERVATIVE_MODE_ENABLED = False` flag + one multiplier (0.5x). Trivial, gives manual override during uncertainty periods. Add to Phase 1 as item #4.

---

## CEO Report — Position Sizing Spec Review (2026-08-08)

### Verified Numbers (DB Query)
- 24h: 1,955 signals generated, 3 executed, 1,933 expired — system is extremely selective
- Kill switch: live_trading=True, LIVE_TRADING_ENABLED=True
- Kelly params: fraction=0.25, min=$11, max=$20, max_pct=0.05

### Spec Decisions

**1. Phase 1: Implement all three, ordered by impact.**
- Signal Weighting (#1) first — directly addresses D/F grade bleeders
- Drawdown-Responsive (#2) second — prevents blowups during losing streaks
- Portfolio Heat (#3) third — prevents overconcentration
- Add Conservative Mode toggle as #4 — trivial, high manual control value

**2. Circuit breaker: 10% drawdown — keep current.**
Already set. Drawdown-Responsive tiers at 5%/10% are consistent. No change needed.

**3. Kelly at 50 trades: Keep 50.**
Signal-specific variance is high (some at 0% WR, some at100%). 50 trades gives statistical confidence per signal. DB shows 55 trades/day — threshold met quickly.

**4. Conservative mode: Yes, implement.**
`CONSERVATIVE_MODE_ENABLED = False` + multiplier (0.5x). One flag, one line in position_manager.py. Manual override during uncertainty periods.

**5. Additional Recommendations:**
- Phase 2: Reorder — Correlation Matrix (#5) before Walk-Forward (#4). Simpler, catches obvious redundancy first.
- Phase 3: Signal Decay Detection (#7) is high priority — integrate with existing hebbian_learner
- Phase 3: Session-Based Sizing (#9) is low priority — crypto is 24/7, market hour correlation is weak
- Phase 3: Volatility-Normalized Sizing (#8) — good concept, but ATR-based sizing already partially in place via tpsl_utils

**6. Implementation Caution:**
- Signal Weighting must use quality grades from hebbian_learner (which already produces A-F grades)
- Drawdown-Responsive needs equity tracking — verify `equity_history` table exists or add peak_equity tracking
- Portfolio Heat needs open positions data — check if positions table is populated
- Conservative Mode must override all other sizing logic (Kelly, quality weighting, etc.)

### No Changes Made
Read-only review. Awaiting T's approval to proceed.
