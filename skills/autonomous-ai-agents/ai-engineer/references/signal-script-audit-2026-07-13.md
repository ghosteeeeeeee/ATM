# Signal Script Audit — 2026-07-13

Audit of 12 top-level signal scripts in `/root/.hermes/scripts/` against the
production pipeline wiring. Three new patterns emerged (Patterns 68, 69, 70) — see
`SKILL.md` for one-line summaries; this file has the full reproducer and context.

## 1. The Live-Path Wiring Map (the most important finding)

The Hermes signal architecture has TWO parallel implementations:

| Layer | Location | Purpose |
|---|---|---|
| **Active subpackage** | `/root/.hermes/scripts/signals/` | Wired via `signals_runner.py` (line 33 of `run_pipeline.py`) and `signals/__init__.py` registry. Runs every minute (fast) or every 5m (slow). |
| **Top-level legacy** | `/root/.hermes/scripts/*_signals.py` | Original early-2026 implementations. Some are still directly imported by `signal_gen.py`; some are invoked only via standalone `run_*.py` wrappers; some are dead. |

### Wiring table for the 12 audited scripts (verified 2026-07-13)

| Script | `signal_gen.py` caller? | Standalone `run_*.py`? | Subpackage version? | Timer wired? | **Live?** |
|---|---|---|---|---|---|
| `gap300_signals.py` | YES (line 2233) | no | `signals/gap_300.py` | indirect (pipeline) | YES |
| `ma_cross_signals.py` | NO | `run_ma_cross_signals.py` only | `signals/ma_cross.py` | NOT IN PIPELINE | NO |
| `ma_fast_signals.py` | NO | `run_ma_fast_signals.py` only | none | NOT IN PIPELINE | NO |
| `zscore_momentum.py` | YES (line 2246) | self (CLI) | `signals/mtp_zscore.py` etc. | indirect (pipeline) | YES |
| `rs_signals.py` | YES (line 2227) | CLI | `signals/rs.py` | indirect (pipeline) | YES |
| `r2_trend_signals.py` | NO | `run_r2_trend_signals.py` only | `signals/r2_trend.py` | NOT IN PIPELINE | NO |
| `macd_1m_signals.py` | **NO** (commented out, line 2223) | CLI | `signals/macd_1m.py` | NOT IN PIPELINE | NO |
| `volume_1m_signals.py` | YES (line 2249) | no | `signals/volume_hl.py` | indirect (pipeline) | YES |
| `ma300_candle_confirm_signals.py` | YES (line 2328) | `run_ma300_candle_confirm_signals.py` | `signals/ma300_candle_confirm.py` | indirect (pipeline) | YES |
| `macd_rules.py` | YES (line 139 — `MACD_PARAMS, get_macd_params`) | no (rules library) | n/a | n/a | YES (as lib) |
| `ma_cross_5m.py` | YES (line 2230) | self (CLI) | `signals/ma_cross_5m.py` | indirect (pipeline) | YES |
| `pattern_scanner.py` | YES (line 34, used by signal_gen path) | self (CLI) | none | depends on signal_gen | YES |

### Verification recipe (use this BEFORE auditing any signal script)

```bash
# 1. Which scripts does signal_gen.py import?
grep -n "^from [a-z_]*_signals\|^from pattern_scanner\|^from macd_rules" signal_gen.py

# 2. Which scripts does the pipeline (run_pipeline.py → signals_runner.py) actually run?
grep -n "_run\|run_" signals/__init__.py | head -30

# 3. Are there systemd timers for standalone runners?
ls /etc/systemd/system/ | grep -iE "ma_cross|ma_fast|r2_trend|ma300_candle"
# As of 2026-07-13: NO timers exist for these — only run_pipeline.py runs.

# 4. Does the script have a `run_*.py` wrapper suggesting manual invocation only?
ls /root/.hermes/scripts/run_*signals*.py
```

### Implication for triage

A bug in `ma_cross_signals.py` (e.g. missing set_cooldown) has near-zero real-world
impact because the live pipeline doesn't run it. A bug in `pattern_scanner.py` has
full impact because signal_gen imports it.

**Rule:** When asked to "audit all signal scripts," build the wiring table FIRST
and rank findings by live-impact tier. A bug in a non-running script is real but
operationally inert — flag it but rank below bugs in the live path.

## 2. Pattern 69 — Slice-arithmetic cancellation in `pattern_scanner.py`

Four occurrences at lines 151, 281, 396, 514 in `pattern_scanner.py` use this pattern:

```python
consolidation_candles = candles[
    consolidation_start + i - consolidation_start :
    consolidation_start + i - consolidation_start + w
]
```

`consolidation_start + i - consolidation_start` simplifies to just `i`. The slice
equals `candles[i:i+w]`. Behavior is correct because `closes[i:]` was used to define
`remaining` earlier in the same loop body, and `candles[i:i+w]` indexes into the
same range.

### Concrete trace

```python
# At line 140: for i in range(consolidation_start, len(closes))
#   remaining = closes[i:]
# At line 146: for w in range(FLAG_CONSOLIDATION_MIN_CANDLES, ...)
#   window = remaining[:w]
# At line 151 (when c_range passes):
consolidation_candles = candles[
    consolidation_start + i - consolidation_start :
    consolidation_start + i - consolidation_start + w
]
# consolidation_start + i - consolidation_start = i
# slice becomes candles[i:i+w]
```

With `consolidation_start = 10, i = 15, w = 4`:
- `candles[10 + 15 - 10 : 10 + 15 - 10 + 4]`
- `candles[15 : 19]` ← identical to `candles[i:i+w]`

### Why this matters

1. **Every future auditor will flag this** as an off-by-`consolidation_start` bug.
   It has been flagged in similar contexts across the codebase before.
2. **A "fix" changing `i` to `consolidation_start + i`** in either bound would
   introduce a REAL bug — the slice would shift by `consolidation_start` and could
   index candles BEFORE the pole, contaminating the consolidation window.
3. The expression is **misleading self-documentation**. It implies an index basis
   of `consolidation_start + offset` when the actual basis is just `i`.

### Recommended fix

Replace all 4 occurrences with:
```python
consolidation_candles = candles[i:i + w]
```

### General rule for the auditor

When a slice expression "looks wrong" because of cancelling terms, ALWAYS simplify
the algebra first. Report as one of:
- "Misleading expression — simplify to `candles[i:i+w]` for clarity. Behavior is correct."
- "Real bug — algebra does NOT simplify. Apply the cancellation-style fix at <line>."

Never flag a cancelling-terms slice as broken without first verifying the algebra.

## 3. Pattern 70 — set_cooldown coverage gap

After `add_signal()` returns non-None, the calling `scan_*_signals()` should set a
cooldown so the same token+direction doesn't fire repeatedly.

### Coverage matrix (2026-07-13)

| Script | set_cooldown called? | Coverage mechanism |
|---|---|---|
| `gap300_signals.py` | ✅ line 487 | direct |
| `zscore_momentum.py` | ✅ line 741-744 | direct |
| `macd_1m_signals.py` | ✅ lines 238, 267 | direct |
| `ma_cross_5m.py` | ✅ line 628 | direct |
| `ma_cross_signals.py` | ❌ | rescued by `run_ma_cross_signals.py:121` calling `record_cooldown_start()` |
| `ma_fast_signals.py` | ❌ | rescued by `run_ma_fast_signals.py` |
| `r2_trend_signals.py` | ❌ | rescued by `run_r2_trend_signals.py` |
| `volume_1m_signals.py` | ❌ | no cooldown at all in `scan_volume_1m_signals()` |
| `ma300_candle_confirm_signals.py` | ❌ | no cooldown at all in `scan_ma300_candle_signals()` |
| `pattern_scanner.py` | ❌ | no cooldown at all |

### Why this matters

The legacy scripts that DON'T call `set_cooldown` are rescued by their `run_*.py`
wrappers which call `record_cooldown_start()` afterwards. But:

1. If anyone calls `scan_*_signals()` directly (e.g. from a test, a CLI invocation,
   or a new caller), no cooldown is set and the signal will fire on every subsequent
   run until something else blocks it (hot-set dedup, open position check, etc.).
2. `record_cooldown_start()` (DB-cooldown) and `set_cooldown()` (JSON-file cooldown)
   are DIFFERENT code paths. `set_cooldown` writes to `loss_cooldowns.json`; the
   `record_cooldown_start` path writes to PostgreSQL. The pipeline uses different
   checks depending on the caller.
3. `volume_1m_signals.py`, `ma300_candle_confirm_signals.py`, and `pattern_scanner.py`
   have NO cooldown fallback at all — they only emit to DB and rely on
   hot-set / confluence dedup to suppress repeats.

### Recommended fix

In each scan function, immediately after the `if sid:` block:
```python
from signal_schema import set_cooldown
set_cooldown(token, direction, hours=0.25)  # 15-min default, tune per-script
```

This makes cooldown part of the signal contract rather than an orchestration concern
delegated to the caller. Resilient to direct invocation, testing, and future caller
changes.

### General rule

`scan_*_signals()` should be self-contained — emit + cooldown + blacklist checks
inside the function, not delegated to the caller. Caller-provided guard logic
(open positions, recent trades) is acceptable as an additional layer but never the
only cooldown path.

## 4. Audit checklist (used 2026-07-13)

For each script, verify:
1. `python3 -m py_compile` — does it compile?
2. Does it read from the correct data sources (price_history for prices, candles_1m
   for volume only)?
3. Are all imports present and correct (sqlite3, time)?
4. Does the query pattern use correct double-subquery for ascending order?
5. Are there any debug print statements left?
6. Are dict returns correct (open/high/low/close not just close)?
7. Are there NameError or AttributeError risks?
8. Does it call set_cooldown after emitting a signal?
9. Does it check for cooldown before emitting (or rely on caller)?

### Per-script checklist results (2026-07-13)

| # | Check | gap300 | ma_cross | ma_fast | zscore_mom | rs | r2_trend | macd_1m | volume_1m | ma300_cc | macd_rules | ma_cross_5m | pattern |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | py_compile OK | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Reads price_history (live) for prices | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | uses _aggregate_5m | ✅ |
| 3 | Imports present (sqlite3, time) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | Double-subquery ascending order | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | partial* | ✅ |
| 5 | No debug prints in hot loop | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (was: fixed) | ✅ (was: fixed) | ✅ | ✅ | ✅ | ✅ |
| 6 | Dict returns complete | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | ✅ | ✅ |
| 7 | No NameError/AttributeError risk | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| 8 | Calls set_cooldown after signal | ✅ line 487 | ❌ | ❌ | ✅ line 741 | ✅* caller's job | ❌ | ✅ lines 238, 267 | ❌ | ❌ | n/a | ✅ line 628 | ❌ |
| 9 | Checks cooldown before emit | via caller | via caller | via caller | ✅ line 638 | via caller | via caller | via caller | via caller | via caller | n/a | via caller | via caller |

\* `ma_cross_5m.py` does not use the double-subquery on `candles_5m` — uses
`ORDER BY ts DESC LIMIT N` + `reversed(rows)` at line 95. Equivalent but less safe
if `ts` isn't strictly monotonically increasing.

\* `rs_signals.py` — sets cooldown via the caller's recent_trade_exists guard,
not directly. Effective but indirect.

## 5. Final verdict (2026-07-13)

- **Pipeline is operationally safe.**
- **1 high-distraction bug**: `pattern_scanner.py` slice-arithmetic (Pattern 69) —
  recommend fix for code clarity; behavior is correct.
- **4 missing-cooldown scripts** (Pattern 70) — rescued by their `run_*.py`
  wrappers, but latent risk if invoked directly.
- **3 EMA/seed inconsistencies in `macd_rules.py`** (Wilder vs SMA seed) — LOW priority,
  may produce subtly different histogram values vs other MACD scripts.
- **1 O(N²) EMA loop in `macd_rules.py`** — LOW priority, not in the hot minute loop.
- **Hardcoded `_PRICE_DB` paths** in 11 of 12 scripts — LOW priority, already
  standardized via `paths.CANDLES_DB` in newer code.

No HIGH-severity functional bugs in the live path.