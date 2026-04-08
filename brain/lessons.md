
## guardian_missing closes bypass signal_outcomes (2026-04-07)

When the guardian detects a trade is missing from HL (ATR SL triggered), it closes the paper trade via `_close_paper_trade_db()` but forgot to call `_record_trade_outcome()` to update the SQLite signals DB. Always ensure both the PostgreSQL trades table AND the SQLite signal_outcomes table are updated when closing trades.

Also: the `close_reason` field should be descriptive — use `'hl_atr_sl'` when an HL fill is verified (ATR SL triggered), and `'guardian_missing'` only when no fill was found within the lookback window.
