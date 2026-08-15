## CEO Report — 2026-08-15 (latest run)

### Diagnosis
Signal starvation: Aug 15 only 19T so far (85% collapse from 100T Aug12). 24h 56T -$0.46 (48.2% WR — RED, 6th consecutive red). 5 open $0 flat. R:R inverted 0.49:1 (avg win 0.38% vs avg loss -0.78%). SL hit 35.8% (123T/48h). Top performers: r2-trend-long2 8T 100% WR, ct-hot+ 3T 100%, mover+ 1T 100%. Worst: range_finder+ 9T -$0.14 33.3% (disabled), range_breakout_short 1T -$0.10 0%.

### Root Cause
Three filters stacked in NEUTRAL regime (103/105 tokens): (1) Confluence gate blocks single-source signals, (2) VEL-FILTER blocks SHORT when price rising, (3) NEUTRAL regime 0.50x scoring penalty. SIGNAL_FILTER_SPEED_MIN lowered 45→30 today (needs 24h to show impact). range_finder (core mean-reversion signal) blocked by confluence gate — only fires in combos. Eval windows active (PM_TRAIL 0.60%, ATR_TP_K_MULT 2.5, TRAILING_ACTIVATION_PCT 0.60%) — close ~Aug 17. Cannot touch these params.

### Fix Applied
ADDED 'range_finder' to STANDALONE_BYPASS_SIGNALS. range_finder- and range_finder_short can now bypass confluence gate. Expected: daily trades ↑ from 19 toward 30-40+. range_finder+ stays disabled (33.3% WR). Combos (bb_bounce+,range_finder+ 52.4% WR) unaffected — validate_source() exact-match blocks standalone only.

### Verification
Monitor: daily trades (must ↑ within 24h), range_finder standalone WR (must >45% to keep enabled), eval close ~Aug 17, R:R ratio (should ↑ from 0.49:1 after eval windows close). NO other changes — eval windows active, SIGNAL_FILTER_SPEED_MIN needs time.
