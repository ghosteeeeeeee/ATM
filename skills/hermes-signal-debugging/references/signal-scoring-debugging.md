---
name: signal-scoring-debugging
description: Debug signal scoring in Hermes — why wrong signals execute, why good signals get blocked, RSI/MACD/regime scoring bugs
triggers:
  - "wrong trade executed"
  - "signal blocked incorrectly"
  - "LONG at local top"
  - "SHORT at local bottom"
  - "ai_decider blocking shorts"
  - "oversold signal not blocked"
  - "falling knife executed"
  - "RSI scoring bug"
  - "regime bonus missing"
  - "only gap-300 fires trades"
  - "only pct-hermes fires trades"
  - "signal dies after 5 minutes"
  - "staleness score zero"
---

# Signal Scoring Debugging — Hermes

Debug why ai_decider executes the wrong signals and blocks the right ones. Applies to `signal_gen.py` and `ai_decider.py`.

## Quick Diagnosis

When a bad trade executes (e.g., LONG at local top):
1. Get the signal that triggered it — `python3 -c "from hermes_tools import terminal; t=terminal('psql \$DB_URL -c \"SELECT signal, direction, entry_price, rsi, velocity FROM trades WHERE token=\'MORPHO\' AND is_open=True;\"')"`
2. Check regime at entry time — `cat /root/.hermes/data/regime_4h.json`
3. Check z-score and percentile at entry — `python3 -c "from hermes_tools import terminal; t=terminal('psql \$DB_URL -c \"SELECT * FROM signals WHERE token=\'MORPHO\' ORDER BY created_at DESC LIMIT 20;\"')"`
4. Compare against the 5 bugs below

## The 5 Scoring Bugs to Check

### Bug 1 — `hmacd-` source hardcoded (signal_gen.py)
**Symptom**: ai_decider can't tell if MACD crossover was bullish or bearish from the source string alone.

```python
# WRONG (line ~1651):
source = f'hmacd-{mtf_macd_direction}'  # mtf_macd_direction might be "LONG" not "+"/"-"

# CORRECT:
mtf_source = f'hmacd+{"+" if mtf_macd_direction == "LONG" else "-"}'
```

**What to check**: Look for `source='hmacd-'` in signal_gen.py — if it's a literal string with no dynamic `+`/`-`, the source name is broken.

---

### Bug 2 — RSI oversold bonus without convergence (signal_gen.py)
**Symptom**: LONG executes when RSI=28 but velocity is still negative and percentile is only 56 (not extreme). The signal fires because RSI is "oversold" but nothing confirms it's a REAL bottom.

**What the old code did**: `rsi < 30 → +3.0 pts` regardless of velocity or percentile.

**What correct scoring requires** (all must be true for +3.0):
- RSI ≤ 30
- pct_long ≤ 35 (percentile agrees — we're at a real bottom, not mid-range)
- z_dir ≠ "rising" (z-score not going up = price not mean-reverting up = no premature bounce)
- vel ≥ 0 (velocity stopped falling = selling pressure exhausted)

**Failing conditions get penalties**:
- z_dir="rising" OR vel < 0 → -2.0 pts (`oversold-falling-knife`)
- pct_long > 35 → -1.5 pts (`oversold-no-regime-confirm`)

**For SHORT**: mirror logic with RSI ≥ 60, pct_short ≤ 35, z_dir ≠ "falling", vel ≤ 0.

---

### Bug 3 — No "premature bounce" detection (signal_gen.py)
**Symptom**: z_dir="rising" (z-score going up = price mean-reverting UP toward average) but the system still takes a LONG. If percentile_long is elevated (price already rallied), this is a chase, not a bounce.

**Rule**: If z_dir="rising" AND percentile_long not deeply suppressed → -2.0 pts AND block.

**Key insight**: z_dir="rising" means the bounce already happened. z_dir="falling" means price is still falling toward the bottom — that's when you want to BUY.

---

### Bug 4 — 4h MACD counter-trend not penalized (signal_gen.py)
**Symptom**: 15m/1h MACD fires a bullish crossover (source=`hmacd+`) but 4h MACD histogram is still negative. The higher timeframe trend is bearish, but the signal ignores it.

**Rule**: 
- LONG + 4h_hist < 0 → -1.5 pts (`4h-bearish-counter`)
- SHORT + 4h_hist > 0 → -1.5 pts (`4h-bullish-counter`)

**How to get 4h hist**: It's in `momentum_cache.macd_hist` (not from the signal source string).

---

### Bug 5 — Fallback asymmetric regime bonus (ai_decider.py)
**Symptom**: In extreme LONG_BIAS markets (93/113 tokens), the fallback algorithm was neutral on both directions. It only penalized SHORT in SHORT_BIAS markets. LONG_BIAS environments got ×1.0 for both LONGs and SHORTs.

**Rule** (make symmetric):
```
LONG_BIAS + LONG:  ×1.15  (encourage longs in long-bias market)
LONG_BIAS + SHORT: ×0.85  (discourage shorts in long-bias market)
SHORT_BIAS + SHORT: ×1.15
SHORT_BIAS + LONG:  ×0.85
```

---

## Z-Score / Regime Conflict Detection

This is the hardest class of bug — regime and z-score disagree, and both are "correct" by their own logic.

**Scenario**: Token is in LONG_BIAS, z=+1.06 (top of range). Both say "go LONG." Price is at a local top. The system is right about the regime but wrong about the timing.

**What z_dir actually means**:
- z_dir="rising": z-score going up = price above its moving average = mean-reversion UP toward average
- z_dir="falling": z-score going down = price below its average = mean-reversion DOWN

**Key thresholds**:
- |z| < 0.25: neutral zone — regime should dominate, z provides almost no signal
- |z| 0.25–0.50: weak signal — direction agrees with regime but magnitude is weak
- |z| > 0.50: strong signal — at extremes, z overrides regime

**Premature bounce pattern** (most dangerous):
1. z-score was positive (price above average = rally happened)
2. Regime is LONG_BIAS (market wants higher prices)
3. z_dir="rising" (price still moving up)
4. → This is the END of a rally, not the start of a new one
5. → Don't LONG here — you're chasing the move

**Late-fade pattern** (also dangerous):
1. z-score was negative (price below average = decline happened)
2. Regime is SHORT_BIAS (market wants lower prices)
3. z_dir="falling" (price still moving down)
4. → This is the END of a decline, not the start of new selling
5. → SHORT here is fading a bottom, not following trend

---

## Investigation Workflow

1. **Get trade details from DB**:
```bash
psql $DB_URL -c "SELECT token, direction, entry_price, entry_time, signal, rsi, velocity FROM trades WHERE is_open=True;"
```

2. **Check regime at entry time**: `cat /root/.hermes/data/regime_4h.json` — look for `long_bias` vs `short_bias` count and per-coin regime.

3. **Get signal history**:
```bash
psql $DB_URL -c "SELECT signal, direction, rsi, velocity, percentile_long, percentile_short, z_score, created_at FROM signals WHERE token='TOKEN' ORDER BY created_at DESC LIMIT 20;"
```

4. **Simulate old vs new scoring**:
```python
# Example: MORPHO LONG at $1.88
# rsi=28.33, vel=-0.0025, pct_long=56.5, z_dir="rising", 4h_hist=+small
# OLD: +3.0 (oversold-confirm) + 0 = +3.0 → EXECUTE
# NEW: -1.5 (oversold-no-regime) + -1.5 (4h-bullish-counter) = -3.0 → BLOCKED
```

5. **Check 4h MACD**: Look at `momentum_cache` table for `macd_hist` at entry time. If it contradicts direction, apply Bug 4 penalty.

6. **Verify fallback regime bonus**: Check `ai_decider.py` for symmetric `LONG_BIAS` handling (should penalize SHORTs in LONG_BIAS market, not just ignore it).

---

## Files to Check

- `/root/.hermes/scripts/signal_gen.py` — RSI scoring (lines ~1050-1130), MACD scoring (lines ~1120-1140), z_dir logic (lines ~620-690)
- `/root/.hermes/scripts/ai_decider.py` — fallback regime bonus (lines ~1610-1630), LLM prompt path
- `/root/.hermes/scripts/hl-sync-guardian.py` — `add_orphan_trade()` (line ~573), phantom close retry (Step 7b)
- `/root/.hermes/scripts/signal_compactor.py` — `_score_signal()` scoring formula (lines ~189-235), staleness_mult, survival_bonus
- `/root/.hermes/data/signals_hermes_runtime.db` — signals SQLite DB for historical signal analysis
- PostgreSQL brain DB — `trades`, `signals` tables

---

## Pattern 6: Staleness Decay Dominates Scoring — Only Gap-300 and Pct-hermes Survive (2026-04-29)

**Symptom**: All signal sources emit (oc-mtf-macd-, oc-rsi-, ma-cross-5m+, pct-hermes+, gap-300-), but only gap-300- and gap-300-,pct-hermes+ combos reach EXECUTED/APPROVED. Others sit at PENDING with 0 survival rounds forever.

**Root cause**: `_score_signal()` in `signal_compactor.py` uses:
```python
staleness_mult = max(0.0, 1.0 - (age_m * 0.2))  # 0 at age=5min
```
This creates a **linear decay** where every minute of age costs 20% of the score. At age=2.5 min, any signal — regardless of confidence — scores 0 and is functionally dead.

**Concrete math** (all signals at age=1m, survival_rounds=0, NEUTRAL regime, speed_mult=1.0):
| Signal | Conf | Score at age=1m | Score at age=2m |
|--------|------|-----------------|-----------------|
| gap-300- | 75 | 60.0 | 45.0 |
| pct-hermes+ | 60 | 48.0 | 36.0 |
| oc-mtf-macd- | 88 | 70.4 | 52.8 |
| ma-cross-5m+ | 80 | 64.0 | 48.0 |

**Why gap-300 specifically wins**: It fires ~4.5×/minute, producing frequent young entries. pct-hermes+ fires ~3.3×/minute. Other signals (oc-rsi-, ma-cross-5m) fire less frequently. The top-10 cutoff means only the freshest entries survive.

**The death spiral**:
1. Signal fires → PENDING, cr=0, age=0
2. At age=2.5min → score ≈ 0 → can't break top-10
3. Can't break top-10 → stays PENDING, cr never increments
4. cr=0 → no survival bonus in next cycle
5. Signal is functionally dead even though it was emitted

**Diagnosis query**:
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "
SELECT source, decision, confidence, survival_rounds, compact_rounds,
  ROUND((julianday('now') - julianday(created_at)) * 1440, 1) as age_m
FROM signals
WHERE created_at > datetime('now','-6 hours')
AND decision IN ('PENDING','APPROVED')
ORDER BY age_m DESC LIMIT 20"
```

**Fix — reduce staleness decay** (`signal_compactor.py` `_score_signal()`):
```python
staleness_mult = max(0.0, 1.0 - (age_m * 0.12))  # was 0.20
# Signal dies at age=8.3min instead of 5min
# pct-hermes+ at conf=60, age=4m → score = 60×0.52 = 31.2 (still competitive)
```

**Also — boost pct-hermes+ source weight** (`signal_compactor.py` `SIGNAL_SOURCE_WEIGHTS`):
```python
('percentile_rank', 'pct-hermes+'): 1.25,  # boost pct-hermes+ (empirically 75-100% WR)
('percentile_rank', 'pct-hermes-'): 0.80,  # suppress pct-hermes- (broken direction)
```

Both changes together: slower decay keeps signals alive longer to accumulate survival rounds, and the source weight gives pct-hermes+ a competitive edge in the top-10 ranking.

---

## Pattern 7: LONG/SHORT Win-Rate Bias — Signal Combo Analysis (2026-04-29)

**Symptom**: SHORT WR significantly outperforms LONG WR despite using inverted logic. 163 trades: LONGS 35.6% WR (118 trades) vs SHORTS 48.9% WR (45 trades). Same signals, inverted — but longs systematically lose more.

**Root Cause**: The inverted logic is NOT symmetric. Built-in biases hurt longs more than shorts.

**Diagnostic Query Set**:

```python
# 1. Overall LONG vs SHORT split
longs = [t for t in closed if t['direction'] == 'LONG']
shorts = [t for t in closed if t['direction'] == 'SHORT']

# 2. Close reason breakdown by direction
for direction, trade_list in [("LONG", longs), ("SHORT", shorts)]:
    cr_counts = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for t in trade_list:
        cr = t.get('close_reason', 'unknown')
        cr_counts[cr]['total'] += 1
        if t['pnl_pct'] > 0: cr_counts[cr]['wins'] += 1
        else: cr_counts[cr]['losses'] += 1

# 3. Signal combo WR — most important analysis
signal_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
for t in trade_list:
    sigs = tuple(sorted(t.get('signal', '').split(',')))
    signal_stats[sigs]['total'] += 1
    if t['pnl_pct'] > 0: signal_stats[sigs]['wins'] += 1
    else: signal_stats[sigs]['losses'] += 1

# 4. Individual signal WR (for both directions)
# 5. Loss distribution: small loss vs big loss breakdown
# 6. ATR_SL_HIT avg loss — are losses tiny (-0.5 to 0%) or real losses?
```

**Key Findings to Look For**:

| Finding | Data Pattern | Likely Cause |
|---------|-------------|-------------|
| ma-cross-5m+ at 20% WR | All losses small (-0.06 to -0.37%) | Lagging indicator, fires after move already done |
| pct-hermes+ LONG 33% WR | Most losses tiny | Mean-reversion fires too early, conflicts with momentum signals |
| gap-300- LONG: 62.7% small losses | -0.5% to 0% range | SL hit immediately after entry |
| oc-rsi- SHORT 28.6% WR | Multiple tiny losses | RSI mean-reversion catches knife |
| vel-hermes+ barely fires | Only 2 trades total | Velocity scoring requires negative velocity for LONG (rare in trends) |
| pct-hermes SHORT 56% WR | Outperforms LONG version | Short direction gets positive velocity bonus more often |

**Systematic Issues Found (2026-04-29)**:

1. **Blacklist `ma-cross-5m+` immediately** — 20% WR, all small losses. The 5m cross is pure lag.
2. **Tighten pct-hermes+ threshold**: `<= 38` instead of `<= 45` for `has_pct_signal` in quiet phase. Only deeply suppressed prices valid for LONG mean-reversion.
3. **Raise gap-300 MIN_GAP_PCT**: 0.05 → 0.08. Reduce false breakouts from noise.
4. **Require oc-rsi- confirmation**: z_score or velocity alignment needed, not solo RSI.
5. **vel-hermes+ grace condition**: Allow neutral velocity when pct_long <= 30 (deeply suppressed) to balance signal rate.

**Why the asymmetry exists**: pct_long_score_fn and pct_short_score_fn are not mirror images. pct_long fires on suppressed prices (dip-buying), pct_short fires on elevated prices (fade rallies). In trending markets, elevated prices tend to continue, so pct_short captures momentum better. Suppressed prices for LONG can keep falling. The velocity scoring is also asymmetric: positive velocity (z rising = price reverting up) rewards SHORT, while negative velocity is required for LONG — but trending markets have positive velocity most of the time.
