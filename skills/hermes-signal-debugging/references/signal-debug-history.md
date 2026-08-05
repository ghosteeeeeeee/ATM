# Signal Debug History — Old Session Artifacts

Moved from SKILL.md to keep it lean. These are historical session artifacts worth preserving.

---

## pct-hermes Direction — INVERTED LOGIC FIXED (2026-05-04)

**Status**: `pct-hermes+` was fixed 2026-05-04 (now ~95% WR). `pct-hermes-` was NOT changed and remains at ~0% WR.

**Root cause of pct-hermes+ consistent losses** (fixed 2026-05-04):

The direction logic was **completely inverted** — `pct-hermes+` was entering LONG at the **top** of its range, catching falling knives in a sustained downtrend.

**Semantics (counter-intuitive):**
- `pct_short` = % of 200-bar lookback where price >= current → **high pct_short = price near BOTTOM** (most bars are above you)
- `pct_long` = % of 200-bar lookback where price <= current → **high pct_long = price near TOP** (most bars are below you)

**What the old code did (WRONG):**
```python
# signal_gen.py lines ~1686-1692 — BUG: inverted direction
if pct_short >= 72:  signal_dir = 'LONG'   # price near BOTTOM → LONG = BUY THE DIP ✓
if pct_long  >= 72:  signal_dir = 'SHORT'  # price near TOP    → SHORT = SELL THE RALLY ✓
```

Wait — actually the code comment says the original was:
```
pct_long >= 72 → SHORT,  pct_short >= 72 → LONG
```
But the actual code was the OPPOSITE:
```
pct_long >= 72 → LONG,   pct_short >= 72 → SHORT
```
This is what was causing the losses — `pct_short >= 72` (price at bottom) → LONG (buy bottom), but in a downtrend price at bottom keeps falling. The signal was a **top picker**, not a bottom picker.

---

## Bug: Cooldown Flood (2026-04-23)

**Symptom**: Hot-set stays empty. Every signal gets `COOLDOWN skip`.

**Root cause**: `decider_run.py` line 672 was calling `set_cooldown()` on **every closed trade**, regardless of profit or loss:
```python
# WRONG — wrote cooldown on EVERY close:
if trade_dir:
    set_cooldown(token.upper(), trade_dir.upper(), hours=1)

# FIXED — only on LOSS:
if trade_dir and 'loss' in reason.lower():
    set_cooldown(token.upper(), trade_dir.upper(), hours=1)
```

**Diagnosis:**
```bash
# Check active cooldown count in PostgreSQL
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW()\")
print(f'Active cooldowns: {cur.fetchone()[0]}')
cur.execute(\"SELECT reason, COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW() GROUP BY reason\")
print('By reason:', cur.fetchall())
"
```

---

## Bug: Sources Showing `--` in Dashboard (2026-04-23)

**Symptom**: Dashboard shows `hot set` instead of actual multi-source strings.

**Root cause** (`/var/www/hermes/signals.html` line 371): Template reads `s.source` (singular) but hot_set entries use `s.sources` (plural):
```javascript
// WRONG — only reads singular `source`:
${s.source || '--'}

// FIXED — fallback to plural `sources`:
${(s.source || s.sources) || '--'}
```

---

## Bug: WR Filter Deadlock (2026-05-05)

**Symptom**: All tokens in hot-set blocked by WR filter. 0 entries despite valid signals.

**Root cause**: Tokens that need SHORT (bad LONG WR) can't get SHORT signals because SHORT-preferring signals are blacklisted. Tokens that are generating LONG (pct-hermes+) fire — but the WR filter blocks them.

**Fix Options**:
- **Option A**: Remove `gap-300+` and `gap300-5m+` from blacklist to allow SHORT signals
- **Option B**: Remove `gap-300+` and `gap300-5m+` from signal generation entirely
- **Option C**: Add SHORT-preferring tokens to LONG blacklist (SKR, CHEX, JTO, WLD, W, JUP)
- **Option D**: Change gap-300+ direction logic to invert based on broad regime

**Recommended**: Option C — add SHORT-preferring tokens to LONG blacklist:
```python
LONG_BLACKLIST = {'SKR', 'CHEX', 'JTO', 'WLD', 'W', 'JUP', ...}
```

---

## Blacklist State (2026-04-29)

Current entries blocking signal diversity:
- `'ma-cross'` — blocks BOTH `ma-cross-5m+` AND `ma-cross-5m-` (substring prefix match)
- `'pct-hermes-'` — blocks all pct-hermes SHORT variants
- `'vel-hermes+'`, `'vel-hermes-'` — blocks velocity signals entirely
- `'hzscore+'`, `'hzscore-'`, `'hzscore'` — blocks all z-score signals
- `'oc-mtf-rsi+'`, `'oc-mtf-rsi-'`, `'oc-mtf-rsi'` — blocks RSI signals
- `'oc-zscore-v9+'`, `'oc-zscore-v9-'`, `'oc-zscore-v9'` — blocks OC zscore signals
- `'fast-momentum+'`, `'fast-momentum-'` — blocks fast momentum signals
- `'pattern_scanner'` — blocks pattern signals
- `'gap-300+'` — blocks gap-300 SHORT signals

---

## Signal Source Blacklist — Per-Token Breakdown (2026-05-05)

| Token | Direction | Source String | Blocking Component | Mechanism |
|-------|-----------|-------------|-------------------|-----------|
| SUSHI | LONG | `accel-300+,hzscore-,rs-s255,rs-s473,vel-hermes+` | `vel-hermes+` → base `vel-hermes` → `SENTINEL_BASES` | Suffix-agnostic |
| SUSHI | LONG | `accel-300+,hzscore-,ma-cross-5m+,rs-s257,vel-hermes+` | `vel-hermes+` | Suffix-agnostic |
| AVAX | SHORT | `gap-300-,hzscore+,rs-r104,vel-hermes-` | `vel-hermes-` | Suffix-agnostic |

**Key insight**: Any signal with `vel-hermes+` or `vel-hermes-` is blocked regardless of other signal quality.

---

## Confluence Gate — 3→2 Unique Types (2026-05-05)

**Symptom**: hot-set.json has 0 entries. Every passing signal gets blocked at HOTSET-FILTER by `vel-hermes+` in blacklist.

**Fix**: Lowered confluence requirement from 3 → 2 unique signal types. A combo with 2+ unique signal types now passes even if one is blacklisted.

**Before**: Required 3 unique signal type prefixes (e.g., `accel-300+,hzscore-,rs-s4065` = 3 types: accel_300, hzscore, rs)
**After**: Only 2 unique signal type prefixes required

---

## vel-hermes+ Blacklist Removal — Partial Fix (2026-05-05)

**What was done**: Removed `vel-hermes` from `SENTINEL_BASES` in `validate_source()`. `vel-hermes+` and `vel-hermes-` can now appear in multi-source combos.

**What was NOT done**: `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` still has entries for `vel-hermes+` and `vel-hermes-` — these are checked FIRST before `validate_source()` runs, so velocity signals are still blocked at the compactor entrance.

**Still needed**: Remove `vel-hermes+` and `vel-hermes-` from `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py`.
