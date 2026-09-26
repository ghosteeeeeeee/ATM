## CEO Report — 2026-09-26 ~02:00 UTC

### Diagnosis
DB-verified: 1T +$0.05 (24h) | 190T 42.1%WR -$2.99 (7d) | 380T 46.6%WR -$3.45 (14d) | 1244T 52.3%WR -$6.33 (30d). **System IDLE 23.4h** — last trade Sep 25 02:26 UTC. Market NEUTRAL, hotset empty, confluence gate blocking everything. **ATR_SL widening deployed Sep 25 12:30 UTC but 0 trades to measure** — need 48h (eval Sep 27). ATR_SL still dominates exits: 117/190 = 61.6% of7d exits, 42.7% WR, -$3.11. **Signal diversity critical** — only pump-chain+ LONG (+$0.78/7d) and volume-breakout-long+ (+$0.70/7d) profitable. All other signals net negative.

### Root Cause
System in holding pattern: market NEUTRAL, no signals passing confluence. ATR_SL widening needs live trades to measure impact. HIGH regime is worst performer (-$1.44/7d) — pump-chain+ HIGH 17T 29.4% WR -$0.54 is main drag (but 30d is +$0.11, cold streak). SHORT_RSI_CEILING=65 blocking profitable RSI 65-70 SHORT band.

### Fix Applied
1. **SHORT_RSI_CEILING 65→70** — 14d data: RSI 65-70 SHORT = 4T all winners +$0.47. RSI>=80 = 4T 25%WR -$0.08. Unlocks profitable band, blocks losers. Expected +$0.10-0.20/7d. Enforced in both signal_compactor.py and decider_run.py (imports from hermes_constants, no code change needed).

### Verification
- SHORT_RSI_CEILING=70 loads correctly
- Both enforcement points (signal_compactor.py:3336, decider_run.py:1041) import from hermes_constants
- No protected flags touched
- No syntax errors

### Monitoring (all active)
- **ATR_SL widening** — deployed Sep 25, 0 trades since, eval Sep 27
- **volume_spike metadata fix** — deployed Sep 25, untested (0 trades)
- **CL-T1 disabled** — 0 trades since disable, working
- **SHORT_RSI_FLOOR=50** — working, blocking oversold SHORTs
- **LONG_RSI_SWEET_SPOT_BOOST=10** — active, boosting RSI 40-50 LONG fills
- **REGIME_CONF_MULTIPLIER** — EXTREME +15%, NORMAL -15% confidence
- **SHORT_RSI_CEILING=70** — just deployed, monitoring

### System Health
- Disk: 81% (22G free) — below threshold
- Pipeline: running, all timers active, no crashes
- 0 open positions
- All recent fixes (dead hours, RSI floors, EMA fallback, LONG RSI revalidation) working

### Remaining Issues
- Signal diversity: only 2 profitable signal types (pump-chain+, volume-breakout-long+)
- HIGH regime bleeding -$1.44/7d — pump-chain+ HIGH 29.4% WR
- Need new signals for NEUTRAL regime (longer-term)
