# Plan: Signal Starvation Fix — 2026-10-12

## Problem Statement

Trade frequency dropped ~2x (31/day → 16/day) while win rate dropped ~14 points (55% → 41%). The filter stack is blocking trades without improving selectivity. Signals fire, pass the confluence gate, then die at execution.

**Evidence (PG-verified daily breakdown):**
- Sep 28–Oct 5 (before tight filters): ~31 trades/day, ~55% WR
- Oct 6–12 (after tight filters): ~16 trades/day, ~41% WR

**Live evidence (2026-10-12 22:40–23:30):**
- 17 SHORT signals fired during BTC dump, 0 executed
- 7 of 11 blocked by SHORT-RSI-HARD-FLOOR (RSI 24–35 < 45)
- 4 LONGs blocked by CONTINUUM-BLOCK (BTC bearish)
- Remaining blocked by score crush (products 0.01–0.20 → final scores 12–22/100)
- Hotset empty for 12+ consecutive cycles

## Root Causes (ranked by impact)

### 1. SHORT-RSI-HARD-FLOOR = 45 (blocks 7/11 SHORT signals)
**File:** `hermes_constants.py` — `SHORT_RSI_HARD_FLOOR = 45`

When BTC dumps and alts fall, RSI naturally drops below 45. The floor prevents shorting during dumps — exactly when you should be short. The floor was designed to prevent catching falling knives, but in a confirmed bear structure (LEAN_BEAR + BELOW EMA300), oversold = continuation, not bounce.

**Data:** 7 SHORT signals blocked at RSI 24–35 on 2026-10-12 during active dump. BTC was LEAN_BEAR + BELOW EMA300.

**Recommendation:** Add bear-structure exemption — when BTC continuum shows LEAN_BEAR/BEAR + BELOW EMA300, lower the floor to 25 (or disable). Mirror of the existing bear-structure exemption on SHORT_RSI_CEILING (line 1959-1979 in decider_run.py).

**Risk:** Could increase falling-knife losses. Mitigate with 7-day shadow mode.

### 2. Score Crush — 25 Multipliers Stack Multiplicatively
**File:** `signal_compactor.py` lines 2109–2131

25 multipliers compound multiplicatively. A few 0.6s and 0.7s produce products of 0.01–0.20. The SCORE-FLOOR at 0.3 rescues the product, but the RR engine is **exempt from the floor** (line 2131: `final_score = score * _mult_adjusted * rr_mult`). A base score of 88 becomes 88 × 0.3 × 0.85 = 22.4.

**Evidence:** INJ SHORT product 0.0160 (1.6% of base), BTC SHORT product 0.0070, JUP LONG product 0.0131. All floored to 0.3, then crushed again by RR.

**Recommendation:** 
- Option A: Remove RR exemption from floor — let the 0.3 floor apply to the full product including RR
- Option B: Cap total multiplier stack at 0.5 (not 0.3) — raise floor
- Option C: Reduce number of active multipliers — audit which ones actually predict outcomes

**Recommendation:** Option A (remove RR exemption). The exemption was added 2026-10-07 ("RR penalties must bite") but the data shows RR grade C/D is assigned to most signals during dumps, making the exemption counterproductive.

### 3. CONTINUUM-BLOCK Kills LONGs During Bear Structure
**File:** `signal_compactor.py` line 2684

Blocks LONG when BTC shows bear structure (phase + linreg + ema all agree). But pump-chain signals are `_btc_exempt` — they bypass this block. Non-pump-chain LONGs (oversold-bounce, r2-trend, etc.) are blocked.

**Evidence:** TRX, WLFI, PURR, NXPC, JUP LONGs all blocked at 23:30 during BTC bear structure. These were oversold-bounce signals firing on RSI 25–67.

**Recommendation:** Add oversold-bounce exemption — oversold-bounce is a mean-reversion signal that works during bear structure (buying dips). It should be exempt from CONTINUUM-BLOCK like pump-chain already is.

### 4. HALL-SHAME Blocks Tokens With 30d WR < 55%
**File:** `signal_compactor.py` — HALL-SHAME filter

Blocks tokens with 30d win rate below 55%. CHIP (33.3% WR) was blocked despite +29% pump. The filter uses historical performance to block current opportunities.

**Recommendation:** Add momentum exemption — skip HALL-SHAME when speed_percentile > 90 or z_score > 2.0. A token pumping +29% overrides its historical WR.

### 5. PENDING Lifecycle Waste
**File:** `signal_compactor.py` lines 5244–5330

Signals sit PENDING for ~11 minutes then expire. The approval path requires the signal's token:direction to be in `hotset_final`. When `hotset_final` is empty (due to score crush), no PENDING signal can be approved.

**Root cause:** Score crush empties the hotset → PENDING signals can't be approved → expire after 5 min.

**Recommendation:** This is a symptom, not a root cause. Fixing the score crush (item 2) will populate the hotset and allow PENDING signals to be approved.

### 6. BB Dead Zone Blocks SHORTs in Chop Zone
**File:** `signal_compactor.py` — SHORT_BB_DEAD_ZONE2

Blocks SHORT when bb_position is in [0.35, 0.55] (mid-band). SYRUP blocked at bb_position 0.3744 — barely inside the band.

**Recommendation:** Narrow the dead zone to [0.40, 0.50] — the current 0.35–0.55 band is too wide and blocks valid SHORTs in mild chop.

## Implementation Priority

| Priority | Change | Risk | Impact |
|----------|--------|------|--------|
| P0 | SHORT-RSI-HARD-FLOOR bear exemption | Medium | Unblocks 7/11 SHORT signals during dumps |
| P0 | Remove RR exemption from score floor | Medium | Fixes score crush, populates hotset |
| P1 | CONTINUUM-BLOCK oversold-bounce exemption | Low | Unblocks dip-buying LONGs in bear |
| P1 | HALL-SHAME momentum exemption | Low | Unblocks pumping tokens with low historical WR |
| P2 | BB dead zone narrowing | Low | Unblocks mild-chop SHORTs |

## Governance

- All changes default OFF (shadow mode) until 7-day data review
- Each change requires independent backtest + bug_hunter verification
- CEO approval required before enabling any flag
- Revert triggers defined per change

## Monitoring

- Track trade frequency (target: back to ~25/day)
- Track WR (target: maintain or improve ~50%)
- Track SHORT execution rate during dumps (target: >50% of approved SHORTs execute)
- Track hotset population rate (target: >0 tokens in hotset >50% of cycles)

## Files to Modify

1. `scripts/hermes_constants.py` — SHORT_RSI_HARD_FLOOR exemption flag
2. `scripts/signal_compactor.py` — RR floor exemption removal, CONTINUUM-BLOCK exemption, HALL-SHAME exemption, BB dead zone narrowing
3. `scripts/decider_run.py` — SHORT-RSI-HARD-FLOOR bear exemption (mirror existing ceiling exemption)
