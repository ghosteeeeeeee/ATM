# Signal Lifecycle Engine — Spec

## Problem Statement

Hermes has 37 signals in `scripts/signals/`, most disabled. The system fires ALL enabled signals every cycle and filters downstream. There's no:
- **Rotation**: "use momentum signals in trending markets, mean-reversion in ranging"
- **Feedback loop**: signal_decay_detector auto-disables but never auto-re-enables
- **Lifecycle states**: signals are just enabled/disabled — no "experimental," "maturing," "deprecated"
- **Dynamic allocation**: hot-set is fixed top-10, not adaptive to market conditions
- **Research pipeline**: new signals are hand-written, never auto-generated from market patterns

**Goal:** Closed-loop signal management — audit → prioritize → rotate → develop → retire.

## Guiding Principle

> Don't rebuild what exists. The compactor already scores with regime weights, the decay detector already auto-disables, the autotuner already tunes params. This engine adds the **meta-layer** that orchestrates them.

## Architecture

```
                    ┌─────────────────────────┐
                    │   Signal Lifecycle Engine │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
     │ signal_auditor  │ │signal_rotator│ │signal_researcher│
     │ (every 6h)      │ │ (every 4h)  │ │ (every 12h)     │
     └────────┬────────┘ └──────┬──────┘ └────────┬────────┘
              │                  │                  │
     ┌────────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
     │ signal_outcomes │ │regime_*.json│ │ candles.db +    │
     │ (SQLite)        │ │ (regime)    │ │ TradingView MCP │
     └─────────────────┘ └─────────────┘ └─────────────────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ hermes_constants.py      │
                    │ (enable/disable signals) │
                    └─────────────────────────┘
```

## Components

### 1. Signal Auditor (`scripts/signal_auditor.py`)

**Timer:** Every 6 hours (before decay detector)

**Purpose:** Rank all signals by "edge score" — the product of win rate, average PnL, and trade count. Output a performance table and suggest actions.

**Data source:** `signal_outcomes` table (7-day window, deduped by `trade_id IS NOT NULL`)

**Logic:**
```
edge_score = (wins/trades) * avg_pnl * sqrt(trade_count)
```

**Output:**
- `data/signal_audit.json` — machine-readable audit results
- `automation/signal_audit.md` — human-readable ranked table
- Suggested actions: `prioritize` (WR>60%, positive PnL), `enable_candidate` (strong WR but disabled), `disable_candidate` (WR<30% and losing), `monitor`

**Safety:** No automatic changes. Read-only audit. Rotator acts on suggestions.

**Integration:** Reads from `signals/__init__.py` to get enabled/disabled status per signal. Maps signal_type names to `*_ENABLED` flags in `hermes_constants.py`.

### 2. Signal Rotator (`scripts/signal_rotator.py`)

**Timer:** Every 4 hours (before pipeline peak)

**Purpose:** Select the optimal signal subset for current market conditions. Enable/disable signals via `hermes_constants.py`.

**Data sources:**
- `signal_audit.json` (from auditor)
- `regime_4h.json` or `regime_5m.json` (current market regime)
- `signal_outcomes` (24h performance for regime-specific analysis)

**Logic:**
1. Read current regime from `/var/www/hermes/data/regime_5m.json`
2. For each signal type, compute regime-specific WR from signal_outcomes (filter by regime column if available, else by time-of-day proxy)
3. Rank signals by regime-adjusted edge score
4. Select top N signals (configurable, default 8-12)
5. Enable selected signals, disable others

**Regime → signal mapping (initial, data-driven later):**
| Regime | Signal Categories to Prioritize |
|--------|--------------------------------|
| TRENDING_UP | momentum, breakout, velocity |
| TRENDING_DOWN | inverse, breakout, exhaustion |
| RANGING | mean-reversion, squeeze, zscore |
| VOLATILE | breakout, acceleration, atr_compression |

**Safety constraints:**
- Max 2 signal changes per cycle
- Never disable a signal with WR > 50% and trades >= 10
- Never enable a signal with WR < 25% and trades >= 5
- Backup `hermes_constants.py` before any change
- Validate Python syntax after write

**Output:**
- Modified `hermes_constants.py` (enable/disable flags)
- `data/signal_rotation.json` — rotation decisions log
- `automation/signal_rotation.md` — human-readable rotation report

### 3. Signal Researcher (`scripts/signal_researcher.py`)

**Timer:** Every 12 hours (background, low priority)

**Purpose:** Discover new signal ideas from market data. Auto-backtest promising patterns. Generate signal templates for human review.

**Data sources:**
- `candles.db` (historical price data)
- TradingView MCP tools (market scanning)
- `signal_outcomes` (existing signal performance for gap analysis)

**Logic:**
1. **Gap analysis:** What market conditions have no signal coverage? (e.g., "no signal handles low-volatility ranging markets well")
2. **Pattern scanning:** Use TradingView MCP (bollinger_scan, volume_breakout_scanner, consecutive_candles_scan) to find statistically unusual patterns
3. **Hypothesis generation:** For each pattern, form a testable hypothesis: "When BBW < 0.02 and volume spikes 2x, price breaks out within 3 candles with 60% WR"
4. **Auto-backtest:** Test hypothesis against 30-day candle history using `candles.db`
5. **If backtest passes** (WR > 55%, trades >= 20, avg PnL > 0):
   - Write signal template to `scripts/signals/_candidates/`
   - Log to `automation/signal_research.md`
   - Human reviews and promotes to `scripts/signals/`

**Safety:** Never auto-enables new signals. Candidates stay in `_candidates/` until human promotes.

**Integration:** Reuses `get_candles_range()` from `backtest_breakout.py`. Uses TradingView MCP for market scanning.

### 4. Signal Lifecycle Manager (`scripts/signal_lifecycle.py`)

**Timer:** Daily (runs auditor + rotator + researcher in sequence)

**Purpose:** Orchestrator. Single entry point for the full lifecycle. Also manages signal state metadata.

**Signal states (tracked in `data/signal_lifecycle.json`):**
```
{
  "accel_300": {
    "state": "active",          # experimental | active | maturing | deprecated
    "enabled_since": "...",
    "last_wr": 57.2,
    "edge_score": 0.342,
    "regime_affinity": ["TRENDING_UP", "VOLATILE"],
    "decay_count": 0,           # times auto-disabled
    "re_enable_count": 1,       # times auto-re-enabled
    "notes": "Strong on longs, weak on shorts"
  }
}
```

**State transitions:**
```
experimental → active      (WR > 50% for 3+ days, 20+ trades)
active → maturing          (WR drops below 40% for 2+ days)
maturing → deprecated      (WR drops below 25% for 3+ days)
deprecated → experimental  (manual re-evaluation only)
experimental → deprecated  (WR < 20% with 10+ trades)
```

**Lifecycle actions:**
- Reads audit results → updates state metadata
- Reads rotation decisions → logs regime affinity
- Reads researcher output → manages candidate pipeline
- Writes daily summary to `automation/signal_lifecycle.md`

## Data Flow (Daily Cycle)

```
06:00 UTC — signal_auditor.py
  └─ Reads signal_outcomes (7d) → ranks signals → writes signal_audit.json
  └─ Suggests enable/disable actions (read-only)

10:00 UTC — signal_rotator.py
  └─ Reads signal_audit.json + regime_5m.json
  └─ Selects best signal subset for current regime
  └─ Enables/disables signals in hermes_constants.py

18:00 UTC — signal_researcher.py
  └─ Scans market patterns via TradingView MCP
  └─ Auto-backtests promising patterns
  └─ Writes candidates to scripts/signals/_candidates/

22:00 UTC — signal_lifecycle.py (daily orchestrator)
  └─ Runs auditor + rotator in sequence
  └─ Updates signal lifecycle states
  └─ Writes daily summary
```

## Files to Create

```
scripts/signal_auditor.py        ✅ (already written, needs spec alignment)
scripts/signal_rotator.py        ❌
scripts/signal_researcher.py     ❌
scripts/signal_lifecycle.py      ❌
scripts/signals/_candidates/     ❌ (directory for new signal templates)
data/signal_audit.json           (output)
data/signal_rotation.json        (output)
data/signal_lifecycle.json       (output — state metadata)
automation/signal_audit.md       (output)
automation/signal_rotation.md    (output)
automation/signal_lifecycle.md   (output)
automation/signal_research.md    (output)
```

## Systemd Timers

```
hermes-signal-auditor.timer       (6h)
hermes-signal-rotator.timer       (4h)
hermes-signal-researcher.timer    (12h)
hermes-signal-lifecycle.timer     (24h)
```

## Safety Rails

1. **Max 2 changes per cycle** — no mass enable/disable
2. **WR guards** — never disable WR>50%, never enable WR<25%
3. **Backup before write** — shutil.copy2 before hermes_constants.py edit
4. **Syntax validation** — compile() after write, restore on failure
5. **No auto-promote** — researcher candidates require human review
6. **Lock files** — prevent concurrent modification
7. **Audit trail** — all changes logged to automation/*.md

## Integration with Existing Systems

| Existing System | How It Integrates |
|----------------|-------------------|
| signal_decay_detector | Auditor reads same data. Decay detector auto-disables; rotator can re-enable if edge recovers. |
| signal_quality_autotuner | Rotator enables/disables signals; autotuner tunes params within enabled signals. |
| signal_compactor | Rotator changes which signals fire; compactor continues scoring/filtering as before. |
| signal_quality_tracker | Tracker records signal+entry; auditor reads outcomes from same data. |
| 4h/15m regime scanners | Rotator reads regime output to select signal subset. |

## Success Metrics

- **Signal rotation accuracy:** >55% WR on rotated signals (vs baseline ~32% current)
- **Decay detection speed:** Detected within 6h (already achieved by decay_detector)
- **Re-enable speed:** Signal re-enabled within 24h of WR recovery
- **Research pipeline:** ≥1 candidate signal generated per week
- **Zero manual signal management:** No CEO intervention needed for routine enable/disable

## Implementation Order

1. **signal_auditor.py** — foundation (already written, align with spec)
2. **signal_rotator.py** — immediate impact (rotation by regime)
3. **signal_lifecycle.py** — state management (orchestrator)
4. **signal_researcher.py** — long-term value (new signal generation)
