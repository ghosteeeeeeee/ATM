# Changes to Monitor — 2026-09-23

## Changes Made Today (Revert if WR regresses)

### 1. SHORT_RSI_FLOOR: 50 → 40
**File:** `hermes_constants.py` line 827
**What:** Allows SHORT when RSI > 40 (was 50)
**Risk:** May allow oversold SHORT (RSI 40-50 = losing band historically)
**Revert:** Set SHORT_RSI_FLOOR = 50

### 2. RR_ENGINE_CONF_HARD_BLOCK_RR: 0.95 → 0.70
**File:** `hermes_constants.py` line 3406
**What:** Allows trades with R:R > 0.70 (was 0.95)
**Risk:** May allow low-quality trades (R:R 0.70-0.95)
**Revert:** Set RR_ENGINE_CONF_HARD_BLOCK_RR = 0.95

### 3. Continuum Engine Phase Relaxed
**File:** `continuum_engine.py` lines 1028-1048
**What:** Phase 3→4 now accepts NORMAL volume with rising velocity (was HIGH/PARABOLIC only)
**Risk:** May enter trades without strong volume confirmation
**Revert:** Restore volume_regime check to HIGH/PARABOLIC only

### 4. Continuum Phase 4→5 Volume Removed
**File:** `continuum_engine.py` lines 1069-1075
**What:** Phase 4→5 no longer requires volume HIGH at tick 30
**Risk:** May reach phase 5 without volume confirmation
**Revert:** Restore volume check at Phase 5

### 5. Chop Gate AT Acceptance
**File:** `signal_compactor.py` line 1178
**What:** Accept EMA300 position 'AT' (not just 'ABOVE') for LONG override
**Risk:** May allow LONG when EMA300 is ambiguous
**Revert:** Change `_e2 in ('ABOVE', 'AT')` back to `_e2 == 'ABOVE'`

### 6. Continuum Signals Reclassified
**File:** `chop_detector.py` lines 95-103
**What:** continuum_osc, continuum_score, continuum_trend reclassified as MEAN_REVERSION
**Risk:** May allow continuum signals in chop (they were blocked as MOMENTUM)
**Revert:** Change back to MOMENTUM classification

## Monitoring Plan

### Daily Check (CEO)
1. Run: `python3 -c "import psycopg2; conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres'); cur = conn.cursor(); cur.execute(\"SELECT COUNT(*), SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END), ROUND(SUM(pnl_usdt)::numeric, 2) FROM trades WHERE close_time > NOW() - INTERVAL '24 hours' AND status='closed'\"); r = cur.fetchone(); print(f'24h: {r[1]}/{r[0]} ({r[1]/r[0]*100:.1f}%) \${r[2]}'); conn.close()"`
2. If WR < 50% or PnL < -$1.00 → revert changes in order

### Revert Priority
1. RR_ENGINE_CONF_HARD_BLOCK_RR → 0.95 (highest risk)
2. SHORT_RSI_FLOOR → 50 (medium risk)
3. Continuum phase relax → restore volume check (medium risk)
4. Chop gate AT → restore ABOVE only (low risk)
5. Continuum reclassification → restore MOMENTUM (low risk)

## Expected Impact
- SHORT_RSI_FLOOR: +$0.05-0.10/day
- RR Engine: +$0.05-0.10/day
- Continuum: +$0.10-0.20/day (if phase transitions work)
- **Total: +$0.20-0.40/day** (conservative estimate)
