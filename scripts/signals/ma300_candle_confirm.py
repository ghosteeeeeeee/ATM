# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

# Re-export so signals/__init__.py import works
from ma300_candle_confirm_signals import scan_ma300_candle_signals

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    from ma300_candle_confirm_signals import scan_ma300_candle_signals
    added, results = scan_ma300_candle_signals(prices_dict)
    return added