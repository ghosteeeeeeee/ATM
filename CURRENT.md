# Current State — brain_auditor #205 2026-10-30 20:50 UTC
**Last Updated: 2026-10-30 20:50 UTC**
**Updated by: brain_auditor #205. Prior: #204 2026-10-30 16:45 UTC (preserved in git history).**

## HEADLINE — Winner-cell offense was a dud (10% hit rate); regime basis fixed. Chop-bleed filters fail bars honestly.

24h 55T +$0.27 56.4% GREEN thin | 7d 178T -$0.11 | 14d 299T -$2.74
Never-armed losers 7d: 61T -$6.62 = 95.1% dollar share (chop-bleed KPI BREACH, entry-quality)

### 1. WINNER-CELL 1.25x BUG (SHIPPED)
- 67 stored-regime winner-cell trades / 7d, only 7 boosted (amount>12).
- Root: `_get_winner_cell_size_mult` reclassed live ATR at open; cells validated on **stored** volatility_regime. ATR walks mid-window → miss.
- Fix: prefer `regime=` (sig/entry volatility_regime); live classify fallback only. execute_trade(vol_regime=...), delayed-entry entry.get('volatility_regime').
- Unit-verified: vb- HIGH→1.25, pc+ EXTREME→1.25, mismatch→1.0.
- Measure: [WINNER-CELL-SIZE] regime_src=sig + amount≈13.9 on next cell opens. 14d tagged-cell net delta bar +$1.00 (same as winner-cell-size-125).

### 2. CHOP-BLEED ENTRY QUALITY — filters fail bars (NO SHIP)
- SHORT dead-gap [-0.5,0.2) ex-pc: t=-0.76 p>0.05; would kill 48% winners.
- LONG weak gap [0.10,0.30): same fail.
- vb- shallow gap>-0.5: directional 14d -$0.75 but block kills 48% winners → PRE-REG dampen 0.75x, bar n>=20 shallow losers + 30d sign.
- first-5m adverse kill REFUTED: net -$2.26 (armed winners dip first).

### 3. SHORT RSI FLOOR STANDING ITEM — MEASURED
7d rsi_14 35-45 SHORT 36T +$0.69 (best) / 14d +$0.22 / 30d -$0.50 n=88. OOS sign flip → floor stays 45.

### 4. SHADOW
Contrarian join 20:30Z: overall 41.1% n=956; pc- 64.6% LIVE-FLIP stands; rider 27.6% no.
floor_admit 48.1% vs 44.0%. Wyckoff join still pending. shadow_trader hard_max -$7188 confirms chop class.

### 5. OPEN
#16588 SOL jup LONG, #16587 BTC continuum-trend+ LONG, #16585 HYPE jup LONG. Size 1.0x.
AMPLIFY: regime-basis fix IS the winner-cell traffic service; no new validated cell this run.
Weekly AMPLIFY due Mon 11-02.

### READINESS
Watch for WINNER-CELL-SIZE regime_src=sig lines + notional ~13.9. Next weekly: re-measure SHORT 35-45 at 30d.
