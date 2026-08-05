# ZScore Momentum Tuner + ZScore Pump — Architecture Reference

**Updated:** 2026-05-16 — validated end-to-end: tuner DB → signal gen → hot-set pipeline.

---

## 1. Storage

**Tuner DB:** `/root/.hermes/data/zscore_momentum_tuner.db`  
**Table:** `token_best_zscore_config`

| Column | Type | Notes |
|---|---|---|
| token | TEXT PK | Uppercase symbol |
| lookback | INTEGER | Best lookback (bars) from sweep |
| threshold | REAL | Best threshold from sweep |
| win_rate | REAL | Backtest win rate % |
| avg_pnl_pct | REAL | Backtest avg PnL % |
| signal_count | INTEGER | Backtest signal count (min 15 required) |
| total_long | INTEGER | Long signals in backtest |
| total_short | INTEGER | Short signals in backtest |
| updated_at | INTEGER | Unix timestamp |

**202 tokens currently tuned.** All have signal_count ≥ 15 → all use tuned params (none fall back to defaults).

---

## 2. Tuner: `zscore_momentum.py`

**Systemd timer:** `hermes-zscore-momentum-tuner.timer` → fires every **4 hours**  
**Service:** `hermes-zscore-momentum-tuner.service` → runs `zscore_momentum.py --sweep --lookback-period 240`

**Sweep flow:**
1. Load blacklists (`SHORT_BLACKLIST | LONG_BLACKLIST` = 119 tokens currently blocked)
2. Load price data: `get_all_token_prices_full(lookback_bars=240)` — 240 bars = last ~4h of 1m data
3. Freshness gate: skip sweep if < 80% of tokens have < 60 bars (keep existing params)
4. Iterate all non-blacklisted tokens through (lookback, threshold) grid
5. Backtest each combo: LONG if z > threshold, SHORT if z < -threshold, exit after `lookback * 2` bars or opposite signal
6. Score: `win_rate + (25 if avg_pnl > 0 else 0)`, require ≥ 15 signals
7. Write best params per token to `token_best_zscore_config`
8. Full sweep: ~6 min for 191 tokens × 286 combos

**CLI:** `python3 zscore_momentum.py --sweep --lookback-period 240`

---

## 3. Signal Generator: `signals/zscore_pump.py`

**Called by:** `signal_gen.py → scan_zscore_pump_signals()`  
**Log:** `/var/www/hermes/logs/signals.log`

**Flow per token:**
1. Load tuned params from `token_best_zscore_config` via `_load_tuner_params()` (cached per process)
2. If `signal_count < 15` → use defaults (`ZSCORE_PUMP_LOOKBACK=24`, `ZSCORE_PUMP_THRESHOLD=2.0`, confidence=80)
3. Otherwise use tuned `lookback` + `threshold`
4. Fetch 1m closes from `signals_hermes.db → price_history` (lookback + 50 bars buffer)
5. Compute z-score on last `lookback` closes
6. Fire signal if `|z| > threshold`
   - z > 0 → LONG (`zscore-pump+`)
   - z < 0 → SHORT (`zscore-pump-`)
7. Apply guards: open position check, trade cooldown, delist check, blacklist, price age > 10 min
8. Direction kill-switches: `ZSCORE_PUMP_PLUS_ENABLED`, `ZSCORE_PUMP_MINUS_ENABLED`
9. Confidence: `min(95, max(80, win_rate))` + z-score bonus capped at +15
10. Write via `add_signal()` → `signals_hermes_runtime.db`

**Key constants (from hermes_constants):**
- `ZSCORE_PUMP_ENABLED = True`
- `ZSCORE_PUMP_LOOKBACK = 24` (default fallback)
- `ZSCORE_PUMP_THRESHOLD = 2.0` (default fallback)
- `ZSCORE_PUMP_MIN_SIGNALS_FOR_TUNED = 15`
- `ZSCORE_PUMP_COOLDOWN_BARS = 10` (~10 minutes)

**Confidence formula:**
```
z_abs = abs(z_score)
conf_bonus = min(15, (z_abs - threshold) * 5)
confidence = min(95, base_confidence + conf_bonus)
```

---

## 4. Data Freshness

`price_history` in `signals_hermes.db` is updated ~1 bar/min per token via hl-sync.  
Staleness threshold in zscore_pump: **120 seconds**. If latest bar > 120s old → token skipped.

At time of session check: **183/191 tokens** had data < 120s old. The 8 stale tokens were mid-sync-gap at that exact moment — not a systemic problem.

---

## 5. Verification Commands

```bash
# Check tuner DB
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/zscore_momentum_tuner.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM token_best_zscore_config')
print('Tuned tokens:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM token_best_zscore_config WHERE signal_count < 15')
print('Below min signals (use defaults):', cur.fetchone()[0])
conn.close()
"

# Check signal log for recent zscore-pump activity
grep "zscore-pump" /var/www/hermes/logs/signals.log | tail -20

# Check price_history freshness
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
now = time.time()
c.execute('SELECT COUNT(DISTINCT token) FROM price_history WHERE timestamp > ?', (now - 120,))
print('Fresh tokens (<120s):', c.fetchone()[0])
c.execute('SELECT COUNT(DISTINCT token) FROM price_history')
print('Total tokens:', c.fetchone()[0])
conn.close()
"
```

---

## 6. Related Files

- `/root/.hermes/scripts/zscore_momentum.py` — tuner + sweep logic
- `/root/.hermes/scripts/signals/zscore_pump.py` — signal generator
- `/root/.hermes/scripts/hermes_constants.py` — ZSCORE_PUMP_* constants
- `/etc/systemd/system/hermes-zscore-momentum-tuner.timer` — 4h timer
- `/etc/systemd/system/hermes-zscore-momentum-tuner.service` — sweep service