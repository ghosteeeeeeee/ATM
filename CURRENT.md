# Current State — brain_auditor #228 2026-11-06 05:00 UTC
**Last Updated: 2026-11-06 05:00 UTC**
**Updated by: brain_auditor #228. Prior: #227 2026-11-06 00:55 UTC (preserved in git history).**

## HEADLINE — The gate-shadow "15-30% capture gap" was a MEASUREMENT-FRAME BUG, not a recorder bug. Correct frame (dedup, not raw lines) = 1.00 overall / every gate n>=10 at 1.00 → disposition CLOSED threshold MET, capture caveats removed from 2 amplify proposals. Shipped `gate_shadow_health.py --per-gate/--selfcheck` so it can't recur.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **gate-shadow-capture-coverage-fix (CLOSED — MET)** | #225/#227 divided gate_shadow.db rows (10-min dedup, UNIQUE gate\|token\|direction\|bucket) by RAW log lines: raw 13,043 vs dedup 2,469/24h → db/raw 0.14–0.28 for every gate BY CONSTRUCTION, reproducing #227's "CONTINUUM 15% / RSI-FLOOR 18% / CONFLUENCE 20%" exactly (0.14/0.17/0.20). Correct frame = CEO D4b tool (same regex + dedup): **24h 1.00 (db 2471 / dedup 2478)**, per-gate **1.00** after one `--record` flush; pre-flush LONG-MIDBAND 0.86 = hourly-recorder lag. BTC-CRASH/VOL-FLOOR/RR "0% in db" = gates that never fired. Caveats on amplify-bbsqueeze-chop-exempt + amplify-vb-high-short-clonehunt REMOVED |
| **jup-yolo-regime-review (CLOSED early, NO CHANGE)** | 14d=30d n=100 net '-1.08'; HIGH 41T '-0.75' / NORMAL 37T '-0.39' / EXTREME 15T '-0.19' / FLAT 7T '+0.25' → no positive cell n>=15; HIGH-vs-rest **t=-0.57 n.s.**; gate to EXTREME/NORMAL keeps '-0.58'. Leak = R:R (armed 64T '+3.76' vs unarmed 36T '-4.84'), owned by stop-tighten 11-14 + xmirror-giveback 11-18 |
| **linreg-fade-fill-funnel (NEW EVAL, due 11-13)** | 78 signals/first 9h, ALL EXPIRED, 0 APPROVED, 0 PG trades all-time. 27 confluence blocks ALL predate the 11-05 bypass (0 on 11-06 = bypass works); path proven once: CONFLUENCE-GATE-PASS → HOTSET-FINAL-BYPASS → PENDING-APPROVE-BYPASS → DECIDER-LOOP AVAX → `EXEC: AVAX SHORT @ $8.149 [linreg-fade-]` → **VOL-GATE-v2 storm (ATR 1.6874% > 1.5%)**. Deaths: 43 compaction_stale_10min (never top-10) + 4 RSI-floor + 3 rr-engine + 1 oversold-knife. Bar: **>=5 live fills by 11-13 AND armed-rate >=50%**, else escalate ONE lever, default NO CHANGE |
| **Harvest pre-read (deadline 11-07)** | **3/4 FAIL**: rolling-50 jup **44%** (bar<35) · HML 7d **37T '-4.73'** (bar<15) · daily net 11-02 '-1.44'/11-03 '-0.29'/11-04 '-0.14'/11-05 '+0.26' = 72h-green FAIL · PASS = LONG-in-SHORT_BIAS 48h **0/18**. Package: bb+warrior last-100 share **15%** (target 25%) FAIL → CEO owns revert call at deadline |
| **Autopsy 48h (MANDATE)** | n=8 = 3 never-adverse / 5 recovered / **0 NEVER** → WRONG-SIDE REFUTED **84th** (#61 p=0.116, #84 t=-0.04) |
| **AMPLIFY weekly** | This week's proposal = amplify-bbsqueeze-chop-exempt (#227; caveat now removed). #228 screen: 6 n>=10 winner cells ALL in-flight; n>=5 early cells sign-flip at 14d (r2v2-long3) or already KILLED (volume-breakout-long+, arm 6.3%) = shipped work. Flip-KPI 0 this week — only shadow→live candidate is linreg-fade, bar registered above |
| **#227/#226/#225 verify** | fade-KEEP / momentum-PASS / candle-FIXED **PASS** (XMR 5m 5026 + LIT 5m 5026 present) · 4h coverage **PASS** · **jup_liq amount=0 STILL PENDING live fire** (compiles; 1,475 log lines, no confirmed non-zero notional) |
| **FLOW RECOVERY shadows (parallel session, 8a229b1c)** | Read-only verify: compile OK on decider_run/signal_compactor/hermes_constants; `[BTC-CHOP-STANDALONE-SHADOW]` 7 lines, `[SETUP-RECALL-SHADOW]` 0; deny paths unchanged by polarity. NOT my change |

### 2. NUMBERS (fresh PG)
- 24h **5T 60.0% '+0.13' GREEN** (jup SHORT 4T '+0.46' carrier) | 7d **257T 54.1% '-2.02'** | 14d 404T 54.7% '-2.23' | 30d 777T 45.6% '-6.45' | **0 open**
- 7d by regime: HIGH 76T 55.3% '-0.91' · EXTREME 57T 49.1% '-0.90' · NORMAL 109T 54.1% '-0.36' · FLAT 16T 68.8% '+0.18'
- Contrarian join 04:30Z: overall flip **43.8% n=1362** | pc- 64.6% LIVE keep | rider 36.7% do-NOT
- Floor join 04:32Z: floor_only 49.3% vs always_admit 43.9%, **p=0.155** → COLLECT to 11-15
- Chop mandate 7d: armed **136T 91.2% '+8.38'** vs unarmed **121T 12.4% '-10.40'** | chop-exit family 85T **'-10.22'**

### 3. SHADOW (3/6 usable + gate_capture now answerable)
- contrarian + floor joins re-ran unconditionally (mandate); shadow_trader 67,850 signals
- Exit A/B: pm_trail **+10,265** vs hard_max **-11,564** / cut_loser -2,175 / rr_engine -4,481 = trail-or-nothing
- oscillator FROZEN / wyckoff RETIRED / rr ORPHANED

### 4. SIGNAL QUALITY — 0 new targets + one pre-registered dead-end
- No signal meets n>=20 + WR<50 + net<0 this run
- vb- SHORT (57T 59.6% '-0.97') and jup LONG (100T 61.0% '-1.08') are WR-positive/negative-net = **R:R class**
- **NEGATIVE RESULT (pre-registered):** 6 entry features × 3 signals, every |t| < 1.7 (RSI -1.62, BB -1.63, gap -0.63, volume -0.07, momentum 0.26, staleness -0.20) → **no entry filter can be justified** for the unarmed half. Do not re-propose RSI/gap/BB filters for jup/vb-/pc+.
- Arm-rate 14d n>=15: jup LONG 64.0% · vb- SHORT 66.7% · pc+ LONG 54.8% · bb-squeeze+ 47.5% · pc- LONG **7.4%** (net '+0.10' — arms almost never, still green)

### 5. READINESS (05:00)
**0 open trades.** Regime: 15m SHORT_BIAS / 4h SHORT_BIAS / continuum BELOW / vol LOW / zscore STRONG_NEG / trend_quality STRONG_DOWN / 0 steers / portfolio good. Both sides agree SHORT_BIAS — no counter-trend size; trail-family first; size 1.0x (size-reduce file absent). Session lock ABSENT; hermes_constants.py diff **EMPTY**; CEO_PROTECTED untouched; 0 Tracebacks in pipeline.log.

**Queue:** 11-07 harvest full read + fill-cap brake + volmom-volbreak → 11-09 zombie-purge → 11-10 four bars + bear-single-source → 11-11 watch-contrarian-live → 11-13 **linreg-fade fill bar** + bbsqueeze-chop-exempt + vb- clonehunt (caveat removed) + pc+ kill → 11-14 stop-tighten → 11-15 floor/wyckoff → 11-19 ema300/jup-short-high.
**CEO:** harvest early-fail 3/4 (deadline 11-07) · winner-cell-mult-150 sign-off · stop-tighten-probe-080 label · NET-KPI.
