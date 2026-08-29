# Wave Period Analysis: ZRO

## Summary

Wave period analysis has been implemented to detect and analyze periodicity in price data. The system identifies peaks and troughs, calculates time periods between them, and detects when wave frequency is changing.

## Key Findings for ZRO

### Wave Characteristics (1h timeframe)
- **Average Period**: 1.99 hours (~2 hours)
- **Period Variability**: High (std dev 2.37 hours)
- **Pattern Consistency**: Very Low
- **Cyclical Pattern**: Yes (autocorrelation 0.506)

### Recent Trades Analysis

| Trade | Entry | Exit | PnL | Duration | Wave Position |
|-------|-------|------|-----|----------|---------------|
| 1 (SHORT) | $1.0660 | $1.0750 | -4.22% | 24.7 min | Post-peak declining |
| 2 (SHORT) | $1.1267 | $1.0905 | +16.06% | 20.7 min | Near trough |
| 3 (SHORT) | $1.1727 | $1.1701 | +1.11% | 25.6 min | Near peak |

### Frequency Changes Detected
Recent wave frequency has been **accelerating** (waves getting faster):
- Aug 27 09:00: -30% faster (moderate)
- Aug 27 15:00: -32% faster (significant)
- Aug 28 18:00: -33% faster (significant)

## Trading Implications

### Current Signal
- **Action**: REDUCE_EXPOSURE
- **Confidence**: 80%
- **Reason**: Irregular wave pattern with high uncertainty

### Key Observations

1. **Asymmetric Extrema**: 313 peaks vs 45 troughs suggests price spends more time declining than rising
2. **Fast Waves**: Average 2-hour periods indicate high-frequency oscillations
3. **Frequency Acceleration**: Recent acceleration often precedes breakouts or increased volatility
4. **Pattern Irregularity**: Low consistency makes timing entries difficult

## Recommendations

1. **Position Sizing**: Reduce size during irregular wave periods
2. **Entry Timing**: Wait for clearer wave structure before entering
3. **Stop Losses**: Use tighter stops given the fast wave cycles
4. **Timeframe Alignment**: Consider higher timeframes (4h) for more stable patterns

## Scripts Created

1. **`wave_period_detector.py`** - Core wave period analysis
2. **`wave_trade_context.py`** - Analyzes trades in wave context
3. **`wave_backtest.py`** - Existing MACD-based wave backtester (already existed)

## Usage

```bash
# Analyze wave periods for any token
python3 scripts/wave_period_detector.py ZRO --timeframe 1h --lookback 720

# Analyze 15m waves for more detail
python3 scripts/wave_period_detector.py ZRO --timeframe 15m --lookback 2880

# JSON output for programmatic use
python3 scripts/wave_period_detector.py ZRO --json

# Analyze trades in wave context
python3 scripts/wave_trade_context.py
```

## Next Steps

1. **Backtest**: Test wave-based entry/exit strategies
2. **Multi-timeframe**: Combine 15m and 1h wave signals
3. **Frequency Filter**: Only trade when wave frequency is stable
4. **Amplitude Filter**: Focus on high-amplitude waves for better risk/reward
