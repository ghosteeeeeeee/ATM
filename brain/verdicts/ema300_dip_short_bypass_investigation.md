# EMA300 Dip Short Bypass Investigation

**Date:** 2026-09-05  
**Severity:** CRITICAL — causing live money losses (SEI -5.40%, STX -5.56%, ETC -4.90%, WLFI/ADA/BCH open)  
**Author:** CEO/Hermes Investigation  

---

## Executive Summary

The `ema300_dip_short` signal is being emitted by the hotset pipeline and executed as trades **after the detection function has correctly blocked it**. The root cause is a **stale signal persistence bug**: signals written to the DB when conditions were valid continue to be processed by the compactor and executed by decider_run even after market conditions reverse (EMA slope turns positive). The detection function only validates conditions at signal generation time — no downstream component re-validates the EMA300 slope condition.

---

## 1. Root Cause Analysis

### Primary Root Cause: No Re-validation of Detection Function Conditions

The system has a fundamental architectural gap:

1. **Detection function** (`ema300_dip_short.py:56-151`) validates 6 conditions including EMA300 slope < 0 at **signal generation time only**
2. **Compactor** (`signal_compactor.py`) reads signals from DB and builds hotset — **does NOT re-run detection function**
3. **Decider** (`decider_run.py`) executes approved signals from hotset — **does NOT re-run detection function**
4. **Preservation path** (`_filter_safe_prev_hotset`) preserves previous hotset entries — **does NOT re-run detection function or SLOPE FILTER**

Once a signal enters the DB, the only thing preventing execution is:
- 5-minute staleness decay (0.2 decay rate → 5 min window)
- SLOPE FILTER in compactor pre-filter (checks PRICE slope, NOT EMA300 slope)
- Various other filters (spike, velocity, etc.)

**The detection function's EMA300 slope check is NEVER re-validated.**

### Contributing Factor: STANDALONE_BYPASS Allows Single-Source Signals

`ema300-dip-short` is in `STANDALONE_BYPASS_SIGNALS` (`hermes_constants.py:1828`), which means:

- Single-source `ema300-dip-short` signals bypass the confluence gate (2+ source requirement)
- They can enter and persist in the hotset with only ONE source
- This is by design (backtested signal), but it means there's no second signal to provide cross-validation

### Contributing Factor: Preservation Path Bypasses Safety Filters

The `_filter_safe_prev_hotset()` function (line 2913-3036) preserves previous hotset entries but does NOT run:

- **SLOPE FILTER** (price trend check)
- **Spike filter** (recent bullish candle check)
- **Velocity filter** (recent price movement check)
- **Detection function conditions** (EMA300 slope, RSI, distance, etc.)

A preserved entry can survive for 5-8 minutes (or longer for FAVORITES tokens) without any re-validation of the detection function's conditions.

### Contributing Factor: Compactor SLOPE FILTER Checks Different Metric

The compactor's SLOPE FILTER (line 1232-1268) checks:
- **Price slope**: Linear regression of 20 1m close prices
- **Threshold**: `ACCEL_300_REGIME_SLOPE_PCT = 0.05%` (or 3x in SHORT_BIAS)

The detection function checks:
- **EMA300 slope**: Percentage change of EMA300 over 20 periods
- **Threshold**: `EMA300_DIP_SHORT_MAX_EMA_SLOPE = 0.0` (hard zero)

These are **different metrics**. A token can have:
- Negative price slope (short-term drop) → passes compactor SLOPE FILTER
- But positive EMA300 slope (long-term EMA still rising) → detection function blocks

The compactor's SLOPE FILTER can also be **relaxed 3x in SHORT_BIAS regime**, further reducing its effectiveness.

---

## 2. Code Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SIGNAL GENERATION (signals_runner.py)            │
│                                                                     │
│  ema300_dip_short.py:scan_signals()                                │
│    └─ detect_ema300_dip_short()                                    │
│         ├─ Condition 1: Price < EMA300                             │
│         ├─ Condition 2: <30% candles above EMA300                  │
│         ├─ Condition 3: EMA300 slope < 0  ← BLOCKS HERE            │
│         ├─ Condition 4: Price within 0.5% of EMA300                │
│         ├─ Condition 5: RSI > 65                                   │
│         └─ Condition 6: Red candle                                 │
│              │                                                     │
│              ├─ Returns None → NO SIGNAL (correct)                 │
│              └─ Returns signal dict → add_signal() → DB (PENDING)  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SIGNAL COMPACTOR (signal_compactor.py)           │
│                                                                     │
│  Step 2: Pre-filter (line 1219-1576)                               │
│    ├─ SLOPE FILTER (line 1232-1268)                                │
│    │   └─ Checks PRICE slope (20-bar linear regression)            │
│    │   └─ Does NOT check EMA300 slope                             │
│    │   └─ Can be relaxed 3x in SHORT_BIAS                         │
│    ├─ CONFLUENCE GATE (line 1270-1562)                             │
│    │   └─ ema300-dip-short in STANDALONE_BYPASS → PASSES          │
│    └─ Other filters (blacklist, conflict, poison)                  │
│                                                                     │
│  Step 9: Build hotset entries (line 1786-1873)                     │
│    └─ Signal enters hotset.json                                    │
│                                                                     │
│  Step 12: Preserve previous hotset (line 2160-2347)                │
│    └─ _filter_safe_prev_hotset()                                   │
│         ├─ Does NOT run SLOPE FILTER                               │
│         ├─ Does NOT run detection function                         │
│         └─ Preserves stale signals for 5-8 minutes                 │
│                                                                     │
│  Step 15: Write hotset.json (line 2680-2739)                       │
│    └─ hotset.json written with stale signal                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DECIDER RUN (decider_run.py)                     │
│                                                                     │
│  main() (line 2515+)                                               │
│    ├─ Reads hotset.json                                            │
│    ├─ Iterates hotset entries                                      │
│    ├─ Checks: blacklist, cooldown, position, staleness             │
│    ├─ Does NOT re-run detection function                           │
│    ├─ Does NOT check EMA300 slope                                  │
│    └─ Executes trade via brain.py                                  │
│                                                                     │
│  RESULT: Trade opened with stale signal                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Specific Lines of Code Involved

### Detection Function (Correct)
| File | Line | Description |
|------|------|-------------|
| `ema300_dip_short.py` | 56-151 | `detect_ema300_dip_short()` — validates all 6 conditions |
| `ema300_dip_short.py` | 97-102 | EMA300 slope check: `if ema_slope >= EMA300_DIP_SHORT_MAX_EMA_SLOPE: return None` |
| `ema300_dip_short.py` | 186-240 | `scan_signals()` — calls detection, writes to DB |

### Compactor (Missing Re-validation)
| File | Line | Description |
|------|------|-------------|
| `signal_compactor.py` | 1232-1268 | SLOPE FILTER — checks PRICE slope, NOT EMA300 slope |
| `signal_compactor.py` | 1237 | Only exempts `inv-accel-300-v2`, not `ema300-dip-short` |
| `signal_compactor.py` | 1254-1261 | Regime relaxation: 3x threshold in SHORT_BIAS |
| `signal_compactor.py` | 1489-1522 | NEUTRAL relax: allows single-source via `STANDALONE_BYPASS_SIGNALS` |
| `signal_compactor.py` | 1538 | `bare_source in STANDALONE_BYPASS_SIGNALS` — bypasses confluence |
| `signal_compactor.py` | 2128-2154 | FINAL CONFLUENCE GUARD — another STANDALONE_BYPASS bypass |
| `signal_compactor.py` | 2913-3036 | `_filter_safe_prev_hotset()` — NO detection function re-validation |

### Constants
| File | Line | Description |
|------|------|-------------|
| `hermes_constants.py` | 1536 | `EMA300_DIP_SHORT_MAX_EMA_SLOPE = 0.0` |
| `hermes_constants.py` | 1289 | `ACCEL_300_REGIME_SLOPE_PCT = 0.05` (compactor slope threshold) |
| `hermes_constants.py` | 1828 | `'ema300-dip-short'` in `STANDALONE_BYPASS_SIGNALS` |

### Decider (Missing Re-validation)
| File | Line | Description |
|------|------|-------------|
| `decider_run.py` | 1972-2059 | Hotset iteration — reads from hotset.json, no detection re-run |
| `decider_run.py` | 2214-2215 | `effective_conf = float(sig_conf) * wave_mult + speed_pts` |

---

## 4. Evidence from Database

### Recent ema300_dip_short Trades (PostgreSQL)
```
BCH  SHORT pnl=  +0.00  open=2026-09-05 03:05  sig=ema300-dip-short       conf=79
ADA  SHORT pnl=  +0.02  open=2026-09-05 02:27  sig=ema300-dip-short       conf=79
WLFI SHORT pnl=  -0.03  open=2026-09-04 23:51  sig=ema300-dip-short       conf=84
SEI  SHORT pnl=  -0.20  open=2026-09-04 23:12  sig=ema300-dip-short       conf=84
ETC  SHORT pnl=  -0.11  open=2026-09-04 18:37  sig=ema300-dip-short       conf=102
STX  SHORT pnl=  -0.12  open=2026-09-04 18:31  sig=ema300-dip-short,rs-r37 conf=99
```

### Signal DB (SQLite)
Multiple tokens (AZTEC, INJ, CASHCAT, HYPE, BTC, CAKE) have ema300_dip_short signals in EXPIRED state — detection function was blocking but compactor was still passing them through the confluence gate via NEUTRAL-relax standalone bypass.

### Log Evidence
```
03:49:02   🔎 [CONFLUENCE-DEBUG] INJ SHORT: source='ema300-dip-short' parts=['ema300-dip-short'] count=1 unique_types=1 -> PASS
03:49:02   ✅ [CONFLUENCE-GATE-PASS] INJ SHORT: {ema300-dip-short} (NEUTRAL-relax: standalone bypass)
```

The compactor was passing INJ SHORT through the confluence gate via NEUTRAL-relax standalone bypass, even though the detection function was returning 0 signals (blocking).

---

## 5. The Bypass Path (Step by Step)

1. **T0**: EMA slope < 0 → detection function fires → signal written to DB (PENDING, conf=82)
2. **T0+1min**: Compactor runs → SLOPE FILTER checks PRICE slope (not EMA300) → may pass
3. **T0+1min**: Confluence gate → `ema300-dip-short` in STANDALONE_BYPASS → PASSES (single source allowed)
4. **T0+1min**: Signal enters top-10 → APPROVED in DB → hotset.json
5. **T0+2min**: decider_run reads hotset.json → executes trade
6. **T0+3min**: Market moves → EMA slope turns positive → detection function now blocks (returns None)
7. **T0+3min**: Compactor runs → detection function produces 0 signals → BUT stale signal still in DB
8. **T0+3min**: Compactor: stale PENDING/APPROVED signal from DB → confluence gate passes (STANDALONE_BYPASS) → hotset.json
9. **T0+3min**: Preservation path: `_filter_safe_prev_hotset()` preserves entry → NO SLOPE FILTER, NO detection re-validation
10. **T0+4min**: decider_run executes stale trade with wrong conditions

---

## 6. Why conf=82.0 Appears in Hotset

The detection function's confidence range is 70-88 (BASE_CONFIDENCE=75, MAX_CONFIDENCE=88). A signal with conf=82 is within this range and was valid when generated.

The compactor writes this confidence to hotset.json. The decider then boosts it:
```python
effective_conf = float(sig_conf) * wave_mult + speed_pts
```

This explains why trades show conf=99, 102, 104 — the raw 82 was boosted by wave_mult (1.10-1.15) and speed_pts (+6.0).

---

## 7. Recommended Fix

### Immediate Fix (Priority 1): Add EMA300 Slope Re-validation to Compactor

Add a **detection function re-validation step** in the compactor's pre-filter (Step 2) and preservation path (Step 12) for `ema300-dip-short` signals:

```python
# In signal_compactor.py, after SLOPE FILTER (line 1268), add:
# ── EMA300 SLOPE RE-VALIDATION (defense-in-depth) ──────────────────
# Re-check EMA300 slope for ema300-dip-short signals.
# The detection function checks this at generation time, but signals
# can persist in the DB after conditions change. This catches stale
# signals where EMA300 slope has turned positive.
if signal_type == 'ema300_dip_short' and direction.upper() == 'SHORT':
    try:
        from hermes_constants import EMA300_DIP_SHORT_MAX_EMA_SLOPE, EMA300_DIP_SHORT_EMA_PERIOD
        _ema_conn = sqlite3.connect(CANDLES_DB, timeout=5)
        _ema_rows = _ema_conn.execute(
            "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 700",
            (token.upper(),)
        ).fetchall()
        _ema_conn.close()
        if _ema_rows and len(_ema_rows) >= 500:
            _closes = [r[0] for r in reversed(_ema_rows)]
            _ema = _closes[0]
            _k = 2.0 / (EMA300_DIP_SHORT_EMA_PERIOD + 1)
            for _c in _closes:
                _ema = _c * _k + _ema * (1 - _k)
            _ema_vals = [_ema]
            # Compute last 20 EMA values for slope
            _ema_v = _closes[0]
            _ema_hist = []
            for _c in _closes:
                _ema_v = _c * _k + _ema_v * (1 - _k)
                _ema_hist.append(_ema_v)
            if len(_ema_hist) >= 20:
                _ema_slope = (_ema_hist[-1] - _ema_hist[-20]) / _ema_hist[-20] * 100
                if _ema_slope >= EMA300_DIP_SHORT_MAX_EMA_SLOPE:
                    log(f"  🚫 [EMA300-SLOPE-RECHECK] {token} SHORT: ema_slope={_ema_slope:+.4f}% >= {EMA300_DIP_SHORT_MAX_EMA_SLOPE}% — stale signal blocked")
                    continue
    except Exception:
        pass  # non-fatal
```

Also add the same check in `_filter_safe_prev_hotset()` for preserved entries.

### Architectural Fix (Priority 2): Store Detection Conditions in Signal Metadata

When `add_signal()` is called, store the detection function's condition values (EMA slope, RSI, distance, trend strength) in `signal_metadata`. The compactor can then re-check these conditions against CURRENT market data.

### Design Fix (Priority 3): Consider Removing ema300-dip-short from STANDALONE_BYPASS

If the signal requires specific market conditions (EMA slope < 0), it may be too risky to allow it as a standalone bypass. Consider requiring confluence (2+ sources) to provide cross-validation.

---

## 8. Confidence Level

**95%** — Root cause is confirmed by:

1. **Code analysis**: Detection function validates at generation time only; no downstream re-validation
2. **Database evidence**: Signals in DB with EXPIRED state while compactor was still passing them through
3. **Log evidence**: Compactor passing signals via `NEUTRAL-relax: standalone bypass` while detection function returns 0
4. **Trade evidence**: Multiple losing trades (SEI, STX, ETC) with ema300-dip-short signal
5. **Architecture gap**: Preservation path bypasses all detection function conditions

The remaining 5% uncertainty is whether the SLOPE FILTER in the compactor should have caught these signals but didn't due to the regime relaxation (3x threshold in SHORT_BIAS) or because price slope diverged from EMA300 slope.

---

## 9. Additional Findings

### Finding: SLOPE FILTER Uses Wrong Metric (Severity: HIGH)
The compactor's SLOPE FILTER (line 1232-1268) checks **price slope** (linear regression of raw closes), but the detection function checks **EMA300 slope** (smoothed average). These are fundamentally different metrics that can diverge. The SLOPE FILTER should be enhanced to also check EMA300 slope for ema300-dip-short signals.

### Finding: Regime Relaxation Weakens SLOPE FILTER (Severity: MEDIUM)
The SLOPE FILTER threshold is relaxed 3x in SHORT_BIAS regime (`ACCEL_300_REGIME_SLOPE_PCT * 3.0`). This means a token with price slope up to 0.15% can pass the filter in SHORT_BIAS, even though the detection function requires EMA slope < 0.

### Finding: PRESERVE-APPROVED-UPSERT Creates Zombie Signals (Severity: HIGH)
The PRESERVE-APPROVED-UPSERT (line 2279-2337) creates APPROVED DB rows for preserved entries. These APPROVED rows are then picked up by decider_run and executed. The 30-minute age guard (line 2276-2278) helps, but the 5-minute staleness decay should be sufficient if the preservation path correctly enforced it.

### Finding: Detection Function EMA300 Computation May Be Inaccurate (Severity: LOW)
The detection function computes EMA300 from 700 1m candles, but the initial EMA value is set to `closes[0]` (line 75-76). For a true EMA300, the initial value should be the SMA of the first 300 values. This may cause slight inaccuracies in the slope calculation, but it's unlikely to be the primary cause of the bypass.

---

## 10. Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `signal_compactor.py` | Add EMA300 slope re-validation in pre-filter (after line 1268) | P1 |
| `signal_compactor.py` | Add EMA300 slope re-validation in `_filter_safe_prev_hotset()` | P1 |
| `signal_compactor.py` | Enhance SLOPE FILTER to check EMA300 slope for ema300-dip-short | P2 |
| `hermes_constants.py` | Consider removing `ema300-dip-short` from `STANDALONE_BYPASS_SIGNALS` | P3 |

---

*This investigation was conducted by the Hermes Trading System CEO. All findings are based on code analysis, database queries, and log inspection.*
