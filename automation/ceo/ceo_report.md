## CEO Report — 2026-10-12

### Diagnosis
Regime-recalibration backtest claimed a profitable SHORT hump at 2.5–4.0% ATR (t=1.92–2.10, LOO-robust, "+$15.71 suppressed"). I re-derived independently (same basis: 5,140 trades, ATR%(14) from 1h candles pre-open — n matches exactly). **The hump does not reproduce at claimed significance.** System: 24h 26T +$1.00 26.9% WR; 7d 145T −$0.10 37.9% (flipped negative).

### Root Cause
Two-part:
1. **Evidence gap (THE PATTERN).** My repro: SHORT 2.5–4.0 n=209 +$1.68 WR 48.8% **t=0.95** (doc: t=1.92). Sub-bin 2.5–3.0 t=1.72 (doc: 2.09). LOO drops **FET** (not XMR) → t=0.49 (doc: 2.10). Doc's LOO n=244 > my full-band n=209 → band membership differs = unreproducible derivation. "+$15.71" is winners-only sum; true unblock counterfactual is **net ≈ +$2** before fees on 209 extra trades.
2. **What DID reproduce:** LONG FLAT edge t=2.65 ✓; LONG decays with ATR ✓; MAXXED (≥4.0) bad BOTH dirs (LONG 44.4% −$1.48; SHORT 24.0% −$1.16) ✓ direction-consistent.

### Decision
1. **MAXXED tier: APPROVED IN PRINCIPLE, shadow-only first.** ≥4.0% is genuinely toxic both directions. Hard constraint: every existing `regime=='EXTREME'` comparison must treat MAXXED as EXTREME-equivalent (naive relabel would accidentally UNBLOCK EXTREME restrictions — blast-radius audit required before any live wiring).
2. **EXTREME-hi SHORT-allow: REJECTED pending reproduction.** The entire economic case (+$15.71) rests on a hump that fails independent verification. No live change to SHORT treatment in 1.5–4.0%.
3. **LONG-restrict EXTREME-hi: NO** — −$2.46/173T t=−1.21, not significant; blanket blocks need more.
4. **Full ladder re-cut: NO** — correctly rejected; per-signal overrides rest on current buckets.

### Verification (pre-code-change, mandatory)
- **own-conclusions: REQUIRED and ordered** — reproduce the SHORT hump with a checked-in, fully scripted derivation; resolve the n=244-vs-209 band mismatch. Pass bar: |t|≥2.0, LOO-robust, net counterfactual (incl. fee drag) > +$5/30d.
- Any future implementation: 48h shadow logging of would-be decisions before enforcement; protected flags untouched; CONFLUENCE_REQUIRED stays True.

### Next
DELEGATE signal_analyst: MAXXED shadow label (observability only, EXTREME-equivalent mapping) + reproduction script. DELEGATE own-conclusions: fresh-eyes repro of the 2.5–3.0 SHORT cell. 7d PnL now −$0.10 — protecting ≥$0 checkpoint.

---

## CEO Acknowledgment — 2026-10-12 02:22 UTC — MAXXED tier DEPLOYED (T-directed)

### Acknowledged
T-directed MAXXED tier is live. Accept the design and the two-pass verification. Commits 2b6c85ca + 1bf84683 pushed.

### Constraint satisfied (structurally)
My hard constraint — naive `regime='MAXXED'` relabel would silently unblock all `== 'EXTREME'` restrictions — is avoided by design, not by audit. `classify_volatility()` unchanged (still returns EXTREME at ATR%>=4.0); MAXXED is an additive block via `is_maxxed()` on `MAXXED_ATR_PCT_THRESH=4.0`. Zero `== 'MAXXED'` comparisons anywhere. MAXXED can only block more, never less. No relabel risk exists.

### Shipped
- `hermes_constants.py`: MAXXED_ATR_PCT_THRESH=4.0, MAXXED_BLOCK_ENABLED=True, MAXXED_REGIME_LOG=True. New constants only; line-2 protection honored.
- `volatility_gate_v2.py`: `is_maxxed()`.
- `signal_compactor.py`: approval-time block, both directions, logs [MAXXED-BLOCK].
- `decider_run.py`: exec-time backstop in `execute_trade()` — BUG-052-safe (return-before-claim).

### Verified
- Static pass: 88 insertions 0 deletions; classify_volatility invariant holds v1+v2; imports complete; conn closed in finally; ATR div-zero guarded.
- Live pass: pipeline restarted 02:09:16 UTC, cycles rc=0, zero tracebacks, 3 tokens MAXXED (S 6.78%, W 5.51%, STRK 5.43%), dry-run of exec backstop fired correctly, GRASS SHORT (ATR 3.82) correctly not blocked. Kill-switch sanity clean.
- Zero [MAXXED-BLOCK] firings since restart is expected — those tokens produced no hotset signals in window. Block is armed and provably functional.

### Decisions on informational findings
1. Fail-open on <15 closed 1h candles (fresh explosive listings): **accept as-is.** Fail-safe by design; no [MAXXED-UNKNOWN] shadow log for now — add if fresh-listing leakage becomes visible.
2. Inlined ATR-14 copy in compactor (drift risk vs `get_atr_pct()`): **defer.** Matches today; cleanup when next touching compactor. Not worth a standalone diff.

### Extensibility
Higher tier later (e.g. APOCALYPSE) = same additive pattern: one `is_*` helper + one additive block; inherits all MAXXED/EXTREME blocks automatically. Threshold is a named constant. T's requirement met.

### No action
Position_manager D3 trail-floor removal + stray HML_TRAIL_MIN_GAP_PCT comment-only edit (value unchanged 0.20) — housekeeping acknowledged, no further action. SHORT EXTREME-hi unblock remains REJECTED pending own-conclusions repro; MAXXED deployment does not change that.
