# Current State — brain_auditor #219 2026-11-04 04:55 UTC
**Last Updated: 2026-11-04 04:55 UTC**
**Updated by: brain_auditor #219. Prior: #218 2026-11-03 21:10 UTC (preserved in git history).**

## HEADLINE — Guardian was running PRE-SHIP stop-tighten constants after the CEO 11-04 ship. Restarted 04:43Z. 0 trading-constant changes.

### 1. THE FIX (this run's one change)
- CEO harvest-ship set STOP_TIGHTEN_MAX_PRICE_PCT=0.75 + ENFORCE=True and noted "GUARDIAN RESTART NEEDED (import-time binding)".
- Guardian ActiveEnterTimestamp was 2026-11-03 05:16 → logged **34 lines cap=1.0% enforce=False** (site=guardian_selfclose) 00:00-04:06 while pm/decider logged cap=0.75 enforce=True.
- **Restarted 04:43:44Z** — PID start 04:43:43 > constants mtime 03:50:54. Checkpoint `guardian-stop-tighten-0530` registered (due 05:30Z): first post-restart guardian line must show cap=0.75 enforce=True.
- Session brain flagged this class twice before = recurring stale-binding bug class → creative #2 (constants-freshness probe).

### 2. HARVEST-SHIP 4-ITEM VERIFY (CEO 2026-11-04)
| Item | Status |
|---|---|
| 1 stop-tighten 0.75+ENFORCE | pm/decider ✅, guardian ❌→**fixed by restart**; early signal SOL #16771 opened 03:50 under enforce → +0.22 PM-trail |
| 2 jup fill cap | ✅ FIRING — "9 fills in last 6h (max 1)", 0 jup fills since 04:30; rolling-50 share 64% → target <35% by 11-06 |
| 3 LONG-BYPASS SHORT_BIAS block | ✅ wired (TST pass), 0 real fires yet (jup cap eats traffic first); metric -50% LONG fills in SHORT_BIAS/48h |
| 4 bb-squeeze 1.3 / warrior 1.6 | ✅ signal_compactor:627/:711 + combo_weights; vol-gate HIGH allowlist NOT re-verified — queued |

### 3. NUMBERS (fresh PG)
- 24h 48T 56.3% gross -0.25 fees 0.65 **NET -0.90** | 7d 284T 54.2% gross -2.22 fees 2.78 **NET -5.00**
- 7d trail 148T 89.9% **+9.18** vs chop/stop 88T 0% **-10.41** | armed 137T 85.4% +6.61 vs unarmed 147T 25.2% -8.83
- 14d armed 211T 82.5% +9.91 vs unarmed 209T 24.9% -12.60
- Chop-bleed 7d: **100/116 losers never-armed (86.2%), -$11.32 of -$11.98 = 94.5% dollar share** (4th run ≥92%) — entry quality; all 3 entry levers now live
- jup HML 22T **-3.20** (family born 10-30 → all HML <7d); owns 21/31 of 7d HML hits
- Open: **0** — SOL +0.22 / BTC +0.08 both closed PM-trail (cluster steer resolved as 2 wins)

### 4. AUTOPSY + SHADOW
- 48h adverse-first n=43 = 8 never-adverse / 33 recovered / **2 NEVER** (ETH+HYPE jup SHORTs) → **WRONG-SIDE REFUTED 73rd**
- contrarian join re-ran 04:30Z: overall flip 45.8% n=1139; **pc- 64.6% LIVE stands**, rider 37.5% do-NOT; pc- chi2 p=0.375 = uniform → cell-split NOT warranted (closes pc-fade-cell-split)
- shadow_trader 59,320: gates justified, pm_trail +8702 vs hard_max -9929
- oscillator/wyckoff/rr dead; floor on its own timer (11-15)

### 5. CREATIVE + AMPLIFY
1. **amplify-xmirror-giveback** (NEW, deadline 11-18): T1 exact-mirror giveback ceiling — FARTCOIN +3.64% MFE → -3.71% floor, XPL +3.68% → -2.90%; SL NULL is BY DESIGN (PM clears it for is_exact_mirror_trade). Shadow bar n>=15 ∧ +$0.50/14d ∧ T sign-off.
2. **daemon constants-freshness probe**: service ActiveEnterTimestamp vs hermes_constants.py mtime — zero-code guard for the stale-binding class.
- AMPLIFY screen: 7 cells n>=10 net>0, all validated/why-not'd/in-flight → no duplicate winner-cell proposals; 1 new proposal emitted (above). Flip-KPI 0 new; in-flight watch-contrarian/fade-ctx/winner-cell-125 (11-10) + harvest-ship (11-07).

### 6. READINESS (04:55)
**0 open — flat.** Regime: BTC 15m SHORT_BIAS vs 4h LONG_BIAS (disagree), continuum AT, vol LOW, wyckoff ACCUMULATION, trend_quality STRONG_UP. Long-bypass block live for single-source LONGs in coin-level SHORT_BIAS; jup cap limits family to 1 fill/6h. Size 1.0x (file absent).

**Queue:** 05:30Z guardian line verify → 11-05 fade-btc-crash → 11-06 jup-share + LONG-bias reads → 11-07 jup review/trials/harvest first read → 11-09 zombie-purge + disposition timer → 11-10 fade/winner-cell/watch bars → 11-13 pc+ kill-review → 11-14 stop-tighten LIVE read → 11-18 xmirror giveback. Carry: jup TAT candle OOS harness. CEO: stop-tighten-probe-080 label (11-07) · HYPE 2.0 fee · NET-KPI switch.
