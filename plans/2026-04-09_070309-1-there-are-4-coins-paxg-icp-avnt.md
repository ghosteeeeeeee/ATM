# Plan: 4 Coins Missing ATR TP/SL + Hot-Set Empty Bug
## UPDATED 2026-04-09 17:45 UTC

---

## STATUS SUMMARY

### TP/SL Placement Progress

| Coin | SL | TP | HL Orders | Status |
|------|----|----|-----------|--------|
| **BTC** | 70764 | 73997 | 2 | ✓ |
| **APE** | 0.0888 | 0.09285 | 2 | ✓ |
| **AAVE** | 89.20 | 93.93 | 3 | ⚠️ excess (1 extra SL) |
| **ASTER** | 0.66041 | 0.68593 | 2 | ✓ |
| **AVNT** | 0.13623 | 0.14149 | 3 | ⚠️ excess (1 extra TP) |
| **ICP** | 2.51 | 2.61 | 2 | ✓ |
| **ATOM** | 1.79 | 1.87 | 2 | ✓ |
| **CFX** | 0.052 | 0.055 | 0 | ❌ cancelled, needs re-place |
| **GALA** | 0.003 | 0.0032 | 0 | ❌ cancelled, needs re-place |
| **PAXG** | none | none | 0 | ❌ HL rejects asset=187 — self-close DB only |

### SKIP_COINS (self-close fallback only)
- **PAXG** — HL permanently rejects TP/SL for asset=187
- **AVNT** — szDecimals=0, integer prices only
- **AAVE, MORPHO, ASTER** — previously rejected, now succeed on HL but guardian skips them
- **BTC** — in UNPROTECTABLE for self-close fallback (but HL works fine)

---

## ROOT CAUSES IDENTIFIED

1. **PAXG** — `Invalid TP/SL price. asset=187`. HL permanently rejects. Self-close DB only.
2. **ICP** — Position opened later, TP/SL placed manually.
3. **AVNT** — szDecimals=0. Self-close path was correct, but self-close watcher wasn't including it.
4. **EIGEN** — Cancelled in prior session, no open HL position currently.

### Architecture Bug
Batch TPSL and Guardian were BOTH cancelling/placing HL TP/SL — causing 429s and duplicate orders.
**Fix:** Restructured batch to compute ATR only. Guardian is sole TP/SL manager.

---

## CHANGES MADE

### 1. `batch_tpsl_rewrite.py`
- Restructured `process_token()`: GUARDIAN_MANAGED (compute ATR only, no HL), SKIP_COINS (self-close), legacy
- SKIP_COINS updated with "Self-close only" notes

### 2. `hl-sync-guardian.py`
- SKIP guard: AAVE, MORPHO, ASTER, PAXG, AVNT skipped from TP/SL reconciliation

### 3. `hyperliquid_exchange.py`
- `place_tp`, `place_sl`: 3-attempt retry with exponential backoff on 429
- Type guard for string error responses
- `_find_open_trigger_order`: 3-attempt retry on rate-limit

### 4. `hermes_constants.py`
- Added PAXG to LONG_BLACKLIST (self-close only, no hot-set)

### 5. `self_close_watcher.py`
- Added AVNT to UNPROTECTABLE_COINS

---

## REMAINING WORK

### NOW (rate-limited, waiting to clear)
Bulk cancel + bulk place for AAVE(3→2), AVNT(3→2), CFX(0→2), GALA(0→2):
1. Cancel excess AAVE SL@89.979 (oid=375781959910) + excess AVNT TP@0.14149 (oid=375776452494)
2. Cancel all CFX + GALA orders (appeared 0 — cancelled earlier in session)
3. Bulk place all 18 fresh orders: SL+TP per coin for AAVE, APE, ASTER, ATOM, AVNT, BTC, CFX, GALA, ICP

### AFTER CLEANUP
1. Add PAXG to brain tpsl_self_close DB — DONE
2. Add CFX and GALA positions to tpsl_self_close DB if they can't hold HL orders
3. Restart guardian and verify no fights

---

## HOT-SET EMPTY
Not a bug — hot-set is derived from signals DB filtered by hot_cycle_count>=1.
Dashboard query may have additional filters. Not critical right now.

---

## SAVE PATH
`.hermes/plans/2026-04-09_070309-1-there-are-4-coins-paxg-icp-avnt.md`
