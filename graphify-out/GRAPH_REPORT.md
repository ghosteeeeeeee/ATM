# Graph Report - /root/.hermes/scripts  (2026-08-05)

## Corpus Check
- 262 files · ~437,186 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4127 nodes · 8157 edges · 250 communities (222 shown, 28 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 91 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Checkpoint & Sync Utils
- MACD Acceleration Signals
- HH/HL & MA Cross Signals
- Acceleration 300 Signals
- Decider Run (AI Decision)
- MTF MACD Tuner
- Signal Schema & Enrichment
- AI Decider & Cascade Flip
- Exchange & Position Manager
- Pump Hunter
- Cooldown & Early Fires
- Audit Logger & Brain
- Decision Log & Reflections
- Hyperliquid Exchange Core
- Cascade Flip Logic
- Signal Generation Pipeline
- Blacklist & Risk Management
- Price Collection & Caching
- Trade Lifecycle Management
- Regime Scanner Logic
- Brain Memory & Tags
- A/B Testing & Optimization
- Context Gate & Market
- Hot Set Management
- Trailing Stop Logic
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 212
- Community 213
- Community 218
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223
- Community 224
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240
- Community 241

## God Nodes (most connected - your core abstractions)
1. `log()` - 266 edges
2. `add_signal()` - 146 edges
3. `get_all_latest_prices()` - 87 edges
4. `price_age_minutes()` - 75 edges
5. `get_open_positions()` - 63 edges
6. `FileLock` - 60 edges
7. `init_db()` - 57 edges
8. `recent_trade_exists()` - 47 edges
9. `run()` - 47 edges
10. `is_delisted()` - 44 edges

## Surprising Connections (you probably didn't know these)
- `qwen2.5:1.5b Production` --semantically_similar_to--> `qwen2.5:1.5b`  [INFERRED] [semantically similar]
  ollama-benchmarks.md → candle_predictor_sweep.yaml
- `scan_accel_300_signals()` --calls--> `is_delisted()`  [INFERRED]
  accel_300_signals.py → hyperliquid_exchange.py
- `get_realized_pnl()` --calls--> `wavg_price()`  [INFERRED]
  hyperliquid_exchange.py → backfill_orphan_hl_prices.py
- `_wait_for_hl_close()` --indirect_call--> `_wait_for_position_closed()`  [INFERRED]
  cascade_flip.py → hl-sync-guardian.py
- `cascade_flip()` --indirect_call--> `_clear_reconciled_token()`  [INFERRED]
  cascade_flip.py → hl-sync-guardian.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Signal Types in Penalty System** — plans_penalty_system_velhermes, plans_penalty_system_hzscore, plans_penalty_system_pcthermes [INFERRED 0.85]

## Communities (250 total, 28 thin omitted)

### Community 0 - "Checkpoint & Sync Utils"
Cohesion: 0.03
Nodes (134): detect_incomplete_run(), On startup, check for a pipeline run that was interrupted mid-trade. Returns…, add_orphan_trade(), _add_to_kill_switch(), _check_and_close_breached_trades(), _check_and_execute_flip(), _check_hard_stops(), _check_stale_rotation() (+126 more)

### Community 1 - "MACD Acceleration Signals"
Cohesion: 0.03
Nodes (96): _get_1m_closes(), Scan for MACD acceleration signals across all tokens. Args: prices_dict:…, Fetch 1m close prices from candles.db (candles_1m table). Returns: list of…, Return SMA series (oldest first), None for indices < period-1., scan_macd_accel_signals(), _sma(), get_opposite_direction_cooldown_hours(), Return hours remaining on the OPPOSITE direction's cooldown. Used by scanner to… (+88 more)

### Community 2 - "HH/HL & MA Cross Signals"
Cohesion: 0.05
Nodes (77): # NOTE: breakout candle size check (HH_HL_ATR_ENTRY_MIN) is skipped —…, _ema(), Compute EMA(period) from a list of prices (oldest first). Returns the most…, _ema(), Compute EMA(period) from a list of prices (oldest first). Returns the most…, Add RSI as standalone signal — filtered to only fire when trend aligns., _run_rsi_signals_for_confluence(), cleanup_stale_approved() (+69 more)

### Community 3 - "Acceleration 300 Signals"
Cohesion: 0.05
Nodes (62): detect_accel_300(), _ema_series(), _get_1m_prices(), _log(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Write to both stdout and signals.log., Detect persistent gap above EMA(300) with growing gap. Fire when ALL of these…, Scan tokens for accel_300 signals. All guards (blacklists, open positions,… (+54 more)

### Community 4 - "Decider Run (AI Decision)"
Cohesion: 0.04
Nodes (60): _check_counter_trend_trap(), _check_hotset_cooldown(), _ctx_gate_get_market_context(), _ctx_gate_get_momentum(), _ctx_gate_get_phase(), _ctx_gate_get_speed(), _ctx_gate_get_zscore(), _ctx_load_cache() (+52 more)

### Community 5 - "MTF MACD Tuner"
Cohesion: 0.07
Nodes (54): build_15m_candles_from_1h(), _cached_request(), compute_macd(), ema(), _fast_backtest(), fetch_15m_klines(), fetch_1h_klines(), fetch_4h_klines() (+46 more)

### Community 6 - "Signal Schema & Enrichment"
Cohesion: 0.05
Nodes (54): add_confluence_signal(), add_signal(), _enrich_indicators(), Add a confluence signal (when ≥2 indicator signals agree on same…, Compute standard indicators from price_history and token_speeds. Returns dict…, Add a new signal. ONE row per token+direction (all signal_types merged). FIX…, _atr(), _count_bounces_with_rejection() (+46 more)

### Community 7 - "AI Decider & Cascade Flip"
Cohesion: 0.07
Nodes (49): _get_signal_streak(), Get cached signal streak, refreshed every 5 minutes (per-key TTL)., increment_pipeline_cycle(), Increment and persist the pipeline cycle counter. Called once per pipeline run…, run(), run(), log(), get_hype_positions() (+41 more)

### Community 8 - "Exchange & Position Manager"
Cohesion: 0.06
Nodes (54): Log an A/B test outcome to W&B (offline) for visual comparison. Also appends a…, record_ab_outcome(), cancel_all_open_orders(), Cancel ALL open orders (trigger AND non-trigger) for a coin in ONE API call.…, adjust_stop_loss(), _analyze_loss_direction(), _bridge_signal_history_to_patterns(), check_and_manage_positions() (+46 more)

### Community 9 - "Pump Hunter"
Cohesion: 0.07
Nodes (51): add_pump_position(), _cancel_brain_record(), check_pump_exits(), close_all(), _close_brain_record(), _create_brain_record(), detect_vol_explosion(), execute_pump_trade() (+43 more)

### Community 10 - "Cooldown & Early Fires"
Cohesion: 0.07
Nodes (44): get_cooldown(), _is_cooldown_key_active(), Helper: check if a specific token:direction key is active. When checking…, detect_accel_300(), detect_breakout(), detect_velocity_ignition(), _ema_series(), _get_1m_prices() (+36 more)

### Community 11 - "Audit Logger & Brain"
Cohesion: 0.07
Nodes (46): trade_open_attempt(), trade_open_failed(), trade_open_success(), add_tag(), add_trade(), backfill_embeddings(), call_ollama(), close_trade() (+38 more)

### Community 12 - "Decision Log & Reflections"
Cohesion: 0.07
Nodes (45): analyze_patterns(), extract_lesson(), generate_reflection(), get_lessons(), _load_decisions(), _log(), log_decision(), Update decision with trade outcome after close. (+37 more)

### Community 13 - "Hyperliquid Exchange Core"
Cohesion: 0.07
Nodes (46): _asset_id(), build_order(), _coin_max_leverage(), _exchange_retry(), _fetch_and_cache_coin_meta(), get_account_value(), get_account_value_curl(), _get_coin_meta_cached() (+38 more)

### Community 14 - "Cascade Flip Logic"
Cohesion: 0.07
Nodes (44): cascade_flip(), _close_paper_position(), _get_db_connection(), clear_expired_evictions(), get_eviction_deadline(), get_flip_k_multiplier(), get_pipeline_cycle(), insert_post_flip_trade() (+36 more)

### Community 15 - "Signal Generation Pipeline"
Cohesion: 0.07
Nodes (45): _compute_confidence(), compute_ema(), _compute_ema_mid_history(), compute_group_emas(), detect_cross(), detect_cross_with_setup(), detect_expansion(), detect_guppy_exit() (+37 more)

### Community 16 - "Blacklist & Risk Management"
Cohesion: 0.08
Nodes (41): compute_direction_performance(), compute_evolution_signals(), compute_sl_learnings(), compute_token_regime_performance(), compute_token_stats(), _db_conn(), get_closed_trades(), Global SL distance analysis: which SL distances have highest win rates overall.… (+33 more)

### Community 17 - "Price Collection & Caching"
Cohesion: 0.06
Nodes (38): Dynamically register a signal at runtime. Useful for plugin-style injection.…, Run a single signal. Threads share the LRU cache with the caller, so…, register_signal(), _run_signal(), detect_ma_cross(), _ema(), _ema_series(), _get_candles_1m() (+30 more)

### Community 18 - "Trade Lifecycle Management"
Cohesion: 0.07
Nodes (22): main(), hebbian_trade_boost(), Estimate historical win rate from Hebbian memory for (token, signal) pair.…, HebbianEngine, main(), Ensure consistent ordering for symmetric storage., Record that concept_a and concept_b fired together. Increments synapse weight.…, Learn all pairs from a set of concepts that fired together. Creates C(n,2)… (+14 more)

### Community 19 - "Regime Scanner Logic"
Cohesion: 0.09
Nodes (40): load_prices(), Load 1m close prices for a token, oldest first. Last N days only., Run backtest across all tokens and flag types., run_backtest(), _atr_1m(), _atr_from_closes(), detect_ascending_triangle(), detect_bear_flag() (+32 more)

### Community 20 - "Brain Memory & Tags"
Cohesion: 0.08
Nodes (36): close_brain(), close_paper(), get_exit_price(), main(), Get the most recent fill price for a coin from HL trade history. NOTE:…, Remove coin from paper open, append to closed with reason=manual_close., Close the open brain trade for coin with reason=manual_close., Record loss cooldown based on PnL. Wins do NOT trigger cooldown. (+28 more)

### Community 21 - "A/B Testing & Optimization"
Cohesion: 0.09
Nodes (37): _compute_confidence(), compute_ema(), _compute_ema_mid_history(), compute_group_emas(), detect_cross(), detect_cross_with_setup(), detect_expansion(), detect_guppy_exit() (+29 more)

### Community 22 - "Context Gate & Market"
Cohesion: 0.08
Nodes (37): _backtest_params(), clear_cache(), compute_zscore(), _fast_zscore(), _get_1m_atr(), get_all_token_prices(), get_all_token_prices_full(), _get_latest_prices() (+29 more)

### Community 23 - "Hot Set Management"
Cohesion: 0.07
Nodes (36): checkpoint_decider_cycle(), checkpoint_guardian_cycle(), checkpoint_list(), checkpoint_orphan_detected(), checkpoint_read_last(), checkpoint_trade_pending(), checkpoint_write(), clear_workflow_state() (+28 more)

### Community 24 - "Trailing Stop Logic"
Cohesion: 0.10
Nodes (37): _place_or_replace_tp(), Place a new TP order if none exists, or replace the existing TP order. Returns…, cancel_bulk_orders(), cancel_sl(), cancel_tp(), clean_all_tpsl_orders(), _exchange_rate_limit(), _find_open_trigger_order() (+29 more)

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (35): mirror_close(), Close a real Hyperliquid position mirroring a paper close. BLOCKED if live…, add_position(), check_exits(), close_all_positions(), _close_brain_record(), cmd_close_all(), cmd_monitor() (+27 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (24): backtest_token(), evaluate_entry_at(), evaluate_exit_at(), fetch_binance_backward(), fetch_token_candles(), IncrementalMACD, load_local_candles(), MultiTimeFrameMACD (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (33): _atr(), _atr_pct(), _bounce_confirmation(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs_signal(), _find_swing_highs_lows() (+25 more)

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (32): analyze(), build_filter_grid(), check_exit(), check_exit_4h_regime(), check_exit_any_flip(), check_exit_both_4h1h(), check_exit_histogram_flip(), compute_macd_state() (+24 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (16): migrate_is_closed(), Add is_closed=1 to all existing candles_1m rows that lack the column., migrate_is_closed(), Add is_closed=1 to all existing candles_5m rows that lack the column., backfill_tf(), main(), Backfill all historical closed windows for one timeframe. Chunks the backfill…, Database configuration for Hermes trading system. Single source of truth for… (+8 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (31): _do_purge(), _enrich_and_write_signals(), _filter_safe_prev_hotset(), _get_open_tokens(), _get_opposing_penalty(), get_regime_1m(), _get_source_weight(), _get_token_wr() (+23 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (18): _get_speed_tracker(), get_all_speeds(), get_fastest_tokens(), get_tracker(), _now_ts(), speed_tracker.py — Token speed, velocity, acceleration, and momentum…, Fetch current prices + recent 5m candle history from local DB, compute all…, Returns full dict of token → speed data (from last update). (+10 more)

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (29): _adjust_param(), analyze_and_adjust(), _calculate_pnl(), _calculate_wr(), _check_daily_limit(), _detect_decay(), _find_weakest_param(), _get_current_value() (+21 more)

### Community 33 - "Community 33"
Cohesion: 0.12
Nodes (27): check_entry(), check_exit(), check_guard_block(), compute_atr(), compute_macd_state(), ema(), generate_all_strategies(), init_results_db() (+19 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (24): acquire_lock(), clear_ab_cache(), _ema(), execute_trade(), get_local_prices(), get_macd(), _kill_hot_signal(), _kill_pending_opposite() (+16 more)

### Community 35 - "Community 35"
Cohesion: 0.11
Nodes (27): compute_atr(), compute_levels(), detect_breakout(), detect_breakout_direction(), detect_breakout_for_token(), detect_compression(), detect_volume_pop(), get_candles() (+19 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (26): _aggregate_5m_from_1m(), _backtest_pair(), detect_cross(), _ema(), _ema_series(), get_5m_candles(), init_tuner_db(), load_params() (+18 more)

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (25): _aggregate_5m_from_1m(), _backtest_pair(), detect_cross(), _ema(), _ema_series(), get_5m_candles(), init_tuner_db(), load_params() (+17 more)

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (25): _compute_macd_histograms(), _compute_rsi(), _compute_rsi_per_tf(), _ema(), _fetch_candles(), _get_fresh_price(), import_mtf_macd_signals(), import_pending_signals() (+17 more)

### Community 39 - "Community 39"
Cohesion: 0.12
Nodes (24): _db_conn(), epsilon_greedy_pick(), evolve_test(), get_all_results(), get_best_variant_for_test(), get_evolution_snapshot(), get_exploration_variant_for_test(), _get_variant_stats() (+16 more)

### Community 40 - "Community 40"
Cohesion: 0.10
Nodes (19): cache_age(), cache_fresh(), ATR cache — persistent file + in-memory ATR cache with 300s TTL. Survives…, Return seconds since cache was written, or 999 if no cache., True if cache exists and is within TTL., Read ATR cache from disk. Returns {token: {atr, ts}} or empty dict., Write ATR cache to disk atomically under file lock., Save ATR value to both memory cache and file cache. Args: token: Token symbol… (+11 more)

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (24): get_atr(), Get ATR for token from persistent cache. Tries in order: 1. Memory cache…, _atr_sl_k_scaled(), _atr_tier(), compute_atr_sl_pct(), compute_atr_sl_tp(), compute_atr_tp_pct(), compute_atr_tp_price() (+16 more)

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (23): detect_capitulation(), detect_extended_move(), detect_higher_low(), detect_reversal_quality(), detect_sharp_reversal(), Detect higher low formation (bullish divergence after downtrend). Looks for: -…, Detect sharp reversal candle (strong momentum shift). A sharp reversal has: - A…, Master function: detect high-probability reversal setups. Combines all pattern… (+15 more)

### Community 43 - "Community 43"
Cohesion: 0.12
Nodes (24): _atr(), _atr_pct(), _bounce_confirmation(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs_signal(), _find_swing_highs_lows() (+16 more)

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (24): evaluate_expired(), generate_report(), _get_current_price(), _get_entry_price(), _get_recent_signals(), _load_results(), _load_tracked(), main() (+16 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (24): backtest_ema20_50(), batch_backtest(), detect_ema20_50_pullback(), _detect_one_direction(), _ema_series(), _get_1m_prices(), _is_bearish_reversal(), _is_bullish_reversal() (+16 more)

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (23): _aggregate_tf(), fetch_all_prices(), _fetch_binance_candles(), _get_active_tokens(), _get_candle_progress(), _init_candles_db(), main(), Store candles to candles.db. (+15 more)

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (23): backtest_signals(), detect_bollinger_squeeze(), detect_consecutive_candles(), detect_volume_breakout(), evaluate_pattern(), generate_template(), get_candles(), get_tokens() (+15 more)

### Community 48 - "Community 48"
Cohesion: 0.28
Nodes (23): bug(), check_ab_testing(), check_cooldowns(), check_db_integrity(), check_hotset(), check_mirror(), check_ollama(), check_paper_hl_sync() (+15 more)

### Community 49 - "Community 49"
Cohesion: 0.13
Nodes (21): closest_candle_before(), compute_z_at(), get_token_tf_data(), hwave_test(), Returns (direction, avg_z_signed, avg_z_abs, avg_vel) or None. Regime filter…, run_backtest(), stats(), vel_sig_gen() (+13 more)

### Community 50 - "Community 50"
Cohesion: 0.13
Nodes (22): backtest_ema20_50(), batch_backtest(), detect_ema20_50_pullback(), _detect_one_direction(), _ema_series(), _get_1m_prices(), _is_bearish_reversal(), _is_bullish_reversal() (+14 more)

### Community 51 - "Community 51"
Cohesion: 0.12
Nodes (22): _atr(), _compute_volume_sma(), _confirm_breakout(), _detect_sos(), _detect_sow(), _detect_spring(), _detect_upthrust(), detect_wyckoff() (+14 more)

### Community 52 - "Community 52"
Cohesion: 0.13
Nodes (21): calculate_r2(), calculate_slope(), calculate_weight_adjustment(), determine_regime(), fetch_candles(), fetch_candles_from_binance(), fetch_candles_from_db(), get_tokens_to_scan() (+13 more)

### Community 53 - "Community 53"
Cohesion: 0.09
Nodes (22): cleanup_stale_signals(), get_learned_adjustments(), get_market_zscore(), get_open(), get_pending_signals(), get_prediction(), get_prices(), is_real_pump() (+14 more)

### Community 54 - "Community 54"
Cohesion: 0.14
Nodes (21): cascade_entry_signal(), compute_mtf_macd_alignment(), _detect_cascade(), _fetch_binance_candles(), get_macd_params(), Return MACD params for token, falling back to DEFAULT., Detect cascade entry condition: smaller TF flips before larger TF confirms.…, Detect cascade entry timing and generate entry/exit signals. Key insight:… (+13 more)

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (22): _clean_expired(), clear_loss_streak(), get_loss_cooldown_remaining(), get_loss_streak(), is_loss_cooldown_active(), _is_win_cooldown_active(), _load_cooldowns(), Load cooldown data from JSON file. Handles two formats: - Old: {"KEY":… (+14 more)

### Community 56 - "Community 56"
Cohesion: 0.14
Nodes (21): apply_recommendations(), evaluate_results(), get_active_params(), get_closed_trades(), get_open_trade_ids(), get_pg_conn(), init_tables(), Record that a trade opened with specific param values. (+13 more)

### Community 57 - "Community 57"
Cohesion: 0.15
Nodes (21): add_all_signals(), get_cached_indicators(), get_cached_prices(), get_fear(), get_gateio_rsi(), get_gateio_signals(), get_open_trades(), get_pending_hype_signals() (+13 more)

### Community 58 - "Community 58"
Cohesion: 0.18
Nodes (18): build_structure_series(), check_exit(), compute_atr_series(), compute_stats(), find_swings_upfront(), fmt(), get_candles(), get_swing_prices() (+10 more)

### Community 59 - "Community 59"
Cohesion: 0.15
Nodes (20): cmd_evaluate(), cmd_pick(), cmd_remaining(), cmd_status(), evaluate_verdict(), get_tested_tokens(), get_trial_outcomes(), load_blacklists() (+12 more)

### Community 60 - "Community 60"
Cohesion: 0.14
Nodes (20): acquire_lock(), get_critical_flags_block(), get_live_trading_status(), get_pipeline_status(), get_position_summary(), get_quick_status_line(), get_regime(), get_wasp_status() (+12 more)

### Community 61 - "Community 61"
Cohesion: 0.14
Nodes (19): IntEnum, CrossoverFreshness, get_macd_exit_signal(), load_token_macd_params(), Load per-token MACD params from tuner DB into TOKEN_MACD_PARAMS dict. Priority:…, Check if a position should be exited based on MACD rules. Returns dict with:…, Regime, _check_cascade_direction_flip() (+11 more)

### Community 62 - "Community 62"
Cohesion: 0.14
Nodes (18): detect_ma300_candle(), _ema(), _ema_series(), _get_candles_1m(), Detect EMA300 + 2-candle confirmation signal. Args: token: token symbol (e.g.…, Scan all tokens in prices_dict for EMA300 + 2-conf signals. Args: prices_dict:…, Compute EMA(period) from a list of prices (oldest first). Returns the most…, Compute EMA series — returns EMA value at each index (oldest first). Returns a… (+10 more)

### Community 63 - "Community 63"
Cohesion: 0.15
Nodes (20): compute_live_pnl(), Compute live (unrealized) pnl_pct from entry and current price. Direction-…, close_position(), filter_by_pnl(), get_all_open_positions(), is_position_on_hl(), is_token_being_closed_by_guardian(), load_config() (+12 more)

### Community 64 - "Community 64"
Cohesion: 0.12
Nodes (20): calculate_confluence(), get_confluence_signals(), get_momentum_state(), get_zscore_tier(), import_fear_signal(), import_rsi_signal(), import_zscore_signal(), _load_momentum() (+12 more)

### Community 65 - "Community 65"
Cohesion: 0.15
Nodes (20): backtest_ema9_sma20(), _compute_gap_series(), _compute_slope_series(), detect_ema9_sma20_cross(), _ema_series(), _ema_slope_series(), _get_1m_prices(), Compute slope over the last `slope_period` bars for each valid value. slope[i]… (+12 more)

### Community 66 - "Community 66"
Cohesion: 0.18
Nodes (20): add_orphan_recovery_trade(), close_hl_position(), close_paper_trade_db(), find_existing_open_trade(), find_recent_closed_trade(), get_db_connection(), get_open_paper_trades(), _is_loss_cooldown_active() (+12 more)

### Community 67 - "Community 67"
Cohesion: 0.15
Nodes (19): calculate_r2(), calculate_slope(), determine_regime(), fetch_candles(), fetch_candles_from_binance(), fetch_candles_from_db(), get_tokens_to_scan(), main() (+11 more)

### Community 68 - "Community 68"
Cohesion: 0.14
Nodes (18): backfill(), get_closed_trades_without_hl_pnl(), get_hl_close_fill(), Get the most recent HL close fill (side=B) for a token after start_time_ms.…, update_trade(), fetch_hl_prices(), main(), ms() (+10 more)

### Community 69 - "Community 69"
Cohesion: 0.14
Nodes (19): compute_series(), get_all_prices(), main(), Group fires into pulses., Run state machine backtest on full price series. Returns events list., run_backtest(), summarize_pulses(), _ema_series() (+11 more)

### Community 70 - "Community 70"
Cohesion: 0.16
Nodes (19): aggregate_1m_to_tf(), detect_cascade_direction(), fetch_and_store(), fetch_and_store_all_tf(), get_candles(), get_conn(), get_last_ts(), get_latest_price() (+11 more)

### Community 71 - "Community 71"
Cohesion: 0.15
Nodes (16): backtest_token(), compute_atr(), compute_levels(), detect_breakout(), detect_breakout_direction(), detect_compression(), get_all_tokens(), get_candles_range() (+8 more)

### Community 72 - "Community 72"
Cohesion: 0.16
Nodes (18): _atr_raw(), compute_atr(), compute_macd(), compute_rsi(), detect_tl_break_baseline(), detect_tl_break_improved(), _linear_regression(), load_candles_5m() (+10 more)

### Community 73 - "Community 73"
Cohesion: 0.16
Nodes (18): is_delisted(), Return True if token is delisted/halted on Hyperliquid (no new positions)., compute_zscore_velocity(), _ema(), _fast_zscore(), get_momentum_stats(), is_reasonable_price(), _log() (+10 more)

### Community 74 - "Community 74"
Cohesion: 0.17
Nodes (18): check_state_transition(), get_signal_history(), load_audit(), load_lifecycle(), log(), main(), Load latest audit data., Get historical performance for a signal type. (+10 more)

### Community 75 - "Community 75"
Cohesion: 0.14
Nodes (18): detect_gap_cross(), _ema_series(), _get_1m_prices(), _init_state_table(), _load_state(), Load state for a token. Returns default (no signal) if none found., Save state for a token to DB., Fetch 1m close prices from price_history (signals_hermes.db), oldest first.… (+10 more)

### Community 76 - "Community 76"
Cohesion: 0.17
Nodes (18): _classify_structure(), _compute_atr(), _detect_breakout(), _detect_pullback(), _find_swing_highs_lows(), _get_candles_from_ohlcv_1m(), _get_candles_from_price_history(), Classify current swing structure at the most recent candle. Args: highs: sorted… (+10 more)

### Community 77 - "Community 77"
Cohesion: 0.20
Nodes (16): atr_check(), atr_sl_hit(), atr_tp_hit(), _base(), guardian_cycle(), log_event(), loss_cooldown_set(), _now() (+8 more)

### Community 78 - "Community 78"
Cohesion: 0.16
Nodes (13): grep_file(), Return list of (line_num, line) matching pattern., get_fast_signals(), get_registered_signals(), get_slow_signals(), Resolve 'enabled' to bool: if string, look up in hermes_constants; otherwise…, Return only the signals where enabled=True and run is not None., Fast signals — run every minute. (+5 more)

### Community 79 - "Community 79"
Cohesion: 0.11
Nodes (18): build_prediction_prompt(), init_predictions_db(), main_loop(), minimax_check(), parse_prediction(), query_llm(), Second-opinion check via Minimax API. Returns {'agree': bool,…, Build Ollama prompt — pure text categories, no numeric values. Research… (+10 more)

### Community 80 - "Community 80"
Cohesion: 0.18
Nodes (17): analyze_by_hour(), analyze_by_regime(), analyze_by_state_direction(), analyze_by_token(), analyze_inversion_effectiveness(), analyze_overall(), apply_prompt_fix(), apply_token_override() (+9 more)

### Community 81 - "Community 81"
Cohesion: 0.17
Nodes (17): event_summary(), log_api_call(), log_budget_exceeded(), log_checkpoint_recovery(), log_event(), log_hotset_updated(), log_trade_entered(), log_trade_failed() (+9 more)

### Community 82 - "Community 82"
Cohesion: 0.16
Nodes (16): extract_and_learn(), extract_entities(), _load_coin_universe(), Extract all typed entities from text. Returns list of (concept_name,…, Extract entities and learn all co-occurring pairs. If engine is None, just…, Load HL coin universe from signals_hermes.db.ohlcv_1m.token., learn_from_event_log(), learn_from_sessions() (+8 more)

### Community 83 - "Community 83"
Cohesion: 0.16
Nodes (16): get_tradeable_tokens(), Return set of tradeable (non-delisted) token names from HL meta., get_allowed_tokens(), get_binance_volumes(), get_hl_universe(), get_top150(), hl_to_binance_symbol(), load_cache() (+8 more)

### Community 84 - "Community 84"
Cohesion: 0.19
Nodes (17): check_and_close(), db_connect(), ensure_table(), get_all_self_close(), guarded_close_position(), mark_triggered(), Load all stored self-close TP/SP from DB., Record that we triggered a self-close. (+9 more)

### Community 85 - "Community 85"
Cohesion: 0.14
Nodes (17): ai_decide(), ai_decide_batch(), _check_token_budget(), _do_compaction_llm(), get_fear(), get_open_trade_details(), get_regime(), _log_wandb() (+9 more)

### Community 86 - "Community 86"
Cohesion: 0.15
Nodes (16): detect_ma_cross(), _ema_series(), _get_candles_1m(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for MA cross signals and write to DB. All guards…, Compute EMA series — returns EMA value at each index (oldest first). Returns a…, Detect 10/200 EMA crossover on 1m candles. Args: token: token symbol (e.g.…, scan_ma_cross_signals() (+8 more)

### Community 87 - "Community 87"
Cohesion: 0.18
Nodes (16): compute_edge_score(), get_registry_status(), get_signal_performance(), get_token_breakdown(), log(), main(), map_signal_to_flag(), Map a signal_type name to its *_ENABLED flag in hermes_constants.py. DB signal… (+8 more)

### Community 88 - "Community 88"
Cohesion: 0.18
Nodes (16): _apply_changes(), _build_prompt(), _call_opencode(), _get_compactor_weights(), _get_current_params(), _load_results(), _log_tune(), main() (+8 more)

### Community 89 - "Community 89"
Cohesion: 0.21
Nodes (16): apply_changes(), get_current_regime(), get_registry_status(), load_audit(), log(), main(), map_signal_to_flag(), Select which signals to enable/disable based on regime and performance. (+8 more)

### Community 90 - "Community 90"
Cohesion: 0.21
Nodes (15): acquire_lock(), call_ceo(), get_debounce_ts(), is_live_trading_enabled(), is_pipeline_healthy(), is_t_away(), load_json(), main() (+7 more)

### Community 91 - "Community 91"
Cohesion: 0.16
Nodes (16): build_ohlcv(), compute_macd_ohlc(), compute_mtf_macd(), compute_rsi_ohlc(), estimate_volume(), get_prices_db(), get_runtime_db(), get_token_data_for_prediction() (+8 more)

### Community 92 - "Community 92"
Cohesion: 0.17
Nodes (16): backtest_ema9_sma20(), _compute_gap_series(), _compute_slope_series(), detect_ema9_sma20_cross(), _ema_series(), _ema_slope_series(), Compute slope over the last `slope_period` bars for each valid value. slope[i]…, Return (EMA series, slope of EMA series) — both oldest first. (+8 more)

### Community 93 - "Community 93"
Cohesion: 0.19
Nodes (15): classify_errors(), detect_alerts(), load_known_patterns(), log(), main(), Compare current patterns against known, return alerts., Append alerts to error_alerts.md., Scan last hour of hermes-pipeline journal for errors. (+7 more)

### Community 94 - "Community 94"
Cohesion: 0.19
Nodes (15): _atomic_write(), _build_open_trades(), _get_current_price(), get_signals_from_db(), get_trades(), _live_trailing_sl(), main(), Compute the live trailing SL for an open position using trailing_stops.json.… (+7 more)

### Community 95 - "Community 95"
Cohesion: 0.15
Nodes (16): _classify_structure(), _compute_atr(), _detect_breakout(), _detect_pullback(), _find_swing_highs_lows(), _get_candles_from_ohlcv_1m(), _get_candles_from_price_history(), Classify current swing structure at the most recent candle. Args: highs: sorted… (+8 more)

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (15): cache_age(), cache_fresh(), fetch_and_cache(), fetch_and_cache_positions(), get_cached_positions(), Shared Hyperliquid /info cache — single fetch per 60s, shared across all…, Return open positions from cache if fresh (< _POS_CACHE_TTL old). Returns…, Return seconds since cache was written, or 999 if no cache. (+7 more)

### Community 97 - "Community 97"
Cohesion: 0.20
Nodes (15): delete_project(), get_projects(), health(), load_kanban(), Load kanban data from JSON file. Seed with defaults if missing., Atomically write kanban data to JSON file., Seed kanban.json with current TASKS.md / PROJECTS.md data., Serve the kanban HTML page. (+7 more)

### Community 98 - "Community 98"
Cohesion: 0.19
Nodes (15): evaluate_macd_rules(), _exit_long_signals(), _exit_short_signals(), _flip_long_signals(), _flip_short_signals(), _long_entry_allowed(), MACDState, Given a computed MACDState, evaluate all entry/exit/flip rules. Returns the… (+7 more)

### Community 99 - "Community 99"
Cohesion: 0.21
Nodes (15): _cooldown_ok(), detect_ema_angle(), _ema(), _get_1m_prices(), _log(), _mark_signal(), # NOTE: signal_schema imports this module, so we lazy-import inside functions, Call AFTER add_signal() succeeds to update in-memory cooldown. (+7 more)

### Community 100 - "Community 100"
Cohesion: 0.13
Nodes (7): check_hl_sync(), check_pipeline_service(), main(), Run a named check and return (ok: bool, msg: str, issues: list), Check pipeline via timer (onshot services go inactive after run)., Check hl-sync service (long-running Type=simple service)., run_check()

### Community 101 - "Community 101"
Cohesion: 0.21
Nodes (12): main(), force_atr_update(), _atr_multiplier(), _compute_dynamic_sl(), _compute_dynamic_tp(), _force_fresh_atr(), Canonical k multiplier — must match decider_run._atr_multiplier., Get ATR for a token. Reads from local atr_cache.json FIRST (no rate limits). If… (+4 more)

### Community 102 - "Community 102"
Cohesion: 0.22
Nodes (14): compute_adx_di(), compute_macd(), evaluate_signals(), load_1h_candles(), macd_acceleration(), main(), MACD histogram acceleration: is the histogram momentum increasing? Returns…, Fire LONG when +DI > -DI and ADX > threshold (and rising). Fire SHORT when -DI… (+6 more)

### Community 103 - "Community 103"
Cohesion: 0.17
Nodes (14): detect_ma_fast_cross(), _ema_series(), _get_candles_1m(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for 8/50 MA cross SHORT signals and write to DB. All…, Compute EMA series — returns EMA value at each index (oldest first). Returns a…, Detect 8/50 EMA crossover on 1m candles — SHORT only. Args: token: token symbol…, scan_ma_fast_signals() (+6 more)

### Community 104 - "Community 104"
Cohesion: 0.22
Nodes (14): analyze_distribution(), _apply_changes(), compute_mfe_mae(), get_closed_trades(), log(), _log_session(), main(), Read a constant value from hermes_constants.py. (+6 more)

### Community 105 - "Community 105"
Cohesion: 0.18
Nodes (14): compute_histogram(), ema(), get_1m_closes(), load_token_params(), Compute EMA of data. Seeds with SMA of first n values (consistent with…, Compute MACD histogram. Returns list of hist values (oldest first)., Scan all tokens for MACD 1m crossovers and emit signals. Args: prices_dict:…, Entry point for signals_runner. Returns count of signals emitted. (+6 more)

### Community 106 - "Community 106"
Cohesion: 0.15
Nodes (12): _load_hot_rounds(), Load hot signals based on review_count (ai-decider survival passes). A hot…, can_short(), get_all_tradeable_tokens(), get_token_chain(), is_hyperliquid(), is_solana_only(), Check if token is available on Hyperliquid. (+4 more)

### Community 107 - "Community 107"
Cohesion: 0.23
Nodes (9): align_to_master(), detect_xover(), IMACD, load_token_data(), Detect crossover. prev_h=None means no previous bar., Load all TFs from local DB. Returns dict with ts/cl lists., For each master_ts, return index into sub_ts that was current., Incremental MACD with no side-effect crossover detection. (+1 more)

### Community 108 - "Community 108"
Cohesion: 0.29
Nodes (13): _atr(), _atr_pct(), _bounce_confirmed(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs_with_touch_count(), _find_swing_highs_lows() (+5 more)

### Community 109 - "Community 109"
Cohesion: 0.20
Nodes (13): cancel_orders_for_coin(), close_position_on_hl(), get_hl_open_orders(), get_hl_positions(), get_paper_trades(), main(), open_position_on_hl(), Close a position on HL. (+5 more)

### Community 110 - "Community 110"
Cohesion: 0.21
Nodes (13): _compute_atr(), detect_atr_compression_signal(), _get_candles_5m(), _get_last_state(), Read current compression state from runtime DB cache table., Persist compression state to runtime DB., State-machine ATR compression + breakout detector on 5m candles. States:…, Entry point for signals_runner. Returns count of signals emitted. If… (+5 more)

### Community 111 - "Community 111"
Cohesion: 0.20
Nodes (13): compute_macd_series(), detect_macd_accel(), _ema(), _get_1m_closes(), Detect MACD(8,50,12) crossover with acceleration confirmation. Args: closes:…, Fetch 1m close prices from candles.db (candles_1m table). Returns: list of…, Entry point for signals_runner. Returns count of signals emitted., Return EMA series (oldest first), None for indices < period-1. (+5 more)

### Community 112 - "Community 112"
Cohesion: 0.22
Nodes (12): _compute_atr(), detect_atr_compression_signal(), _get_candles_5m(), _get_last_state(), Read current compression state from runtime DB cache table., Persist compression state to runtime DB., State-machine ATR compression + breakout detector on 5m candles. States:…, Scan all tokens in prices_dict for ATR compression breakouts on 5m. Returns:… (+4 more)

### Community 113 - "Community 113"
Cohesion: 0.21
Nodes (11): cache_data, load_ab_tests(), load_candle_runs(), load_decisions(), load_prediction_accuracy(), load_signal_stats(), Load decisions.jsonl into DataFrame., Load win rate stats from signals DB. (+3 more)

### Community 114 - "Community 114"
Cohesion: 0.23
Nodes (12): get_hotset_status(), get_pipeline_health(), get_recent_signals(), get_signal_performance(), get_token_speed_summary(), get_trades_metrics(), main(), Get token speed distribution. (+4 more)

### Community 115 - "Community 115"
Cohesion: 0.27
Nodes (12): clear_stale(), get_breadcrumbs(), log_fail(), log_start(), log_success(), Return the current breadcrumb state for inspection., Record that a step has started., Record that a step completed successfully. (+4 more)

### Community 116 - "Community 116"
Cohesion: 0.22
Nodes (12): _aggregate_candles(), _compute_bb(), _detect_signal(), _get_ticks(), _in_cooldown(), Check if token+direction is in cooldown., Main scan entry point. Called by signals_runner., Fetch recent ticks for a token from price_history. (+4 more)

### Community 117 - "Community 117"
Cohesion: 0.24
Nodes (12): compute_z(), evaluate_trade(), main(), mtf_alignment(), nearest_5m(), Returns gate result dict for a single trade. entry_ts = unix timestamp of trade…, Z-score of last close vs 20-bar rolling mean. None if < 20 bars., Is z_score becoming more extreme (toward ±2) or reverting toward 0? (+4 more)

### Community 118 - "Community 118"
Cohesion: 0.30
Nodes (11): backtest_token(), compute_bb(), compute_rsi(), detect_bb_bounce(), get_1h_trend(), load_candles_1h(), load_candles_5m(), main() (+3 more)

### Community 119 - "Community 119"
Cohesion: 0.23
Nodes (9): backtest_token(), _calc_pnl(), compute_stats(), fetch_candles_for_backtest(), backtest_guppy.py — Guppy MMA Historical Backtester…, Backtest top tokens by data availability., Fetch all candles for a token in a time range, ordered oldest→newest., Walk through historical candles for a single token using a rolling window. At… (+1 more)

### Community 120 - "Community 120"
Cohesion: 0.29
Nodes (11): calc_ema_series(), ComboStats, find_crosses(), get_candles(), get_tokens(), main(), Fetch 1m candles for a token (oldest first)., EMA series — None before warmup, float after. (+3 more)

### Community 121 - "Community 121"
Cohesion: 0.30
Nodes (11): backtest_signal(), compute_acceleration(), compute_roc(), compute_vol_ratio(), get_candles_4h_with_vol(), main(), Get 4h candles with volume. Returns (ts, close, volume)., Rate of Change: % change over N periods. (+3 more)

### Community 122 - "Community 122"
Cohesion: 0.18
Nodes (9): build_pattern_prompt(), candle_pattern(), detect_support_resistance(), pattern_summary(), Very simple: recent swing highs/lows., Convert pattern list to readable text., Simple RSI-like from recent momentum., Return list of detected patterns in the last 3 candles. (+1 more)

### Community 123 - "Community 123"
Cohesion: 0.30
Nodes (11): _atr(), _atr_pct(), _bounce_confirmed(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs(), _find_swing_highs_lows() (+3 more)

### Community 124 - "Community 124"
Cohesion: 0.20
Nodes (12): _fetch_funding(), _fetch_orderbook(), _fetch_volume(), get_hl_data(), Worker: fetch funding rate for one token., Worker: fetch l2Book spread for one token., Worker: estimate volume ratio from recentTrades., Fetch HL market data in parallel: funding rates, orderbook spread, volume. All… (+4 more)

### Community 125 - "Community 125"
Cohesion: 0.24
Nodes (11): fetch_binance_klines(), get_binance_symbol(), get_db_count(), get_db_max_ts(), insert_candles(), main(), Map HL token to Binance symbol., Fetch klines from Binance. All times in milliseconds. (+3 more)

### Community 126 - "Community 126"
Cohesion: 0.26
Nodes (11): extract_entities(), get_connection(), infer_label(), learn_pair(), node_id(), parse_session_file(), Path, Fast entity extraction, returns list of (concept, label_type). (+3 more)

### Community 127 - "Community 127"
Cohesion: 0.24
Nodes (11): acquire_lock(), append_audit_log(), audit_find_stale(), check_kanban_sync(), main(), Find tasks with stale revisit dates or blocked > 7 days., # TODO: implement, Verify TASKS.md and kanban.json are in sync. (+3 more)

### Community 128 - "Community 128"
Cohesion: 0.24
Nodes (11): acquire_lock(), check_disk_space(), extract_open_tasks(), main(), Check disk space on /root and /tmp. Returns (ok, message)., Acquire a file lock to prevent concurrent runs., Release the file lock., Extract open tasks from TASKS.md. (+3 more)

### Community 129 - "Community 129"
Cohesion: 0.24
Nodes (11): detect_r2_rev_signal(), _get_candles_5m(), _ols_params(), _precompute_x(), Fetch 5m OHLCV candles from candles.db (oldest first). Freshness guard: skip if…, Entry point for signals_runner. Returns count of signals emitted., Compute OLS slope, intercept, R² from a list of prices (oldest first)., Precompute x stats for fast rolling OLS. Call once per window size. (+3 more)

### Community 130 - "Community 130"
Cohesion: 0.30
Nodes (11): _check_divergence(), compute_zscore(), detect_zscore_pump(), _get_1m_prices(), _load_tuner_params(), _log(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Detect z-score momentum signal given pre-fetched price history. Fire when: -… (+3 more)

### Community 131 - "Community 131"
Cohesion: 0.18
Nodes (11): get_hype_meta_batched(), Get meta from shared HL cache (written by price_collector)., get_max_leverage(), Get max leverage for a token from Hyperliquid meta API. Cached for 1 hour to…, get_meta(), Return meta dict — PRIMARY SOURCE is hl_cache.json (written by…, get_hyperliquid_tokens(), get_max_leverage() (+3 more)

### Community 132 - "Community 132"
Cohesion: 0.40
Nodes (10): backtest_token(), compute_bb(), compute_rsi(), detect_bb_bounce(), get_1h_trend(), load_candles_1h(), load_candles_5m(), main() (+2 more)

### Community 133 - "Community 133"
Cohesion: 0.33
Nodes (10): compute_stats(), _ema_series(), find_signals(), get_candles(), get_tokens(), main(), Find MA300 + candle confirmation signals and simulate trades., Compute EMA series — returns EMA value at each index (oldest first). None for… (+2 more)

### Community 134 - "Community 134"
Cohesion: 0.25
Nodes (10): _check_cascade_direction_flip(), _check_macd_rules_flip(), _check_mtf_alignment_flip(), _get_open_positions(), Cascade direction flip: cascade_entry_signal() says cascade is ACTIVE and its…, MACD rules engine flip: macd histogram has turned against our position. Returns…, Read open positions from PostgreSQL brain DB. {TOKEN: direction}., Called by signal_gen.run() every pipeline run. For each open position, run… (+2 more)

### Community 135 - "Community 135"
Cohesion: 0.22
Nodes (10): BREADCRUMB(), breadcrumb_trace(), check_step_health(), get_breadcrumbs_for_step(), get_last_breadcrumbs(), Get the last N breadcrumbs for inspection., Get last N breadcrumbs for a step prefix (e.g. 'signal_gen')., Check if a pipeline step ran recently. Returns: {'healthy': bool, 'last_run':… (+2 more)

### Community 136 - "Community 136"
Cohesion: 0.27
Nodes (10): infer_label(), Infer label type from a concept name string., extract_concepts(), main(), normalize_concept(), Path, Normalize concept name for deduplication. Filters out obvious garbage., Parse a file, extract concepts, learn all pairs within it. (+2 more)

### Community 137 - "Community 137"
Cohesion: 0.25
Nodes (10): detect_r2_rev_signal(), _get_candles_5m(), _ols_params(), _precompute_x(), Fetch 5m OHLCV candles from candles.db (oldest first). Freshness guard: skip if…, Scan pre-filtered tokens for R² mean reversion signals on 5m. All guards…, Compute OLS slope, intercept, R² from a list of prices (oldest first)., Precompute x stats for fast rolling OLS. Call once per window size. (+2 more)

### Community 138 - "Community 138"
Cohesion: 0.25
Nodes (10): detect_r2_short(), _get_candles_1m(), _ols_params(), _precompute_x(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for R² confirmed downtrend signals. All guards…, Compute OLS slope, intercept, R² from a list of prices (oldest first). Returns…, Precompute x stats for fast rolling OLS. Call once per window size. (+2 more)

### Community 139 - "Community 139"
Cohesion: 0.25
Nodes (10): _get_candles_1m(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for support/resistance signals and write to DB. All…, scan_rs_signals(), get_latest_prices_from_candles(), get_open_positions(), is_blacklisted(), main() (+2 more)

### Community 140 - "Community 140"
Cohesion: 0.24
Nodes (10): get_candles(), get_tokens(), main(), Scan all tokens in prices_dict for volume HL signals. Returns count., Entry point for signals_runner. Returns count of signals emitted., Fetch all tokens that have 1m candle data (from signal_schema price list)., Fetch last N 1m candles for token: price from price_history, volume from…, run() (+2 more)

### Community 142 - "Community 142"
Cohesion: 0.29
Nodes (10): classify_sources(), get_recent_trades(), get_signal_sources_for_trade(), pnl_emoji(), Get closed paper trades from brain.trades in the study window., Get the signal sources that contributed to a trade within the window., Separate OpenClaw (mtf-*) from Hermes sources., Build a sortable key string for the source combination. (+2 more)

### Community 143 - "Community 143"
Cohesion: 0.20
Nodes (10): _default_ab_params(), get_ab_params(), get_cached_ab_variant(), load_ab_config(), Get cached A/B variant or select new one, Load A/B test configuration, Select a variant for a given A/B test. Uses Thompson sampling from ab_utils…, Get A/B test parameters for a trade. Returns a dict with all relevant params.… (+2 more)

### Community 144 - "Community 144"
Cohesion: 0.22
Nodes (9): archive_to_json(), build_analysis_db(), get_closed_trades(), get_pg_columns(), get_runtime_signal(), Fetch closed trades from PostgreSQL. Returns list of dicts., Archive trades to gzipped JSON lines (one file per day)., Find the best matching signal from signals_hermes_runtime.db for a trade.… (+1 more)

### Community 145 - "Community 145"
Cohesion: 0.31
Nodes (9): build_prompt(), compute_macd(), compute_rsi(), make_features(), parse_response(), Features from closes up to T-1, used to predict candle T direction., Extract direction from natural language response — tail-biased with regex., run_backtest() (+1 more)

### Community 146 - "Community 146"
Cohesion: 0.24
Nodes (8): _determine_is_closed(), fetch_and_store(), _klines(), Fetch klines from Binance. Returns list of candle dicts or empty list on…, Determine if a candle at timestamp `ts` is closed. Binance klines: the candle…, Main fetch + store loop. Fetches 1m + 5m for all tokens concurrently., Quick sanity check on CHIP candles., verify_chips()

### Community 147 - "Community 147"
Cohesion: 0.20
Nodes (10): Pre-fetch HL volume data for all tokens with open positions. Runs in a…, _warmup_volume_cache(), _fetch_volume_data(), _load_volume_cache(), Load cached volume data. Returns {token: {ts, vol_last, vol_ma, confirmed}}, Save volume cache to disk atomically., Fetch last 24h of 1h candles for token via ccxt+Hyperliquid. Returns {vol_last,…, Pre-fetch HL volume data for a list of tokens — non-blocking. Reads existing… (+2 more)

### Community 148 - "Community 148"
Cohesion: 0.22
Nodes (10): get_available_tokens(), get_candles(), Fetch candle rows from candles.db. interval: '1m', '5m', '15m', '1h', '4h'…, Return list of tokens available in candles_1m., Scan a single token for guppy signal. Returns signal dict or None., Scan all available tokens in candles_1m for guppy signals. Returns list of…, scan_all_tokens(), scan_token() (+2 more)

### Community 149 - "Community 149"
Cohesion: 0.27
Nodes (9): get_ab_variant(), get_cached_ab_variant(), _get_wandb_run(), _load_ab_config(), Shared A/B testing utilities — canonical Thompson sampling implementation. Both…, Lazily initialize W&B run for Hermes A/B tests (offline, project=hermes-ai)., Get A/B variant for test_name, cached globally per test_name. Token and…, Load A/B config from /root/.hermes/config/ab_tests.json. (+1 more)

### Community 150 - "Community 150"
Cohesion: 0.31
Nodes (10): _build_hotset_from_db(), _get_hotset_from_file(), live_macd(), live_rsi(), live_zscore(), _load_prices(), Read the authoritative hot-set from hotset.json (written by…, Load price history for token (module-level memoised, refreshed <60s). (+2 more)

### Community 151 - "Community 151"
Cohesion: 0.22
Nodes (10): _clear_reconciled_token(), _get_reconciled_trade_id(), _load_reconciled_state(), _mark_hl_reconciled(), Load persisted reconciled state from disk., Persist reconciled state to disk, pruning entries older than 24 hours., Record that an HL position has been reconciled to a specific trade_id., Get the trade_id that was reconciled for this HL position, or None. (+2 more)

### Community 152 - "Community 152"
Cohesion: 0.25
Nodes (9): get_calibration_summary(), get_category_multipliers(), get_signal_type_stats(), _get_source_weight(), Query signal_outcomes for per-signal-type win rate stats. Returns dict:…, Human-readable calibration report for all signal types with enough data., Aggregate per-signal-type stats into category multipliers. Returns: {category:…, Return confidence multiplier for (signal_type, source). Two-layer system: 1.… (+1 more)

### Community 153 - "Community 153"
Cohesion: 0.31
Nodes (6): backtest_signal(), compute_accel(), compute_pct_rank(), get_candles(), Acceleration = change in z-score over ACCEL_WINDOW bars., pct_long = % of prices below current price (suppressed = good for LONG).

### Community 154 - "Community 154"
Cohesion: 0.36
Nodes (8): _get_token_data(), get_universe(), load_blacklists(), main(), Load closes + pre-compute z-scores for all lookbacks (one-time per token)., Sweep ALL thresholds × directions for one token, one lookback. Returns list of…, run_lookback(), sweep_combo()

### Community 155 - "Community 155"
Cohesion: 0.25
Nodes (8): acquire_lock(), _get_mtf_macd_summary(), get_prediction_accuracy(), main(), CLI: candle_predictor.py [--nowandb] [--interval 15|60|240] [--minimax], Format MTF MACD data into a readable string for the prompt., Get per-token prediction accuracy for the last 20 predictions., # NOTE: lowered from 40→25 on 2026-04-06 to let new prompt variants accumulate

### Community 156 - "Community 156"
Cohesion: 0.22
Nodes (8): # NOTE: 'vel-hermes' bare sentinel removed — vel-hermes+/vel-hermes- now…, # NOTE: hzscore+,hzscore- merge artifacts are now IMPOSSIBLE because, # NOTE: do NOT use this for PnL calculations — use, # NOTE: signals/rs.py had hardcoded values that diverged from this file., # NOTE: price_history is close-only (open=high=low=close per row), so swing, # NOTE: Lines 373-384 removed 2026-05-06 — were duplicate with inconsistent…, # NOTE: inv-accel-300- is DISABLED (INVERSE_ACCEL_300_MINUS_ENABLED=False #…, # NOTE: momentum+/momentum- had NO Layer 2 kill-switch in signal_schema.py…

### Community 157 - "Community 157"
Cohesion: 0.22
Nodes (8): apply_pnl_ground_truth(), compute_hl_pnl_pct(), pnl_sanity_check(), Compute pnl_pct from HL's unrealized_pnl and position_value. Used when we have…, Apply HL ground truth at close time. When hype_pnl_usdt is available (HL fills…, Check if PnL values are suspicious (>1000% or <-99%). Returns True if PnL is…, Zero out PnL when values are suspicious. Returns (0.0, 0.0, entry_price) to…, zero_suspicious_pnl()

### Community 158 - "Community 158"
Cohesion: 0.33
Nodes (8): get_latest_prices_from_candles(), get_open_positions(), is_blacklisted(), main(), Get the most recent price per token from candles.db., Return token -> direction dict for currently open HL positions., Write a cooldown entry when a trade CLOSES so the same direction cannot re-…, record_cooldown_start()

### Community 159 - "Community 159"
Cohesion: 0.36
Nodes (8): detect_exhaustion(), _ema(), main(), Entry point for signals_runner. Returns count of signals emitted., Compute EMA30 over a list of closing prices., Detect exhaustion reversal signal for a token. exhaustion SHORT: prior…, run(), scan()

### Community 160 - "Community 160"
Cohesion: 0.33
Nodes (8): _get_open_pos(), _get_open_pos_dict(), is_live_trading_enabled(), # NOTE: Do NOT shadow hermes_constants here — import from hermes_constants…, Return {token: direction} for all open positions., Scan all tokens and emit pct-hermes signals for price extremes. Returns: Number…, recent_trade_exists(), run()

### Community 161 - "Community 161"
Cohesion: 0.36
Nodes (7): compute_indicators(), get_atr_at(), get_prices_at(), main(), Get n 1m close prices ending at timestamp ts from price_history., Compute ATR(period) from 5m candles at timestamp ts., Compute z_score, RSI, MACD, BB, momentum from close prices. Returns dict.

### Community 162 - "Community 162"
Cohesion: 0.39
Nodes (7): backtest_combo(), compute_stats(), get_candles(), pop_zscore(), Z-score at idx using window bars ending at idx (not including current bar)., Backtest mtp_zscore for ONE token and parameter combo., run_sweep()

### Community 163 - "Community 163"
Cohesion: 0.46
Nodes (7): backtest_one_token(), compute_stats(), get_all_tokens(), get_candles(), pop_zscore(), run_sweep(), save_partial()

### Community 164 - "Community 164"
Cohesion: 0.39
Nodes (7): backtest_threshold(), get_candles(), main(), Get 4h candles sorted oldest→newest. Returns (ts, close)., Compute rolling z-score with given lookback window., direction: 'positive' = z > threshold (expect reversion DOWN = SHORT)…, rolling_zscore()

### Community 165 - "Community 165"
Cohesion: 0.39
Nodes (7): detect_exhaustion(), _ema(), main(), Scan all tokens (or single token) and emit exhaustion signals. Args: conf_min:…, Compute EMA30 over a list of closing prices., Detect exhaustion reversal signal for a token. exhaustion SHORT: prior…, scan()

### Community 166 - "Community 166"
Cohesion: 0.25
Nodes (8): compute_macd_state(), ema(), get_macd_bullish_score(), get_macd_entry_signal(), Compute EMA of a price list., Compute full MACD state for a token. Args: token: Token symbol (e.g. 'BTC')…, Quick -3 to +3 score for a token. Used by ai_decider weighting., Returns dict with: allowed: bool reason: str state: MACDState Usage: result =…

### Community 167 - "Community 167"
Cohesion: 0.25
Nodes (8): _atr_sl_k_scaled(), _dr_atr(), get_trade_params(), _pm_get_atr(), Fetch ATR(14) for token. Reuses _ATR_CACHE from decider-run if available via…, Local proxy — uses _atr_multiplier from this module (no decider_run dependency)., Scale k_SL by z-score exhaustion + velocity stall + speed. Returns k multiplier…, Compute SL and TP for a new trade. SL is ATR(14)-based via _dr_atr() →…

### Community 168 - "Community 168"
Cohesion: 0.39
Nodes (7): get_net_pnl(), main(), parse_experiment(), Convert PostgreSQL Decimal/None to float., Extract list of (test_name, variant_id) from experiment JSON/string., Compute net PnL after fees., to_f()

### Community 169 - "Community 169"
Cohesion: 0.36
Nodes (7): analyze_group(), classify_signal(), get_trades(), main(), print_result(), Classify a signal string into categories., Analyze a group of trades.

### Community 170 - "Community 170"
Cohesion: 0.43
Nodes (7): disable_signal(), get_signal_performance(), log(), main(), _main_impl(), Query signal_outcomes for 24h performance (dedup, trade_id IS NOT NULL)., Disable a signal by setting its flag to False in hermes_constants.py.

### Community 171 - "Community 171"
Cohesion: 0.36
Nodes (7): detect_trend_purity(), _ema(), Entry point for signals_runner. Returns count of signals emitted., Compute EMA30 over a list of closing prices., Detect trend purity signal for a token. LONG: price consistently above EMA30…, run(), scan()

### Community 172 - "Community 172"
Cohesion: 0.25
Nodes (8): check_pipeline_not_stuck(), check_stale_locks(), _get_lock_holder_pid(), _pid_alive(), Check if the pipeline lock indicates a stuck pipeline. NOTE (2026-07-13):…, Check if a process is alive., Return list of PIDs holding a lock (via lsof)., Check all Hermes lock files. Fail if > threshold AND holder process is dead.…

### Community 173 - "Community 173"
Cohesion: 0.39
Nodes (7): detect_trend_purity(), _ema(), main(), Scan all tokens (or single token) and emit trend_purity signals. Args:…, Compute EMA30 over a list of closing prices., Detect trend purity signal for a token. LONG: price consistently above EMA30…, scan()

### Community 174 - "Community 174"
Cohesion: 0.43
Nodes (6): characterize(), cluster(), fetch(), main(), Fetch closed trades from PostgreSQL with duration computed., Find clusters: same token+direction within 5min of each other.

### Community 175 - "Community 175"
Cohesion: 0.48
Nodes (6): fetch_audit_lines(), fetch_price_around(), fetch_signal(), fetch_trade(), main(), Return audit-log lines that mention the trade's id within +/- around_seconds of…

### Community 176 - "Community 176"
Cohesion: 0.43
Nodes (6): fetch_1m_klines(), hl_to_binance(), main(), process_token(), Fetch 1m klines from Binance covering last 48h. Returns [(ts, close)]., Fetch and store 1m candles for one token. Returns (token, rows_inserted,…

### Community 177 - "Community 177"
Cohesion: 0.43
Nodes (6): backfill_batch(), fetch_klines(), hl_to_binance(), main(), Map Hyperliquid token → Binance symbol., Fetch 1h klines from Binance. Returns [(timestamp_sec, close_price)].

### Community 178 - "Community 178"
Cohesion: 0.52
Nodes (6): call_minimax(), compute_indicators(), load_candles(), load_price_history(), main(), parse_response()

### Community 179 - "Community 179"
Cohesion: 0.48
Nodes (6): backtest_momentum_cross(), get_candles(), main(), Returns list of (z, prev_z) tuples for each price point. prev_z = z from…, LONG: z crosses above +threshold (prev_z < threshold, z >= threshold) SHORT: z…, rolling_zscore()

### Community 180 - "Community 180"
Cohesion: 0.38
Nodes (5): close_hl(), fix_and_close_db(), Market close on Hyperliquid. Returns True on success., Fix entry_price if needed, mark closed in DB. Returns trade info., ts()

### Community 181 - "Community 181"
Cohesion: 0.43
Nodes (5): compute_adx(), ema(), Compute ADX using Wilder smoothing., run_backtest(), true_range()

### Community 182 - "Community 182"
Cohesion: 0.38
Nodes (6): _get_returns(), monte_carlo_gate(), monte_carlo_gate_oracle(), Shadow-mode wrapper — always allows but logs what WOULD have been blocked. Use…, Fetch last N trade returns from signal_outcomes., Run Monte Carlo simulation to estimate if a signal type is still profitable.…

### Community 183 - "Community 183"
Cohesion: 0.29
Nodes (7): Confidence Paradox, effective_conf, hzscore Signal, pct-hermes Signal, Penalty System, trap_penalty, vel-hermes Signal

### Community 184 - "Community 184"
Cohesion: 0.43
Nodes (6): fmt(), get_futures_symbols(), get_klines(), main(), Fetch all USDT-margined perpetual futures symbols. Retries on truncate., Fetch last N 1-minute klines. Retries on rate limit or truncate.

### Community 185 - "Community 185"
Cohesion: 0.38
Nodes (6): apply_to_confidence(), get_directional_vol(), _neutral_result(), Return a neutral result when we can't get data., Convenience wrapper: fetch directional volume and return (adjusted_confidence,…, Fetch candles and return directional volume analysis. Args: token: Trading…

### Community 186 - "Community 186"
Cohesion: 0.52
Nodes (6): compute_z(), evaluate_trade_1m(), main(), Uses price_history (1m resolution, timestamps in seconds). Speed: % change over…, wave_phase_from_snapshot(), z_trajectory()

### Community 187 - "Community 187"
Cohesion: 0.33
Nodes (6): get_hype_all_mids_batched(), Update current_price for all open trades using Hyperliquid prices, Get all mids from shared HL cache (written by price_collector)., update_trade_prices(), get_allMids(), Return allMids dict — PRIMARY SOURCE is hl_cache.json (written by…

### Community 188 - "Community 188"
Cohesion: 0.53
Nodes (5): characterize(), fetch(), main(), Returns (sl_pct_with_sign_convention, is_wrong_side)., sl_pct_and_side()

### Community 189 - "Community 189"
Cohesion: 0.33
Nodes (4): find_cross_bar(), find_latest_below_bar(), Find the latest bar where price was below EMA, starting from start_idx and…, Find the cross bar (most recent transition to direction).

### Community 190 - "Community 190"
Cohesion: 0.53
Nodes (5): backfill_symbol(), _cached_request(), fetch_klines_backward(), main(), Fetch klines from Binance going BACKWARD from current_oldest_ts_ms. Returns…

### Community 191 - "Community 191"
Cohesion: 0.33
Nodes (6): add_to_watch_list(), get_effective_tokens(), load_watch_list(), Load dynamically-added tokens (from traded coins)., Add a token to the watch list (called when a coin is traded)., TOP_TOKENS + dynamically watched tokens (recently traded).

### Community 193 - "Community 193"
Cohesion: 0.53
Nodes (5): PYTHONPATH, dashboard.sh script, start(), status(), stop()

### Community 194 - "Community 194"
Cohesion: 0.33
Nodes (6): _acquire_lock_with_heartbeat(), _is_primary_alive(), Check if the primary guardian process is still alive by reading its PID from…, Write heartbeat with PID so other guardians can detect if we're alive., Acquire lock using flock + heartbeat file for stale lock detection., _write_heartbeat()

### Community 195 - "Community 195"
Cohesion: 0.47
Nodes (5): backtest(), ema(), Return (win_rate, avg_pnl, n_signals) for SHORT signals only., Load candles from DB, sweep params, store best config per token., run_sweep()

### Community 196 - "Community 196"
Cohesion: 0.33
Nodes (6): Bayesian Optimization, qwen2.5:1.5b, W&B Sweep Configuration, Hardware Constraints, qwen2.5:1.5b Production, qwen2.5:3b Not Viable

### Community 197 - "Community 197"
Cohesion: 0.47
Nodes (5): get_tf_tables(), main(), Return {interval: table_name} for all candle tables in candles.db., Trim a single table: keep max_allowed newest rows per token., trim_table()

### Community 198 - "Community 198"
Cohesion: 0.47
Nodes (5): _get_token(), github_api(), main(), Get token from _secrets first (primary), then ~/.netrc fallback., sh()

### Community 199 - "Community 199"
Cohesion: 0.50
Nodes (3): archive_month(), Write rows to a gzipped JSONL file for the given year/month., run_archive()

### Community 200 - "Community 200"
Cohesion: 0.60
Nodes (4): fetch_klines(), hl_to_binance(), main(), Fetch 1h klines from Binance. Returns [(timestamp_sec, close)].

### Community 201 - "Community 201"
Cohesion: 0.50
Nodes (4): backtest_token(), ols_slope_r2(), Compute slope and R² of closes (y) vs index (x)., Backtest R² regression signal on one token's close series. direction: 'long' or…

### Community 202 - "Community 202"
Cohesion: 0.40
Nodes (4): wandb-sync.sh script, WANDB_API_KEY, WANDB_DIR, WANDB_MODE

### Community 204 - "Community 204"
Cohesion: 0.50
Nodes (4): decide_inversion(), get_accuracy_stats(), Get direction-specific accuracy for a token, optionally filtered by…, Decide whether to INVERT a prediction based on historical accuracy. Returns…

### Community 205 - "Community 205"
Cohesion: 0.50
Nodes (4): _fetch_trades_sync(), prefetch_volume(), Fetch recentTrades for one token (called from background thread)., Batch-fetch recentTrades for all tokens in parallel using threads. Runs in…

### Community 206 - "Community 206"
Cohesion: 0.50
Nodes (3): Detect bollinger_squeeze LONG signals. Returns list of signal dicts., # TODO: Implement real-time detection logic, run()

### Community 207 - "Community 207"
Cohesion: 0.50
Nodes (4): _call_minimax(), _get_minimax_client(), Build minimax OpenAI-compatible client from auth.json., Call minimax MiniMax-M2 model. Returns content or empty string on failure.

### Community 208 - "Community 208"
Cohesion: 0.67
Nodes (3): backtest(), ols_slope_r2(), Mean reversion entry: enter when price has deviated significantly from…

### Community 209 - "Community 209"
Cohesion: 0.67
Nodes (3): backtest_fast(), ols_slope_r2(), Fast version: skip SAMPLE_RATE bars.

### Community 210 - "Community 210"
Cohesion: 0.50
Nodes (4): get_token_exchange(), is_sol_token(), Check if token is Solana-only, Get exchange for token

### Community 212 - "Community 212"
Cohesion: 0.67
Nodes (3): main(), Run checks. If heal=True, apply fixes for failed checks., run_checks()

## Knowledge Gaps
- **14 isolated node(s):** `PYTHONPATH`, `start-litellm.sh script`, `wandb-sync.sh script`, `WANDB_API_KEY`, `WANDB_DIR` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `log()` connect `AI Decider & Cascade Flip` to `Checkpoint & Sync Utils`, `Community 128`, `MACD Acceleration Signals`, `Acceleration 300 Signals`, `Decider Run (AI Decision)`, `Exchange & Position Manager`, `Pump Hunter`, `Community 142`, `Blacklist & Risk Management`, `Brain Memory & Tags`, `Community 148`, `Hot Set Management`, `Community 151`, `Community 25`, `Community 155`, `Community 30`, `Community 34`, `Community 163`, `Community 35`, `Community 39`, `Community 52`, `Community 53`, `Community 55`, `Community 57`, `Community 60`, `Community 191`, `Community 63`, `Community 64`, `Community 194`, `Community 67`, `Community 66`, `Community 78`, `Community 79`, `Community 80`, `Community 90`, `Community 100`, `Community 101`, `Community 109`, `Community 127`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `add_signal()` connect `Signal Schema & Enrichment` to `MACD Acceleration Signals`, `HH/HL & MA Cross Signals`, `Acceleration 300 Signals`, `Community 129`, `Community 130`, `Community 134`, `Exchange & Position Manager`, `Community 137`, `Community 138`, `Community 139`, `Cooldown & Early Fires`, `Community 140`, `Price Collection & Caching`, `Regime Scanner Logic`, `Context Gate & Market`, `Community 27`, `Community 159`, `Community 160`, `Community 35`, `Community 36`, `Community 165`, `Community 37`, `Community 38`, `Community 42`, `Community 43`, `Community 171`, `Community 45`, `Community 173`, `Community 50`, `Community 51`, `Community 182`, `Community 54`, `Community 185`, `Community 57`, `Community 61`, `Community 62`, `Community 64`, `Community 65`, `Community 73`, `Community 75`, `Community 76`, `Community 86`, `Community 95`, `Community 99`, `Community 103`, `Community 105`, `Community 110`, `Community 111`, `Community 112`, `Community 116`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `get_all_latest_prices()` connect `HH/HL & MA Cross Signals` to `MACD Acceleration Signals`, `Community 129`, `Acceleration 300 Signals`, `Signal Schema & Enrichment`, `Community 137`, `Cooldown & Early Fires`, `Community 138`, `Community 140`, `Price Collection & Caching`, `Context Gate & Market`, `Community 27`, `Community 160`, `Community 36`, `Community 37`, `Community 42`, `Community 43`, `Community 45`, `Community 50`, `Community 51`, `Community 54`, `Community 187`, `Community 62`, `Community 65`, `Community 73`, `Community 75`, `Community 76`, `Community 96`, `Community 105`, `Community 110`, `Community 111`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **What connects `PYTHONPATH`, `start-litellm.sh script`, `wandb-sync.sh script` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Checkpoint & Sync Utils` be split into smaller, more focused modules?**
  _Cohesion score 0.027264920566766854 - nodes in this community are weakly interconnected._
- **Should `MACD Acceleration Signals` be split into smaller, more focused modules?**
  _Cohesion score 0.034556396816152204 - nodes in this community are weakly interconnected._
- **Should `HH/HL & MA Cross Signals` be split into smaller, more focused modules?**
  _Cohesion score 0.04561101549053356 - nodes in this community are weakly interconnected._