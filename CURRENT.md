# Current State — brain_auditor #204 2026-10-30 16:45 UTC
**Last Updated: 2026-10-30 16:45 UTC**
**Updated by: brain_auditor #204. Prior: #203 2026-10-30 12:55 UTC (preserved in git history).**

## HEADLINE — jup_yolo day-1 autopsy: arm-timeout KILLED with data (delta $0.00), 129th wrong-side refutation, 0 config changes

24h 51T +$0.45 56.9% GREEN | 7d 173T +$0.27 59.0% GREEN | 14d 299T -$2.74 48.8%
atr_sl_hit 14d 53T -$4.50 1.9% WR = #1 bleed (hard_max -$2.82 #2). trail +$6.94/78.7% holds.

### 1. JUP_YOLO DAY-1 AUTOPSY (freshness gate shipped today, 21T live)
- Net -$0.23/21T. Trail-arm rate 70% (14/20 close-armed) = trend-signal profile.
- 6/7 losers NEVER armed: MFE 0.08-0.33, MAE 0.58-1.12 — chop mirrors, dump <30m.
- **arm-timeout counterfactual cf30/45/60 = $+0.00 delta → KILLED.** Losses complete
  before any timeout can fire; ATR SL/cut-loser already exits them. Not an exit bug.
- entry-filter scan: rsi [50,56) 6T 33% vs outside +$0.17 — n=6 INSUFFICIENT.
  is_stale=true 3T net +$0.08 → freshness gate working as designed.
- Verdict: n=21 < ship bar. MONITOR. No filter.

### 2. CONTRARIAN JOIN REFRESHED 16:31Z (mandate)
pump-chain- flip 64.6% (226/350) STAYS LIVE-FLIP. btc-pump-rider+ 27.5% do NOT flip.
Overall 41.0% n=955. Per-signal rule holds.

### 3. LOSING AUTOPSY (adverse-first, selfcheck PASS) — 129th consecutive refutation
48h n=24 = 7 never-adverse / 13 recovered / **4 NEVER (16.7%)** → wrong-side REFUTED.

### 4. CREATIVE (3 logged)
- KILL: jup_yolo arm-timeout (tested, rejected).
- PRE-REG: inverse-conviction mirror — pro jup_leverage>=800: 10T 50% -$0.33 vs
  <800: 9T 67% -$0.07 (chasing loud pro = late). Bar: n>=40 AND sign AND fk<25%.
- SHADOW-OK: first-5m momentum-deficit collector (targets atr_sl_hit -$4.50 bleed).

### 5. PRE-REG PROGRESS (run #203 carryover)
vb- bb_position [0.6,0.8): 7d n=5 net -$0.30 40% (bar n>=15) — accumulating.
bandxEMA300 MONITOR +$0.66 no escalate. #139 HOLD for LONG-below-EMA300 STANDS.

### 6. OPEN
#16572 BTC jup_yolo LONG 63m mfe 0.28% UNARMED — watch (never-armed cohort is the
loser class; exit engines own it). #16576/#16577 r2v2-long3 (PONS no candle data).
24h red cell: jup_yolo LONG 19T -$0.40 (only n>=5 red).

### READINESS
Regime: 15m LONG_BIAS / 4h SHORT_BIAS, LOW vol, CALM, trend_quality STRONG_DOWN.
Size 1.0x. Weekly AMPLIFY due Mon 11-02 (Friday skip logged: no cell clears bar).
Storm-confl-waiver 2/3 packets. vb- 0.6-0.8 band pre-reg live. Last-run verify PASS.
