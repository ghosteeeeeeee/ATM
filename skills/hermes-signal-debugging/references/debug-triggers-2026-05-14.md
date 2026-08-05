# Hermes Signal Debugging — 2026-05-14 Session Triggers

- "accel-300 LONG losing — no regime awareness" → 23% WR, all exits via atr_sl_hit → regime filter added to detect_accel_300 using 50-bar linear regression on candles.db
- "accel-300 stale signals" → loop returns historical bar, wrong direction in hot-set → FINAL_VERIFY + gap magnitude check added
- "switch EMA to pandas" → pd.Series.ewm(span=300, adjust=False) + None warmup padding
- "RS returns 0 signals — TypeError" → rs.py add_signal missing source/confidence args, confirmed applied
- "accel-300 SHORT signs verified" → gap_then-gap_now SHORT positive=accelerating; delta_last>=delta_prev rejection correct