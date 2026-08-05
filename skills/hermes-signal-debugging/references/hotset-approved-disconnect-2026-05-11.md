# Hot-set / APPROVED Divergence — 2026-05-11

## Problem

Two completely different token lists in the pipeline simultaneously:

| Source | Tokens |
|--------|--------|
| **hot-set.json** (signal_compactor output) | AVAX, AVNT, ADA, BSV, BERA, BRETT, FET, ENS, CHIP |
| **APPROVED DB** (get_approved_signals) | CAKE, LAYER, ATOM, DASH, FIL, LINEA, 0G, GRIFFAIN, ETH, APEX, ETHFI, MERL, COMP, ME, BLUR, AAVE, DYDX, 2Z, IP, NEAR, XMR, LINK, MON, SNX, SUSHI, EIGEN, TAO, GALA |
| **Intersection** | ENS (only one) |

Both lists have high-confidence signals (70-88%) but no live trades.

---

## Root Cause 1: signals_runner Background Fork — Hot-set Always 1 Cycle Stale

Pipeline order in `run_pipeline.py`:
```
1. signal_compactor.py  (SYNCHRONOUS — reads DB, writes hotset.json)
2. decider_run.py       (SYNCHRONOUS — reads hotset.json immediately)
3. signals_runner.py    (BACKGROUND via Popen + start_new_session=True)
```

signals_runner forks off signal scripts and returns immediately. signal_compactor runs in the same loop iteration — it reads signals_hermes_runtime.db BEFORE signals_runner has finished writing new signals. hotset.json always reflects the PREVIOUS cycle's signals.

**Evidence**: Every journalctl cycle shows compactor reporting approved=N before signals_runner lines appear.

---

## Root Cause 2: decider_run Silently Skips ~29 Tokens Per Cycle

Journal logs across cycles 18360-18367:
- compactor: `approved=10 | rejected=0` every cycle
- decider_run: `34 skipped, 0 entered, 0 delayed exec` per cycle
- BUT only 5 WR-blocked SKIPs logged: LAYER, NEAR, ENS, DASH, 2Z

29 tokens are being silently skipped before any gate logs them.

**Debug fix applied** (decider_run.py ~line 1527):
```python
log(f"[DECIDER-LOOP] #{i+1} {token} {direction} conf={confidence} hotset={'YES' if in_hotset else 'NO'} src={source[:60]}")
```

---

## Root Cause 3: PostgreSQL brain Connection Failing

`_get_direction_wr()` in decider_run.py uses `psycopg2.connect(**BRAIN_DB_DICT)` → exit code 1. Falls back to `(50.0, 0)`.

For LAYER/NEAR/ENS/DASH/2Z: real WR data (44%/33%) exists in PostgreSQL but connection fails → fallback `(50.0, 0)` is returned when real data should be. Still blocks because `50.0` doesn't satisfy `wr < 50`, but the real 44%/33% would also block. The failure masks whether connection-fix would change anything.

For new tokens (BERA, EIGEN, ADA, BSV etc.): no trade history → fallback `(50.0, 0)` → WR gate condition `wr < 50 AND count >= 3` fails (count=0), so they pass.

---

## Key Files

| File | Line | Relevance |
|------|------|-----------|
| signal_compactor.py | 518-552 | CONFLUENCE GATE: 2+ unique signal types required |
| signal_compactor.py | 850-862 | accel-300+ required for LONG entries |
| signal_compactor.py | 635 | regime call (uses `get_regime_5m`) |
| signal_compactor.py | 902-934 | Step 12 preserve previous hot-set merge |
| decider_run.py | 1514-1534 | DEBUG LOG added (2026-05-11) |
| decider_run.py | 1664-1668 | Surfing gate: survival_rounds < MIN_SURVIVAL_ROUNDS |
| decider_run.py | 1711 | Main regime filter (1m LR) |
| decider_run.py | 1798 | WR gate: `if wr < 50 and wr_count >= 3` |

---

## Still Unknown

1. Why only 5 of ~34 skipped tokens are logged per cycle
2. Whether `is_position_open()` or `_is_guardian_closing()` silently blocks hot-set tokens
3. Whether `speed=0%` block fires silently
4. Whether `min_exec_confidence` filter fires before logging

---

## Related

- `references/approved-hotset-divergence.md` — prior session analysis (partially superseded)
- `references/pipeline-timing-2026-05-06.md` — signals_runner background fork timing gap
- `references/signal-compactor-model-redesign.md` — signal_compactor architecture
- `references/short-signal-performance-2026-05-11.md` — PostgreSQL WR data stale from May 8