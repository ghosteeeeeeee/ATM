=== Signal Performance Report ===
Generated: 2026-10-17 08:17 UTC
Period: Last 6h | 24h

NOTE: 6h window had ZERO closed trades. All data below is 24h.

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
(none — no new kill candidates met criteria)

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
(none — no signal met boost bar: WR>55% + 5T + PnL>$0.05)

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 40.0% | -$0.53 | 10 | ALREADY KILLED 2026-10-16 (DOJI_BOTTOM_ENABLED=False). 24h trades opened pre-kill. No action. |
| pump-chain- | SHORT | 0.0% | -$0.29 | 5 | WATCH. 24h all-EXTREME losers, but all-time EXTREME 250T 43.6%WR +$3.71. HIGH already blocked (PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED). CEO reverted EXTREME block 2026-10-07. 5T = noise vs history. |
| ai-trader+ | LONG | 50.0% | -$0.28 | 6 | WATCH. WR at 50%, not kill-worthy. All-time: EXTREME -$0.08, NORMAL -$0.33, HIGH +$0.01 — no winning regime ≥55%. |
| bb-bounce-v2-long+ | LONG | 40.0% | -$0.12 | 5 | ALREADY MITIGATED. EXTREME blocked 0.0 mult (vol_gate_v2:380, 2026-10-16). 24h EXTREME trades opened pre-block. NORMAL/FLAT kept. |
| ai-trader-manual | LONG/SHORT | 0-33% | -$0.10 | 6 | MANUAL trades — not signal-gated. No action. |
| volume-buildup- | SHORT | 75.0% | -$0.03 | 4 | WATCH. High WR, tiny loss, under 5T threshold. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
(no signal with ≥2 closed trades had positive PnL in 24h window — quiet/losing day)

ISSUES:
- Zero closed trades in last 6h — pipeline may be throttled or market quiet. Not necessarily a bug; monitor next cycle.
- pump-chain- SHORT EXTREME 24h 0/5 all atr_sl/hard_max_loss exits. All-time EXTREME still positive (+$3.71/250T). If next cycle shows continued EXTREME bleed, revisit EXTREME block despite CEO revert — data may have flipped.
- No direction inversions found in 24h.
