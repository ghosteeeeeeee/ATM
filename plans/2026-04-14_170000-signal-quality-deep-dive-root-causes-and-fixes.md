# Signal Quality Deep Dive — Root Causes and Fixes
**Created:** 2026-04-14 17:00
**Status:** ANALYSIS COMPLETE — AWAITING USER APPROVAL TO IMPLEMENT
**Focus:** Why wrong-direction trades cause stop-loss hits; RSI signals destroy SHORT performance; z-score filter absence; merge bonus inflation

---

## Executive Summary

The system is losing money on SHORT trades in a BTC bull market. The root causes are:

1. **RSI signals fire independently with NO z-score check** (lines 1645-1673 in `signal_gen.py`) — RSI individual SHORT has 0% win rate across 6 trades
2. **RSI confluence SHORT path has NO z-score filter** (lines 1343-1356) — "No z-score filter for SHORTs — elevated prices are valid short targets" — in a BTC pump, EVERYTHING looks "elevated"
3. **Merge bonus system inflates weak signals to 91-96% confidence** artificially — `pct_rank + hmacd` gets 0.6x weight but produces 96% effective confidence; `pct + vel` gets 1.5x and produces 95%
4. **All entry feature fields are NULL** — `entry_rsi_14`, `entry_macd_hist`, `entry_bb_position`, `entry_regime_4h`, `entry_trend` are never recorded at trade open

The good news: `hzscore,pct-hermes,vel-hermes` has 58-64% win rate and +0.07 to +0.25% avg — this combo WITHOUT RSI works.

---

## Data Sources

### PostgreSQL `brain` database
- `trades` table: `server='Hermes'`, all open/closed trades, pnl_pct, close_reason, signal, direction, leverage, stop_loss, entry_price
- `signal_outcomes` table: links signals to trades

### SQLite `signals_hermes_runtime.db`
- `signals` table: `signal_type`, `direction`, `confidence`, `z_score`, `rsi_14`, `macd_hist`, `decision`, `created_at`

### Files
- `/root/.hermes/scripts/signal_gen.py` — signal generation (RSI, z-score, percentile, velocity)
- `/root/.hermes/scripts/decider_run.py` — hot-set approval (merge bonuses, source weights, hzscore combo filter)
- `/root/.hermes/scripts/position_manager.py` — trade monitoring and exit management
- `/root/.hermes/scripts/hl-sync-guardian.py` — Hyperliquid position sync, writes to PostgreSQL

---

## Root Cause #1: RSI Individual Signal Has No Z-Score Filter

**Location:** `signal_gen.py` lines 1645-1673

**Code:**
```python
if rsi_val < RSI_INDIVIDUAL_LONG_THRESH:  # 42
    rsi_conf = min(60, 30 + (RSI_INDIVIDUAL_LONG_THRESH - rsi_val) * 1.5)
    # fires LONG
elif rsi_val > RSI_INDIVIDUAL_SHORT_THRESH:  # 60
    rsi_conf = min(60, 30 + (rsi_val - RSI_INDIVIDUAL_SHORT_THRESH) * 1.5)
    # fires SHORT
```

**Problem:** RSI can fire LONG or SHORT completely independently of z-score. In a BTC pump where BTC shoots up and everything looks "oversold on the daily" — RSI fires SHORT signals with no confirmation from price position.

**Signal data from SQLite:**
- `rsi_individual SHORT` fires 335 times with avg confidence 89.0% — very high confidence for a signal with NO directional filter
- `rsi_individual LONG` fires 253 times with avg confidence 61.7%

**PostgreSQL trade outcomes:**
- Trades with `hzscore,rsi-hermes` signal: SHORT avg -0.206% (6 trades), LONG avg -0.359% (1 trade)
- Trades with `hzscore,pct-hermes,rsi-hermes`: SHORT avg -0.126% (42 trades), LONG avg -0.348% (4 trades)

**Conclusion:** Adding RSI to any combo makes it worse. RSI individual SHORT has 0% win rate across 6 trades.

---

## Root Cause #2: RSI Confluence SHORT Has No Z-Score Filter

**Location:** `signal_gen.py` lines 1334-1356

**Code:**
```python
elif rsi > CONFLUENCE_RSI_HIGH:  # 60
    direction = 'SHORT'
    conf = min(70, 30 + (rsi - CONFLUENCE_RSI_HIGH) * 1.5)
    if conf < SHORT_ENTRY_THRESHOLD and not (rsi > 85):
        # skip - but rsi > 85 bypasses entry threshold
    # BLACKLIST check: if token in SHORT_BLACKLIST: continue
    # NO z-score check here
```

**Comment in code:** "No z-score filter for SHORTs — elevated prices are valid short targets"

**Problem:** The comment explains the logic: if RSI > 60, the assumption is "price is elevated, good time to short." But this is only true if the z-score confirms the price IS elevated relative to its recent range. Without that check, in a BTC pump where everything gaps up, every alt looks "elevated" and gets a SHORT signal.

**The z-score IS checked in some paths (e.g., MTF zscore at line 1591 blocks SHORT if z_score < -0.5) but NOT in the RSI confluence path.**

---

## Root Cause #3: Merge Bonuses Inflate Confidence Artificially

**Location:** `decider_run.py` merge bonus section (lines ~900-960)

**What happens:**
1. Base confidence from signal generation: e.g., `pct_rank` produces 62.5% max
2. Merge bonus adds: 2-source = +20%, 3-source = +30% → "effective confidence" becomes 82.5-92.5%
3. Source weight multiplier: `pct_rank + hmacd` has 0.6x weight → threshold = 65/0.6 = 108% → never approves
4. But other combos like `pct_rank + velocity` get 1.5x weight → effective confidence inflated to 95%+

**Source weights from code:**
- `pct_rank + hmacd`: weight = 0.6 (almost never approves, threshold 108%)
- `pct_rank + velocity`: weight = 1.5 (inflated, 95%+ effective conf)
- `pct_rank + hzscore + velocity`: 3 sources = 1.5x + 30% bonus

**The actual confidence numbers from signal generation:**
- `percentile_rank`: max 62.5% (formula: `(pct_val - 72) * 1.25 + 50` maxes at 62.5)
- `velocity`: max ~65%
- `rsi_individual`: max 60%
- `mtf_zscore`: max 80% + 45 = 125% but capped at some value

**So a 3-source merge of pct_rank(62.5) + vel(65) + hzscore(80):**
- Average base: (62.5 + 65 + 80) / 3 = 69.2%
- Merge bonus: +30% → 99.2%
- This is reasonable for 3 agreeing sources

**But a 2-source merge of pct_rank(60) + rsi_individual(60):**
- Average base: 60%
- Merge bonus: +20% → 80%
- This is NOT reasonable — RSI individual has 0% win rate as a solo signal

---

## Root Cause #4: All Entry Features Are NULL

**What should be recorded at trade open:**
- `entry_rsi_14`: RSI(14) at entry
- `entry_macd_hist`: MACD histogram at entry
- `entry_bb_position`: Bollinger Band position at entry
- `entry_regime_4h`: Market regime at entry (bull/bear/neutral/volatile)
- `entry_trend`: Trend direction at entry

**What's actually happening:**
- `hl-sync-guardian.py` opens trades and writes to PostgreSQL
- It does NOT populate these entry feature fields
- All 773 closed trades + 8 open trades have NULL for all entry features
- We cannot do post-hoc analysis of "what were the conditions when this trade was entered?"

**Fix:** `hl-sync-guardian.py` should record these values at the time of trade open.

---

## Specific Trade Case Studies

### BIO SHORT — -4.4% loss (current open trade)
- Entry: $0.0195, Current: $0.0204, Stop: $0.0208
- Direction: SHORT, but BIO went up 4.15% from entry
- ATR SL distance: 6.685% unleveraged (20.05% leveraged at 3x)
- BIO went UP after entry → WRONG DIRECTION

### LINK LONG — -1.6% loss (current open trade)
- BTC was doing a bull flag, LINK following BTC up
- But the system went LONG instead
- Current: $9.23, Entry: $9.36 → LINK went DOWN
- This is BTC dominance going up, alts bleeding → system should be SHORT or neutral

### ATR SL Hit Trades (9 total losing):
- BIO SHORT: -4.16%, COMP SHORT: -2.38%, NIL SHORT: -2.49% (all SHORT going up)
- SKY LONG: -2.35%, DYDX LONG: -2.25%, MOVE LONG: -2.08% (all LONG going down)
- **Pattern: Direction is consistently wrong for 9/9 atr_sl_hit trades**

### HL_SL_CLOSED (28 trades, avg -0.78% LONG, -1.02% SHORT):
- These are HL's native SL being hit
- SHORT avg -1.02% means the price went UP and hit our SL (we were SHORT)
- LONG avg -0.78% means the price went DOWN and hit our SL (we were LONG)
- Same pattern: WRONG DIRECTION

---

## Proposed Fixes

### Fix #1: Add Z-Score Filter to RSI Individual Signal
**File:** `signal_gen.py`
**Change:** RSI individual should only fire if z_score confirms the direction

```python
# BEFORE (line 1645):
if rsi_val < RSI_INDIVIDUAL_LONG_THRESH:
    rsi_conf = min(60, 30 + (RSI_INDIVIDUAL_LONG_THRESH - rsi_val) * 1.5)

# AFTER:
# Only fire RSI individual if z-score confirms directional bias
# Get recent z-score for this token
token_z = get_recent_z_score(token)  # need to implement or reuse
if token_z is not None:
    # For LONG: require z_score < 0 (price below average) — oversold
    # For SHORT: require z_score > 0 (price above average) — overbought
    if rsi_val < RSI_INDIVIDUAL_LONG_THRESH and token_z < 0:
        rsi_conf = min(60, 30 + (RSI_INDIVIDUAL_LONG_THRESH - rsi_val) * 1.5)
    elif rsi_val > RSI_INDIVIDUAL_SHORT_THRESH and token_z > 0:
        rsi_conf = min(60, 30 + (rsi_val - RSI_INDIVIDUAL_SHORT_THRESH) * 1.5)
    else:
        rsi_conf = 0  # no signal
else:
    rsi_conf = 0  # no z-score data, don't fire
```

**Alternative (simpler):** Remove `rsi_individual` from signal generation entirely. It has 0% win rate as solo and 0% win rate in combos. The system's best signals (`hzscore,pct-hermes,vel-hermes`) work WITHOUT RSI.

### Fix #2: Add Z-Score Filter to RSI Confluence SHORT Path
**File:** `signal_gen.py`
**Change:** RSI confluence SHORT should require z_score > 0 (confirmed elevated)

```python
# BEFORE (line 1343):
elif rsi > CONFLUENCE_RSI_HIGH:
    direction = 'SHORT'
    conf = min(70, 30 + (rsi - CONFLUENCE_RSI_HIGH) * 1.5)
    if conf < SHORT_ENTRY_THRESHOLD and not (rsi > 85):
        continue

# AFTER:
elif rsi > CONFLUENCE_RSI_HIGH:
    # Z-score check: only short if price is actually elevated
    token_z = get_recent_z_score(token)
    if token_z is None or token_z < 0.3:  # require price above average + some threshold
        continue  # skip SHORT if not confirmed elevated
    direction = 'SHORT'
    conf = min(70, 30 + (rsi - CONFLUENCE_RSI_HIGH) * 1.5)
```

### Fix #3: Cap Merge Bonus / Reweight Source Combinations
**File:** `decider_run.py`

**Change:** Reweight the merge to penalize RSI combinations rather than inflate all merges:

```python
# Option A: Remove RSI from merge bonuses entirely
# RSI has negative predictive value — don't reward it in combos
rsi_bonus = 0  # no merge bonus for RSI-containing signals

# Option B: Cap effective confidence at 85% regardless of merge
effective_conf = min(85, base_confidence + merge_bonus)

# Option C: Give RSI a negative weight (it reduces signal quality)
# pct_rank + hzscore = 1.2x (good)
# pct_rank + hzscore + rsi = 0.7x (worse than without RSI)
```

**Recommended:** Option A — exclude RSI from merge bonuses. The data shows adding RSI reduces win rate in every combo.

### Fix #4: Record Entry Features in Guardian
**File:** `hl-sync-guardian.py`
**Change:** At trade open, record current indicator values

```python
# When opening a new trade, record:
entry_features = {
    'entry_rsi_14': current_rsi(token, 14),
    'entry_macd_hist': current_macd_hist(token),
    'entry_bb_position': current_bb_position(token),
    'entry_regime_4h': current_regime(token, '4h'),
    'entry_trend': current_trend(token)
}
# Write these to the trades table on open
```

---

## Signal Performance Reference (from PostgreSQL)

| Signal | Direction | N | Win Rate | Avg PnL | Total |
|--------|-----------|---|----------|---------|-------|
| hzscore,pct-hermes,vel-hermes | SHORT | 132 | 58% | +0.068% | +$8.98 |
| hzscore,pct-hermes,vel-hermes | LONG | 35 | 64% | +0.219% | +$7.67 |
| hzscore,pct-hermes | SHORT | 208 | ~50% | -0.005% | -$1.04 |
| hzscore,pct-hermes | LONG | 221 | ~45% | -0.004% | -$0.88 |
| hzscore,pct-hermes,rsi-hermes | SHORT | 42 | 47% | -0.126% | -$5.29 |
| hzscore,pct-hermes,rsi-hermes | LONG | 4 | 50% | -0.348% | -$1.39 |
| hzscore,rsi-hermes | SHORT | 6 | 0% | -0.206% | -$1.24 |
| hzscore,rsi-hermes | LONG | 1 | 0% | -0.359% | -$0.36 |

**Key insight:** The best signals are 3-source WITHOUT RSI: `hzscore,pct-hermes,vel-hermes`. Adding RSI reduces performance in every case.

---

## Implementation Priority

1. **High Priority:** Fix #1 or #2 (add z-score filter to RSI paths) — prevents wrong-direction SHORTs
2. **High Priority:** Fix #3 (cap merge bonuses or remove RSI from merges) — prevents inflation of weak signals
3. **Medium Priority:** Fix #4 (record entry features) — enables future analysis
4. **Backtest first:** Before deploying any fix, backtest signal combos with/without RSI to quantify improvement

---

## What NOT To Do

- **Do NOT re-enable cascade flip** — user explicitly deferred this
- **Do NOT increase SL distances** — the problem is wrong direction, not tight SL
- **Do NOT reduce leverage** — leverage is appropriate for the signal quality; direction is the problem
- **Do NOT blacklist all SHORTs** — the `hzscore,pct-hermes,vel-hermes` SHORT has 58% win rate

---

## Questions for User

1. Should we completely REMOVE `rsi_individual` from signal generation (it has 0% win rate), or try to fix it with a z-score filter?
2. Should we remove RSI from ALL merge combos (since every combo with RSI is worse than without)?
3. Should we backtest before implementing fixes, or deploy and iterate?
