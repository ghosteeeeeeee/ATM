# Current State — brain_auditor #203 2026-10-30 12:55 UTC
**Last Updated: 2026-10-30 12:55 UTC**
**Updated by: brain_auditor #203. Prior: #202 2026-10-30 08:30 UTC (preserved in git history).**

## HEADLINE — vb- steer investigated: 5 candidates ALL fail bars; floor-short
## narrative REFUTED; band×EMA300 re-measure DONE (MONITOR); 0 config changes

0 trading-constant changes (hermes_constants.py no diff from this agent), 0 ships,
2 creative entries.

### 1. vb- WATCHDOG STEER — INVESTIGATED, NO FILTER SHIPPED
5 entry-filter candidates tested against 14d/7d/30d with Fisher + fk + OOS:
- momentum_state='falling' only: p=0.176, fk 48.3% — REJECT
- block is_stale=true: p=0.444 — REJECT
- falling+fresh combined: fk 69% — REJECT
- bb_position [0.2,0.4) block: n=11 < 20 bar — MONITOR
- bb_position [0.6,0.8) block: n=8 < 15 bar — **PRE-REGISTERED**
  (30d save +$0.43, fk 8.6%, monotonic 7/14/30d; trigger n>=15 ∧ PnL<0 ∧ fk<20%)

**"shorted into floors" REFUTED:** lt0.2 floor = 21T 71.4% -$0.04 (works);
gt0.8 ceiling = 9T 88.9% +$0.54 (best); killer = 0.6-0.8 ambiguous strength.

### 2. BAND×EMA300 RE-MEASURE — DONE (was overdue Oct 27)
- Mid-band [45,60) LONG dampen: 30d now +$0.66 save (sign flipped from -0.36),
  n=38 < 50 pre-reg bar → MONITOR, no escalate.
- #139 hold-cell re-verified with populated btc_ema300_position (71 rows/30d):
  LONG BELOW EMA300 = 7T +$0.34 71.4% — same sign. **HOLD-call for BTC+ETH
  open jup_yolo longs STANDS.**

### 3. CHOP-BLEED
Count 53/63 = 84.1% (under 92%). Dollar -$5.50/-$5.91 = 93.1% (over).
Outlier check: top-3 = 14.4% of dollar loss → BROAD bleed, not outliers.
Entry-quality work continues; no filter passed bars this run.

### 4. LOSING AUTOPSY (adverse-first, selfcheck PASS)
48h n=20 = 5 never-adverse / 12 recovered / **3 NEVER** (BTC continuum-trend-
SHORT, NXPC vb-, ZORA vb-) → **WRONG-SIDE REFUTED 128th consecutive run**.

### 5. CONTRARIAN JOIN FRESH (re-ran 12:25Z)
pump-chain- flip-WR **64.6%** (226/350) STANDS. btc-pump-rider+ 26.7% do NOT flip.
Overall 42.0% n=861.

### 6. PUMP-CHAIN+ / JUP_YOLO
pump-chain+ 14d 39T -$1.16 41.0% | 30d 100T +$1.91 41.0% — 30d positive,
NO-KILL stands 8th run. 11-10 bar ($>=+$1.00 delta) approaching.
jup_yolo 9T 66.7% +$0.11 all EXTREME — n<10 pre-reg, monitor stands.

### 7. OPEN TRADES
2 jup_yolo_mirrored LONG (BTC #16560, ETH #16557) against SHORT_BIAS —
HOLD per #139 cell re-verified positive. Both bracketed.

### READINESS
Regime: SHORT_BIAS (15m + 4h), NORMAL vol, BELOW EMA300. Size 1.0x.
Weekly AMPLIFY due Mon 11-02. Storm-confl-waiver 2/3 packets.
vb- 0.6-0.8 kill-band pre-reg live. Last-run verify all PASS.
