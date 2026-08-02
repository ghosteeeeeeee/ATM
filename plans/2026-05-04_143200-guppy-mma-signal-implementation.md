# Guppy MMA Signal — Implementation Plan

## Status: CORE BUILT | Tuning + Integration Pending

Last updated: 2026-05-04

---

## What Was Built

| File | Location | Status |
|------|----------|--------|
| Detection engine | `/root/.hermes/scripts/guppy_signals.py` | ✅ Done |
| Standalone runner | `/root/.hermes/scripts/run_guppy_signals.py` | ✅ Done |
| Backtester | `/root/.hermes/scripts/backtest_guppy.py` | ✅ Done |
| Dashboard | `/var/www/hermes/guppy.html` | ⬜ Pending |
| Integration (constants, guardian, PM) | — | ⬜ Pending |
| Systemd service | — | ⬜ Pending |

---

## Architecture

```
run_guppy_signals.py (systemd timer: every 60s)
├── --scan     → guppy_signals.py → detect_guppy_signal() → open positions
├── --monitor  → check open positions for TP/SL exits
├── --status   → show open positions
└── --close ALL → close all positions

guppy_signals.py
├── Reads: candles.db → candles_1m / candles_5m / candles_15m (LOCAL ONLY, no HL API)
├── Signal: detect_guppy_signal(rows) → {direction, confidence, squeeze, separation, ...}
├── Exit:   check_guppy_exit() → TP/SL check + fast-group flip
└── No HL API calls anywhere in the signal pipeline

run_guppy_signals.py
├── GUPPY_ENABLED gate (const in hermes_constants.py)
├── GUPPY_LIVE=1 env var → real HL trades via mirror_open/mirror_close
├── GUPPY_LIVE=0/unset → dry run, logs what it would do
├── Tracker: /var/www/hermes/data/guppy_positions.json  ← (NOT pump-hunter.json)
└── Brain DB: signal='guppy' records so guardian/PM skip guppy positions
```

**Why standalone (not hot-set):**
- Guardian manages ATR TP/SL exits — incompatible with guppy's TP-based exits
- signal_compactor blocks single-source signals (conf-1s rule)
- pump_hunter, zscore_pump, atr_compression_signals all use the same standalone pattern
- Verdict: self-managed is the only clean architecture

**Price data: LOCAL ONLY — zero HL API calls for signal detection or exit monitoring**
- candles.db: `/root/.hermes/data/candles.db` (2.6GB, populated by HL sync)
- Tables: `candles_1m`, `candles_5m`, `candles_15m`, `candles_1h`, `candles_4h`
- HL API only needed for actual trade execution (deferred to live phase)

---

## Signal Detection (`guppy_signals.py`)

### Constants (current tuned values)
```python
FAST_GROUP = [3, 5, 8, 10, 12, 15]
SLOW_GROUP = [30, 35, 40, 45, 50, 60]
SQUEEZE_THRESHOLD = 0.003    # 0.3% — fast group within this % of slow = squeeze
MIN_SEPARATION_PCT = 0.2     # 0.2% — minimum separation to confirm expansion
EXPANSION_BARS = 2           # separation must grow over 2 bars
SLOW_TREND_LOOKBACK = 10      # bars to check slow group trend direction
MIN_VOLUME_RATIO = 2.0        # volume must be 2x 20-bar avg to confirm signal
MIN_SIGNAL_SEPARATION = 0.1  # 0.1% — minimum sep% to even consider a signal
SQUEEZE_LOOKBACK = 20        # bars to look back for squeeze detection
```

### Core Functions
- `compute_ema(closes, period)` — standard EMA
- `compute_group_emas(closes, periods)` → {period: ema_value}
- `get_group_mid(emas)` — average of group EMAs
- `get_group_high_low(emas)` — max/min of group EMAs
- `is_squeezed(fast_emas, slow_emas)` — fast group within 0.3% of slow group midpoint
- `detect_expansion(fast_emas, slow_emas, closes)` — is separation growing over 2 bars?
- `detect_cross(fast_mid_history, slow_mid_history)` → 'LONG' | 'SHORT' | None
- `detect_slow_group_trend(slow_mid_history, lookback)` → 1 / -1 / 0
- `_compute_confidence(squeeze, separation, direction, volume_confirm)` → 0.0–1.0
- `detect_guppy_signal(rows)` → {signal, direction, confidence, squeeze, separation, source} | None
- `check_guppy_exit(rows, position)` → {exit: bool, reason: str, price: float} | None

### Signal Logic (current)
```
1. Compute fast EMAs (3-15) and slow EMAs (30-60) from close prices
2. Squeeze check: fast group within 0.3% of slow group midpoint? (squeeze = coiled spring)
3. Trend filter: slow group must be rising (LONG) or falling (SHORT) over SLOW_TREND_LOOKBACK bars
4. Expansion check: separation must be GROWING over EXPANSION_BARS (not just a momentary spike)
5. Cross check: fast group above slow group (LONG) or below (SHORT)
6. Volume confirmation: volume ≥ 2x 20-bar average (strengthens signal)
7. Confidence score: 0–1 based on squeeze, separation, volume, bars since cross

Entry signal fires when: squeeze + slow trend aligned + expansion + cross + min confidence
```

### Signal Output
```python
{
  'signal':    'guppy_long' or 'guppy_short',
  'direction': 'LONG' or 'SHORT',
  'confidence': 0.0–1.0,
  'squeeze':    True/False,
  'separation': float,   # % difference between fast and slow group midpoints
  'source':    'guppy_long' or 'guppy_short',
}
```

---

## Exit Logic

### Live (`run_guppy_signals.py --monitor`)
```
Priority order:
1. TP hit: position PnL ≥ TP_PCT → close at market, record 'tp' exit reason
2. SL hit: position PnL ≤ -SL_PCT → close at market, record 'sl' exit reason
3. Reverse signal: opposite guppy signal fires → close + reverse, record 'guppy_fast_flip'
4. end_of_data: no position left open at end of backtest/scan
```

### Current Tuned Parameters (15m)
```
INTERVAL  = 15m      ← 15m dramatically better than 1m/5m
TP_PCT    = 0.75%    ← TP-only, no SL (SL cuts off winners)
CONF      = 0.50
LOOKBACK  = 120 bars
```

### Why no SL?
- Adding SL=0.50% to TP=0.75% on HYPE: 18 trades, 50% win rate, +0.29% avg PnL
- TP-only at 0.75%: 14 trades, 57% win rate, +0.38% avg PnL
- SL stops out valid winners prematurely — guppy exits work better as "book profit" than "cut losses"

---

## Backtest Results (2026-05-04)

### HYPE, 15m, TP=0.75% only, conf=0.5 ← BEST RESULT
- 14 trades, **57% win rate**, **+0.38% avg PnL**
- Best: +3.31%, Worst: -1.93%, Max drawdown: -1.93%
- Avg bars held: 170.8
- Squeeze rate at entry: 64.3%

### HYPE, 15m, TP=0.75% + SL=0.50%, conf=0.5
- 18 trades, 50% win rate, +0.29% avg PnL
- SL adds trades but reduces avg PnL

### 5-token scan, 15m, TP=0.75% (87 total trades)
| Token | Trades | Win Rate | Avg PnL |
|-------|--------|----------|---------|
| AAVE  | 20     | 35%      | +0.99%  |
| 2Z    | 18     | 56%      | +0.27%  |
| ADA   | 20     | 35%      | -0.17%  |
| ACE   | 17     | 18%      | -1.28%  |
| 0G    | 12     | 25%      | -1.88%  |
| **Total** | **87** | **34%** | **-0.27%** |

→ Signal quality is token-dependent. HYPE is the best case; uniform scanning across all tokens is unprofitable.

### 1m vs 5m vs 15m (HYPE, no TP/SL)
| Interval | Trades | Win Rate | Avg PnL |
|----------|--------|----------|---------|
| 1m       | 23     | 23%      | -0.52%  |
| 5m       | 21     | 38%      | -0.20%  |
| 15m      | 8      | 63%      | +0.62%  |

→ 15m >> 5m >> 1m. Higher timeframe = cleaner trends, fewer false signals. Guppy was designed for higher timeframes.

### Key Findings
1. **15m is the right timeframe** — 1m/5m are too noisy, groups constantly crossing
2. **TP-only exits are the right approach** — "book profit fast" works; SL cuts winners early
3. **0.75% TP is the sweet spot** on 15m HYPE — 57% win rate, best avg PnL
4. **Token selection matters** — not universally profitable across all coins
5. **Squeeze alone is not enough** — expansion + trend filter + cross all needed together

---

## Files

### `/root/.hermes/scripts/guppy_signals.py` ✅
Pure detection library. stdlib + sqlite3 only. No HL API.
```
get_available_tokens(interval)        → list of token symbols
get_candles(token, interval, lookback) → list of (ts, open, high, low, close, volume)
compute_ema(closes, period)           → float
compute_group_emas(closes, periods)  → {period: ema_value}
get_group_mid(emas)                   → float
get_group_high_low(emas)              → (low, high)
is_squeezed(fast_emas, slow_emas)     → bool
detect_expansion(...)                 → dict {expanding, separation, sep_then, sep_now}
detect_cross(...)                     → 'LONG' | 'SHORT' | None
detect_slow_group_trend(...)          → 1 / -1 / 0
_compute_confidence(...)              → float 0–1
detect_guppy_signal(rows)             → signal dict | None
check_guppy_exit(rows, position)      → exit dict | None
```

### `/root/.hermes/scripts/run_guppy_signals.py` ✅
Standalone runner. Modes: `--scan`, `--monitor`, `--status`, `--close ALL`.
- Tracker: `/var/www/hermes/data/guppy_positions.json`
- Dry run by default; `GUPPY_LIVE=1` or `--live` flag enables real trades
- Creates/closes brain DB records with `signal='guppy'`

### `/root/.hermes/scripts/backtest_guppy.py` ✅
Historical backtester. Pure stdlib + sqlite3.
- `backtest_token(token, interval, tp_pct, sl_pct, min_confidence)` → list of trades
- `scan_all_tokens(...)` → aggregated results across all tokens
- CSV output: `/root/.hermes/data/guppy_backtest_results.csv`
- `--tp` / `--sl` CLI args for exit parameterization

### `/var/www/hermes/guppy.html` ⬜
Dashboard. Template: `pump-hunter.html` at same path. Reads from `guppy_positions.json`.

---

## Integration Points

### 1. `hermes_constants.py` — add:
```python
GUPPY_ENABLED = False                    # master kill switch
GUPPY_TP_PCT  = 0.75                     # take profit %
GUPPY_SL_PCT  = 0.0                      # stop loss % (0 = disabled)
GUPPY_INTERVAL = '15m'                   # candle interval
GUPPY_MIN_CONF = 0.50                    # minimum confidence threshold
GUPPY_MAX_POSITIONS = 3                  # max concurrent guppy positions

SIGNAL_GENERATOR_ENABLED = {
    # ... existing signals ...
    'guppy': False,                      # per-signal kill switch
}
```

### 2. `hyperliquid_exchange.py` — add GUPPY_LIVE bypass:
```python
# In mirror_open() / mirror_close() / place_tp() / place_sl():
# After is_live_trading_enabled() check:
if os.environ.get('GUPPY_LIVE', '').lower() in ('1', 'true', 'yes'):
    pass  # allow guppy through
```

### 3. `position_manager.py` (line ~259, ~283, ~307) — add 'guppy':
```python
AND (signal IS NULL OR signal NOT IN ('pump_hunter', 'zscore_pump', 'guppy'))
```

### 4. `hl-sync-guardian.py` (lines ~607, ~634, ~975, ~1054) — add 'guppy':
```python
signal NOT IN ('pump_hunter', 'guppy')
```
Also fix latent bug: add `zscore_pump` to these lists too.

### 5. Brain DB — `signal='guppy'` records:
- `run_guppy_signals.py` writes `signal='guppy'` on open
- `run_guppy_signals.py` writes `close_reason='tp'/'sl'/'guppy_fast_flip'` on close
- Guardian and PM skip records where `signal='guppy'`

### 6. Systemd service + timer:
```ini
# /etc/systemd/system/hermes-guppy.service
[Service]
ExecStart=/usr/bin/python3 /root/.hermes/scripts/run_guppy_signals.py --scan
Environment=GUPPY_LIVE=0
Environment=PYTHONUNBUFFERED=1

# /etc/systemd/system/hermes-guppy.timer
[Timer]
OnCalendar=*:0/1          # every 1 minute
OnCalendar=*:0/15         # --monitor every 15 seconds (second timer or embedded)
```

---

## Signal Type Names

| | LONG | SHORT |
|--|--|--|
| **signal** | `guppy_long` | `guppy_short` |
| **source tag** | `guppy_long` | `guppy_short` |
| **brain DB signal** | `guppy` | `guppy` |
| **exit_reason** | `tp`, `sl`, `guppy_fast_flip`, `end_of_data` | same |

---

## TODO

- [x] Create `guppy_signals.py` detection engine ✅
- [x] Create `run_guppy_signals.py` standalone runner ✅
- [x] Create `backtest_guppy.py` validation script ✅
- [x] Tune parameters via backtesting ✅ (15m, TP=0.75%, no SL, conf=0.50)
- [ ] Create `guppy.html` dashboard
- [ ] Add `GUPPY_ENABLED`, `GUPPY_TP_PCT`, `GUPPY_SL_PCT`, `GUPPY_INTERVAL`, `GUPPY_MIN_CONF` to `hermes_constants.py`
- [ ] Add `SIGNAL_GENERATOR_ENABLED['guppy']` to `hermes_constants.py`
- [ ] Add `GUPPY_LIVE` bypass to `hyperliquid_exchange.py`
- [ ] Update `position_manager.py` — add 'guppy' to exclusion list (line ~259, ~283, ~307)
- [ ] Update `hl-sync-guardian.py` — add 'guppy' to ALL exclusion lists
- [ ] Fix latent bug: add `zscore_pump` to guardian exclusion lists
- [ ] Create systemd service + timer for `run_guppy_signals.py`
- [ ] Dry run: verify `--scan`/`--monitor`/`--status`/`--close ALL` all work end-to-end
- [ ] Live: flip `GUPPY_ENABLED = True`, set `GUPPY_LIVE=1`

---

## Open Questions

1. **Monitor frequency**: `--monitor` every 15s or 60s? Fast-group flip is time-sensitive but TP exits are just price checks.
2. **Token filter for scanning**: Backtest shows high variance across tokens. Should guppy only scan tokens with recent volume spike? Or scan everything and let confidence filter?
3. **Confidence threshold**: 0.50 is current. Higher = fewer but higher-quality signals. Worth testing 0.60–0.70 on 15m.
4. **Position sizing**: Fixed size? ATR-based? Not yet determined — deferred to live phase.
