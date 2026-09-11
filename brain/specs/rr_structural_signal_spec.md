# Risk-Reward Structural Signal Spec

**Date:** 2026-09-11
**Type:** New signal generator (generates signals FROM structural R:R analysis)
**Checklist:** add-signal + signal-lab

---

## Thesis (signal-lab Step 1)

**WHY should this work?**

Most signals fire on technical indicators (MACD, RSI, BB). These are lagging — they follow price, not predict it. The RR engine already computes structural quality for every token: S/R levels, liquidity clusters, volatility regime, and R:R ratio. Instead of using the RR engine as a gate that filters OTHER signals, use it as the primary detection source. Fire on structure, not indicators.

**Market mechanic:** Structural breakout — when a coin has clear air (no resistance above for LONG), strong R:R (3:1+), and is in the right volatility regime (NORMAL/HIGH), the structural setup is favorable. The RR engine already knows this — we just need to listen.

**Edge:** The RR engine evaluates ~200 tokens every compaction cycle. Most get poor scores (Grade D/F). The ones that score Grade A/B have genuinely excellent structure. By firing ONLY on Grade A/B setups, we filter 80%+ of noise before it even reaches the hotset.

---

## Signal Identity

```
Signal name:   rr_structural
Source tags:   rr-struct+ (LONG), rr-struct- (SHORT)
Signal types:  rr_structural_long, rr_structural_short
Timeframe:     15m (structural — not tick-level)
```

---

## Entry Conditions (signal-lab Step 2)

### LONG fires when ALL of:
1. RR engine score ≥ 70 (Grade B or better)
2. R:R ratio ≥ 3.0 (minimum 3:1 reward:risk)
3. Grade = A or B
4. Open skies (no resistance within 2% above) OR clear structural target within 1-2%
5. Volatility regime = NORMAL or HIGH (skip FLAT/EXTREME)
6. ATR% between 0.5% and 1.5% (sweet spot — enough energy, not too noisy)

### SHORT fires when ALL of:
1. RR engine score ≥ 70 (Grade B or better)
2. R:R ratio ≥ 3.0
3. Grade = A or B
4. Open skies (no support within 2% below) OR clear structural target within 1-2%
5. Volatility regime = NORMAL or HIGH
6. ATR% between 0.5% and 1.5%

### Confidence Calculation
```
base_conf = RR_STRUCTURAL_CONF_BASE (65)
rr_bonus = min(20, (rr_ratio - 3.0) * 5)     # R:R of 5.0 → +10, R:R of 7.0 → +20
grade_bonus = 10 if grade == 'A' else 5        # Grade A → +10, B → +5
open_sky_bonus = 5                              # no resistance = +5
liquidity_bonus = 5 if magnet_score > 0.5 else 0  # clusters nearby = +5
confidence = min(RR_STRUCTURAL_CONF_CAP, base + bonuses)
```

---

## Exit Rules (signal-lab Step 3)

Uses standard ATR SL/TP (managed by position_manager.py, not signal-specific):
- SL: ATR-based (from hermes_constants ATR_SL_MIN/ATR_SL_MAX)
- TP: Structural target from RR engine (nearest S/R or ATR-based fallback)
- Trailing: Standard PM_TRAIL activation at 0.40%

No signal-specific exit logic needed — the ATR system handles it.

---

## Files to Create/Modify (add-signal checklist)

### Step 0: Verify data source

```bash
cd /root/.hermes/scripts && python3 -c "
from risk_reward_engine import evaluate_rr
r = evaluate_rr('BTC', 'LONG', 80000)
print(f'Data source OK: R:R={r[\"rr_ratio\"]:.2f} Score={r[\"score\"]} Grade={r[\"grade\"]}')
print(f'  S/R levels: {len(r[\"sr_map\"])}')
print(f'  Regime: {r[\"vol_width\"][\"atr_regime\"]}')
"
```

### Step 1: Signal script

**File:** `scripts/signals/rr_structural.py`

```python
#!/usr/bin/env python3
"""rr_structural — Fire on structurally excellent R:R setups.

Uses the risk_reward_engine to evaluate structural quality for every token.
Fires signals ONLY when the engine scores Grade A/B with R:R ≥ 3.0.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from tokens import get_all_tradeable_tokens
from risk_reward_engine import evaluate_rr

from hermes_constants import (
    RR_STRUCTURAL_ENABLED,
    RR_STRUCTURAL_PLUS_ENABLED,
    RR_STRUCTURAL_MINUS_ENABLED,
    RR_STRUCTURAL_MIN_SCORE,
    RR_STRUCTURAL_MIN_RR,
    RR_STRUCTURAL_MIN_ATR_PCT,
    RR_STRUCTURAL_MAX_ATR_PCT,
    RR_STRUCTURAL_REGIMES,
    RR_STRUCTURAL_COOLDOWN_HOURS,
    RR_STRUCTURAL_CONF_BASE,
    RR_STRUCTURAL_CONF_CAP,
    RR_STRUCTURAL_OPEN_SKY_BONUS,
    RR_STRUCTURAL_LIQ_BONUS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'rr_structural_long'
SIGNAL_TYPE_SHORT = 'rr_structural_short'
SOURCE_LONG       = 'rr-struct+'
SOURCE_SHORT      = 'rr-struct-'


def _log(msg):
    print(f'[rr-struct] {msg}', flush=True)


def detect(token, price):
    """Evaluate structural R:R for a token. Returns signal dict or None."""
    # LONG evaluation
    long_result = evaluate_rr(token, 'LONG', price)
    if (long_result['grade'] in ('A', 'B') and
        long_result['rr_ratio'] >= RR_STRUCTURAL_MIN_RR and
        long_result['score'] >= RR_STRUCTURAL_MIN_SCORE and
        long_result['vol_width']['atr_regime'] in RR_STRUCTURAL_REGIMES and
        RR_STRUCTURAL_MIN_ATR_PCT <= long_result['vol_width']['atr_pct'] <= RR_STRUCTURAL_MAX_ATR_PCT):

        # Compute confidence
        conf = RR_STRUCTURAL_CONF_BASE
        conf += min(20, int((long_result['rr_ratio'] - 3.0) * 5))
        conf += 10 if long_result['grade'] == 'A' else 5
        if not any(l.get('type') == 'resistance' for l in long_result['sr_map']):
            conf += RR_STRUCTURAL_OPEN_SKY_BONUS  # open skies
        if long_result['liquidity'].get('magnet_score', 0) > 0.5:
            conf += RR_STRUCTURAL_LIQ_BONUS
        conf = min(RR_STRUCTURAL_CONF_CAP, conf)

        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': long_result['rr_ratio'],
            'price': price,
            'notes': f"R:R={long_result['rr_ratio']:.2f} Score={long_result['score']} Grade={long_result['grade']}",
        }

    # SHORT evaluation
    short_result = evaluate_rr(token, 'SHORT', price)
    if (short_result['grade'] in ('A', 'B') and
        short_result['rr_ratio'] >= RR_STRUCTURAL_MIN_RR and
        short_result['score'] >= RR_STRUCTURAL_MIN_SCORE and
        short_result['vol_width']['atr_regime'] in RR_STRUCTURAL_REGIMES and
        RR_STRUCTURAL_MIN_ATR_PCT <= short_result['vol_width']['atr_pct'] <= RR_STRUCTURAL_MAX_ATR_PCT):

        conf = RR_STRUCTURAL_CONF_BASE
        conf += min(20, int((short_result['rr_ratio'] - 3.0) * 5))
        conf += 10 if short_result['grade'] == 'A' else 5
        if not any(l.get('type') == 'support' for l in short_result['sr_map']):
            conf += RR_STRUCTURAL_OPEN_SKY_BONUS
        if short_result['liquidity'].get('magnet_score', 0) > 0.5:
            conf += RR_STRUCTURAL_LIQ_BONUS
        conf = min(RR_STRUCTURAL_CONF_CAP, conf)

        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': short_result['rr_ratio'],
            'price': price,
            'notes': f"R:R={short_result['rr_ratio']:.2f} Score={short_result['score']} Grade={short_result['grade']}",
        }

    return None


def scan_signals():
    """Scan all tradeable tokens for structurally excellent R:R setups."""
    added = 0
    tokens = get_all_tradeable_tokens()

    for token in tokens:
        token_upper = token.upper()

        # Price age check
        if price_age_minutes(token) > 10:
            continue

        # Get latest price
        from signal_schema import get_all_latest_prices
        prices = get_all_latest_prices()
        price_data = prices.get(token_upper)
        if not price_data or price_data.get('price', 0) <= 0:
            continue
        price = price_data['price']

        # Detect
        sig = detect(token_upper, price)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not RR_STRUCTURAL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not RR_STRUCTURAL_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token_upper, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token_upper,
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='15m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token_upper, direction, hours=RR_STRUCTURAL_COOLDOWN_HOURS)
            _log(f'{token_upper} {direction} conf={sig["confidence"]} {sig["notes"]}')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    added = run()
    _log(f'Total: {added} signals')
```

### Step 2: Constants in hermes_constants.py

```python
# ── RR Structural Signal ────────────────────────────────────────────────────
# rr_structural.py — fire on structurally excellent R:R setups
RR_STRUCTURAL_ENABLED         = True   # master kill-switch
RR_STRUCTURAL_PLUS_ENABLED    = True   # LONG direction
RR_STRUCTURAL_MINUS_ENABLED   = True   # SHORT direction
RR_STRUCTURAL_MIN_SCORE       = 70     # minimum RR engine score (Grade B+)
RR_STRUCTURAL_MIN_RR          = 3.0    # minimum R:R ratio
RR_STRUCTURAL_MIN_ATR_PCT     = 0.5    # minimum ATR% (skip flat coins)
RR_STRUCTURAL_MAX_ATR_PCT     = 1.5    # maximum ATR% (skip extreme noise)
RR_STRUCTURAL_REGIMES         = ('NORMAL', 'HIGH')  # allowed regimes
RR_STRUCTURAL_COOLDOWN_HOURS  = 4      # per-token+direction cooldown
RR_STRUCTURAL_CONF_BASE       = 65     # base confidence
RR_STRUCTURAL_CONF_CAP        = 92     # max confidence
RR_STRUCTURAL_OPEN_SKY_BONUS  = 5      # bonus for open skies (no resistance)
RR_STRUCTURAL_LIQ_BONUS       = 5      # bonus for liquidity proximity
```

### Step 3: Register in signals/__init__.py

**3A. Import flags:**
```python
RR_STRUCTURAL_ENABLED, RR_STRUCTURAL_PLUS_ENABLED, RR_STRUCTURAL_MINUS_ENABLED,
```

**3B. Import run function:**
```python
try:
    from signals.rr_structural import run as _rr_structural_run
except Exception:
    _rr_structural_run = None
```

**3C. Add to SIGNAL_REGISTRY:**
```python
{'name': 'rr_structural', 'enabled': 'RR_STRUCTURAL_ENABLED', 'run': _rr_structural_run},
```

**3D. Add to _SLOW_SIGNALS** (scans all tokens):
```python
_SLOW_SIGNALS = {'momentum', 'mtf_momentum', 'signal_confluence', 'rr_structural'}
```

### Step 4: Layer 2 in signal_schema.py

**4A. In `add_signal()` component loop:**
```python
# rr-struct
if _comp == 'rr-struct+':
    try:
        from hermes_constants import RR_STRUCTURAL_PLUS_ENABLED
        if not RR_STRUCTURAL_PLUS_ENABLED:
            print(f'  DEBUG add_signal BLOCKED: {token} {direction} source="{source}" RR_STRUCTURAL_PLUS_ENABLED=False', flush=True)
            return None
    except ImportError:
        pass
if _comp == 'rr-struct-':
    try:
        from hermes_constants import RR_STRUCTURAL_MINUS_ENABLED
        if not RR_STRUCTURAL_MINUS_ENABLED:
            print(f'  DEBUG add_signal BLOCKED: {token} {direction} source="{source}" RR_STRUCTURAL_MINUS_ENABLED=False', flush=True)
            return None
    except ImportError:
        pass
```

**4B. In `is_component_disabled()` function:**
```python
# Add to import block:
from hermes_constants import (
    ...
    RR_STRUCTURAL_ENABLED, RR_STRUCTURAL_PLUS_ENABLED, RR_STRUCTURAL_MINUS_ENABLED,
)

# Add to function body:
if c == 'rr-struct': return not RR_STRUCTURAL_ENABLED
if c == 'rr-struct+': return not RR_STRUCTURAL_PLUS_ENABLED
if c == 'rr-struct-': return not RR_STRUCTURAL_MINUS_ENABLED
```

### Step 5: Source weight in signal_compactor.py

```python
('rr_structural_long',  'rr-struct+'):  1.0,
('rr_structural_short', 'rr-struct-'):  1.0,
```

### Step 5a: STANDALONE_BYPASS_SIGNALS (solo signal)

```python
STANDALONE_BYPASS_SIGNALS = (
    ...,
    'rr-struct',  # structural R:R quality signal, works solo
)
```

### Step 5b: Volatility filter (REGIME_SIGNALS)

```python
# In volatility_gate.py REGIME_SIGNALS:
'NORMAL': {
    ...,
    'rr-struct', 'rr-struct+', 'rr-struct-',
},
'HIGH': {
    ...,
    'rr-struct', 'rr-struct+', 'rr-struct-',
},
```

Structural signal works in NORMAL and HIGH regimes. Skip FLAT (no energy) and EXTREME (too noisy for structural assessment).

### Step 5c: PROFIT_MONSTER_BYPASS_SIGNALS

NOT needed — this signal uses standard ATR SL/TP managed by position_manager, not its own exit logic.

---

## Backtest Plan (signal-lab Step 4)

```sql
-- Validate: does Grade A/B RR engine score predict profitable trades?
SELECT
  CASE WHEN score >= 70 THEN 'GRADE_A_B' ELSE 'GRADE_C_D_F' END as tier,
  COUNT(*) as signals,
  ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
  ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
  ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl
FROM signal_outcomes
WHERE signal_type LIKE 'rr_structural%'
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY tier;
```

**Minimum requirements:**
- 20+ trades in sample
- WR > 52%
- Avg PnL > 0.05%
- Total PnL > $0

---

## Verification (add-signal Step 6)

```bash
# 1. Syntax check
cd /root/.hermes/scripts && python3 -c "
import py_compile
files = [
    'signals/rr_structural.py',
    'hermes_constants.py',
    'signals/__init__.py',
    'signal_schema.py',
    'signal_compactor.py',
    'volatility_gate.py',
]
for f in files:
    py_compile.compile(f, doraise=True)
    print(f'{f}: OK')
"

# 2. Import chain
cd /root/.hermes/scripts && python3 -c "
from signals.rr_structural import run
from signals import get_slow_signals
slow = get_slow_signals()
rr = [s for s in slow if s['name'] == 'rr_structural']
assert len(rr) > 0, 'NOT in registry'
assert rr[0]['run'] is not None, 'run function is None'
print(f'Registry: OK (enabled={rr[0][\"enabled\"]})')

from volatility_gate import REGIME_SIGNALS
for regime in ['NORMAL', 'HIGH']:
    found = any('rr-struct' in s for s in REGIME_SIGNALS.get(regime, set()))
    assert found, f'MISSING from {regime}'
print('Volatility gate: OK')
"

# 3. Dry run
cd /root/.hermes/scripts && timeout 60 python3 signals/rr_structural.py

# 4. Check logs
tail -100 /root/.hermes/logs/pipeline.log | grep rr_structural
```

---

## Pre-flight Checklist (add-signal)

| Check | Status |
|-------|--------|
| DB connections safe (finally blocks) | ✅ uses existing evaluate_rr |
| No hardcoded numbers | ✅ all in hermes_constants |
| Blacklist in script | ✅ checks LONG/SHORT_BLACKLIST |
| Cooldown set | ✅ uses set_cooldown |
| Not in _DEAD_SIGNALS | ✅ new signal |
| Source format consistent | ✅ rr-struct+/rr-struct- |
| Source not blacklisted | ✅ new source |
| In REGIME_SIGNALS | ✅ NORMAL + HIGH |
| In is_component_disabled() | ✅ added |
| In STANDALONE_BYPASS | ✅ solo signal |
| run() function exists | ✅ |

---

## What NOT to touch

| Component | Why |
|-----------|-----|
| signals_runner.py | Auto-discovers from registry |
| signal_outcomes table | Auto-created by position_manager |
| DB schema | Uses existing signals table |
| systemd timers | Pipeline runs signals_runner automatically |
| decider_run.py | Layer 3 auto-applies |
