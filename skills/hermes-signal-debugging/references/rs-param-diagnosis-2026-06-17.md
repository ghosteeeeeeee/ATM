# RS Signal Diagnosis & Fixes (2026-06-17 to 2026-06-18)

## Session 2026-06-17 — Param Fixes Applied

### RS_PROXIMITY_K = 0.70 → 3.0
For low-vol tokens (ATR%=0.04%): 0.70×0.04% = 0.029% max distance. A level 0.54% away (0G example) = 12.9 ATRs — **18x too tight**. Fixed to 3.0 (allows 0.12%).

### RS_BOUNCE_THRESH_ATR = 1.0 → 0.33
Touch gate = 0.2 ATR = 0.000025 absolute. Bounce follow-through = 0.025% of level = 0.000076. Ratio: 0.000076/0.000025 = **3.0x** — structurally impossible. Fixed to 0.33 (touch = 0.067 ATR; bounce = 0.9x touch gate, achievable).

### RS_TOUCH_HARD_CAP = 120 → 200
Was blocking the best SHORT bucket (151-200 tc: 66.7% WR avg, +2.0% PnL). 201-300 is natural ceiling at 17.4% WR.

### RS_BROKEN_SHORT_ENABLED = True → False
Comment said "DISABLED" but constant was True — was filling hot-set with counter-trend traps (29% WR). Fixed to False.

### RS_BROKEN_RESISTANCE_LONG_ENABLED = True → False
Counter-trend trap (BLUR/BRETT loss pattern). Fixed to False.

---

## Session 2026-06-18 — Confluence Gate Root Cause

**Problem:** Param fixes were correct but RS signals still never reached hot-set.

**Root cause discovered:** `signal_compactor.py` confluence gate (lines 538-599) requires **2+ unique signal types**. RS fires 6 times/hour and accel fires 1,680 times/hour — they **never co-occur in the same 5-minute PENDING window**. Zero RS+accel combos in 30 minutes of observation.

### Evidence
```
ACCEL_300_STANDALONE_BYPASS_ENABLED=False, CONF=70
Last 30 min: 35 accel signals (all single-source) / 3 RS signals (all single-source)
Zero RS+accel combos in same 5-min bucket
All PENDING signals: BLOCKED — only 1 unique types
```

### Confluence Key Normalization (signal_compactor.py:558-566)
```python
part = re.sub(r'-broken$', '', part)       # rs-s-broken → rs-s
part = re.sub(r'^rs-[sr]', 'rs', part)     # rs-s86, rs-r1774 → rs
return re.sub(r'\d+$', '', part) or part   # rs-s86 → rs-s
```
Collapses `rs-s86`, `rs-r1774`, `rs-s-broken` → `rs`. So `accel-300-+rs-s86` = 2 unique types = PASS.

### Diagnosis Command
```bash
cd /root/.hermes/scripts && python3 signal_compactor.py --verbose --dry 2>&1 | grep CONFLUENCE
```

### What Would Fix It

| Option | Effect | Risk |
|--------|--------|------|
| `ACCEL_300_STANDALONE_BYPASS_ENABLED=True` | Accel alone bypasses confluence | Was disabled for 40% WR |
| Change pipeline order (signals_runner before compactor) | Signals persist longer as PENDING | Minor |
| Widen confluence time window | Older signals combine with new | RS expires at 5 min anyway |

### Related Files
- `signals/rs.py` — RS signal generator
- `signal_compactor.py` — Confluence gate (lines 538-599)
- `hermes_constants.py` — RS and bypass constants
