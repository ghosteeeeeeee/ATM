# Chart Pattern Recognition for Hermes

## Goal
Add real-time chart pattern detection (Head & Shoulders, Bull/Bear Flags, Wyckoff, Elliot Wave) as a signal source that feeds into the existing Hermes pipeline — augmenting or replacing fragile confluence checks for cascade flips like VVV.

---

## Context / Assumptions

- Price + volume data is available via HL API (candles endpoint) and SpeedTracker
- Hermes already has: momentum_score, velocity_5m, acceleration, z_score, RSI, MACD
- Pattern signals would feed into `signal_gen.py` as an additional `signal_type`
- Would initially be used as **cascade flip confirmation** (like the coin-regime fallback just added) and eventually as **primary entry signals**
- Rule-based detection is preferred over ML for this V1 (deterministic, auditable, no training data needed)

---

## Patterns to Implement

### 1. Head & Shoulders (H&S) / Inverse H&S
**What it detects:** Distribution top (H&S = short signal), Accumulation bottom (Inverse = long signal)
**Logic:**
- Find 3 swing highs: left shoulder, head (highest), right shoulder (lower than head)
- Neckline = line connecting the two troughs after shoulders
- Breakdown: price closes below neckline with volume confirmation → SHORT
- Inverse: mirror logic for bottoms

**Signal output:** `pattern_hns` with direction, confidence (based on shoulder symmetry), breakout confirmation

### 2. Bull Flag / Bear Flag
**What it detects:** Continuation patterns after strong impulse moves
**Logic:**
- Identify strong impulse move (flag pole): > 5% move in < 10 candles
- Flag = parallel channel moving against the impulse direction (1-5 candles)
- Volume declining during flag formation
- Breakout in direction of pole = entry

**Signal output:** `pattern_flag` with direction, pole strength, breakout confirmation

### 3. Wyckoff Accumulation / Distribution
**What it detects:** Institutional accumulation before markup, distribution before markdown
**Logic (Accumulation phase A):**
- Spring: quick down-thrust below support, immediately reverses (false breakdown)
- SOS (Sign of Strength): price recovers above spring low on decreasing volume
- JMO (Jump Over the Creek): retests support area from above
-BUY: entering phases C-D (Markup begins)

**Key events to detect:**
- Spring (potential bottom, long signal)
- Breakout above trading range high (confirms accumulation, long)
- Upthrust / Distribution pattern (mirror of spring, short)
- WYckoff schematics - COMPOSITE MAN metaphor

**Signal output:** `pattern_wyckoff` with phase (A/B/C/D), direction

### 4. Elliot Wave (Impulse + Corrective)
**What it detects:** 5-wave impulse patterns (wave 3 = strongest, wave 5 = weaker), ABC corrections
**Logic:**
- Wave 1/3/5: impulse moves in the direction of the trend (each must be > 61.8% of the previous)
- Wave 2: retraces 38.2-78.6% of wave 1 (never fully)
- Wave 3: never the shortest (usually longest)
- ABC correction: 3-wave pullback after impulse
- Identify wave 3 breakout → strong momentum signal

**Simplified V1 detection:**
- Detect 5 consecutive impulse/pullback sequences
- Calculate Fibonacci relationships between waves
- Flag wave 3 starts (accelerated momentum) and wave 5 starts (momentum divergence)

**Signal output:** `pattern_elliot` with wave_number, direction, fib_ratio

---

## Data Sources

| Data | Source | Refresh |
|---|---|---|
| OHLCV 1m | HL `/candle?interval=1m` | Every pipeline run |
| OHLCV 5m | HL `/candle?interval=5m` | Every pipeline run |
| Volume profile | Computed from candles | Every pipeline run |
| Price velocity | SpeedTracker | Live |
| Price acceleration | SpeedTracker | Live |

**Note:** HL candles have rate limits. Cache aggressively. For V1, 1m candles only for active positions/tokens in hot-set.

---

## Architecture

```
signal_gen.py (existing)
    └── pattern_scanner.py (NEW)
            ├── detect_head_shoulders(candles) → Signal | None
            ├── detect_flag(candles) → Signal | None
            ├── detect_wyckoff(candles) → Signal | None
            └── detect_elliot(candles) → Signal | None

cascade_flip (position_manager.py)
    └── checks pattern signals as confluence (alongside existing signal DB check)
```

**NEW file:** `/root/.hermes/scripts/pattern_scanner.py`

Pattern signals are lightweight structs written directly to signals DB:
```python
{
    'token': 'VVV',
    'signal_type': 'pattern_hns',
    'direction': 'LONG',      # or SHORT
    'confidence': 72.5,       # pattern quality score
    'source': 'pattern_scanner',
    'decision': 'PENDING',    # pipeline decides whether to execute
    'price': current_price,
    'pattern_detail': {       # pattern-specific metadata
        'type': 'inverse_hns',
        'neckline': 7.34,
        'breakout_px': 7.38,
        'symmetry_score': 0.82
    }
}
```

---

## Competition Model — Independent Primary Signals (APPROVED 2026-04-06)

**T's directive:** Pattern signals are **independent**, not subordinate. They run on ALL tokens, compete with mtf_macd signals equally, and bubble up based on actual performance.

```
signal_gen.run() execution order:
  1. _run_pattern_signals()    ← NEW: ALL tokens, runs FIRST
  2. _run_mtf_macd_signals()    ← existing: per-token momentum scoring loop
  3. run_confluence_detection() ← existing: confluence detection

ai_decider.py scoring:
  - All signal types scored the same way (base_confidence from DB)
  - Pattern signals: 1.25× multiplier applied at hot-set scoring time
  - mtf_macd signals: 1.0× multiplier (baseline)
  - Pattern multiplier adjustable per pattern type: flag, hns, wyckoff, elliot

Performance tracking:
  - After 50+ trades per signal type: compare win rates
  - WR > 55% → multiplier boost to 1.5×
  - WR 45-55% → keep at 1.25×
  - WR 40-45% → reduce to 0.75×
  - WR < 40% → disable that pattern type
```

### Signal Types Competing
| Signal Type | Source | Current Role |
|---|---|---|
| `momentum` | mtf_macd | Primary (existing) |
| `pattern_flag` | pattern_scanner | Bull/Bear Flag + Ascending/Descending Triangle |
| `pattern_hns` | pattern_scanner | Head & Shoulders + Inverse H&S |
| `pattern_wyckoff` | pattern_scanner | Wyckoff Accumulation/Distribution phases |
| `pattern_elliot` | pattern_scanner | Elliot Wave impulse + corrective patterns |

All written to signals DB with `source='pattern_scanner'`, `decision='PENDING'`.

### Performance Calibration — WR-Based Auto-Multiplier (BUILT 2026-04-06)
Applies to ALL signal types. After 15+ trades, WR drives multiplier.

```
WR >= 55%  → 1.5× (boost winning signals)
WR 45-55%  → 1.25× (keep baseline)
WR 40-45%  → 0.75× (suppress borderline)
WR < 40%   → 0.0× (exclude from hot-set entirely)
```

**Implementation:** `ai_decider.py`
- `get_signal_type_stats()` — queries signal_outcomes
- `get_category_multipliers()` — aggregates to category level
- `_wr_to_multiplier()` — applies threshold rules
- `SIGNAL_TYPE_CATEGORY_MAP` — maps composite signal_type → category
- `_get_source_weight()` — applies calibration on top of SOURCE_WEIGHT_OVERRIDES

**Live findings (2026-04-06):**
- `decider`: 22.8% WR / 101 trades → DISABLED ⚠️
- `conf-2s`: 33.3% WR / 39 trades → DISABLED
- `conf-3s`: 24.0% WR / 25 trades → DISABLED
- `conf-1s`: 45.5% WR / 110 trades → 1.25× ✅
- `hl_reconcile`: 51.0% WR / 51 trades → 1.25× ✅
- `pattern_scanner`: no data yet → 1.0× baseline (1.25× override pending WR data)

Check status anytime: `python3 -c "from ai_decider import get_calibration_summary; print(get_calibration_summary())"`

---

## Step-by-Step Implementation Plan

### Phase 1 — Foundation (V1, lowest risk)
1. Create `pattern_scanner.py` with OHLCV candle fetching + caching
2. Implement **Bull Flag / Bear Flag** detection first (simplest, most common)
   - Detect flag pole (> 5% impulse in N candles)
   - Detect flag channel (parallel, 1-5 candles, opposite direction)
   - Detect breakout with volume confirmation
3. Write unit tests with synthetic price data
4. Integrate as cascade flip confluence check

### Phase 2 — Wyckoff + H&S
5. Implement **Wyckoff Accumulation** (spring → SOS → JMO → BUYC)
6. Implement **H&S** (left shoulder, head, right shoulder, neckline, breakdown)
7. Integrate both as cascade flip confluence sources
8. Backtest on historical trades (VVV specifically, last 7 days)

### Phase 3 — Elliot Wave + Production
9. Implement **Elliot Wave** simplified detection (5-wave sequences, Fibonacci)
10. Add pattern signals to `signal_gen.py` as standalone entry signals (not just cascade backup)
11. Add pattern quality scoring to existing signals (if H&S + mtf_macd agree, boost confidence)
12. Full backtest on closed trades

---

## Files Likely to Change

| File | Change |
|---|---|
| `/root/.hermes/scripts/pattern_scanner.py` | **NEW** — all pattern detection logic |
| `/root/.hermes/scripts/position_manager.py` | Cascade flip checks pattern_scanner as confluence |
| `/root/.hermes/scripts/signal_gen.py` | Emits pattern signals to DB |
| `/root/.hermes/brain/trading.md` | Document pattern signals, confidence scoring |
| `/root/.hermes/scripts/candle_fetcher.py` | May need to add if not already present |

---

## Testing / Validation

1. **Synthetic data tests:** Feed known H&S, flag, Wyckoff price series, verify correct detection
2. **Historical backtest:** Run pattern scanner on last 30 days of VVV candles, see if it would have caught the entry
3. **Paper trading:** Add `paper=True` guard before any real execution from pattern signals
4. **Confidence calibration:** Compare pattern confidence vs actual outcomes on closed trades

---

## Risks & Tradeoffs

| Risk | Mitigation |
|---|---|
| Pattern detection is inherently subjective (traders disagree on H&S) | Start with flags (objective criteria), defer H&S to Phase 2 |
| HL API rate limits on candle fetches | Aggressive caching, only fetch for tokens in hot-set + active positions |
| Overlapping patterns causing contradictory signals | Signal priority: mtf_macd > pattern, pattern used as confluence only in V1 |
| False breakout rate high on low-timeframe candles | Require volume confirmation + candle close (not just wick) |
| Complexity creep | Hard scope Phase 1 = flag detection only, no scope creep |

---

## Open Questions

1. **Which timeframe?** 1m is noisy, 5m more reliable but slower to update. Start with 1m for active position management, 5m for signal generation.
2. **Volume data quality?** HL volume can have dust trades. Should volume be filtered by trade size?
3. **Pattern confidence calibration:** What confidence should a flag breakout get? What about a perfect H&S? Need historical baseline.
4. **Pattern vs existing signals:** Should pattern signals replace mtf_macd signals, or only act as flip confluence? T's call.
5. **Elliot Wave complexity:** Full EW is extremely complex. V1 should only detect obvious 5-wave sequences with clean Fibonacci. Don't try to label every wave.

---

## Immediate Next Step (Before Any Code)

Run a quick feasibility check: fetch VVV's last 100 candles (1m) and visually/code inspect whether a flag or H&S pattern was forming in the data. This validates whether the data quality supports pattern detection before writing any detection logic.
