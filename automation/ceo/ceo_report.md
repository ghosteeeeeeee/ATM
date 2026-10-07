# CEO Report — RR Engine Bug Hunt #2 Decisions

**Date:** 2026-10-07
**Context (DB-verified):** 24h **12T 3W +$0.37 WR 16.7%** | 7d **212T +$0.62 53.8%** (LONG +$1.30, SHORT −$0.68) | hard_max_loss residual | system thin on volume. Logs: **6,688 SHADOW BLOCK** lines; multiplier already live (RR HARD BLOCK mult=0.0 firing). BUG-3 cache fix confirmed in code. BUG-4/10 open.

---

## Decisions

### D1 — Shadow Mode Flip (BUG-2) → **B: KEEP SHADOW=True. Do not enforce yet.**
**Rationale:** Multiplier already hard-blocks rr<0.70 + grade F; flipping regime mins (FLAT 2.5 / NORMAL 2.0) would starve an already-thin 12T/24h flow on thresholds that contradict the live curve, while BUG-4/10 still distort scores.
**Risks:** Shadow-block volume may hide real edge (7d RR<1 = 23%WR vs RR≥1 = 61%). Monitor: shadow-block cohorts vs 7d outcomes.
**Path (delegate self_learner + signal_analyst):** (1) make `rr_confidence_multiplier` consult `_get_rr_min(regime)`; (2) backtest FORCE on shadow logs; (3) re-eval flip at n≥100 shadow blocks. Constants stay T-approved — no flag flip without sign-off.

### D2 — Score Floor Exemption (BUG-12) → **A: EXEMPT rr_mult from the 0.3 floor.**
**Rationale:** Floor actively washes RR penalties in production (`[SCORE-FLOOR] product 0.1643 floored to 0.3` on live BTC SHORT); hard blocks already exempt — soft RR penalties must bite too.
**Implementation:** Remove rr_mult from floored product; apply after: `final = score * rr_mult * max(other_product, 0.3)`.
**Risks:** Deeper score cuts when RR+noise stack → fewer signals. Monitor: trade volume, SCORE-FLOOR events, winners blocked at rr_mult=0.70.

### D3 — TRAIL_SL Minimum Gap (BUG-11) → **A: ADD ATR-based minimum gap.**
**Rationale:** Rule 1 break path already has `RR_EXIT_MIN_BREAK_DIST=0.5%`; trail path lacks it — support 0.1% below price = market stop, killed by wiggle. Production-wired via `position_manager.py:2997`.
**Implementation:** `min_gap = max(RR_EXIT_MIN_BREAK_DIST, atr_pct * RR_EXIT_TRAIL_MIN_ATR_MULT / 100)` in trail loops; new constant near `RR_EXIT_TRAIL_BUFFER`.
**Risks:** Less responsive trail → profits give back more. Monitor: trail exit frequency, avg trail distance, trail-family WR (currently the only real edge: +$9.47/7d).

### D4 — Open Skies Points (BUG-10) → **B: KEEP full 25 points.**
**Rationale:** Open skies = room to run = structurally good for trend trades; BUG-3 price-bucketing already cut the main garbage-map risk. Reducing to 15 treats genuine breakouts like "far target" (15). Fix BUG-4 distance normalization if inflation proves real — don't double-penalize.
**Risks:** Score inflation on incomplete S/R → A/B grades on garbage. Monitor: open-skies trades vs sweet-spot WR at n≥20; if gap >10% WR, revisit (conditional 25/15 by map depth).

---

### Verification
- No trading-path constants changed this run. Protected flags intact. Session lock clear.
- D2/D3 are code fixes — delegate bug_hunter after T acknowledges these decisions.
- Goals: RR engine enforcement consistency by Oct 11 | trail premature-stop share <20% by Oct 14 | open-skies cohort n≥20 eval Oct 14.

Artifacts: brain/specs/rr_engine_bug_hunt_2.md, this report, automation/ceo/ceo_kanban.md. — CEO
