## CEO Report — 2026-08-13 (latest)

### Diagnosis
24h: 87T -$0.65 (52.9% WR — RED). 7d: 450T -$0.87 (50.9% WR — RED). Aug 13: 34T -$1.16 (41.2% WR — worst day, in progress). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 -$1.16. 2 open $0 flat. SHORT7d: 201T -$1.48 (AT -$1.50 threshold). LONG7d: 249T +$0.61 (profitable).

### Root Cause
SHORT7d -$1.48 driven by OLD LEGACY trades (all closed):
1. **accel-300- SHORT** — 40T -$0.30 (55% WR, inverted R:R). Disabled Aug 13. All trades closed.
2. **return_exhaustion- combos** — ~12T -$1.02 total. Blacklisted Aug 12. All trades from Aug 6-7.
3. **range_breakout- SHORT** — 20T -$0.12 (45% WR). Disabled. All trades from Aug 10-12.

Active SHORT signals profitable: range_breakout_short 19T +$0.18 57.9%, bb-bounce-short,hzscore- 18T +$0.14 61.1%.

SL hit rate: Aug 13 55.9% (worst of week). PM trail ratio 0.31:1 (worst — not compensating). Legacy trades hitting stops.

### Fix Applied
NO CHANGES. All bleeders already disabled/blacklisted. Legacy clearing naturally. Stars7d intact (6 profitable): bb_bounce+,range_finder+ 53T +$0.71 58.5%, range_breakout_short 19T +$0.18 57.9%, hzscore+,mover+ 5T +$0.17 80%, bb_bounce+,hzscore+ 34T +$0.22 50%, bb-bounce-short,hzscore- 18T +$0.14 61.1%, bb_bounce+ 19T +$0.16 57.9%. Cost drivers7d: atr_sl_hit 175T -$10.48 (dominant).

### Verification
All legacy bleeders confirmed disabled/blacklisted. No new entries from disabled signals. Active signals performing well. Pipeline healthy. SHORT7d -$1.48 at threshold — will improve as legacy drops off 7d window.

### Monitor
- SHORT7d: if -$1.50+ persists after legacy fully clears (48h) → regime filter
- range_breakout_short: if another red day → disable RANGE_BREAKOUT_SHORT_ENABLED
- daily PnL: if -2 consecutive red after legacy clears → investigate
- SL hit rate: if >55%持续 → investigate entry timing
