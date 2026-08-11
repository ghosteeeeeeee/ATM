## CEO Report — 2026-08-11 Signal Degradation Analysis

### Diagnosis
Verified DB: 24h 33T -$0.53, 33.3% WR — RED. 7d 363T +$0.55, 52.1% WR — positive. Zero open positions. System functional but signal-starved — trades happening (33T/24h) but hotset empty, no new entries queuing.

### Root Cause (3 layers)
1. **SL misfire (resolved):** Aug 10 tightened SL to 0.5% — SL hit rate jumped to 64.7%. Reverted to 1.2% Aug 11. `bb_bounce+,hzscore+` dropped from 80% WR → 25% WR at 0.5% SL. Same signal, same market — only SL changed.

2. **Volatility gate over-blocking (active):** REGIME_SIGNALS whitelist too narrow. Pipeline log shows `trend_momentum_near_sma+ not suited for NORMAL` repeated every minute — this signal isn't in the NORMAL whitelist. Tokens like W (ATR 0.69%, NORMAL regime) are generating signals that get rejected by the gate. FLAT regime only allows `bb_bounce`/`bb_bounce+` — any combo signal not matching exactly gets blocked.

3. **COSIG-GATE poison block (active):** `bb_bounce+,hzscore+` LONG poison-blocked at line 613-614 of signal_compactor.py based on 23.1% WR — but that WR was from the 0.5% SL era. The signal was 80% WR 48h earlier under proper 1.2% SL params. Damaged-period data is poisoning the decision.

### Current Regime Distribution
- FLAT: 45 tokens (AAVE, ADA, ASTER, BCH, etc.)
- NORMAL: 63 tokens (0G, ALGO, AVAX, BNB, etc.)
- HIGH: 28 tokens (AVNT, AXS, BERA, etc.)
- EXTREME: 30 tokens (ACE, APE, AR, BIO, etc.)

### Fix Required
**Unfreeze the system** by addressing 2 code blocks:

1. **Expand REGIME_SIGNALS** in `volatility_gate.py` — add `trend_momentum_near_sma` to NORMAL, add more combo signals to FLAT
2. **Remove COSIG-GATE poison block** on `bb_bounce+,hzscore+` LONG (lines 613-616 of signal_compactor.py) — data is from wrong SL era

### What NOT to change
- SL params (1.2% min, 2.5% max) — correct, leave alone
- Trailing distance (0.60%) — correct, leave alone
- `bb_bounce+,range_finder+` — 60.4% WR all-time, 53T +$0.82 — star, leave alone
- SHORT trend filter (15m) — working, SHORT profitable 7d

### 24-48h Monitoring Plan
| Metric | Current | Target | Action if missed |
|--------|---------|--------|-----------------|
| Volatility gate acceptance | ~0% | >50% | Expand whitelist further |
| bb_bounce+,hzscore+ WR | 18.2% (24h) | >50% | COSIG-GATE removal should fix |
| SL hit rate | unknown (frozen) | <30% | Already reverted, monitoring |
| Open positions | 0 | 1-3 | System should self-correct after gate fix |
| Daily trades | 33 | 30-60 | Gate expansion should restore volume |

### Decision
**Two code changes needed to unfreeze the system.** Neither is a param change — both are gate logic fixes based on stale data. The signal quality was fine at 1.2% SL; the gates are what's blocking recovery.
