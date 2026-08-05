---
name: hermes-signal-debugging
description: Debug and fix signal direction, hot-set entry filtering, and source weight issues in the Hermes trading system
triggers:
  - "signals show EXECUTED=1 but no trade on HL or in archive DB — brain.py RC=1 silent failure (empty stderr, HL API error), or signal_compactor marked EXPIRED (which also sets executed=1); check pipeline journal for mirror_open failures — see refs: signals-executed-no-trades-2026-06-18.md"
  - "brain.py mirror_open returns RC=1 with empty stderr — HL API error is in stdout (print result dict), not stderr capture; check journal for 'stdout=' to see actual error; old root cause was hyperliquid_exchange.py hardcoded 0x5AB4... (revoked) and filter excluded SIGNING_KEY from .secrets.local; current state: .secrets.local has 0x8507... working wallet; hyperliquid_exchange.py now loads from .secrets.local correctly; verify with: python3 -c 'from hyperliquid_exchange import get_wallet; print(get_wallet().address)'"
  - "phase_accel not appearing in hot-set"
  - "LAYER-type move not detected"
  - "zscore-momentum tuner sweeps 0 tokens"   # refs: zscore-tuner-bug.md
  - "hotset empty but PENDING: confluence gate blocks single-source signals (ACCEL_300_STANDALONE_BYPASS disabled); RS fires 12x/hr, accel fires 1680x/hr, they never land in same 5-min window — see refs: signals-executed-no-trades-2026-06-18.md"
  - "rs.py bounce false positives"  # refs: rs-audit-jun-2026.md
  - "rs.py no signals: proximity K too tight, bounce threshold inverted, clustering amplifies touches"  # refs: rs-prox-2026-06-17.md
  - "rs.py swing high off-by-one"  # refs: rs-audit-jun-2026.md
  - "accel-300 not firing on clean downtrend (BLUR, ME below EMA300 for 400+ bars)"  # refs: accel-300-sustained-breakdown-jun-2026.md26.md
  - "accel-300 missing clean1min breakouts on small-price tokens"      # refs: accel-300-gap-calibration-jun-2026.mdy-entry-jun-2026.md, accel-300-all-sessions.md
  - "AVNT SHORT pattern — want to catch early, chop filter too tight" # refs: accel-300-early-entry-jun-2026.md
  - "ME SHORT fired when price was marginally below EMA300, immediate reversal"   # refs: me-ton-accel-300-marginal-cross-jun-2026.md
  - "accel-300 scanner returns 0 but manual trace shows gate1 passing for DYDX/BABY/CC — data pipeline blocked" # refs: accel-300-lb35-signal-works-jun-2026.mdd
  - "accel-300 LOOKBACK+STALE_BARS incompatible: LOOKBACK=250 + STALE_BARS=25 =0 signals; cross at bar 441, detection starts550, bars_since=109+, all >25 → ALL blocked; LOOKBACK=30 works (cross at 441, detection starts 330, bars_since=10); STALE_BARS must track LOOKBACK"   # Jun 6 2026
  - "MIN_GAP_PCT_SHORT is a MAXIMUM — abs(gap) < threshold inverts the gate: -4.39% XLM rejected, -0.05% chop passes; raise to 0.50+ or fix logic"   # Jun 6 2026
  - "accel-300 dry-run 0 signals but live trading has signals"   # Jun 6 2026 — LOOKBACK too short + gap is maximum not minimum, refs: accel-300-hardcoded-thresholds-jun-2026.md
  - "accel-300 regime filter blocking valid signals"   # Jun 6 2026 — ACCEL_300_REGIME_SLOPE_PCT=0.008 blocks 27/30 tokens as NEUTRAL; 155 historical SHORT trades placed WITHOUT this filter; fix: raise threshold to 0.002 or remove filter; refs: accel-300-regime-filter-blocks-all-jun-2026.md
  - "constant from hermes_constants not being used by signal"   # refs: accel-300-hardcoded-thresholds-jun-2026.md
  - "signal passes all upstream gates but returns None" # refs: accel-300-hardcoded-thresholds-jun-2026.md — regime filter blocking as NEUTRAL
  - "accel-300 constants in hermes_constants not being read by signal code"   # Jun 6 2026 — ONLY 2 of 10 constants imported, rest hardcoded, refs: accel-300-hermes-constants-import-gap-jun-2026.md
  - "ACCEL_300_LOOKBACK changed but signal still finding 0 coins"   # Jun 6 2026 — LOOKBACK controls search window start: max(PERIOD+LOOKBACK, n-1-LOOKBACK), smaller LOOKBACK = narrower window = fewer crosses found
  - "MIN_GAP_PCT_SHORT is blocking strong SHORT signals"   # Jun 6 2026 — abs(gap) < threshold rejects deep gaps (-4.39%, -0.25%), treats them as "too volatile" — threshold is a maximum not a minimum
  - "MIN_GAP_PCT_SHORT is blocking deep gaps like -4.39% for XLM"  # Jun 6 2026 — gap treated as maximum not minimum
  - "accel-300 not firing even with regime_slope relaxed to 0.008"  # Jun 6 2026 — MIN_GAP_PCT_SHORT blocks all strong signals
  - "why is MIN_GAP_PCT_SHORT rejecting -0.25% MORPHO gap"  # Jun 6 2026 — abs(gap) < 0.15 rejects deep gaps
  - "dry-run returns 0 signals but market has 81 tokens in strong trends"  # Jun 6 2026
  - "accel-300 passes gap/growth/slope but no signal fires"   # ACCEL_300_STALE_BARS hardcoded at accel_300.py:291 — only MORPHO hits this, refs: accel-300-hardcoded-thresholds-jun-2026.md
  - "accel-300+ LONG fires into counter-trend moves"   # 30% WR, refs: short-bias-diagnosis.md
  - "RS confirmation is backwards for accel-300"   # 45 trades, 22% WR vs rs-broken would be better — refs: accel-300-rs-backwards-jun-2026.md
  - "regime slope hardcoded in accel_300.py"   # refs: accel-300-regime-hardcoded-jun-2026.md
  - "price_history has only 1 row per token — EMA(300) cannot compute, regime filter bypassed"   # refs: accel-300-data-staleness-jun-2026.md
  - "candles_1m is stale (8.7 days) — data pipeline broken upstream, both tables same age"   # refs: accel-300-data-staleness-jun-2026.md
  - "slope threshold 0.03 blocks EVERYTHING — all tokens in flat/neutral regime (-0.005 to -0.016%/bar)"   # refs: accel-300-regime-slope-threshold.md
  - "accel-300 chop filter hardcoded in accel_300.py lines ~312-321, NOT in hermes_constants"   # refs: accel-300-chop-filter-2026-06-05.md
  - "accel-300 regime filter hardcoded in accel_300.py lines ~406-410, NOT in hermes_constants"   # refs: accel-300-chop-filter-2026-06-05.md
  - "T explicitly: do NOT add coins to allowlist to bypass regime filter"   # refs: accel-300-chop-filter-2026-06-05.md
  - "zscore-pump+ LONG 0% WR"   # mean-reversion fires into falling mean, refs: short-bias-diagnosis.md
  - "rs-r-broken and rs-s-broken directional asymmetry"   # refs: rs-broken-reclassify-patch.md
  - "MERL ME BRETT executing with single source accel-300"
  - "single-source preserved entry bypassed merge guard"
  - "confluence gate passed but entry has only 1 source in hot-set"
  - "rs-r86,rs-s-broken passing confluence (same family counted as 2 types)"   # refs: rs-rs-broken-confluence-collapse-2026-06-03.md
  - "accel-300-,rs-s-broken still passes confluence — accel-300- ≠ rs family, so 2 types, 38% WR worst group"   # NEW 2026-06-03

NOTE: See references/single-source-bypass-2026-05-12.md for root-cause (PENDING-to-APPROVED path lacks confluence check) and fix location (signal_compactor.py line ~1039).
  - "debug logs not appearing in pipeline.log"
  - "UnboundLocalError cannot access local variable 'combo_key'"
  - "hermes-trades-api shows APPROVED but PostgreSQL has no trade"
  - "debug logs not appearing in pipeline.log"
  - "UnboundLocalError cannot access local variable 'combo_key'"
  - "hermes-trades-api shows APPROVED but PostgreSQL has no trade"
  - "why does signals.json show APPROVED but HL has no trade"
  - "APEX MERL INJ ME all APPROVED but no trades in PostgreSQL"
  - "signals APPROVED in UI not reaching Hyperliquid"
  - "how does a single-source signal get past the confluence gate"
  - "decider_run not checking source count at execution time"
  - "confluence gate not enforced at execution"
  - "signal_compactor preserves single-source from prev_hotset"
  - "hot-set single signal through"
  - "signal_type key mismatch"
  - "only one open trade hotset full"
  - "counter-flip strangling entries"
  - "ma-cross-5m-short not passing gate"
  - "hwave disabled SHORT gap"
  - "zero signals ever APPROVED"
  - "hotset full no entries approved"
  - "sub-second exits"
  - "trade closed too fast"
  - "regime_bull_flip firing incorrectly"
  - "regime_bull_flip too aggressive"
  - "short signals losing"
  - "short win rate dropping"
  - "IMX SHORT closed immediately"
  - "TRB short closed in seconds"
  - "flip hzscore naming"
  - "hzscore+ should be long"
  - "analyze SHORT signal performance"
  - "best short signals"
---

**BEHAVIORAL: Match explanation to what T needs in that moment (2026-05-09)**

T asks a direct question ("which one is extra?") → give the direct answer ("none — the 16 columns are intentional"). NOT an architecture tour. If he seems confused, simplify. If he says "any luck" — show current counts/verification, not another explanation.

T says "let's get back to improving signals" → do NOT re-explain what was already built or debugged in prior turns. Just show the current state and what's needed to make it work.

**Scope enforcement**: If T says "we're going one by one through the scripts starting with signal-runner", review signal_runner.py ONLY. If he says "can you just look at X, not Y" → immediately drop Y. He had to repeat the same request twice (2026-05-08) because I kept branching into tangent areas. If you're about to explain something that isn't the script in question, you're branching.

**T's verification requirement**: When T says "call the ai-engineer to verify BEFORE making any changes", he means it. If you're unsure about a fix, call the ai-engineer first — not after applying the fix. Live PostgreSQL tests count as verification. Code review alone does not.

**Rule**: When T asks about a specific script/file/topic — do THAT task ONLY. Do not branch into related-but-different areas.

## ⚠️ BEHAVIORAL: Single-source signals — SOUL.md rule (2026-05-08)

**T's explicit rule**: "single source signals NEVER pass through the confluence gate." This was confirmed in the context of the live trading failure investigation where ENS/OG/BERA opened and closed on HL with no system trace.

**Why**: Single-source signals blocked by the confluence gate (requires 2+ unique signal types) never enter the hot-set → `get_approved_signals()` returns empty → `decider_run` executes nothing → HL positions open with no DB match → guardian orphan path fires → phantom DB records + stale closing markers → `_is_guardian_closing()` permanently blocks tokens in `decider_run`.

**T's trading philosophy**: "first candle against us we're out, book profit fast." Tighter SL (0.50-2.0%), faster TP (0.75-5.0%, k_tp ×1.25). Single-source signals stay PENDING/EXPIRED — this is intentional, not a bug.

## ⚠️ CONFLUENCE GATE — strict 2+ unique types, no bypass (2026-05-08)

**File:** `signal_compactor.py` lines 488-498

**Current gate logic:**
```python
if unique_signal_types >= 2:
    pass_gate = True
else:
    gate_msg = f'only {unique_signal_types} unique types {{{source}}} — need 2+'
    pass_gate = False
if not pass_gate:
    log(f"  🔒 [CONFLUENCE-GATE-BLOCK] {token} {direction}: {gate_msg}")
    continue  # signal is BLOCKED, never enters hot-set
```

**The `_signal_type_key()` function strips numeric levels** — `rs-s386` and `rs-s406` both collapse to `rs-s` (counts as 1 type). This means RS signals from multiple price levels do NOT contribute multiple unique types toward confluence.

**Why `accel-300+` is always blocked:** It fires on many tokens but `accel-300+` is a single signal type. In a typical 5-min window, nothing else fires on the same token+direction with sufficient overlap to merge. Result: every `accel-300+` signal hits `unique_signal_types=1` and gets blocked.

**Evidence from trading.log (2026-05-08, 17:09-17:37):**
```
ATOM LONG: only 1 unique types {accel-300+} — need 2+
DYM LONG: only 1 unique types {accel-300+} — need 2+
ENS LONG: only 1 unique types {accel-300+} — need 2+
```
Every token in the hot-set blocked simultaneously — this is the confluence gate, not individual signal quality.

**No bypass path exists.** The old CONFLUENCE_REQUIRED=False kill-switch was explicitly removed (T: "we don't want single source signals to pass, period"). If a single-source signal should ever pass, the gate itself must be restructured — adding a new bypass flag would repeat the same mistake.

**T's philosophy on single-source signals:** "first candle against us we're out, book profit fast" — tighter stops (SL 0.50-2.0%), faster profit-taking (TP 0.75-5.0%). This suggests single-source `accel-300+` with tight ATR stops might be acceptable even without confluence, but the gate enforces the 2-type requirement regardless.

The `archive-trades.py` DELETE is at lines 502-510:
```python
ids = [t['id'] for t in closed_trades]
cur.execute(f"DELETE FROM trades WHERE id IN ({placeholders})", ids)
conn_pg.commit()
```
If run with `--apply`, it archives to gzipped JSON then DELETES from PostgreSQL. Running it on a table that is the ONLY source of truth for open positions would wipe all position tracking.

**Impact on trades.json**: `update-trades-json.py` queries `WHERE status='open'` and `WHERE status='closed'`. If archiving deleted those rows, the dashboard shows 0 open/0 closed even though HL has live positions.

**Note**: `archive-trades.py` was created May 8 03:16, NOT in git (untracked file). Changes to it won't appear in `git diff HEAD`.

## P2: Orphan Recovery trade_id Collision (hl-sync-guardian.py)

**File:** `hl-sync-guardian.py`, `add_orphan_trade()`

Guardian orphan recovery uses hardcoded trade_id values:
```python
trade_id = 3000000  # first orphan
trade_id = 5000000  # second orphan
```

PostgreSQL `trades` table already has rows with `trade_id=3000000` (PURR) and `trade_id=5000000` (XLM). When guardian tries to record an orphan close:
```
[FAIL] Failed to create guardian_orphan record for 2Z: duplicate key value violates unique constraint "trades_trade_id_key"
DETAIL: Key (trade_id)=(3000000) already exists.
```

The orphan close still executes on Hyperliquid (the HL position is closed), but the PostgreSQL record is never written. This makes orphan recovery closes invisible to trades.html.

**Fix:** Use `SELECT MAX(id)+1 FROM trades` instead of hardcoded values, or use `ON CONFLICT DO NOTHING`.

**8-33 second trade lifetimes:** The open/close pairs on HL (BRETT, AXS, GALA, INJ, TAO, ATOM, LTC, ETH, CAKE, APEX, DYM, DASH, 2Z, AAVE, ENS) at 8-33 second intervals are **guardian orphan closes** — the guardian found real HL positions (from before the confluence gate change), tried to record them in DB, hit the trade_id collision, but still closed the HL positions. The closes shown are HL fills from guardian orphan recovery, not system entries.

# Hermes Signal Debugging

## Critical Bug Patterns

- **accel-300 loop start silently breaks detection** (Jun 2026): `ACCEL_300_LOOP_START = PERIOD + LOOKBACK` exceeded dataset size when LOOKBACK was raised to 500. Fix: loop start = `PERIOD + PERSISTENCE_BARS`. Full analysis in `references/accel-300-loop-start-bug-jun-2026.md`.

### P1: signals/rs.py — `_level_recently_broken` always returned False (2026-05-08)
**Root cause**: `_get_candles_1m()` synthesizes candles as `{'open':r[1], 'high':r[1], 'low':r[1], 'close':r[1]}` — open always equals close.
The function checked `opened < level < closed` — impossible with `open == close`.
**Fix**: Changed to compare successive candle closes for level crossing:
```python
# Resistance broken: prev_close < level < curr_close (price crossed above)
# Support broken:   prev_close > level > curr_close (price crossed below)
for i in range(1, len(recent)):
    prev_close = recent[i - 1]['close']
    curr_close = recent[i]['close']
    if prev_close < level < curr_close: return True
    if prev_close > level > curr_close: return True
```
**Guard fix**: Changed `len(candles) < lookback + 1` → `len(candles) < lookback` — the `+1` was
incorrectly added during the fix, causing the function to reject exactly `lookback` candles (e.g.,
3 candles with `lookback=3` would return False early instead of checking).

### P1: signals/rs.py — `_bounce_confirmation` replaced single-candle with two-candle logic (2026-05-08)
**Files:** `signals/rs.py` (current, canonical) vs `rs_signals.py` (original at d31692f)

**Original (d31692f: rs_signals.py lines 154-183) — EASIER:**
```python
if direction == 'LONG':
    for c in recent:
        touch_pct = abs(c['low'] - level) / level * 100.0
        if touch_pct < 0.20:           # wick touched level
            if c['close'] > c['open']:  # THIS candle was bullish → bounce
                return True
```

**Current (signals/rs.py lines 174-219) — HARDER:**
```python
if direction == 'LONG':
    for i, c in enumerate(recent):
        if abs(c['close'] - level) < thresh:  # close must be AT level (not wick)
            if i + 1 < len(recent):
                next_close = recent[i + 1]['close']
                if next_close > c['close'] * 1.0005:  # NEXT candle must move >0.05%
                    return True
```

**Two changes, both tightening:**
1. **Touch detection**: Old uses `low` (wick) — easy to satisfy even in chop. New uses `close` only — requires price to actually converge to the level. With close-only candles (open=high=low=close), this is a much harder condition.
2. **Direction confirmation**: Old checks THIS candle's direction (`close > open`). New requires the NEXT candle to move >0.05% in signal direction — a 2-candle sequence instead of 1.

**Result**: Old fired on ANY bullish candle that touched via wick. New requires price to be at the level AND the next candle to follow through — much stricter in ranging/choppy markets.

**Fix options** (user preference: "be careful, it was working really well"):
- **Option A (restore original)**: Use wick-touch + single-candle directional check. Matches May 6 behavior.
- **Option B (conservative middle)**: Keep close-touch detection but restore single-candle directional check.
- **Option C (keep sequential)**: Keep 2-candle logic but lower 0.05% to 0.01%.

**User's explicit constraint**: "be careful it was working really well" — the system WAS firing ~110 RS signals/cycle on May 6 with the original single-candle logic. The current code is the regression.

### Middle-ground fix: restored old single-candle condition (2026-05-08)
**Applied to:** `signals/rs.py`, `_bounce_confirmation` (lines 200-219)

**Three states of the bounce logic:**
1. **Original (rs_signals.py, d31692f)**: `if touch_pct < 0.20 and c['close'] > c['open']` — any bullish candle that wick-touches level. Fired prolifically on May 6 (~110/cycle).
2. **Current (signals/rs.py, d31692f)**: `abs(c['close']-level) < thresh AND next_close > c['close'] * 1.0005` — requires price to converge to level AND next candle to follow >0.05%. Much stricter; RS dropped to ~3/day in ranging markets.
3. **Middle-ground (applied 2026-05-08)**: Two conditions, either/or:
   - **(a)** touch candle is bullish (close > open) → fires immediately like original
   - **(b)** next candle moved >0.025% in signal direction → half the old threshold, catches partial follow-through

```python
# Applied fix:
if direction == 'LONG':
    for i, c in enumerate(recent):
        if abs(c['close'] - level) < thresh:
            if c['close'] > c['open']:       # condition (a): this candle was bullish
                return True
            if i + 1 < len(recent):
                if next_close > c['close'] * 1.00025:  # condition (b): next candle +0.025%
                    return True
```

**Result**: 59 RS signals per scan (vs ~3/day before). 3 bounce=True (passed both conditions),
56 bounce=False (passed condition (a) only, touch candle was directional but no follow-through).

**Note**: `scan_rs_signals` returns `(added, signaled_tokens)` where `signaled_tokens` is a list of
token strings. The signal COUNT is the first item. Do NOT parse the signal output strings to count —
use `cnt` from the return tuple.

**Confirm the fix is live**:
```bash
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0,'.')
from signal_schema import get_all_latest_prices
from signals.rs import scan_rs_signals
prices = get_all_latest_prices()
added, tokens = scan_rs_signals(prices)
print(f'RS signals: {added}')
"
```

### P1: signals/rs.py — bounce=True now achievable (2026-05-09 fix)
`_BOUNCE_THRESH_ATR=0.20` was 31-33x too tight for low-ATR tokens. For ADA (ATR=0.024%),
threshold was 0.0048% of price — noise-level. Result: every token showed `bounce=False`.

**Fix applied (2026-05-09):**
- `_BOUNCE_THRESH_ATR`: 0.20 → 1.00 (5x more forgiving)
- `RS_PROXIMITY_K`: 1.20 → 1.00 (fires closer to level = earlier entry)
- `RS_MIN_TOUCHES`: 5 → 8 (stronger structural levels only)

Result: bounce=True now achievable. BIGTIME first to achieve it. Signal count 11→8 (fewer, stronger).

Full trace + verification pattern: `references/rs-bounce-proximity-fixes-2026-05-09.md`

**Rule for ATR-normalized thresholds:** Always compute the absolute threshold value in price
terms for a representative low-ATR token before setting an ATR multiplier. A threshold of
`0.20 * ATR` that seems reasonable for BTC (ATR ~0.5%) becomes `0.10%`. For tokens with
ATR of `0.024%`, it becomes `0.0048%` — noise. The fallback path (`price * 0.0015`) was
31x wider, making the ATR-normalized path unreachable.

### P1: signals/hh_hl.py — breakout_threshold unit mismatch (2026-05-09)
**File:** `signals/hh_hl.py`, `_detect_breakout()` lines 236-245

`_classify_structure()` returns `breakout_strength` in **percent units** (e.g., 0.014 = 0.014%),
but `HH_HL_BREAKOUT_THRESHOLD = 0.0005` is in **decimal fraction** (= 0.05%). The comparison
`0.014 >= 0.0005` was always True — so AAVE fired on a 0.014% "breakout" when it needed 0.05%.

**Fix applied:**
```python
if structure == 'HH_HL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
```
After fix, only genuine 0.05%+ breakouts pass: AVAX(0.050%), POPCAT(0.053%), SAGA(0.050%).
AVAX/POPCAT/SAGA all at exactly 0.050% — the floor. User noted may want 0.08-0.10%.

Full trace in `references/hh-hl-threshold-bug-2026-05-09.md`.
**Pattern to prevent this:** Before comparing any threshold constant against a computed value:
(1) find where the computed value is created and check its unit, (2) find where the threshold
is defined and check its unit, (3) normalize before comparing. Variable names are not reliable
indicators of units — always trace the actual formula.

### P1: signals/rs.py — `_bounce_confirmation` produces `bounce=False` on every token (2026-05-09)
**Root cause**: `_BOUNCE_THRESH_ATR=0.20` creates impossibly tight thresholds for low-ATR tokens.
For ADA at price $0.272: ATR=0.0000653, threshold=0.000013 (0.0048% of price). Price must be
within 0.005% of the level to count as a touch. The fallback (`price * 0.0015 = 0.000408`) is
**31x wider** — the ATR-normalized path is 31x too tight to ever fire.

**Fix (2026-05-09, applied):**
- `_BOUNCE_THRESH_ATR`: 0.20 → 1.00 (5x more forgiving)
- `RS_MIN_TOUCHES`: 5 → 8 (stronger levels only)
- `RS_PROXIMITY_K`: 1.20 → 1.00 (closer to level = earlier entry)

**Result**: bounce=True now achievable. BIGTIME is first token to achieve it. Signal count
dropped from 11 → 8 tokens, which is the right direction (fewer, stronger).

### P1: signals/hh_hl.py — breakout_threshold unit mismatch (2026-05-09)
**File:** `signals/hh_hl.py`, `_detect_breakout()` lines 236-245

`_classify_structure()` returns `breakout_strength` in **percent units** (e.g., 0.014 = 0.014%),
but `HH_HL_BREAKOUT_THRESHOLD` in `hermes_constants.py` is in **decimal fraction** (0.0005 = 0.05%).
The comparison `0.014 >= 0.0005` was always True — so AAVE fired on a 0.014% "breakout" when it
needed 0.05%.

**Fix applied:** Normalize to same units before comparing:
```python
if structure == 'HH_HL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
```

Full trace in `references/hh-hl-threshold-bug-2026-05-09.md`.

### P2: signals/rs.py — unused `high_touch` variable and `window` parameter (2026-05-08)
`_build_level_touches()` had `window: int = None` parameter (never used) and computed
`high_touch = abs(c['high'] - level)` in the legacy path without using it. Removed both.

### ⚠️ Dual RS implementation — signals/rs.py vs rs_signals.py (2026-05-08)
Two implementations exist. The system uses `signals/rs.py` (canonical, post-fix).
`rs_signals.py` (552 lines, original) has different logic:
- **ATR band filter**: rs_signals.py has `_RS_ATR_BAND_SOFT_MIN/MAX` still **active** (rejects
  0.3–0.6 ATR band); signals/rs.py has it deprecated/commented out
- **`_level_recently_broken`**: rs_signals.py uses wick-cross logic (also broken on close-only data)
- **`_bounce_confirmation`**: rs_signals.py uses fixed 0.20% touch threshold; signals/rs.py uses
  ATR-normalized thresholds
- **`signaled_tokens` type**: rs_signals.py returns `list[str]` (correct); run_rs_signals.py
  unpacks as `list[tuple]` → crashes on first signal fire

Only `signals/rs.py` is in the live pipeline. rs_signals.py is deprecated.

### P0: r2_rev/r2_trend module name swap in name_to_module (2026-05-08)
**File:** `signals/__init__.py`, `name_to_module` dict
```python
'r2_rev': 'r2_trend',   # loads r2_trend.py — WRONG
'r2_trend': 'r2_rev',   # loads r2_rev.py — WRONG
```
Both map to `r2_rev.py` (import is from `r2_rev` at lines 131+136). Result: both
registry entries execute `r2_rev.py` code regardless of which signal name is invoked.
**Fix:** `r2_rev → r2_rev`, `r2_trend → r2_trend`.

### Two-dispatch system — `_run_signal()` is the ONLY dispatcher (2026-05-08)
The `run()` function on a module is **NOT optional** — it IS the dispatch target.

```python
def _run_signal(args):
    sig_name, module_name = args
    mod = __import__(f'signals.{module_name}', fromlist=['run'])
    fn = getattr(mod, 'run', None)  # ← only looks for 'run' attribute
    if fn is None:
        return sig_name, None       # ← SILENT SKIP, no log
    # fn called below with prices dict
```

The `signal['run']` field in SIGNAL_REGISTRY is **never called directly**. It's only used
as `is not None` check to filter out broken imports. The actual call chain:

```
signals_runner.run_all_signals()
  → ThreadPoolExecutor(21 workers)
    → _run_signal((name, module_name))
      → importlib.import_module(f'signals.{module_name}')
      → getattr(mod, 'run', None)   ← ONLY entry point
      → fn(prices)
```

**15 signals missing `run()` attribute but wired via registry? FALSE.** All 15 DO have
`run()` on the module (verified via `hasattr()` + import test). The grep for `^def run`
missed them because they use a different entry point convention. The authoritative
check is `getattr(mod, 'run', None)` in Python.

**2 signals not even in registry (dead code, never called):**
- `macd_1m` — not in SIGNAL_REGISTRY, not imported anywhere
- `ema20_50` — not in SIGNAL_REGISTRY, not imported anywhere

### P1: signals/rs.py — missing `run()` entry point, RS signals silently skipped (2026-05-08)
**File:** `signals/rs.py`

**_run_signal()** in `signals/__init__.py` dispatches via:
```python
mod = __import__(f'signals.{module_name}', fromlist=['run'])
fn = getattr(mod, 'run', None)  # ← scans for 'run' attribute
if fn is None:
    return sig_name, None        # ← SILENT SKIP, no log
```

`signals/rs.py` only exported `scan_rs_signals()` — no `run()` function existed.
Result: RS is registered (`RS_ENABLED=True`), appears in `get_registered_signals()`, but
always returns `None` and disappears. No error, no log — completely silent.

**Fix**: Add a `run()` wrapper to `signals/rs.py`:
```python
def run(prices_dict=None):
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices() if prices_dict is None else prices_dict
    added, tokens = scan_rs_signals(prices)
    return added
```

**Status: FIXED (2026-05-08)** — `run()` wrapper added at line 572.

**Detect silent skips:**
```python
# Compare registry size vs active size — any gap means broken import
from signals import SIGNAL_REGISTRY, get_registered_signals
print(f"Total registered: {len(SIGNAL_REGISTRY)}, Active: {len(get_registered_signals())}")
# Gap = broken imports or run=None entries

# Direct test — import each module and check for run()
import sys; sys.path.insert(0, '/root/.hermes/scripts')
for name in ['rs','atr_compression','ema9_sma20','guppy','hh_hl','macd_accel','ma_cross','trend_purity']:
    mod = __import__(f'signals.{name}', fromlist=['x'])
    has = hasattr(mod, 'run')
    print(f"{name}: run={'YES' if has else 'MISSING'}")
```

### P1: guppy has no `run()` function — always silently returns None (2026-05-08)
**File:** `signals/__init__.py`, import at line 110-113
```python
from signals.guppy import scan_all_tokens as _guppy_run  # guppy.py has scan_all_tokens, NOT run
```
`_run_signal()` does `getattr(mod, 'run', None)` — finds nothing → returns `(sig_name, None)`.
Guppy signal is registered and appears in `len(SIGNAL_REGISTRY)` but never actually runs.
**Pattern**: ALL signal modules must export a `run()` function — `signals_runner` specifically
looks for `run`, not `scan_all_tokens` or any other entry point.

### P1: momentum, mtf_momentum, phase_accel — None imports, unreachable (2026-05-08)
All three import `run` from their respective modules, but those modules don't export `run`:
```python
from signals.mtf_momentum import run as _mtf_momentum_run   # → None
from signals.momentum import run as _momentum_run           # → None
from signals.phase_accel import run as _phase_accel_run     # → None
```
`_*_run = None` → `get_registered_signals()` filters them out (run is None).
They are registered in SIGNAL_REGISTRY but completely unreachable via `run_all_signals()`.
**Fix**: Either add `run()` wrappers to those modules, or change the import to use the
actual entry point function name.

### ⚠️ `replace_all=True` bulk string replacement catches unintended lines (2026-05-08)
When patching time windows in SQL queries, `replace_all=True` can hit multiple occurrences
across different function contexts. Always read surrounding context before and after each
bulk replace to confirm each hit is intentional.

**Example**: `-15 minutes` → `-5 minutes` with `replace_all=True` hit 4 occurrences in
`signal_compactor.py` — but 2 were in `_score_signal()` (opposing-signal penalty context,
different semantics) and had to be manually reverted. The other 2 were the actual bugs
(`_get_opposing_penalty` line 258, GROUP BY query line 346).

**Always verify**: read context around each changed line, confirm the replacement is
correct for that specific query. A change that is correct in one SQL query may be
semantically wrong in another.

### P0: min_age_for_approval race condition — zero APPROVED signals (2026-05-08)
**File:** `signal_compactor.py` lines 979+

A 2026-05-07 uncommitted change added a minimum age gate for `accel-300+`:
```python
min_age_for_approval = 5.0  # signal must be ≥5 min old to be APPROVED
```
But signals EXPIRE at `age_m < 5.0` (line 1033). These are mutually exclusive — no
signal can satisfy both. Result: **0 APPROVED, 3,733 EXPIRED** in 6 hours.

**Verify:**
```sql
SELECT decision, COUNT(*) FROM signals GROUP BY decision;
```

**Fix:** Remove the gate entirely — hzscore is disabled (`HZSCORE_ENABLED=False`),
so there is no counter-signal for accel-300+ to wait for. The gate serves zero purpose.

### P0: ACCEL_300_TOKEN_ALLOWLIST — uncommitted, restricts to 23/191 tokens (2026-05-08)
**File:** `hermes_constants.py` (working copy only, NOT in git HEAD)

User does NOT recall adding this. It blocks `accel-300+` to only 23 tokens
(DASH, TON, GRIFFAIN, S, ADA, UNI, TRB, OP, ZK, XMR, TAO, XRP, COMP, PROMPT,
LINK, FIL, ETC, PURR, MERL, DYDX, ATOM, ONDO, 0G). ~168 other tokens are
completely blocked regardless of momentum.

**If T does not recall it:** `git diff hermes_constants.py` to confirm, then
`git restore hermes_constants.py` to revert to HEAD.

### P1: 11 of 14 registered signals returning 0 — investigation path (2026-05-08)
**Symptom:** `signal_compactor` last ran only 2 signals (accel_300, rs). 12 others
returned 0.

**Step 1 — What's in the DB:**
```sql
SELECT signal_type, direction, COUNT(*) n
FROM signals WHERE created_at > datetime('now', '-6 hours')
GROUP BY signal_type, direction ORDER BY n DESC;
```

**Step 2 — Which have working run() functions:**
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from signals import SIGNAL_REGISTRY, _resolve_enabled
for e in SIGNAL_REGISTRY:
    print(f"{'ON ' if _resolve_enabled(e) else 'OFF'} {e['name']:25s} run={'YES' if e.get('run') else 'NONE'}")
```

**Step 3 — *_ENABLED flags:**
```bash
grep "_ENABLED" /root/.hermes/scripts/hermes_constants.py | grep -v "^#"
```

**Known outages this session** (2026-05-08, 01:00-04:00 UTC):
- `mtf_zscore`, `percentile_rank`, `velocity`, `ma_cross_5m_long`, `ma_cross_5m_short`, `counter_flip` — all stopped within the same 3-hour window
- `accel_300` kept firing (partially restricted by ACCEL_300_TOKEN_ALLOWLIST)
- `rs` kept firing (confirmed working independently)

### P0: compact_hot_set() never called from main() — APPROVED queue permanently empty (2026-05-08)
**File:** `signal_compactor.py` — `main()` calls `process_pending_signals()` and
`expire_stale_signals()` but **never calls `compact_hot_set()`**.

The `compact_hot_set()` function (lines 990-1070) contains the `SET decision='APPROVED'`
SQL that promotes signals. Since main() never calls it, the APPROVED queue is
permanently empty. `decider_run.py` lines 922-944 reads `WHERE decision='PENDING'`
directly, so trades still execute — but they go PENDING→EXECUTED bypassing the
APPROVED promotion step entirely.

This is the reason GOOD_STANDALONE_SIGNALS bypass never worked: the bypass logic
that sets `decision='APPROVED'` is in a function that is never invoked.

### P1: CONFLUENCE_REQUIRED shadowed by local reassignment (2026-05-08)
`signal_compactor.py` line 26 imports `CONFLUENCE_REQUIRED` from `hermes_constants` (value `True`).
A dead local variable `CONFLOENCE_REQUIRED = True` existed at line 517 (now removed).
The imported `CONFLUENCE_REQUIRED` is correctly used at line 541. Removal confirmed clean.

### P2: _enrich_and_write_signals() and _preserve_previous_hotset() are dead code (2026-05-08)
Both functions are defined but never called anywhere in the codebase.
- `_enrich_and_write_signals()` (lines 1417-1537): was meant to write signals.json but
  that was intentionally moved to hermes-trades-api.py — function never deleted.
- `_preserve_previous_hotset()` (lines 1344-1414): preservation uses
  `_filter_safe_prev_hotset()` directly, this wrapper is never called.
Safe to delete both. No impact on current behavior.

### P1: GOOD_STANDALONE_SIGNALS audit — removals and gate fix (2026-05-08)
**File:** `signal_compactor.py`

**Removals (all failing the gate anyway):**
- `pct-hermes-`: WR=5%, avg=-0.449, total=-18.0 — losing on every metric, would never pass gate
- `hzscore+`: non-directional (in `NON_DIRECTIONAL_PREFIXES`), can't appear in `long_srcs`/`short_srcs`, can't pass gate as single-source
- `hzscore-`: same — non-directional, removed

**Correction:**
### P0: min_age_for_approval race condition — zero APPROVED signals (2026-05-08)
**File:** `signal_compactor.py` lines 979+

A 2026-05-07 uncommitted change added a minimum age gate for `accel-300+`:
```python
min_age_for_approval = 5.0  # signal must be ≥5 min old to be APPROVED
```
But signals EXPIRE at `age_m < 5.0` (line 1033). These are mutually exclusive — no
signal can satisfy both. Result: **0 APPROVED, 3,733 EXPIRED** in 6 hours.

**Verify:**
```sql
SELECT decision, COUNT(*) FROM signals GROUP BY decision;
```

**Fix:** Remove the gate entirely — hzscore is disabled (`HZSCORE_ENABLED=False`),
so there is no counter-signal for accel-300+ to wait for. The gate serves zero purpose.

### P0: ACCEL_300_TOKEN_ALLOWLIST — uncommitted, restricts to 23/191 tokens (2026-05-08)
**File:** `hermes_constants.py` (working copy only, NOT in git HEAD)

User does NOT recall adding this. It blocks `accel-300+` to only 23 tokens
(DASH, TON, GRIFFAIN, S, ADA, UNI, TRB, OP, ZK, XMR, TAO, XRP, COMP, PROMPT,
LINK, FIL, ETC, PURR, MERL, DYDX, ATOM, ONDO, 0G). ~168 other tokens are
completely blocked regardless of momentum.

**If T does not recall it:** `git diff hermes_constants.py` to confirm, then
`git restore hermes_constants.py` to revert to HEAD.

### P1: 11 of 14 registered signals returning 0 — investigation path (2026-05-08)
**Symptom:** `signal_compactor` last ran only 2 signals (accel_300, rs). 12 others
returned 0.

**Step 1 — What's in the DB:**
```sql
SELECT signal_type, direction, COUNT(*) n
FROM signals WHERE created_at > datetime('now', '-6 hours')
GROUP BY signal_type, direction ORDER BY n DESC;
```

**Step 2 — Which have working run() functions:**
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from signals import SIGNAL_REGISTRY, _resolve_enabled
for e in SIGNAL_REGISTRY:
    print(f"{'ON ' if _resolve_enabled(e) else 'OFF'} {e['name']:25s} run={'YES' if e.get('run') else 'NONE'}")
```

**Step 3 — *_ENABLED flags:**
```bash
grep "_ENABLED" /root/.hermes/scripts/hermes_constants.py | grep -v "^#"
```

**Known outages this session** (2026-05-08, 01:00-04:00 UTC):
- `mtf_zscore`, `percentile_rank`, `velocity`, `ma_cross_5m_long`, `ma_cross_5m_short`, `counter_flip` — all stopped within the same 3-hour window
- `accel_300` kept firing (partially restricted by ACCEL_300_TOKEN_ALLOWLIST)
- `rs` kept firing (confirmed working independently)

### P0: compact_hot_set() never called from main() — APPROVED queue permanently empty (2026-05-08)
**File:** `signal_compactor.py` — `main()` calls `process_pending_signals()` and
`expire_stale_signals()` but **never calls `compact_hot_set()`**.

The `compact_hot_set()` function (lines 990-1070) contains the `SET decision='APPROVED'`
SQL that promotes signals. Since main() never calls it, the APPROVED queue is
permanently empty. `decider_run.py` lines 922-944 reads `WHERE decision='PENDING'`
directly, so trades still execute — but they go PENDING→EXECUTED bypassing the
APPROVED promotion step entirely.

This is the reason GOOD_STANDALONE_SIGNALS bypass never worked: the bypass logic
that sets `decision='APPROVED'` is in a function that is never invoked.

### P1: CONFLUENCE_REQUIRED shadowed by local reassignment (2026-05-08)
`signal_compactor.py` line 26 imports `CONFLUENCE_REQUIRED` from `hermes_constants` (value `True`).
A dead local variable `CONFLOENCE_REQUIRED = True` existed at line 517 (now removed).
The imported `CONFLUENCE_REQUIRED` is correctly used at line 541. Removal confirmed clean.

### P2: _enrich_and_write_signals() and _preserve_previous_hotset() are dead code (2026-05-08)
Both functions are defined but never called anywhere in the codebase.
- `_enrich_and_write_signals()` (lines 1417-1537): was meant to write signals.json but
  that was intentionally moved to hermes-trades-api.py — function never deleted.
- `_preserve_previous_hotset()` (lines 1344-1414): preservation uses
  `_filter_safe_prev_hotset()` directly, this wrapper is never called.
Safe to delete both. No impact on current behavior.

### P2: unique_tokens computed but never used (2026-05-08)
**File:** `signal_compactor.py` line 590:
```python
unique_tokens = list({s[0].upper() for s in signals})
```
Populated but never referenced — regime lookups happen per-signal inside the loop.
Dead variable, not a bug but indicates incomplete refactor.

### P2: Silent None on missing run() — no error logged (2026-05-08)
**File:** `signals/__init__.py`, `_run_signal()`:
```python
if fn is None:
    return sig_name, None   # silent, no log
```
Signal that has no `run` function silently produces `None` and disappears from results.
**Detect**: `len(SIGNAL_REGISTRY)` vs `len(get_registered_signals())` — any gap means
a signal has `run=None` (broken import or missing entry point).

### Dual-flag confusion: registry `enabled=True` but hermes_constants says `False` (2026-05-08)
The SIGNAL_REGISTRY had hardcoded `{'enabled': True}` for 8 signals (`pct_hermes`, `vel_hermes`,
`hzscore`, `hmacd`, `mtf_momentum`, `momentum`, `phase_accel`, `fast_momentum`), while their
`*_ENABLED` flags in `hermes_constants` were `False`. This created **two places to check**
to understand why a signal wasn't running — exactly the kind of duplication that causes bugs
when T toggles a flag without realizing the registry was overriding it.

**T's exact words**: "we need to fine-tune it, mainly if blocked in hermes_constants it should
import that flag and stay blocked, I can't be hunting two flags for the same script"

This is the core user preference: **one flag per signal, no dual-control**. Every signal's
enabled/disabled state must trace back to exactly one source of truth in `hermes_constants.py`.

**Fix (2026-05-08)**: Store the flag name as a string in the registry entry. Resolve it
dynamically at access time via `_resolve_enabled()`:

```python
# In SIGNAL_REGISTRY entries:
{'name': 'pct_hermes', 'enabled': 'PCT_HERMES_ENABLED', 'run': _pct_hermes_run}

def _resolve_enabled(entry):
    import hermes_constants as hc
    enabled = entry['enabled']
    if isinstance(enabled, str):
        return getattr(hc, enabled, False)
    return enabled

def get_registered_signals():
    return [s for s in SIGNAL_REGISTRY if _resolve_enabled(s) and s['run'] is not None]
```

Now there is **one flag per signal**: `hermes_constants.PCT_HERMES_ENABLED = False` → signal
never runs. No registry override to hunt.

### Verify a signal's enabled state resolves correctly from hermes_constants (2026-05-08)
```python
cd /root/.hermes/scripts && python3 -c "
from signals import SIGNAL_REGISTRY, _resolve_enabled
import hermes_constants as hc

for e in SIGNAL_REGISTRY:
    if isinstance(e['enabled'], str):
        flag_name = e['enabled']
        resolved = _resolve_enabled(e)
        real = getattr(hc, flag_name, 'MISSING')
        match = 'OK' if resolved == real else 'MISMATCH'
        print(f'{match} {e[\"name\"]:20s} {flag_name}={resolved}')
"
# Should print OK for all 8 flag-mapped signals
# FAST signals running: only those with *_ENABLED=True in hermes_constants
# SLOW signals: momentum + mtf_momentum (if their flags are True)
```

### `register_signal()` hardcodes `enabled: True` — same dual-flag problem (2026-05-08)
Dynamic signal injection via `register_signal(name, run_fn)` always set `{'enabled': True}`.
If T disabled a signal in `hermes_constants`, injecting it at runtime would bypass that flag.
**Fix (2026-05-08)**: `register_signal(name, run_fn, enabled=True)` now accepts an optional
`enabled` param. Pass a flag name string to stay consistent: `register_signal('my_sig', fn, enabled='MY_SIG_ENABLED')`.

### `run_all_signals(prices_dict=None, ...)` — dead parameter (2026-05-08)
`prices_dict` was accepted but completely ignored. Always fell back to `get_registered_signals()`.
No callers passed it — confirmed by searching the entire codebase. Removed from signature.
If a future caller needs to pass a prices dict, the function needs a real implementation.

### ⚠️ Threshold constant unit mismatch — always verify before comparing (2026-05-09)
**Pattern:** A function computes a value in one unit (e.g., percent), and a threshold constant
is defined in a different unit (e.g., decimal fraction) in `hermes_constants.py`. The comparison
silently passes when it shouldn't.

## ⚠️ Diagonal trendline direction — anchor at START, not END (2026-05-09)
**File:** `signals/tl_break.py` — diagonal breakout signal

When building a diagonal trendline breakout signal, the trendline must be anchored at the
**START of the lookback window**, not the END:

```python
# WRONG — anchor at END (trendline floats above breakout zone):
start_price = closes[diag_end - 1]
slope = (closes[-1] - closes[diag_end - 1]) / (diag_end - 1)

# CORRECT — anchor at START (trendline is a real resistance/support line):
start_price = closes[0]
slope = (closes[diag_end - 1] - closes[0]) / (diag_end - 1)
```

Anchor-at-end projects the diagonal forward from the end, placing it in the current price zone.
If the diagonal slopes down, the projected line sits near current price — no bounces detected
because price hasn't had room to bounce against it. Anchor-at-start projects backward, making
the diagonal a proper historical level that price consolidated against.

**Direction from breakout, not from diagonal slope:** A down-sloping diagonal can produce
a SHORT (if price breaks below) or a LONG (if price breaks above). The diagonal is the
consolidation pattern; the breakout direction determines the trade:

```python
# Down-slope diagonal (start > end): price oscillates below it
# → break ABOVE diagonal = LONG,  break BELOW diagonal = SHORT

# Up-slope diagonal (start < end): price oscillates above it
# → break BELOW diagonal = SHORT, break ABOVE diagonal = LONG
```

**Pairwise bounce clustering:** Original code only checked adjacent sorted bounces. With 3+
bounces (e.g., OP with 7), non-adjacent pairs can be tighter. Always use O(n²) pairwise
search for any 2 bounces within `3 × ATR`:

```python
def _cluster_bounces_simple(bounces, atr, max_price, min_price):
    """Find any pair of bounces within 3*ATR — not just adjacent pairs."""
    for i in range(len(bounces)):
        for j in range(i + 1, len(bounces)):
            if abs(bounces[i]['price'] - bounces[j]['price']) <= 3 * atr:
                return (bounces[i]['price'] + bounces[j]['price']) / 2
    return None
```

**Bounce direction must match signal direction:** When counting touches, a LONG requires
price BELOW diagonal then next candle ABOVE. A SHORT requires price ABOVE diagonal then
next candle BELOW. Inferring bounce direction from the diagonal slope is wrong — use the
signal `direction` param instead.

### accel-300+ fires late at peaks — root causes and fixes (2026-05-09)
**Symptom**: accel-300+ fires when momentum has already peaked, position immediately reverses

**Root Cause — STRONG gap growth = WORSE win rate:**
- gap_growth >= 0.20%: 20% WR, avg -0.124% (catching the peak)
- gap_growth < 0.10%: 44.4% WR, avg +1.052% (fresh breakouts)

**Two-phase timing fix (applied 2026-05-10, accel_300.py lines 251-292):**
1. **Bars 0-3 (fresh breakouts):** Fire on gap_growth alone — no marginal acceleration check
2. **Bars 4-10 (extended):** Require marginal acceleration — `delta_last > delta_prev`
3. **Bars > 10 (stale):** Block entirely

**Key params (eased from overly tight):** `MIN_GAP_PCT`: 0.20→0.15, `MIN_GAP_GROWTH_PCT`: 0.05→0.03, `COOLDOWN_BARS`: 10→12

### RS co-signal quality: touch count vs PnL — fire on FRESH levels (2026-05-10)
**Problem**: RS fires on ancient macro levels (264-12,284 touches) instead of reactive bounces (8-50 touches).

**Evidence from 38 accel-300+ trades:**

| RS Touch Count | Win Rate | Avg PnL |
|---|---|---|
| 1-20 touches | **44%** | **+0.80%** |
| 21-50 | 18% | +0.24% |
| 51-100 | 20% | +0.47% |
| 100+ | 40% | +0.02% |
| No RS co-signal | 33% | +0.90% |

**8 big winners** (all LONG, accel-300+): S+4%, ASTER+3.6%, MON+3.4%, FET+3.2%, ETH+3.1%, APEX+2.2%, ORDI+1.8%, 0G+1.7% — RS co-signals had 8, 84, 36, 34, (none), 8, 10, 112 touches. **Sweet spot: 8-36 touches.**

**Fixes:** Lower `RS_PROXIMITY_K 1.00→0.70` (fire when price within 0.7 ATR of level). Add recency bonus to confidence so recent touches score higher than ancient ones.

**⚠️ trades.json field names**: `t['signal']` (NOT `source`), `t['pnl_pct']` (NOT `pnl`), `t['coin']` (NOT `token`).

### Silent import failures — broken signal module = silent disappearance (2026-05-08)
Each signal's `run` is set to `None` inside a bare `except Exception:` block on import.
If a signal module is broken, it silently disappears from the registry with no warning.
The runner logs "no signals to run" only if the list is empty, not if one signal was silently dropped.
**Pattern to detect**: compare `len(SIGNAL_REGISTRY)` vs `len(get_registered_signals())` —
any gap means a signal has `run=None` (either import failed or run function is absent).

### signal_runner.py is almost never the culprit (2026-05-08)
**File:** `/root/.hermes/scripts/signals_runner.py` (83 lines)

Verified clean: it correctly calls all 14 registered signals via `_run_signal()`,
passes `prices_dict` to 1-arg functions, calls 0-arg functions without args, and
logs non-None results. If the pipeline log shows 0 signals or wrong signal counts,
the runner itself is not the problem — the individual signal module's `run()` is
returning `None`, `0`, or an empty list.

**Diagnostic**: `signals_runner.py` logs `Signal {name}: {result}` only when
`result is not None`. A signal returning `None`, `0`, or `[]` is invisible in
the pipeline log. Always check the signal module directly before blaming the runner.

### Every signal module MUST have a `run()` function (2026-05-07)
`signals_runner` uses `getattr(mod, 'run', None)` — if the module has no `run()`, the
signal is **silently skipped** every cycle with no error or log. Most dangerous class of bug
because the signal appears enabled/registered but never fires.

**13 signals were affected** (found 2026-05-07): `rs`, `ma_cross`, `ma_cross_5m`,
`hh_hl`, `guppy`, `macd_accel`, `trend_purity`, `phase_accel`, `fast_momentum`,
`momentum`, `mtf_momentum`, `hmacd`, `accel_300`.

Also: `hzscore.py` had a second silent failure mode — `avg_z` referenced at line 126
but not assigned until line 132 → `UnboundLocalError` on every token. `run()` existed
but always crashed. Fixed by moving `avg_z = statistics.mean(valid_z)` before the check.

**Pattern** — every signal module needs:
```python
def run() -> int:
    prices = get_all_latest_prices()
    return scan_xxx_signals(prices)
```

**Verify**: `hasattr(module, 'run')` must return True for all registered signals.

### `ma_cross_5m` silently fails if tuner DB dir doesn't exist (2026-05-07)
`_TUNER_DB = os.path.join(DATA_DIR, 'ma_cross_5m_tuner.db')` — if `DATA_DIR` doesn't
exist as a directory (e.g. `/root/.hermes/scripts/data/` was never created), the
`sqlite3.connect()` call fails with `OperationalError: unable to open database file`.
The fix: `os.makedirs(DATA_DIR, exist_ok=True)` before the connect call.

### Signals fire on disjoint token sets — check overlap before assuming combos can form (2026-05-07)
`hzscore+` (~20 tokens) and `pct-hermes-` (~46 tokens) have near-zero overlap in runtime.
Even with 15-min windows, they almost never produce a merged combo on the same token.
The `accel-300+`/`hzscore-` LONG combo works because they fire on the same tokens.
Before designing a combo, verify the component signals actually share token universes:
```python
rc.execute("SELECT DISTINCT token FROM signals WHERE signal_type='hzscore' AND direction='SHORT' AND created_at>datetime('now','-2h')")
hzscore_tokens = set(r[0] for r in rc.fetchall())
rc.execute("SELECT DISTINCT token FROM signals WHERE signal_type='percentile_rank' AND direction='SHORT' AND created_at>datetime('now','-2h')")
pct_tokens = set(r[0] for r in rc.fetchall())
overlap = hzscore_tokens & pct_tokens
print(f"hzscore: {len(hzscore_tokens)}, pct: {len(pct_tokens)}, overlap: {overlap}")
```

### Minimum age before approval — prevent fast-firing signals from dominating (2026-05-07)
`accel-300+` fires every 1 minute, hits top-10 in 3 minutes, gets approved before
`hzscore-` (fires every 5 min) can merge. Add minimum age gate:
```python
if age_m < 5.0 and 'accel-300+' in source:
    still_pending_ids.append(sid)  # wait for hzscore- to potentially merge
    continue
```

### ⚠️ Pct-hermes- standalone: 0% WR, 32 trades (2026-05-07 live audit)
Old baseline said 23% WR / -$0.32 from 13 trades. Live data: **0% WR, -52.3% avg_pnl
across 32 trades.** Much worse than the old small-sample audit suggested. Still in
GOOD_STANDALONE_SIGNALS with `{'wr': 35}` — that WR is stale. Remove it from
GOOD_STANDALONE_SIGNALS or at minimum verify with live SQL before trusting.

### Small sample fallacy — never add to GOOD_STANDALONE_SIGNALS < 30 trades
pct-hermes+ was added based on 3 trades at 100% WR. Live: 4.7% WR. The
WR threshold check (`info['avg'] >= 0`) is a financial gate — cannot be calibrated
on 3 samples. Enforce minimum 30-trade sample before adding any signal to
GOOD_STANDALONE_SIGNALS.

### ⚠️ pct-hermes+ in GOOD_STANDALONE_SIGNALS — REMOVE IT (2026-05-07)
pct-hermes+ was added to GOOD_STANDALONE_SIGNALS based on a 3-trade sample (100% WR, +$2.31).
Live outcome data tells a different story: **64 trades, 4.7% WR, -52.9% avg_pnl**.
This is not a "good" signal by any definition. Remove it:
```python
# WRONG — added 2026-05-07 based on 3 trades, must be removed:
'pct-hermes+':   {'wr': 100, 'avg': 0.770, 'dir': 'LONG'},   # 64 trades, 4.7% WR
```
**Rule: never add a signal to GOOD_STANDALONE_SIGNALS with fewer than 30+ trades.**
Even with 30 trades, require WR >= 40% AND avg_pnl > 0.

### pct-hermes+ all EXPIRED — missing GOOD_STANDALONE_SIGNALS entry (2026-05-07)
1,759 pct-hermes+ signals fired in 6h, 100% EXPIRED, 0 PENDING. Root cause: pct-hermes+ was NOT in GOOD_STANDALONE_SIGNALS, so single-source pct-hermes+ signals could not pass the confluence gate without a 2nd co-signal type. The compactor requires single-source signals to be explicitly listed in GOOD_STANDALONE_SIGNALS to bypass the co-signal requirement.
- pct-hermes-: ~4,980 fires/2h (SHORT)
- pct-hermes+: ~1,759 fires/2h (LONG)
- hzscore-: ~5,401 fires/2h (almost all expire before merging)
- accel-300+: only ~142 fires/2h (token allowlist limits it)
- vel-hermes: ~252 fires/2h (avg_z filter rarely satisfied)

When signals fire on disjoint token sets or at different frequencies, merging rarely occurs even within a 5-min window. Adding pct-hermes+ as a standalone allows LONG signals to reach the hot-set without requiring a co-signal to merge within the window.

### Patching SQL strings — use replace_all=True (2026-05-07)
When changing time windows in SQL queries, the patch must target the SQL line,
not just the log message. Always verify: run the compaction and confirm the log
output shows the new window size (e.g., `X combo_keys in 15-min window`).

### pct-hermes- is a losing standalone signal (2026-05-07)
Despite passing the confluence gate (35% WR, +0.22% avg historically), pct-hermes-
standalone was the worst performer in trades.json (13 trades, 23% WR, -$0.32).
Remove from GOOD_STANDALONE_SIGNALS — requires a co-signal.

### accel-300+ approved too fast — needs minimum age (2026-05-07)
accel-300+,hzscore- (42% WR, $10.47) is the best combo. But accel-300+ standalone
(31% WR, $3.45) gets approved in 3 minutes before hzscore- can merge (fires every 5 min).
Fix: add minimum 5-minute age check before approving accel-300+.

## ⚠️ Confluence Not Working — Root Cause Debugging (2026-05-08)

### The Core Problem: signal_gen fires signals sequentially, each creating its own combo_key

`signal_gen` fires each signal source in its own cycle:
- Cycle N: `accel-300+` fires → writes `combo_key="TON:LONG:accel-300+"` → PENDING
- Cycle N+1: `RS` fires → writes `combo_key="TON:LONG:rs-s48"` → different row

**Result**: RS and accel-300+ are NEVER in the same combo_key row. `GROUP_CONCAT(DISTINCT source)` never merges them in the compactor's GROUP BY query.

**Evidence** (live DB):
```sql
-- All BOTH accel_300 + RS in last 60 min — all EXPIRED, all compact_rounds=0:
TON:LONG:accel-300+,rs-s48  EXPIRED (created=15:50, conf=81)
TAO:LONG:accel-300+,rs-s96  EXPIRED (created=15:50, conf=81)
S:LONG:accel-300+,rs-s8     EXPIRED (created=15:50, conf=79)
LINK:LONG:accel-300+,rs-s27 EXPIRED (created=15:50, conf=70)
```

These merged signals DO exist (signal_types='accel_300_long,support_resistance') — the `add_signal()` merge logic works. But they expire before reaching hot-set.

### Why merged signals expire

1. **Created at `:04`** — RS fires within 1-2 min of accel-300+, merge happens
2. **Compact_rounds=0** — never cycled through the compactor's staleness check before expiring
3. **APPROVED flow broken** — `compact_hot_set()` was NEVER called from `signal_compactor.main()`
   (fixed 2026-05-08: now called)

### 5-minute age gate issue (2026-05-08)

`signal_compactor.py` line 999: merged signals need to be **5+ minutes old** before APPROVED:
```python
if age_m < min_age:
    still_pending_ids.append(sid)  # keep PENDING, don't approve
```

For `accel-300+`: `min_age=5.0` minutes. This gives other signals time to merge before approval.
BUT: signals with only `accel-300+` (single-source) also pass GOOD_STANDALONE_SIGNALS and get approved after 5 min — flooding hot-set with single-source entries.

### Current hot-set: all single-source (2026-05-08)

```
/var/www/hermes/data/hotset.json — 10 entries:
  DASH:LONG:accel-300+   (rounds=1, score=74.3)
  ETC:LONG:accel-300+    (rounds=1, score=64.6)
  DYDX:LONG:accel-300+   (rounds=1, score=64.6)
  COMP:LONG:accel-300+   (rounds=1, score=64.6)
  ...
  UNI:LONG:accel-300+    (rounds=4, score=19.5)
  SUSHI:LONG:accel-300+  (rounds=4, score=19.5)
```

**Zero merged combos** (accel-300+,rs-sNN) in current hot-set.

### User's goal: "hot-set should only allow signals for coins that have confluence"

**Fix options**:
1. **Remove `accel-300+` from GOOD_STANDALONE_SIGNALS** — requires confluence (2+ signal types OR RS co-signal)
2. **Relax age gate** — merged signals get approved faster before single-source dominates
3. **Short-circuit approval for RS-merged combos** — if combo has RS, approve immediately

**Applied fix (2026-05-08)**: Removed 23-token ACCEL_300_TOKEN_ALLOWLIST (uncommitted change, not in git HEAD). Set to `set()` for no filter.

### Diagnostic SQL — check confluence in real-time

```python
import sqlite3
con = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = con.cursor()

# Check merged signals (2+ signal types)
cur.execute("""
    SELECT token, direction, signal_types, source, combo_key, decision,
           created_at, compact_rounds
    FROM signals
    WHERE created_at > datetime('now', '-30 minutes')
    AND signal_types LIKE '%,%'
    ORDER BY created_at DESC
""")

# Check combo_keys with both accel and rs
cur.execute("""
    SELECT combo_key, signal_type, COUNT(*) cnt
    FROM signals
    WHERE created_at > datetime('now', '-10 minutes')
    AND combo_key LIKE '%accel-300+%'
    AND combo_key LIKE '%rs-%'
    GROUP BY combo_key
""")

# Hot-set source diversity
import json
with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)
for e in hs['hotset']:
    src = e.get('source', '')
    print(f"  {e['token']:8s} src={src}")
```

## Core Workflow

### Diagnosing empty or degraded hot-set (in order)

1. **Check what's actually firing**:
```python
import sqlite3
rconn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
rc = rconn.cursor()
rc.execute("""
    SELECT signal_type, direction, COUNT(*) as n
    FROM signals WHERE created_at > datetime('now', '-30 minutes')
    GROUP BY signal_type, direction ORDER BY n DESC
""")
for r in rc.fetchall(): print(f"  {r[0]}({r[1]}): {r[2]}")
```

2. **Check which signals have run()**:
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
for mod_name in ['pct_hermes','vel_hermes','hzscore','accel_300','rs','ma_cross_5m']:
    mod = __import__(f'signals.{mod_name}', fromlist=[''])
    print(f"{mod_name}: run={'YES' if hasattr(mod,'run') else 'MISSING'}")
```

3. **Check hot-set content**:
```python
import json
with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)
for e in sorted(hs['hotset'], key=lambda x: x.get('confidence',0), reverse=True):
    print(f"  {e.get('token')} {e.get('direction')}: conf={e.get('confidence')} src={e.get('source')}")
```

4. **Check trades.json signal breakdown**:
```python
import json
from collections import defaultdict
with open('/var/www/hermes/data/trades.json') as f:
    t = json.load(f)
closed = t.get('closed', [])
by_sig = defaultdict(lambda: {'n':0,'wins':0,'pnl':0.0})
for trade in closed:
    sig = trade.get('signal','unknown')
    by_sig[sig]['n'] += 1
    by_sig[sig]['wins'] += 1 if trade.get('pnl_pct',0) > 0 else 0
    by_sig[sig]['pnl'] += trade.get('pnl_usdt', 0)
for sig, d in sorted(by_sig.items(), key=lambda x: x[1]['pnl'], reverse=True):
    n, w, pnl = d['n'], d['wins'], d['pnl']
    print(f"  {sig[:50]:50s}: n={n:3d} WR={w/max(1,n)*100:4.0f}% ${pnl:+.2f}")
```

## ⚠️ CRITICAL: Baseline Data Is Stale (2026-05-07 Live Audit)
The trades.json baseline (200 trades) is **actively misleading**. Live signal_outcomes
(3,280 trades, runtime DB) paint a much darker picture:

**Overall system: 11.2% WR across 3,280 trades. Nearly everything loses money.**

### Live Outcomes (runtime DB — 2026-05-07, all trades)
```sql
-- Best by WR (min 10 trades)
SELECT signal_type, direction, COUNT(*) cnt, SUM(is_win) wins,
       ROUND(100.0*SUM(is_win)/COUNT(*),1) wr,
       ROUND(100.0*AVG(pnl_pct),3) avg_pnl
FROM signal_outcomes
GROUP BY signal_type, direction
HAVING cnt >= 10
ORDER BY wr DESC, avg_pnl DESC;

-- Overall system WR
SELECT COUNT(*) total,
       ROUND(100.0*SUM(is_win)/COUNT(*),1) overall_wr,
       ROUND(100.0*AVG(pnl_pct),3) overall_avg_pnl
FROM signal_outcomes;
```

**Live results (runtime DB, ~3,280 trades):**
| Signal | Trades | WR | avg_pnl% |
|--------|--------|-----|----------|
| `hl_reconcile` SHORT | 35 | 57.1% | -1453% (!) |
| `hzscore-,pct-hermes-` SHORT | 26 | 34.6% | -4.9% |
| `hzscore+,pct-hermes+,vel-hermes+` LONG | 38 | 23.7% | -31.9% |
| `ma-cross-5m-long,pct-hermes+` LONG | 38 | 21.1% | -49.0% |
| `hzscore+` SHORT | 73 | 20.5% | -33.8% |
| `accel-300+` LONG | 42 | 19.0% | -27.0% |
| `phase-accel+` LONG | 9 | low-n | tiny sample |
| `pct-hermes+` LONG | 64 | **4.7%** | -52.9% |

**WR Collapse Timeline:**
| Period | WR | Trades |
|--------|-----|--------|
| Mar 11-30 | ~53% | ~200 |
| Apr 1-20 | ~25% | ~400 |
| Apr 21-30 | ~14% | ~500 |
| May 5-7 | ~0% | ~100 |

The collapse is regime-driven, not purely a signal calibration problem. The market shifted from range-bound to strong bullish continuation. SHORTS get destroyed; accel-300+ fires near momentum peaks that reverse.

**Key findings:**
- `pct-hermes+` (added to GOOD_STANDALONE_SIGNALS 2026-05-07): **4.7% WR, 64 trades** — NOT good, remove it
- `accel-300+,hzscore-` combo: 52 trades, 15.4% WR, -35.7% avg_pnl (not the +$10.47 the old baseline claimed)
- `pct-hermes-` solo: 32 trades, **0% WR** (was 23% in old baseline)
- `hl_reconcile` has 57% WR but -1453% avg_pnl — one or two catastrophic trades
- Overall system is losing badly across nearly all signal types

### Action: GOOD_STANDALONE_SIGNALS WR Data Is Unreliable
The hardcoded `{'wr': XX, 'avg': Y.Y}` in signal_compactor.py line ~471 comes from
a 2026-05-06 audit. Live outcomes differ substantially. Always re-audit with the SQL
above before trusting or updating those values.

**The pct-hermes+ entry (`'wr': 100, 'avg': 0.770`) was added based on 3 trades — a
small-sample fallacy. It should NOT be in GOOD_STANDALONE_SIGNALS.**

## ⚠️ P0: ENS/OG/BERA/LINEA/LAYER/BRETT/SNX/ORDI — Confirmed Orphan Chain (2026-05-08)

**What we know for certain:**
- HL history confirms LAYER, BRETT, LINEA, ORDI, SNX opened on HL between 21:21-21:27
- PostgreSQL `trades` table: ZERO records for any of these tokens
- Guardian log: `[PASS] LAYER closed (guardian_orphan)`, same for LINEA, ORDI, SNX
- Guardian orphan INSERT fails: `duplicate key violates trades_trade_id_key` — trade_id=3000000 owned by PURR (id=8780)
- Pipeline log shows `EXEC: LINEA LONG @ $0.004163 conf=99%` but no PostgreSQL INSERT followed

**What remains UNCONFIRMED:**
- Whether ENS/OG/BERA actually opened on HL (HL history not shown for them)
- Whether their PostgreSQL INSERTs failed and mirror_close rollbacks also failed
- Whether they went through the guardian orphan path

**The confirmed orphan path:**
```
decider_run atomic claim passes → execute_trade → brain.py
→ mirror_open() succeeds on HL
→ PostgreSQL INSERT fails (reason unknown — not trade_id collision for these tokens)
→ mirror_close() rollback attempted → if failed → ORPHAN on HL
→ Guardian detects orphan → closes HL position
→ No DB record created (INSERT already failed)
```

**The trade_id collision is only for guardian's OWN INSERT**, not the decider_run path. Guardian's orphan INSERT uses `trade_id = lev * 1000000`. PURR (lev=3) owns trade_id=3000000. When guardian tries to INSERT its own `guardian_orphan` record for any lev=3 token, it collides.

**The real unanswered question:** Why did PostgreSQL INSERT fail for these tokens? The INSERT has 39 columns and 39 values. If the count mismatched, we'd see a Python/psycopg2 error. If a constraint failed, we'd see a specific constraint error. The error chain suggests a silent failure mode we haven't reproduced in isolation.

**When investigating this:** Check pipeline.log for `[brain.py] ✅` confirmation — absence means brain.py was never reached or INSERT failed silently.

## How to Review a Script for T

T does systematic code review — going through scripts one-by-one. When he gives a
behavioral spec ("signals expire in 5 mins unless they find confluence"), he means
**implement that spec**, not explain what the existing code does. If the code does
something different, fix it first, then explain what changed.

T's workflow: (1) confirm the intended behavior, (2) make the code match, (3) verify
the change is clean. He doesn't want a tour of the broken logic before the fix.

**On patching SQL strings with `replace_all=True`**: always verify each replacement
was intentional. Bulk string replacements catch unintended hits — read context before
confirming each change is correct.

### Never add to GOOD_STANDALONE_SIGNALS with < 30 trades
pct-hermes+ was added based on 3 trades at 100% WR (+$2.31). Live: 64 trades,
4.7% WR. The avg_pnl gate (>= 0) failed because 3 trades can never establish a
reliable avg_pnl. Enforce 30-trade minimum before adding any signal to the list.

### Hardcoded WR values in signal_compactor.py are stale by definition
They are audited periodically (last: 2026-05-06), but live outcomes change daily.
Before trusting or updating GOOD_STANDALONE_SIGNALS values, always run the live
SQL query. Do not use the hardcoded values as ground truth.

### Adding a signal to GOOD_STANDALONE_SIGNALS is not free
It lets that signal pass the confluence gate *without* any co-signal. If the signal
has poor WR, it floods the hot-set with losing entries. Always verify live WR >= 40%
See: `references/rs-rs-broken-confluence-collapse-2026-06-02.md`

### accel-300-,rs-s-broken STILL passes confluence (NEW 2026-06-03)
`accel-300-` and `rs` are different families → 2 unique types → passes, 38% WR worst combo.
See: `references/accel-300-rs-broken-confluence-hole-2026-06-03.md`

### Everything losing might be an ATR SL problem, not a signal problem
ATR SL was raised from 0.15%/0.30% to **0.50%/1.0%** on 2026-05-07
(`ATR_SL_MIN=0.005`, `ATR_SL_MAX=0.010` in hermes_constants.py).
Previous loss data may not reflect post-change behavior. A signal that stopped out at
0.15% SL might win at 0.50%. This is T's explicit preference: "first candle against us we're out,
book profit fast" — tighter SL floor (0.50%) and faster profit-taking (TP 0.75-5.0%, k_tp ×1.25).
Before declaring a signal fundamentally broken, check whether the new SL floor
would have let it breathe.

### Market regime dominates signal quality — WR can collapse without a signal bug
System WR collapsed from 53% (Mar) → 25% (Apr) → 14% (Apr-end) → 0% (May 5-7).
Root cause: strong bullish regime in early May. SHORT signals (pct-hermes- 0% WR,
hzscore+ 20.5% WR) get crushed when price keeps breaking higher.
- pct-hermes- fires at market bottoms → price keeps going up → stop loss hit
- pct-hermes+ fires at market tops → price mean-reverts in trending market → stop loss hit
- accel-300+ fires near local momentum peaks → subsequent reversal hits SL
**Implication**: The signal system may be correct but the market regime makes it
unprofitable. Raising PCT_RANK_THRESH from 88→95 (2026-05-07) was the wrong
direction — it makes pct-hermes+ only catch the most extreme prints, which then
mean-revert harder in a trending market. Consider reverting to 88 or going lower.

### ACCEL_300_BLOCK_COSIGS is based on stale WR data
`ACCEL_300_BLOCK_COSIGS = {'ma-cross-5m+', 'pct-hermes+'}` in hermes_constants.py
blocks those combos from forming. The block was calibrated on May 6 stats that may
not reflect current regime. Re-evaluate whether blocking pct-hermes+ is correct —
in a bullish regime, accel-300++pct-hermes+ (35.7% WR in combo) may outperform
accel-300+ alone (19% WR).

### phase-accel+ barely fires but is not in GOOD_STANDALONE_SIGNALS
phase-accel+ fires only 9 times in the runtime DB — extremely rare. It was NOT in
GOOD_STANDALONE_SIGNALS as of 2026-05-07. With a 9-signal sample, it can't be
calibrated. Either remove it from consideration or add it to GOOD_STANDALONE with
a warning that sample is too small.

### ⚠️ CRITICAL: GOOD_STANDALONE_SIGNALS bypass blocked by avg_pnl>=0 gate (2026-05-08)
The naming mismatch claim below is **INCORRECT** — `_signal_type_key()` returns HYPHEN format
(`accel-300+`) which DOES match the dict keys. The real blocking issue is the avg_pnl gate.

**Current dict entries** (restored 2026-05-08 with live stats — all negative avg_pnl):
```python
GOOD_STANDALONE_SIGNALS = {
    'accel-300+':  {'wr': 17, 'avg': -0.319, 'dir': 'LONG'},   # 23 trades, all neg
    'pct-hermes-': {'wr':  5, 'avg': -0.449, 'dir': 'SHORT'},  # losing
    'hzscore+':    {'wr': 21, 'avg': -0.338, 'dir': 'SHORT'},  # losing
    'hzscore-':    {'wr': 16, 'avg': -0.704, 'dir': 'LONG'},   # losing
}
```

**The blocking line** (`signal_compactor.py` line ~519):
```python
if info['avg'] >= 0:  # ALL entries have avg < 0 — gate NEVER passes
    bypass_confluence()
```

**Fix options:**
1. Lower threshold to `avg >= -0.5` — captures signals that are net positive after fees despite losing individually
2. Change criterion to `total_pnl > 0` — captures that big winners outweigh small losers (accel-300+: 4 wins × +258% vs 18 losses × -38%)
3. Remove avg_pnl check entirely and rely on WR threshold (WR >= 20%) as pass criterion

**The combo_key model is the REAL architecture problem** (see below) — fixing the avg_pnl gate alone won't solve it.

### CRITICAL: combo_key model prevents ALL signal merging (2026-05-08)
**Root cause of empty hot-set and no trades.**

`signal_gen` fires each signal source in its own cycle — `accel-300+` in one cycle,
`hzscore-` in a separate cycle. Each creates a SEPARATE `combo_key` row:

```
combo_key = "DASH:LONG:accel-300+"   ← one signal source, one row
combo_key = "DASH:LONG:hzscore-"     ← separate cycle, separate row
```

**Result**: `accel-300+` and `hzscore-` never share the same combo_key row, so
`GROUP_CONCAT(source)` never merges them. Every signal appears as single-source.
The confluence gate (requires 2+ unique signal types) blocks ALL of them.

**Evidence**: 23 PENDING `accel_300_long` rows, 13 PENDING `mtf_zscore` rows — zero
multi-source PENDING combos exist in the current window.

**DASH's `accel-300+,hzscore-` in hot-set is a remnant** from a prior cycle when
both fired close enough together to share a combo_key. The `_filter_safe_prev_hotset()`
preserves it for one cycle, but new cycles only produce single-source entries.

**Why single-source signals ever reach hot-set**: The `accel-300+,rs-s44` combo
DOES merge — because RS runs in the same fast-signal cycle as accel-300+, so both
write to the DB within the same 1-min window and share the same combo_key.

**Fix options**:
1. Merge at signal_gen time: pass in-token-previous-cycle sources into current cycle
2. Relax confluence gate for RS co-signals only (RS is the proven differentiator)
3. Lower GOOD_STANDALONE_SIGNALS threshold so accel-300+ passes alone

### CRITICAL: Zero signals ever reached APPROVED — approval flow is dead code (2026-05-08)
**Decision counts in runtime DB:** `APPROVED=0`, `PENDING=80`, `EXECUTED=35`, `SKIPPED=160`

All 35 EXECUTED signals went directly `PENDING → EXECUTED`, bypassing the `APPROVED` step entirely.

**Root cause chain:**
1. `signal_compactor.main()` calls `process_pending_signals()` + `expire_stale_signals()` — never calls `compact_hot_set()`
2. `compact_hot_set()` (lines 990-1070) contains the `SET decision='APPROVED'` SQL — but is **never invoked**
3. `decider_run.py` lines 922-944 reads `WHERE decision='PENDING'` directly — never reads `APPROVED`
4. Result: `APPROVED` queue is permanently empty; decider executes directly from `PENDING`

**The hot-set JSON (`/var/www/hermes/data/hotset.json`) is read-only enrichment** — wave_phase,
regime, speed_percentile are attached for scoring, but the hot-set is never the execution source.

**Fix options:**
1. Fix `signal_compactor.main()` to call `compact_hot_set()` — restores full pipeline
2. OR fix `decider_run` to read `hotset.json` as execution source instead of `PENDING` table
3. OR remove the APPROVED layer entirely and let decider_run use PENDING directly with relaxed filters

### ⚠️ CRITICAL: hzscore hard-blocked in decider_run (2026-05-08)
**`decider_run.py` lines 1121-1126:**
```python
if sig_src == 'hzscore':
    rejection_reason = "combo-only, no confluence"
    continue  # BLOCKED
```

**This blocks ALL hzscore signals regardless of co-signals.** Even if hzscore+,pct-hermes-
merged signal reached PENDING, the `sig_src` (first source prefix) being `'hzscore'`
causes immediate rejection. `hzscore+/-` IS the directional signal (positive=SHORT,
negative=LONG), not a confluence indicator — this block is semantically incorrect.

**Impact**: hzscore is the 2nd most common base signal (5,509 fires) but is permanently
blocked in the execution layer. All hzscore combo trades depend on a different signal
being the first source prefix to pass the block.

### ⚠️ decider_run filter chain can block high-confidence signals (2026-05-08)
decider_run applies filters sequentially to PENDING signals:
1. **wave_mult** (0.70-1.10): falling+LONG→0.70, accelerating+SHORT→COUNTER_PENALTY
2. **speed_pts**: speed percentile scoring
3. **trap_penalty**: if token's own z-score contradicts direction, drops effective_conf
4. **regime_penalty**: counter-regime signals penalized 0-30 pts
5. **overextended block**: both directions blocked if overextended (except bottoming+LONG)
6. **hzscore block**: `sig_src=='hzscore'` → BLOCKED
7. **final_conf check**: effective_conf < 55 → BLOCKED

**FIL LONG (conf=80.0) and GRIFFAIN LONG (conf=80.0) are SKIPPED** despite high confidence.
Wave/regime/trap filters applied sequentially can drop effective_conf below threshold even
when raw confidence is high.

### ⚠️ Market regime dominance — WR collapse is structural (2026-05-08)
| Period | WR | Regime |
|--------|-----|--------|
| Mar 11-30 | ~53% | Range-bound |
| Apr 1-20 | ~25% | Early trend |
| Apr 21-30 | ~14% | Mean-reversion |
| May 5-7 | ~0% | Strong bullish continuation |

**In strong bullish regime (May 5+):**
- SHORT signals destroyed: pct-hermes- (fires at bottoms, price keeps going up), hzscore+
  (fires SHORT at local peaks, price grinds higher), counter_flip SHORT (blocks valid entries)
- LONG signals improved: accel-300+ avg peak +9.92% (May 5+), vs +2.6% overall
- RS co-signals critical: accel-300+ alone = 17.4% WR; accel-300+,rs-s16-150 = **100% WR, +343% peak**

**Implication**: The system needs regime-aware signal weighting. In bullish regimes, SHORT
signals should be suppressed or heavily penalized. In bearish/range regimes, LONG signals
suppressed. The counter-regime penalties in decider_run go in the right direction but
may not be aggressive enough.
**Symptom**: `accel-300+` DASH shows: +4.06% (win) → 67 min later -4.05% (loss), same token.
**Root cause**: Guardian or profit-monster is taking +4% profit (reasonable at 10-20X leverage
= 40-80% of equity), closing the position, then the same accel-300+ signal re-fires and
re-opens the position, getting stopped out at the next reversal.

**Pattern across accel-300+**: 22 unique trades — 4 big wins (+154% to +406%) vs 18 big losses
(-105% to -405%). The system is systematically cutting winners and re-entering.

**Duplicate rows in signal_outcomes**: Each trade produces 2 rows (entry signal + exit signal).
For DASH on May 6: id 3135 +4.06% (entry), id 3136 +3.16% (exit). Then id 3145 -3.15% (entry),
id 3146 -4.05% (exit). Same signal, same token, opposite outcomes within 67 minutes.

**Check for this bug**: Compare entry vs exit pnl_pct for same token+signal within a short window.
```sql
SELECT token, signal_type, created_at, pnl_pct,
  LAG(pnl_pct) OVER (PARTITION BY token, signal_type ORDER BY id) as prev_pnl
FROM signal_outcomes WHERE signal_type = 'accel-300+'
ORDER BY token, id;
-- Look for +X% followed by -Y% on same token within 2 hours
```

**Fix direction**: After a TP close, the signal should not re-trigger on the same token for
at least N minutes. OR: the guardian should track "recently closed by TP" and block re-entry
signals for a cooldown window.

### accel-300- does NOT exist — only plus (2026-05-07)
phase_accel.py only generates `accel-300+` (PHASE_ACCEL_MINUS_ENABLED=False). There is
no negative acceleration signal for shorts. If SHORT acceleration is desired, need to
enable PHASE_ACCEL_MINUS_ENABLED and implement negative acceleration logic.

### accel-300+ fires late at peaks — root causes and fixes (2026-05-09)
**Symptom**: accel-300+ fires when momentum has already peaked, position immediately reverses
against us.

**Root Cause #1 — Acceleration confirms too late**: The acceleration spike is the *result* of
price already having moved significantly. By the time the delta spike crosses the threshold,
the move is 1-3 candles old and exhausting.

**Implication**: The solution is earlier entry *with better confirmation*, not just lower thresholds.
Relaxing ATR SL is NOT the primary fix — it would let winners breathe but also let losers run.
The real fix is to catch the acceleration BEFORE it exhausts.

**Recent closed trades analysis pattern (2026-05-09):**
To diagnose accel-300+ timing, load recent closed trades and examine:
```python
import json
from collections import defaultdict

with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)

# Group by signal source
closed = data.get('closed', [])
by_src = defaultdict(list)
for t in closed:
    src = t.get('signal', 'unknown')
    by_src[src].append(t)

# For each signal, show entry price vs immediately after
for src, trades in by_src.items():
    if 'accel' not in src.lower(): continue
    for t in trades[-5:]:
        print(f"{src[:60]:60s} {t.get('token'):8s} entry={t.get('entry_price')} pnl={t.get('pnl_pct', 0):+.2f}%")
```

**Slope-of-slope acceleration fix (recommended):** Instead of raw acceleration delta, require
the EMA20 slope itself to be steepening. If EMA20 is flattening (slope decreasing), reject
the signal even if current bar has high acceleration. This catches the peak before it forms.

**Extension rejection alternative:** If price has moved >X% in the last Y bars, reject the
signal. X should be ~2× the max TP target (e.g., reject if price is 4%+ extended from recent
base). Pattern: accel-300+ fires at local peaks → next candle reverses → SL hit. The peak
detection would block these.

## ⚠️ accel-300+ boosting from pct-hermes — over-sized positions (2026-05-08)
`pct-hermes+` boosting mediocre `accel-300+` entries to conf=99, causing over-sizing with
leverage 5. `pct-hermes+` alone has 4.7% WR — it should not be boosting conf above 55.

**Fix**: Lower the pct-hermes weight in combo scoring. OR increase the WR threshold for signals
that contribute to conf boosting.
The only consistently profitable signals are `accel-300+` combined with support/resistance
bounce confirmations (`rs-s48`, `rs-s72`, `rs-s140`, `rs-s150`, `rs-s44`):
- `accel-300+,rs-s48` PURR +474%
- `accel-300+,rs-s48` GRIFFAIN +526%
- `accel-300+,rs-s140` +332%
- `accel-300+,rs-s72` +344%
- `accel-300+,rs-s44` +200%
- `accel-300+,momentum,mtf-macd,rsi` DASH +480%
- `accel-300+,rs-s150,trend_purity+` GRIFFAIN +526%
- `accel-300+,ma-golden10,rs-s46,trend_purity+` VVV +213%

Pattern: accel-300+ momentum confirmation + strong support level (16-150 touches) = wins.
RS touch count < 16 or > 150 = catastrophic losses (0% WR, -27% to -184%).
When adding to GOOD_STANDALONE_SIGNALS, require minimum 30-trade sample and live
WR >= 40% AND avg_pnl > 0. Never add on small samples (pct-hermes+ was added on 3 trades).

### CRITICAL: GOOD_STANDALONE_SIGNALS bypass is BROKEN by naming mismatch (2026-05-07)
The GOOD_STANDALONE_SIGNALS dict uses **hyphen** format keys:
```python
GOOD_STANDALONE_SIGNALS = {
    'accel-300+':   {'wr': 42, 'avg': 0.438, 'dir': 'LONG'},
    'pct-hermes-': {'wr': 35, 'avg': 0.221, 'dir': 'SHORT'},
    ...
}
```
But `signal_type` in the DB uses **underscore** format: `'accel_300_long'`, `'percentile_rank'`, `'mtf_zscore'`.
The `_signal_type_key()` at line 517 converts source prefix to underscore format.
The bypass check at line 519 `if base_type in GOOD_STANDALONE_SIGNALS` compares
`'accel_300_long'` against `{'accel-300+', ...}` — **this NEVER matches**.
**Result**: ALL single-source signals are held to the 2+ co-signal gate, regardless of
whether they're in GOOD_STANDALONE_SIGNALS. The entire bypass mechanism is dead code.
Fix: either change GOOD_STANDALONE_SIGNALS keys to underscore format (e.g., `'accel_300_long'`)
OR change `_signal_type_key()` to return hyphen format.

### CRITICAL: signal_outcomes is 2-rows-per-trade — is_win=1 means PEAK, not WIN (2026-05-07)
The signal_outcomes table produces **2 rows per trade**:
- Row with `is_win=1`: peak PnL (the best point the position reached)
- Row with `is_win=0`: exit PnL (where the position closed)
For winners: row 1 (is_win=1) = peak AND exit. Row 2 (is_win=0) = also exists.
For losers: row 1 (is_win=1) = peak, row 2 (is_win=0) = exit at loss.
**Correct query for exit PnL**: `MIN(pnl_pct) GROUP BY (token, direction, signal_type, created_at)`
**Correct query for peak PnL**: `MAX(pnl_pct) GROUP BY (token, direction, signal_type, created_at)`
**Correct query for win/loss**: `MAX(CASE WHEN is_win=1 THEN pnl_pct END)` — non-NULL = winner
**Example**: DASH accel-300+: +406.45% peak (is_win=1) → -405.16% exit (is_win=0).
The position went to +406% then exited at -405% — the PM closed it at a +4% intra-candle
move, then the same signal re-entered and got stopped. This is the position management bug.

### RS signals confirmed working — dead code to clean up (2026-05-08)
**✅ RS signals NOW confirmed writing PENDING signals to DB** (2026-05-08 00:42:47).
Live test: 5 signals written (AVAX rs-s40, BTC rs-s46, DASH rs-r214, ETH rs-s9, ORDI rs-r515).
`signals/rs.py` is the canonical implementation. `rs_signals.py` is the old deprecated version
(with bugs) — no longer in the pipeline.

**Orphaned constants to delete from signals/rs.py** (lines 226-227, never used):
```python
_RS_ATR_BAND_SOFT_MIN  = 0.30  # DELETE — never referenced
_RS_ATR_BAND_SOFT_MAX  = 0.60  # DELETE — never referenced
```

**RS_PROXIMITY_K=1.20 may be too tight** — price must be within 0.13% of a level for BTC
(ATR ~$120 = 0.11% of $107K → 1.2× ATR = 0.13%). Many valid bounce setups missed.
Consider widening to 2.0× ATR.

**SOL SHORT blocked by SHORT_BLACKLIST** in add_signal() — price at $142, strong bullish
trend. This is expected behavior, not a bug.
With RS_COOLDOWN_HOURS = 4, RS fires at most 6 times per day per token.
Even if it did fire, the GOOD_STANDALONE_SIGNALS bypass is broken (see above),
so it would still need a co-signal to pass the confluence gate.

### RS signals confirmed WORKING — test pattern (2026-05-08)
`scan_rs_signals` confirmed producing signals in isolation:
```
  LONG  BTC      conf= 88% level=79659.70 touches=43 bounce=False [rs-s43]
  SHORT ETH      conf= 75% level=2275.75  touches=16 bounce=False [rs-r16]
  LONG  SOL      conf= 86% level=88.357   touches=430 bounce=False [rs-s430]
added=3, signaled=['BTC', 'ETH', 'SOL']
```
**Test pattern** (run from `/root/.hermes/scripts`):
```python
import sys; sys.path.insert(0, '.')
from signal_schema import get_all_latest_prices, init_db
from signals.rs import scan_rs_signals
init_db()
prices = {k: v for k, v in get_all_latest_prices().items() if k in ('BTC', 'ETH', 'SOL')}
added, signaled = scan_rs_signals(prices)
print(f'added={added}, signaled={signaled}')
```
If `added=0` in pipeline but `added>0` here → `add_signal()` is blocking in full pipeline context
(blacklist/cooldown/position guard). If both return 0 → `_bounce_confirmation` or `_level_recently_broken`
returning False for market condition reasons (no bounce in last 6 candle boundaries, level recently broken).

### Orphaned RS constants — safe to delete (2026-05-08)
Lines 226-227 of `signals/rs.py`:
```python
_RS_ATR_BAND_SOFT_MIN  = 0.30  # DELETE — never referenced
_RS_ATR_BAND_SOFT_MAX  = 0.60  # DELETE — never referenced
```
Band filter was removed in prior session. These two lines are dead code. Safe to delete.

### ACCEL_300_TOKEN_ALLOWLIST — uncommitted working-copy change (2026-05-08)
`ACCEL_300_TOKEN_ALLOWLIST` in `hermes_constants.py` is an **uncommitted change** (not in git HEAD).
23 tokens: `DASH`, `TON`, `GRIFFAIN`, `S`, `ADA`, `UNI`, `TRB`, `OP`, `ZK`, `XMR`, `TAO`, `XRP`, `COMP`, `PROMPT`, `LINK`, `FIL`, `ETC`, `PURR`, `MERL`, `DYDX`, `ATOM`, `ONDO`, `0G`.

Effect: `accel_300+` can only fire on those 23 tokens. The other ~168 tokens in the 191-token
universe are completely blocked from this signal regardless of market conditions.

If T does not recall adding this: it is in the **working copy only**. Either `git diff` to see
exactly what changed, or `git restore hermes_constants.py` to revert to HEAD.

### `ACCEL_300_BLOCK_COSIGS` blocks proven combos
`ACCEL_300_BLOCK_COSIGS = {'ma-cross-5m+', 'pct-hermes+'}` in hermes_constants.py line 387.
These combos are blocked from forming. Calibration was from May 6 stats that may not reflect
current regime. Re-evaluate — `accel-300+,pct-hermes+` (35.7% WR in combo) may outperform
`accel-300+` alone (19% WR) in bullish regimes.

## Core Workflow
broken at the APPROVED step. The guardian/decider_run are executing signals without them
ever being promoted to APPROVED.

**Diagnosis SQL:**
```sql
SELECT decision, COUNT(*) FROM signals GROUP BY decision;
-- Expected: PENDING, EXECUTED, SKIPPED, EXPIRED, APPROVED
-- Actual: EXPIRED=17,990, SKIPPED=141, PENDING=76, EXECUTED=35, APPROVED=0

-- Check what SKIPPED signals have
SELECT token, source, confidence, rejection_reason
FROM signals WHERE decision='SKIPPED' LIMIT 10;
-- rejection_reason is often EMPTY — mystery SKIPs

-- SKIPPED vs EXECUTED confidence
SELECT decision, AVG(confidence), COUNT(*)
FROM signals GROUP BY decision;
-- SKIPPED avg_conf often HIGHER than EXECUTED — wrong signals getting blocked
```

**Known SKIPPED signals with high confidence:**
- FIL LONG: conf=80.0 — SKIPPED
- S LONG: conf=79.0 — SKIPPED
- GRIFFAIN LONG: conf=80.0 — SKIPPED

These should be in the hot-set but are blocked somewhere before APPROVED.

These should be in the hot-set but are blocked somewhere before APPROVED.

### executed=1 vs decision='EXECUTED' — dual tracking bug (2026-05-07)
The signals table has 17,206 rows with `executed=1` but only **35 rows** with
`decision='EXECUTED'`. Two independent tracking systems:
- `executed=1`: set by **guardian** when it closes a position (marks the entry signal as "exited")
- `decision='EXECUTED'`: set by **decider_run** when it opens a position
These systems are out of sync. The 17,206 `executed=1` rows are closed positions (from
the guardian side), NOT opened positions. To find truly executed signals, query
`decision='EXECUTED'`, NOT `executed=1`.
**Critical bug**: The `executed` flag was set by a prior execution pathway that no longer
exists. Current pathway writes `decision='EXECUTED'` but doesn't set `executed=1`.
Result: signals that reached decider (SKIPPED/REJECTED) and then got phantom-closed by
guardian show `executed=1` even though they were never actually opened.
**Fix needed**: Unify the two tracking systems — decider should set `executed=1` when
it actually opens a position, not just write `decision='EXECUTED'`.

### `regime_bull_flip` — Disabled via Killswitch (2026-05-11)
**Symptom**: IMX SHORT entered at 0.19048, exited at 0.19054 (+0.03%) by `regime_bull_flip`, but
price continued down to ~0.189 after exit. The MACD 1H regime flipped to BULL, triggering the
exit on a SHORT that was correctly positioned.

**Root cause**: `macd_rules.py` line 324-325:
```python
def _exit_short_signals(s: MACDState) -> list:
    ...
    if s.regime == Regime.BULL:
        signals.append('regime_bull_flip')
```
The regime flips to BULL when MACD line (EMA12-EMA26) crosses above zero on 1H. In strong
trending markets, this can fire on a brief momentum uptick that immediately resumes the trend
against the SHORT position. The exit is lagging — it fires after price has already moved enough
to shift the EMA relationship.

**Pattern observed (TRB SHORTs 2026-05-11)**:
| Trade | Dir | Signal | Close Reason | Age |
|-------|-----|--------|--------------|-----|
| TRB SHORT | SHORT | hzscore+,rs-r1372 | regime_bull_flip | 34s |
| TRB SHORT | SHORT | hzscore+,rs-r8622 | atr_sl_hit | 4s |
| TRB SHORT | SHORT | hzscore+,rs-r2232 | regime_bull_flip | 5s |
| IMX SHORT | SHORT | rs-r636,vel-hermes- | regime_bull_flip | 5s |

**Fix applied**: `macd_rules.py` — commented out the `regime_bull_flip` append, wired to
killswitch `REGIME_BULL_FLIP_ENABLED` in `hermes_constants.py` (default `False` = disabled).

**Killswitch in hermes_constants.py**:
```python
REGIME_BULL_FLIP_ENABLED = False  # Disable regime_bull_flip exit (fires too often on short timeframe)
```

**Note**: `regime_bear_flip` (for LONG positions) is still active at line 295. If T experiences
similar premature exits on LONG positions, apply the same pattern.

**Symptom**: TRB trades firing and closing within 4-6 seconds. AAVE trade closed in 13 minutes.
Both entry signal and exit reason are valid individually — but entry fires too late, catching
the END of a move that immediately reverses.

**Exit reason → root cause mapping:**
| Close Reason | Direction | Root Cause |
|--------------|-----------|------------|
| `histogram_fading_fas` | LONG | MACD histogram was already contracting when signal fired. The acceleration spike IS the peak. |
| `regime_bull_flip` | SHORT | Macro regime flipped to BULL (MACD line > 0 on 1H), closing SHORT positions even when price continues down. |
| `atr_sl_hit` (< 60s) | either | Price moved against position immediately — signal caught a late entry. |
| `profit_monster` | either | TP hit normally. |

### `regime_bull_flip` — How It Fires (2026-05-11)

**Source:** `macd_rules.py` line 324-325:
```python
def _exit_short_signals(s: MACDState) -> list:
    ...
    if s.regime == Regime.BULL:
        signals.append('regime_bull_flip')
```

**Trigger:** MACD line (EMA12 - EMA26) crosses above zero on the 1H chart → `regime = Regime.BULL` → SHORT positions are exited.

**Lag problem**: The regime shift is confirmed by price ALREADY having moved enough to shift the EMA relationship. In strong trending markets (like IMX SHORT on 2026-05-11), the regime flip can fire at a local bounce that immediately resumes — the exit catches the micro-reversal, not the trend change.

**IMX example (2026-05-11 02:18):**
```
Entry:  0.19048 SHORT (rs-r636,vel-hermes-)
Exit:   0.19054 — closed by regime_bull_flip
Price continued: DOWN to ~0.189 (trade was right, exit was wrong)
```

The MACD 1H regime turned BULL against the SHORT — but price kept falling. The regime flip was a false signal in a continuing bear trend. The exit was triggered by short-term 1H momentum that wasn't sustained.

**Diagnostic SQL:**
```sql
SELECT
  coin, direction, signal, close_reason,
  ROUND(pnl_pct, 3) pnl_pct,
  ROUND((julianday(close_time) - julianday(open_time)) * 86400, 1) AS age_seconds
FROM trades
WHERE status = 'closed'
ORDER BY open_time DESC
LIMIT 20;
```

### ⚠️ accel-300+ in NEUTRAL market — 22 consecutive losers (2026-05-11)
**Symptom**: Last 30 closed trades = 8 winners, 22 losers. Almost all losers are
`accel-300+,rs-sXX` — ATR stops hit immediately after entry, market reverses.

**Full session data**: `references/last-30-losers-2026-05-11.md`

**Root Cause — Market is 103/105 NEUTRAL**:
```
regime_5m.json aggregate: 1 LONG_BIAS (LAYER), 1 SHORT_BIAS (CHIP), 103 NEUTRAL
```
In a NEUTRAL market, accel-300+ fires on breakouts that immediately reverse. The
signal catches local tops. RS confirms the entry but the market has no follow-through.

**5m regime filter is NOT blocking NEUTRAL tokens**:
- `signal_compactor.py` lines 219-225: NEUTRAL regime → `reg_mult = 1.0` (no bonus, no penalty)
- Regime is a **multiplier** on existing signals, not a **gate** for neutral conditions
- A token with NEUTRAL regime and accel-300+ sails straight through to hot-set

**All current hot-set entries have final_score=0.000** — the scoring equation
`final_score = score * survival_bonus * staleness_mult * reg_mult * source_mult * speed_mult`
produces 0.000 despite confidence 77-84% on all entries. Something in the scoring
pipeline is broken (not yet diagnosed).

**accel-300+ has no killswitch for neutral market**:
```python
# hermes_constants.py line 379
ACCEL_300_ENABLED = True   # No regime gate — fires even when 103/105 tokens NEUTRAL
ACCEL_300_TOKEN_ALLOWLIST = set()  # empty = no token filter
ACCEL_300_BLOCK_COSIGS = {'ma-cross-5m+', 'pct-hermes+'}  # No neutral-market gate
```

**Key asymmetry from archive data**:
| Signal | N | Win% | Avg% | Total$ |
|--------|---|------|------|--------|
| `hzscore+,pct-hermes-,vel-hermes-` (short triple) | 39 | 46.2% | +0.382% | +$14.90 |
| `accel-300+,rs-sXX` (long, current) | 164 | 33.5% | +0.077% | — |

The short triple combo is significantly stronger. In a neutral market, SHORT signals
with `pct-hermes-` work (46% WR) while LONG accel-300+ in neutral mostly loses.

**What to check when losses stack up**:
1. Check aggregate regime: `cat /var/www/hermes/data/regime_5m.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['aggregate'])"`
2. If `overall: NEUTRAL` and `neutral: 95+` → block accel-300+ entries until regime shifts
3. Check hot-set final_scores: if all 0.000 → scoring pipeline bug (separate issue)

**Fix direction**: Add NEUTRAL-regime killswitch for accel-300+ — when aggregate market
regime is NEUTRAL with high confidence, do not fire new accel-300+ entries. The signal
works in trending markets (LONG_BIAS/SHORT_BIAS) but not in chop.

## ⚠️ When T Says "Flip hzscore+/hzscore-" — Confirm Intent First (2026-05-11)

T said: "previously hzscore+ was short, I want hzscore- to be short now and hzscore+ to be for long"

This is ambiguous — two interpretations:
1. **Flip the label/naming** (source field): `hzscore-` source name should mean LONG instead of SHORT (keep the action, rename the label)
2. **Flip the logic/action**: `hzscore+` should fire LONG instead of SHORT (change what the signal does)

**Current system**: `hzscore+` fires SHORT, `hzscore-` fires LONG (inverted from naming). The source field label is backwards from what you'd expect.

**The patch that was applied** — line 118 in `signals/hzscore.py`:
```python
# Before: hz_dir_char = '-' if local_dir == 'LONG' else '+'  (label inverted from action)
# After:  hz_dir_char = '+' if local_dir == 'LONG' else '-'  (label matches action)
```

This flips the **label** only — `hzscore+` now = LONG, `hzscore-` now = SHORT (label matches action). The actual signal logic (direction it fires for a given z-score reading) was NOT changed.

**If T wants the logic flipped** (action = opposite): Change lines 102-104 in `hzscore.py`:
```python
# Current (z > 0 = SHORT, z < 0 = LONG):
local_dir = 'SHORT' if bullish_tfs >= 2 else ('LONG' if bearish_tfs >= 2 else None)

# To flip logic (z > 0 = LONG, z < 0 = SHORT):
local_dir = 'LONG' if bullish_tfs >= 2 else ('SHORT' if bearish_tfs >= 2 else None)
```

**Lesson**: When T says "flip X to Y" for a signal/direction, always ask: label/name or actual logic/action? The distinction matters for which lines to change.

Full trace: `references/hzscore-naming-flip-2026-05-11.md`

**Pattern across TRB (2026-05-11):**
| Trade | Dir | Entry Signal | Close Reason | Age |
|-------|-----|-------------|--------------|-----|
| TRB SHORT | SHORT | hzscore+,rs-r1372 | regime_bull_flip | 34s |
| TRB SHORT | SHORT | hzscore+,rs-r8622 | atr_sl_hit | 4s |
| TRB SHORT | SHORT | hzscore+,rs-r2232 | regime_bull_flip | 5s |
| TRB LONG | LONG | accel-300+,rs-s198 | histogram_fading_fas | 51s |
| TRB LONG | LONG | accel-300+,rs-s1764 | histogram_fading_fas | 6s |

**Fix directions:**
- `histogram_fading_fas` on LONG: Apply slope-of-slope filter — reject if EMA20 slope is
  flattening even with high acceleration delta. The peak detection catches the exhaustion.
- `regime_bull_flip` on SHORT: In bullish regime, suppress SHORT signals more aggressively.
  Check regime before executing counter-direction signals.
- Sub-second exits on 98% confidence signals = confirmation framework too slow for signal rate.

**Full performance reference data:** `references/signal-performance-ref-2026-05-08.md`

## Core Workflow

## Common Patterns

### Hot-set empty → check compactor logs
`grep "APPROVED\|EXPIRED\|COOLDOWN" /root/.hermes/logs/pipeline.log`

### Silent skips — hot-set tokens never appear in exec output (2026-05-11)
**Symptom**: hotset.json has 10 valid tokens (all LONG, conf 70-88%), pipeline shows
`0 entered | 34-37 skipped` every cycle, but only 5 tokens appear in the SKIP log
(LAYER/NEAR/ENS/DASH/2Z — all WR-blocked). The other 8 hot-set tokens (BRETT/BERA/FET/
CHIP/AVAX/EIGEN/ADA/BSV) are completely invisible in the logs.

**Root cause**: Tokens silently fail a gate BEFORE the per-token logging line is reached.
The WR gate check logs immediately when it blocks a token. Other gates fail silently.

**Diagnostic**: Add debug logging at the top of the decider_run exec loop:
```python
# At the start of the per-signal loop in _run_hot_set() / execution gate:
log(f"  PROCESSING {token} {direction} conf={confidence}")
```
Then add a log at EACH gate check showing pass/fail:
```python
# Before is_position_open check:
log(f"    is_position_open={is_position_open(token)}")
```
```python
# Before _is_guardian_closing check:
log(f"    guardian_closing={_is_guardian_closing(token)}")
```
```python
# Before counter-trend trap:
log(f"    counter_trap_regime={regime_1m}")
```
```python
# Before regime filter:
log(f"    regime_filter_regime={regime_1m}")
```

**Known silent-fail candidates (decider_run execution gate)**:
1. `is_position_open()` — returns True if already in HL position
2. `_is_guardian_closing()` — guardian orphan path marks token as closing
3. `speed=0% block` — if price hasn't moved in lookback window
4. Counter-trend trap at line 1689 — regime check against _get_regime_1m
5. Regime filter at line 1711 — regime check against _get_regime_1m
6. Loss cooldown — _is_loss_cooldown_active() from signal_schema
7. Overextended check — both directions blocked if price too far from MA

**Key files to check**:
- decider_run.py lines 1590-1760: the execution gate loop
- decider_run.py lines 1780-1820: WR gate + MAX_POS check
- decider_run.py lines 1680-1710: counter-trend trap + regime filter

### Only one signal type → check run() functions + GOOD_STANDALONE_SIGNALS
If one type floods hot-set (e.g. pct-hermes-), it may be in GOOD_STANDALONE_SIGNALS
while others require co-signals that never form.

### Signals not merging → check window + token overlap
Different signal generators fire on different token sets. hzscore (~20 tokens) and
pct-hermes (~46 tokens) have near-zero overlap. Merging requires same token+direction
within the compaction window.

### Win rate filter blocking everything → check decider_run.py WR threshold
If all hot-set tokens show `direction paused`, the 50% WR threshold may be too strict
for a system with 34% average WR.
