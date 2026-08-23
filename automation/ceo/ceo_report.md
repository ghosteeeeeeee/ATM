## CEO Report — 2026-08-23 ~13:30 UTC (241st run)

### Diagnosis
System BREAK-EVEN, ct-hot+ RE-ENABLED BY T (RESEARCH_FLAGS). Verified DB: 24h 37T -$0.27, 40.5% WR. 7d: 229T -$1.33, 51.5% WR. **ct-hot+ DOMINANT LOSER** — 47T/7d -$3.47, 34.0% WR (RESEARCH_FLAGS, CEO cannot disable). Without ct-hot+: 7d +$2.08, 56.2% WR (system profitable). hl_copy_trader 58T/7d +$2.15, 53.4% WR (ONLY performer). PM_TRAIL 76T/7d +$3.43, 90.8% WR (carrying). **SHORT 7d: 26T -$1.40, 26.9% WR (ALL losing).** ATR_SL 36T/48h -$6.51 (dominant loss). 5 open: all ct-hot+ LONG. Disk: 83%.

### Root Cause
1. **ct-hot+ RE-ENABLED BY T** — CEO killed Aug 22, T re-enabled same day (RESEARCH_FLAGS). CEO cannot touch. Trades age out Aug 24-25.
2. **SHORT side has no edge** — hzscore- standalone bypass fires in SHORT_BIAS regime, but SHORT signals 26T/7d 26.9% WR all losing. SHORT-NEUTRAL block working correctly (verified: all Aug 23 SHORT trades opened in SHORT_BIAS regime, none in NEUTRAL).
3. **hzscore- standalone bypass** — hzscore- is in STANDALONE_BYPASS_SIGNALS, bypasses confluence gate. Fires in SHORT_BIAS. 9T/7d -$0.20 55.6% WR — marginal loser.

### Fix Applied
NO CHANGES — ct-hot+ in RESEARCH_FLAGS, cannot disable. hzscore- re-enabled by T (signal starvation fix), cannot disable without T approval. SHORT-NEUTRAL block verified working correctly.

### Verification
- SHORT-NEUTRAL block: VERIFIED — all Aug 23 SHORT trades in SHORT_BIAS regime, 0 in NEUTRAL
- MIN_PRE_MOVE 0.3: r2-trend-long3 23T/7d +$0.06, 52.2% WR (break-even, eval EXTENDED to Aug 25)
- PM_TRAIL: 90.8% WR (holding >80% target)
- ct-hot+ trades age out: Aug 24-25 (48h)

### Next Actions
1. **Recommend T disable ct-hot+** — 47T/7d -$3.47, 34.0% WR. DOMINANT LOSER. CEO cannot touch RESEARCH_FLAGS.
2. **Monitor MIN_PRE_MOVE 0.3** — break-even, eval EXTENDED to Aug 25
3. **Monitor PM_TRAIL WR** — must hold >80%, currently 90.8%
4. **Monitor SHORT-NEUTRAL block** — verified working, monitor SHORT PnL improvement
5. **Monitor disk** — 83%, trigger at 85%
