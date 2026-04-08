# Plan: Wave Rider Backtest Engine

## Goal

Build a systematic backtest engine that tests all combinations of wave-based MACD entry/exit/sizing strategies against historical Hyperliquid candles (1h/4h/15m). Rank combinations by Sharpe/return/win-rate. Then wire the best configs into the live trading system.

---

## Data Available

| Table | Rows | Date Range |
|---|---|---|
| candles_4h | 3,000 | 2026-01-13 → 2026-04-06 |
| candles_1h | 3,000 | 2026-03-17 → 2026-04-06 |
| candles_15m | 3,001 | 2026-04-01 → 2026-04-06 |

Signals_hermes_runtime.db also has ~184M rows of signal history for learning.

---

## The Strategy Parameter Space

### Entry Gates (test ALL combinations)

**Direction trigger (which TF first signals):**
- 15m_only: Enter when 15m MACD fires first
- 1h_only: Enter when 1h MACD fires first
- 4h_only: Enter when 4h MACD fires first
- 15m+1h_confirm: Enter when both 15m AND 1h agree
- 15m+4h_confirm: Enter when both 15m AND 4h agree
- 1h+4h_confirm: Enter when both 1h AND 4h agree
- all_three: Enter when all three TFs agree

**Direction:** LONG or SHORT

**Wave filter (entry only allowed when wave >= N):**
- wave >= 1 (any — baseline)
- wave >= 2 (at least 2nd correction)
- wave >= 3 (deep correction — reversal zone)
- wave >= 4 (tired trend — high risk/reward reversal)

**Velocity filter:**
- vel > 0 (any positive — momentum building)
- vel >= 0.05 (moderate momentum)
- vel >= 0.15 (strong momentum)
- vel >= 0.30 (very strong momentum)
- vel >= 0 AND hist_rate > 0 (momentum + acceleration both confirming)
- vel >= 0 AND hist_rate > 0 AND wave >= 2 (triple confirmation)

**For SHORT reversal entries specifically:**
- vel < 0 (velocity negative — MACD line turning down)
- vel <= -0.05 (moderate down)
- vel <= -0.15 (strong down)
- vel DECREASING: current_vel < prev_vel (accelerating into the short)
- vel FLAT/FLAT-NEGATIVE: |vel| < 0.03 AND vel < 0 (stalled momentum = reversal coming)
- vel FLAT then negative: prev_vel > -0.03 AND curr_vel < -0.05 (stall-then-drop = ideal reversal pattern)

**Crossover freshness:**
- FRESH_required: crossover_age <= 2 candles
- STALE_allowed: any age
- STALE_only: crossover_age > 2 (mean-reversion on old crosses)

**Wave reversals (key concept — what T wants):**
- Entry when: wave >= 2 AND velocity is DECREASING (stalling/flipping) = wave exhaustion = reversal
- For SHORT: MACD line velocity decreasing/flattening = 4H bull wave running out of steam → ride the bear wave down
- For LONG: MACD line velocity decreasing/flattening = 4H bear wave running out of steam → ride the bull wave up

### Position Sizing

**Wave-based size:**
- wave=1: size_mult = 1.0 (fresh trend, full size)
- wave=2: size_mult = 0.75 (correction, slightly smaller)
- wave=3: size_mult = 0.50 (deep correction)
- wave=4+: size_mult = 0.25 (tired trend, small or skip)

**Velocity-based size boost:**
- vel > 0.30: boost size by +25%
- vel > 0.15: boost by +15%
- vel < -0.20 (for shorts): boost by +20% (strong bearish momentum)
- vel decreasing into entry (stalling): reduce by -30% (reversal risky)

**Combined size formula:**
```
size_mult = wave_mult * velocity_mult * base_size
```

### Exit Rules (test each independently AND in combination)

**Exit on wave exhaustion:**
- exit when wave >= 4 (trend exhausted, reversal likely)
- exit when wave >= 3 AND velocity < threshold

**Exit on velocity reversal:**
- LONG exit: macd_line_velocity crosses below 0 (momentum broken)
- LONG exit: macd_line_velocity decreases by > 50% in one candle (momentum fading fast)
- SHORT exit: macd_line_velocity crosses above 0
- SHORT exit: |velocity| decreases by > 50% in one candle (bear momentum fading)

**Exit on histogram reversal:**
- hist_rate flips against position
- hist crosses zero

**Time-based exit:**
- exit after N candles (wave-based time target)
  - wave=1: hold 4-8 candles
  - wave=2: hold 8-16 candles
  - wave=3: hold 16-32 candles
  - wave=4: hold until reversal signal, max 48 candles

**Stop loss:**
- 1.5% hard stop
- 2.0% hard stop
- 1.5x ATR stop
- 2.0x ATR stop
- No stop (run to reversal signal)

**Take profit:**
- 2:1 RR
- 3:1 RR
- Trailing stop (swing low/high)
- Wave-4 exit (take profit when wave reaches 4)

---

## The Bidirectional Wave Rider Strategy (Core Design)

The cascade trade plan is a **permanent bidirectional oscillator** — it never commits to one direction. It rides waves in both directions, reversing at exhaustion points:

```
Bull wave (4H MACD > 0, regime = BULL):
  - Velocity INCREASING → hold LONG / add
  - Velocity PEAKING → exit LONG, prepare to reverse
  - Velocity DECREASING/stalling → ENTER SHORT (ride bear wave down)

Bear wave (4H MACD < 0, regime = BEAR):
  - Velocity INCREASING (becoming more negative) → hold SHORT / add
  - Velocity PEAKING (becoming less negative) → exit SHORT, prepare to reverse
  - Velocity DECREASING/stalling → ENTER LONG (ride bull wave up)
```

**The "Stall-Then-Drop" pattern (for SHORT entries):**
```
prev_vel = +0.15  (momentum still bullish, wave 3 building)
curr_vel = -0.05  (momentum just flipped — wave 3 exhausted, wave 4 beginning)

→ ENTER SHORT immediately as bear wave starts
```

**The "Stall-Then-Rise" pattern (for LONG entries):**
```
prev_vel = -0.15  (momentum still bearish, wave 3 building)
curr_vel = +0.05  (momentum just flipped — wave 3 exhausted, wave 4 beginning)

→ ENTER LONG immediately as bull wave starts
```

**Key insight:** The reversal is highest probability when:
1. Wave >= 3 (the trend is tired, not fresh)
2. Velocity flips sign (momentum engine has shifted direction)
3. Histogram rate confirms (acceleration in the new direction)
4. 4H regime is opposite to your entry (you're catching the new wave, not fading it)

### Universal Entry Rules (test both directions)

**SHORT entry triggers:**
```
vel < 0 AND wave >= 2 AND 4h_regime != BULL   → stall-then-drop short
vel DECREASING AND hist_rate < 0 AND wave >= 3 → momentum fading, short
vel < prev_vel AND |vel| > 0.10 AND wave >= 3  → velocity acceleration into short
```

**LONG entry triggers (mirror):**
```
vel > 0 AND wave >= 2 AND 4h_regime != BEAR   → stall-then-rise long
vel INCREASING AND hist_rate > 0 AND wave >= 3  → momentum building, long
vel > prev_vel AND |vel| > 0.10 AND wave >= 3   → velocity acceleration into long
```

### Universal Exit Rules

For LONGs:
- vel crosses below 0 (bull momentum broken → reverse to SHORT)
- vel decreases by >50% in one candle (momentum fading fast)
- wave >= 4 (trend exhausted → take profit, reverse)

For SHORTs:
- vel crosses above 0 (bear momentum broken → reverse to LONG)
- |vel| decreases by >50% in one candle (bear momentum fading)
- wave >= 4 (trend exhausted → take profit, reverse)

---

## Backtest Engine Architecture

```
scripts/
  wave_backtest.py          # Main backtest runner
  wave_strategies.py        # Strategy definitions (param combos)
  wave_results.db           # SQLite: stores all test results
  wave_dashboard.py         # Streamlit UI for results
```

### wave_backtest.py

```python
# Pseudocode
for token in TOP_TOKENS:
    load_1h_candles(token)   # 3,000 rows
    load_4h_candles(token)
    load_15m_candles(token)

    # Align all TFs to same timestamps
    for i in range(max(len(1h), len(4h))):
        compute macd_state for 1h, 4h at i
        extract wave_number, velocity for each

        for strategy in ALL_STRATEGY_COMBOS:
            if strategy.entry_condition_met(state_15m, state_1h, state_4h):
                entry_price = close[i]
                direction = strategy.direction
                size = strategy.size_mult(state_1h, state_4h)
                sl = strategy.stop_loss(entry_price, atr)
                tp = strategy.take_profit(entry_price)

                # Simulate trade
                for j in range(i+1, min(i+MAX_HOLD, len_data)):
                    exit_if = (
                        strategy.exit_condition_met(state_at_j) OR
                        price_hits_sl OR
                        price_hits_tp OR
                        candle_count_exceeded
                    )
                    if exit_if:
                        record_trade_result(strategy, pnl, hold_time, exit_reason)
                        break
```
```
### Strategy Count

```
Entry triggers: 7 (15m_only, 1h_only, 4h_only, 15m+1h, 15m+4h, 1h+4h, all_three)
Wave filters: 4 (wave >= 1, >= 2, >= 3, >= 4)
Velocity filters: 7 (see below)
Crossover freshness: 3 (FRESH, STALE, ANY)
Exit rules: 6 combinations
Stop loss: 4 options
Take profit: 4 options
Failure mode guards: 6 options (see below)

Total combos: 7 × 4 × 7 × 3 × 6 × 4 × 4 × 6 = 677,376 configs
```

The failure mode guards are the most important additions — they directly test whether the safeguards above actually help:

**Failure Mode Guard Options:**
1. `none` — no guard, pure wave count only
2. `extended_wave_block` — wave >= 5 AND |vel| > 0.15 → go flat, no reverse
3. `regime_required_for_reverse` — reverse only if 4H regime also flips (stronger signal than vel alone)
4. `no_double_reverse` — after failed reversal, require fresh signal before re-entering
5. `chop_cooldown_2` — after 2 consecutive losses, skip next 5 signals
6. `triple_confirm` — reverse requires vel AND hist_rate AND (wave>=4 OR regime) all confirming
7. `all_guards` — combine all of the above

We expect `all_guards` and `triple_confirm` to have higher win rates but fewer total trades. `none` will have the most trades but worst win rate. The sweet spot is whichever gives the best risk-adjusted return (Sharpe), not just win rate.

**Velocity filter variations (7 combos):**
1. `vel > 0` — any positive momentum
2. `vel >= 0.05` — moderate positive
3. `vel >= 0.15` — strong positive
4. `vel >= 0.30` — very strong
5. `vel > prev_vel` — velocity increasing (momentum building)
6. `vel < prev_vel` — velocity decreasing (momentum waning)
7. `stall_then_flip: |prev_vel| < 0.03 AND curr_vel > 0.05` — stall-then-rise (long entry) / `|prev_vel| < 0.03 AND curr_vel < -0.05` — stall-then-drop (short entry)

For short entries the signs flip: `vel < 0`, `vel <= -0.05`, `vel <= -0.15`, `vel < prev_vel` (more negative = accelerating down), `stall_then_drop`.

With 5 tokens × 3 timeframes = 15 data series, that's ~1.7M trade simulations. Filter down to high-signal combos first.

### Phase 1: Parameter Space Reduction

Run coarse grid first (step size 3 for velocity, wave 1/3 only, single TF confirm):
- ~500 configs per token → ~7,500 simulations
- Top 50 configs per metric → refine grid around those

---

## Position Management During a Wave

One of the most important decisions: **do you add to a winning position or just hold?**

**Wave scaling strategies to test:**

1. **Full position at entry, no adds** — simplest, baseline
2. **Add on wave confirmation**: Add 0.5x more when wave >= 2 AND velocity confirms (e.g., vel > 0.10 on a long)
3. **Add on velocity acceleration**: If already in position and vel increases by >30% in one candle, add 0.25x more
4. **Scale OUT as wave ages**: Reduce size as wave goes from 2→3→4 (take profit off the table progressively)
   - wave=1: 1.0x
   - wave=2: 0.75x
   - wave=3: 0.50x
   - wave=4: 0.25x or exit entirely

5. **Add on reversal entries only**: Only full size when entering at a velocity reversal (stall-then-flip), smaller size when catching a fresh wave

**Stop loss management:**
- Hard SL at entry ( ATR-based) — don't adjust
- Trailing SL: once in profit by 1.5x SL distance, move SL to breakeven
- SL tightens as wave ages: wave=2 → SL at entry, wave=3 → SL at 0.5% profit, wave=4 → take what you have

---

## Quick BTC 4H Validation Test (Before Full Grid)

## Quick BTC 4H Validation Test (Before Full Grid) ✅ DONE

Ran: 2026-04-07 01:15 UTC
Results: See `/root/.hermes/brain/wave-backtest-results.md`

Key finding: **Momentum continuation works better than pure reversal trading.**

| Config | N | WR | Sharpe |
|---|---|---|---|
| BTC 4H wave>=2 decreasing, vel_flip | 5 | 60% | +10.96 |
| BTC 4H wave>=2 any, vel_flip | 16 | 50% | +4.15 |
| BTC 4H wave>=1 any, vel_flip | 134 | 37% | -0.47 |
| ETH 4H wave>=2 any, vel_flip | 13 | 23% | +0.15 |

**Stall-then-flip thesis:** Partial confirmation. The pattern fires but wave>=3 almost never appears on 4H BTC. Strategy must use wave>=2 as the minimum.

**Next:** Run on 1H and 15m data for more statistical power.

---

### Phase 3: Fine-Grained Search

Run full grid around top 20 coarse configs:
- Velocity thresholds: 0.01, 0.03, 0.05, 0.08, 0.12, 0.15, 0.20, 0.25, 0.30
- Wave thresholds: 1, 2, 3, 4
- Full exit rule combos

### Phase 3: Multi-token validation

Validate top 10 configs across all 20+ tokens in DB. Config must hold up across tokens, not just backtest well on one.

---

## Metrics to Track Per Config

| Metric | Description |
|---|---|
| total_trades | Count |
| win_rate | % winners |
| avg_pnl_pct | Mean % return per trade |
| sharpe_ratio | Return / std dev |
| max_drawdown | Worst peak-to-trough |
| avg_hold_time | candles held |
| reversal_count | Times we reversed direction (vs just stopping out) |
| reversal_win_rate | % wins on reversal trades specifically |
| avg_reversal_pnl | Mean % return on reversals only |
| exit_wave_exhaustion | % exits from wave=4 (trend exhausted) |
| exit_velocity_reversal | % exits from vel flip (momentum broken) |
| exit_stop_loss | % SL hits |
| exit_take_profit | % TP hits |
| longs_won / shorts_won | Directional breakdown |
| avg_vel_at_entry | Mean velocity when we entered (confirms stall-then-drop works) |
| avg_wave_at_entry | Mean wave number when we entered (confirms wave>=3 is sweet spot) |
| max_consecutive_reversals | Max back-to-back reversals without a stop loss |
| wrong_reversal_count | Times we reversed and got stopped (misread the wave) |
| avg_loss_wrong_reversal | Mean loss on wrong reversals specifically |
| extended_wave_skipped | Times wave>=5 blocked a reverse (extended wave guard fired) |
| chop_cooldown_triggered | Times chop cooldown fired (skipped signals due to chop) |
| regime_flip_required | Times regime didn't flip, prevented a reverse (regime guard fired) |

---

## Wave Rider Risk Model — Failure Modes and Safeguards

The wave counter is probabilistic, not deterministic. Waves extend (5-7 waves happen), corrections fake as reversals, and the counter itself can be wrong. The strategy MUST have explicit protections.

### Failure Mode 1: Extended Waves (5, 6, 7)
**What happens:** You reverse at wave 4 thinking trend is exhausted. Wave 5 extends violently in the original direction. You get run over on a massive move.

**Real example:** Bitcoin's 2021 bull run had extended waves. Anyone who sold the "wave 4" dip in March got demolished by wave 5 to 69k.

**Safeguard to test:**
- If wave >= 5 AND |vel| > 0.15: **DO NOT reverse**. Take profit (or loss), go flat. The trend is extended — don't fight it.
- If wave >= 5 AND |vel| < 0.10: Wave is tired, consider exit + flat (not reverse).

### Failure Mode 2: ABC Corrections Faking as 5-Wave Impulses
**What happens:** Price drops 15%, you think wave 4 finished. You reverse to LONG. But it was actually wave A down, you're in wave B retrace, and wave C takes price even lower.

**Safeguard:** Reverse only when **BOTH** velocity flips AND the 4H regime flips (not velocity alone). Regime flip is a stronger signal — it requires MACD line to actually cross zero, which takes more than a vel flicker.

### Failure Mode 3: Misread Wave Counter Entirely
**What happens:** We think we're in wave 3, actually we're in wave 1 of a new trend. We reverse too early and miss the real move.

**Safeguard:** Hard ATR stop always. Wrong = limited damage. Don't average down on a misread.

### Failure Mode 4: Wrong Reversal — Original Direction Resumes Immediately
**What happens:** We reverse SHORT. Price rips higher 2% in 4 candles. That was still wave 3 momentum. We were wrong.

**Safeguard — no double-reverse:**
- If stopped out AND vel has NOT confirmed our reversal (vel is now POSITIVE again), the original wave is STRONGER than we thought
- Go flat, don't re-reverse until velocity flips back AND wave >= 3 again
- This prevents: reverse → stop → reverse again → stop again = cascading losses

### Failure Mode 5: Choppy Market — Wave Rider Gets Whipsawed
**What happens:** Market chops sideways. Every small vel flip triggers a reversal. We lose 5 in a row paying spread + SL on each.

**Safeguard — chop cooldown:**
- After 2 consecutive failed reversals: skip next 5 reversal signals
- After 3 consecutive failed reversals: skip next 10 signals + alert (something structural changed)
- If reversal win rate over last 10 reversals < 40%: pause strategy

### Failure Mode 6: Strong Momentum Doesn't Confirm Velocity
**What happens:** vel is dropping (momentum waning) but histogram_rate is still strongly positive. Price keeps running. vel is lying.

**Safeguard — triple confirmation for reversals:**
- Reverse requires: vel_flip AND hist_rate flips AND (wave >= 4 OR regime_flip)
- If only vel flips but hist_rate and regime still confirm original direction: skip reversal

### Failure Mode 7: Position Scaled Wrong on Failed Reversal
**What happens:** You add to a losing reversal position. It gets worse. Margin call.

**Safeguard:** Never add to a position that has moved against you. Only add when the position is in profit. A failed reversal = exit completely, not average down.

---

## Position Management Rules (Test Each)

| Rule | Behavior |
|---|---|
| `no_scale_on_loss` | Never add to a losing position. Only add when in profit. |
| `scale_on_wave_confirm` | Add 0.5x when wave confirms your direction (wave goes from 2→3 while in profit) |
| `scale_on_vel_accel` | Add 0.25x if vel accelerates >30% in one candle while in profit |
| `scale_out_aging_wave` | Reduce size as wave 2→3→4 (take profit on the table progressively) |
| `trailing_sl_breakeven` | Once in profit by 1.5× SL distance, move SL to breakeven |
| `no_reverse_after_stop` | After failed reversal, require fresh signal before re-entering |

---

## Quick BTC 4H Validation Test (Before Full Grid)

```sql
CREATE TABLE wave_results (
    id INTEGER PRIMARY KEY,
    token TEXT,
    strategy_hash TEXT,    -- encoded strategy params (no direction — bidirectional)
    entry_trigger TEXT,   -- '15m_only','1h+4h_confirm',etc
    wave_min INTEGER,
    velocity_pattern TEXT, -- 'decreasing','stall_then_flip','any_pos','increasing',etc
    crossover_fresh TEXT, -- 'FRESH','STALE','ANY'
    exit_rule TEXT,       -- 'wave4','vel_flip','trailing',etc
    stop_loss_pct REAL,
    take_profit_rr REAL,
    -- results
    total_trades INTEGER,
    win_rate REAL,
    avg_pnl_pct REAL,
    sharpe REAL,
    max_dd REAL,
    avg_hold_candles REAL,
    reversal_count INTEGER,
    reversal_win_rate REAL,
    avg_reversal_pnl REAL,
    longs_won INTEGER,
    shorts_won INTEGER,
    avg_vel_at_entry REAL,
    avg_wave_at_entry REAL,
    exit_wave4_pct REAL,
    exit_vel_flip_pct REAL,
    exit_sl_pct REAL,
    exit_tp_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token ON wave_results(token);
CREATE INDEX idx_sharpe ON wave_results(sharpe DESC);
CREATE INDEX idx_reversal_wr ON wave_results(reversal_win_rate DESC);
```

---

## Dashboard (Streamlit)

```
wave_dashboard.py
Port: 54321/nginx location: /wave
```

Features:
1. **Top strategies table** — sortable by any metric
2. **Equity curve** — plot of best strategy over time
3. **Parameter sensitivity charts** — e.g., win_rate vs wave_threshold (should show wave=2-3 sweet spot)
4. **Velocity threshold curve** — win_rate vs vel_threshold (finds optimal velocity cutoffs)
5. **Confusion matrix** — which exit rules fire most often vs expected
6. **Multi-token heatmap** — does strategy work across tokens or just BTC?
7. **Live config export** — click "deploy" to write best config to ai_decider constants

**Reference:** `/root/.hermes/brain/wave-backtest-results.md` — full results, token analysis, and next steps

---

## Implementation Steps

### Step 1: Quick BTC 4H Validation (30 sec)
Write and run a single strategy test on BTC 4H to confirm the core stall-then-flip thesis works before investing in the full grid. If it shows promise (~55%+ win rate on reversals, positive Sharpe), proceed.

### Step 2: Build wave_strategies.py (strategy definitions)
Define the Strategy dataclass with all parameters, and the exhaustive param grid. Include the bidirectional reversal tracker (distinguish "reversal" exits from "stop loss" exits).

### Step 3: Build wave_backtest.py (core engine)
Extract candles from candles.db, compute MACD/wave/vel for each TF, run all strategy simulations, write to wave_results.db. Include position management (adds, scaling out, trailing SL).

### Step 4: Run coarse grid
Run on top 5 tokens (BTC, ETH, SOL, LINK, AAVE) across all timeframes.
Expect: ~2-4 hours runtime for 112K combos.

### Step 5: Build wave_dashboard.py
Streamlit dashboard reading from wave_results.db. Sortable by reversal_win_rate, sharpe, avg_reversal_pnl. The "reverse win rate" is the key metric — it's the win rate specifically on the velocity reversal entries (the core of T's strategy).

### Step 6: Refine + multi-token validate
Fine-grained search around top configs. Top configs must work across at least 4/5 tokens — no overfitting to BTC alone.

### Step 7: Wire into signal_gen.py — "WAVE_REVERSAL" signal type
The wave rider is a **swing signal**: it carries its own entry AND exit rules. It doesn't just say LONG, it says:
```
{
  "signal_type": "WAVE_REVERSAL",
  "direction": "SHORT",
  "entry_trigger": "stall_then_drop",
  "wave_number": 3,
  "velocity": -0.08,
  "entry_reason": "4h bull momentum exhausted, vel flipped negative",
  "exit_rule": "vel_flip OR wave4 OR trailing_stop",
  "size_mult": 0.50,
  "atr_stop": 1.5
}
```
This gets written to the signals DB just like any other signal type. The ai_decider and decider-run already know how to handle signals with embedded metadata.

### Step 8: Add to ai_decider hot-set
The WAVE_REVERSAL signals compete with other signal types for hot-set entry. The hot-set already has wave_phase and is_overextended — wire in the full wave_number and velocity so decider-run can see them.

### Step 9: Live paper trading validation
Run the winning wave_reversal config in paper mode for 2 weeks before going live. Track reversal_win_rate live vs backtest — if they're within 10%, the signal is robust.

---

## Key Files to Create

| File | Purpose |
|---|---|
| `/root/.hermes/scripts/wave_strategies.py` | Strategy dataclass + param grid |
| `/root/.hermes/scripts/wave_backtest.py` | Core backtest engine |
| `/root/.hermes/scripts/wave_dashboard.py` | Streamlit results dashboard |
| `/root/.hermes/data/wave_results.db` | SQLite with all results |
| `/root/.hermes/data/wave_candidates.json` | Top N configs for review |

---

## Critical: The "Stall Then Drop" Pattern

The most important velocity pattern for T's goal:

```
prev_vel = +0.15  (momentum still bullish)
curr_vel = -0.05  (momentum just flipped negative)

= STALL-THEN-DROP = highest probability short entry
```

Why: The MACD line was charging up, suddenly stalls (velocity near 0), then breaks down. This is the classic "wave 3 → wave 4 exhaustion" pattern. Price typically drops hard on this because:
1. Wave 3 had strong momentum behind it
2. Wave 4 is the correction
3. The velocity flip confirms wave 3 is done and wave 4 (bear) has begun

Code to detect:
```python
def stall_then_drop(prev_vel, curr_vel, stall_thresh=0.03, drop_thresh=-0.05):
    was_stalling = abs(prev_vel) < stall_thresh or prev_vel > -stall_thresh
    dropped = curr_vel < drop_thresh
    return was_stalling and dropped

def stall_then_rise(prev_vel, curr_vel):
    was_stalling = abs(prev_vel) < 0.03
    rose = curr_vel > 0.05
    return was_stalling and rose
```

Also important: **velocity DECREASING** even if still positive (e.g., +0.20 → +0.05) = momentum waning = reversal risk. The rate of velocity change matters as much as absolute value.
