## CEO Report — 2026-10-12

### Chase Block vs Late Entry Decision

**DECISION: Option B (refined) — quality-tiered chase exemption. NOT a flat threshold raise, NOT removal.**

**Root-cause correction:** The task's framing is wrong on two counts:
1. **gap_at_entry is NOT latency.** It's price-vs-EMA300 extension (decider_run.py:4724). Staleness data proves the filter stack is fast: AIXBT/INJ/USELESS executed 1-2min after signal. The "filter stack latency" diagnosis is incorrect.
2. **The AIXBT/INJ/USELESS losers were NOT chase-blocked.** Their gaps were 0.01%, 0.28%, 1.22% — all below the 2.0% threshold. They entered early in BTC chop with no momentum. Different failure mode entirely. USELESS was correctly blocked LATER (16:00, gap 4.74%) when it was extended.

**Verified evidence (PG self-query):**
- Historical gap>2% executed LONGs (14d, pre-tightening): 8T, 25% WR, -$1.10. **All conf 71-102.**
- GRASS Oct 12 00:36-00:43: conf=193, setup WR=75% n=8, passed CTX-GATE/VOL-GATE/sentiment/hotset. Blocked at gap 4.66→6.77% (bull override active at 3.0%). Token continued up.
- Recent chase-blocks: CFX conf 129, USELESS conf 88, ICP conf 48-121 — **none** would pass a conf≥150 gate.

**Why not the other options:**
- **A (raise to 5-8%):** Would also admit all 8 historical losers (conf 71-102, 25%WR). Blunt instrument.
- **C (speed up stack):** Staleness already 1-2min. Wrong diagnosis.
- **D (momentum confirmation):** Another filter, more latency. The conf+setup gate IS quality confirmation.
- **E (scale position):** Execution doesn't support it; exemption achieves the goal simpler.

**Fix applied:** `CHASE_EXEMPT_MIN_CONF=150`, `CHASE_EXEMPT_MIN_SETUP_N=8`, `CHASE_EXEMPT_MIN_SETUP_WR=60`, `CHASE_EXEMPT_GAP_MAX=8.0` (hermes_constants.py:865-871). Exemption in decider_run.py:4786-4802 — only widens the GAP branch; z-score block intact. Historical losers all rejected by conf<150 gate. Only GRASS-class signals (conf≥150 + proven setup) qualify.

**Honest limitation:** n=1 GRASS winner. The conf separation (losers 71-102 vs GRASS 193) is theoretically clean and the gate is narrow, but this is not statistically significant alone. **Revert trigger: exempt cohort n≥5 with WR<40% or PnL<-$1 over 14d.** Self-check 9/9 PASS.

### Diagnosis
7d PnL +$0.41, WR 41.4%. hard_max_loss 46T 0%WR -$5.60 remains #1 bleed (entry-side, separate issue). Chase filter was blocking the highest-quality signal of the day (GRASS conf 193) while admitting low-quality near-EMA entries that lost in chop.

### Root Cause
Flat chase threshold treats conf-48 and conf-193 identically. High-confidence momentum continuation (the biggest pumps, by definition the most extended) gets the same block as low-confidence late chases.

### Fix Applied
Quality-tiered exemption: conf≥150 + setup WR≥60% + n≥8 → gap limit 8.0%. Base threshold 2.0% unchanged for everyone else. Z-score block unchanged.

### Verification
py_compile OK both files. Self-check 9/9 PASS (scripts/test_chase_exempt.py). Historical losers all rejected by new gate (conf 71-102 < 150). Protected flags INTACT. Next pipeline cycle loads fresh — no restart.
