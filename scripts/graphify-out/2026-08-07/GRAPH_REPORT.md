# Graph Report - scripts  (2026-08-06)

## Corpus Check
- 278 files · ~454,300 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4395 nodes · 8650 edges · 256 communities (228 shown, 28 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0ab91381`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hl-sync-guardian.py
- add_signal
- get_momentum_stats
- hyperliquid_exchange.py
- signal_schema.py
- decider_run.py
- __init__.py
- self_close_watcher.py
- candle_predictor.py
- atr_compression.py
- log
- mtf_macd_tuner.py
- hh_hl.py
- smoke_test.py
- pump_hunter.py
- hl_fill_monitor.py
- wyckoff.py
- signal_analyst.py
- guppy.py
- pattern_scanner.py
- brain.py
- paths.py
- HebbianEngine
- _get_conn
- position_manager.py
- guppy_signals.py
- zscore_momentum.py
- run_guppy_signals.py
- backtest_mtf_macd.py
- close_position
- mtf_macd_backtest.py
- signal_compactor.py
- rs.py
- unified_scanner.py
- SpeedTracker
- cascade_flip.py
- self_learner.py
- wave_backtest.py
- ai_decider.py
- breakout_engine.py
- signals/ma_cross_5m.py
- ma_cross_5m.py
- get_cooldown
- hermes-trades-api.py
- oc_signal_importer.py
- ab_optimizer.py
- signal_quality_tracker.py
- run
- blacklist_tester.py
- price_collector.py
- rs_signals.py
- signal_researcher.py
- wasp.py
- backtest_hwave_bonus_thresholds.py
- init_db
- backtest_ema20_50
- hl_leaderboard.py
- tl_break.py
- sync_open_trades.py
- 4h_regime_scanner.py
- hype_cache.py
- checkpoint_utils.py
- hl_wallet_discovery.py
- strategy_optimizer.py
- audit_logger.py
- backtest_hh_hl.py
- context-compactor.py
- scrape_all_sources
- ma300_candle_confirm_signals.py
- signal_importer.py
- 15m_regime_scanner.py
- log_error
- backtest_gap300.py
- bug_hunter.py
- candle_db.py
- scan_gap300_state
- backtest_breakout.py
- backtest_tl_break.py
- detect_ema9_sma20_cross
- counter_flip.py
- profit_monster.py
- signal_lifecycle.py
- get_realized_pnl
- candle_tuner.py
- log_event
- hh_hl_signals.py
- record_cooldown_start
- ab_learner.py
- vortex_break.py
- top150.py
- signal_auditor.py
- signal_quality_autotuner.py
- signal_rotator.py
- fast_momentum.py
- away_detector.py
- cascade_flip_helpers.py
- error_analyzer.py
- hebbian_learner.py
- Plan: Fix the Penalty System That Inverts Signal Quality
- macd_rules.py
- kanban_api.py
- evaluate_macd_rules
- detect_ema9_sma20_cross
- ema_angle.py
- sync_kanban_tasks.py
- trading-checklist.py
- backtest_adx_macd.py
- param_auto_tuner.py
- pipeline_watchdog.py
- is_solana_only
- bollinger_squeeze.py
- run_backtest
- backtest_rs_tiers.py
- rule_based_context_gate
- mtf_macd.py
- macd_accel.py
- atr_compression_signals.py
- hermes-dashboard.py
- hebbian_session_learner.py
- hl_copy_signal.py
- is_cooldown_active
- obs_dashboard.py
- pipeline_breadcrumbs.py
- r2_trend_signals.py
- backtest_ma_cross.py
- evaluate_trade
- backtest_bb_bounce.py
- backtest_guppy.py
- backtest_signal
- backtest_patterns.py
- detect_rs
- fetch_binance_candles.py
- hebbian_seed_sessions.py
- hermes-brain-sync.py
- hl_copy_tui.py
- ma_cross.py
- r2_rev.py
- backtest_bb_bounce_v2.py
- backtest_ma300_candle_confirm.py
- run_pipeline.py
- compute_mtf_macd_alignment
- error_breadcrumbs.py
- hyperliquid-trader.py
- r2_rev_5m_signals.py
- study_winning_combos.py
- get_ab_params
- archive-trades.py
- backtest_candle.py
- binance_volume_collector.py
- daily_git_commit.py
- _seed_universe_candles
- fetch_hl_volume.py
- scan_for_signals
- zscore_pump.py
- backtest_combined_momentum_mean_reversion.py
- backtest_zscore_pump_full.py
- get_db
- exhaustion.py
- _secrets.py
- backtest_mtp_zscore.py
- backtest_threshold
- process_delayed_entries
- .learn_pair
- rebuild_ab_results.py
- rsi_backtest.py
- signal_decay_detector.py
- check_pipeline_not_stuck
- find_abandoned_trades.py
- trace_trade.py
- backfill_price_history_48h.py
- backfill_prices.py
- backtest_minimax.py
- backtest_momentum_cross
- graceful_close.py
- grid_backtest.py
- _close_trade_impl
- monte_carlo_gate
- gap300_5m_signals.py
- volume_alert.py
- get_directional_vol
- evaluate_trade_1m
- detect_ma_100_signal
- abandoned_trade_root_cause.py
- simulate_accel_300_signal.py
- backfill_candle_files.py
- check_new_trades.py
- dashboard.sh
- hermes_ab_utils.py
- _acquire_lock_with_heartbeat
- backtest
- Ollama Model Benchmarks
- get_trade_history
- backtest_mtp_zscore_full.py
- trim_candle_files.py
- update-git.py
- fetch_klines
- backtest_token
- hermes_file_lock.py
- wandb-sync.sh
- analyze_24h_streaks_and_path.py
- get_ab_variant
- scan
- trend_purity_signals.py
- volume_hl_signals.py
- main
- _call_minimax
- backtest
- backtest_fast
- sweep_r2_5m.py
- start-litellm.sh
- detect_ma_100_signal
- audit_dependencies.py
- get_embedding
- store_thought
- .recall
- detect_macd_accel
- archive-signals.py
- _aggregate_5m.py
- get_fast_group_direction
- _fetch_trades_sync
- run_checks
- check_ceo_timer
- check_hl_sync_active
- check_kill_switches_working
- check_new_signals_generating
- check_no_flapping
- check_obs_metrics_fresh
- check_openmemory_accessible
- check_pattern_scanner_sources
- check_pipeline_log_errors
- check_pipeline_step_timings
- check_price_data_fresh
- check_profit_monster_fires
- check_pump_hunter_log
- check_pump_hunter_positions
- check_signal_db
- check_signal_decay_detector
- check_signal_win_rate
- check_token_speed_tracker
- check_trade_frequency
- check_trading_timers
- check_trailing_stops_exists
- _fix_stale_locks

## God Nodes (most connected - your core abstractions)
1. `log()` - 266 edges
2. `add_signal()` - 154 edges
3. `get_all_latest_prices()` - 95 edges
4. `price_age_minutes()` - 77 edges
5. `get_open_positions()` - 63 edges
6. `FileLock` - 60 edges
7. `init_db()` - 59 edges
8. `recent_trade_exists()` - 47 edges
9. `run()` - 47 edges
10. `is_delisted()` - 44 edges

## Surprising Connections (you probably didn't know these)
- `_wait_for_hl_close()` --indirect_call--> `_wait_for_position_closed()`  [INFERRED]
  cascade_flip.py → hl-sync-guardian.py
- `cascade_flip()` --indirect_call--> `_clear_reconciled_token()`  [INFERRED]
  cascade_flip.py → hl-sync-guardian.py
- `SetupStats` --uses--> `HebbianEngine`  [INFERRED]
  decider_run.py → hebbian_engine.py
- `SetupStats` --uses--> `FileLock`  [INFERRED]
  decider_run.py → hermes_file_lock.py
- `SetupStats` --uses--> `SpeedTracker`  [INFERRED]
  decider_run.py → speed_tracker.py

## Import Cycles
- None detected.

## Communities (256 total, 28 thin omitted)

### Community 0 - "hl-sync-guardian.py"
Cohesion: 0.03
Nodes (134): FileLock, Exclusive flock context manager with retry. Args: lockname: Base name for…, add_orphan_trade(), _add_to_kill_switch(), _check_and_close_breached_trades(), _check_and_execute_flip(), _check_hard_stops(), _check_stale_rotation() (+126 more)

### Community 1 - "add_signal"
Cohesion: 0.03
Nodes (148): detect_accel_300(), _ema_series(), _get_1m_prices(), _log(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Write to both stdout and signals.log., Detect persistent gap above EMA(300) with growing gap. Fire when ALL of these…, Scan tokens for accel_300 signals. All guards (blacklists, open positions,… (+140 more)

### Community 2 - "get_momentum_stats"
Cohesion: 0.06
Nodes (50): get_opposite_direction_cooldown_hours(), Return hours remaining on the OPPOSITE direction's cooldown. Used by scanner to…, compute_regime(), compute_score(), compute_zscore_percentile(), detect_spike(), ema(), get_momentum_stats() (+42 more)

### Community 3 - "hyperliquid_exchange.py"
Cohesion: 0.03
Nodes (114): _place_or_replace_tp(), Place a new TP order if none exists, or replace the existing TP order. Returns…, close_brain_trade(), get_brain_positions(), get_brain_trade_by_token(), get_hot_tokens(), get_hype_positions(), get_recent_signal_tokens() (+106 more)

### Community 4 - "signal_schema.py"
Cohesion: 0.03
Nodes (99): compute_all_indicators(), compute_macd(), compute_rsi(), compute_zscore(), _db_cursor(), _enrich_indicators(), get_all_latest_prices(), get_latest_price() (+91 more)

### Community 5 - "decider_run.py"
Cohesion: 0.06
Nodes (41): _check_counter_trend_trap(), _check_hotset_cooldown(), context_gate(), _ctx_load_cache(), _ctx_save_cache(), _get_hotset_approval_rate(), _get_hotset_last_updated(), _get_token_zscore() (+33 more)

### Community 6 - "__init__.py"
Cohesion: 0.06
Nodes (41): # NOTE: 'vel-hermes' bare sentinel removed — vel-hermes+/vel-hermes- now…, # NOTE: hzscore+,hzscore- merge artifacts are now IMPOSSIBLE because, # NOTE: do NOT use this for PnL calculations — use, # NOTE: signals/rs.py had hardcoded values that diverged from this file., # NOTE: price_history is close-only (open=high=low=close per row), so swing, # NOTE: Lines 373-384 removed 2026-05-06 — were duplicate with inconsistent…, # NOTE: inv-accel-300- is DISABLED (INVERSE_ACCEL_300_MINUS_ENABLED=False ) but…, # NOTE: momentum+/momentum- had NO Layer 2 kill-switch in signal_schema.py… (+33 more)

### Community 7 - "self_close_watcher.py"
Cohesion: 0.06
Nodes (52): cache_age(), cache_fresh(), get_atr(), ATR cache — persistent file + in-memory ATR cache with 300s TTL. Survives…, Return seconds since cache was written, or 999 if no cache., True if cache exists and is within TTL., Read ATR cache from disk. Returns {token: {atr, ts}} or empty dict., Write ATR cache to disk atomically under file lock. (+44 more)

### Community 8 - "candle_predictor.py"
Cohesion: 0.05
Nodes (60): acquire_lock(), add_to_watch_list(), build_ohlcv(), build_prediction_prompt(), compute_macd_ohlc(), compute_mtf_macd(), compute_rsi_ohlc(), decide_inversion() (+52 more)

### Community 9 - "atr_compression.py"
Cohesion: 0.21
Nodes (13): _compute_atr(), detect_atr_compression_signal(), _get_candles_5m(), _get_last_state(), Read current compression state from runtime DB cache table., Persist compression state to runtime DB., State-machine ATR compression + breakout detector on 5m candles. States:…, Entry point for signals_runner. Returns count of signals emitted. If… (+5 more)

### Community 10 - "log"
Cohesion: 0.04
Nodes (73): _get_signal_streak(), Get cached signal streak, refreshed every 5 minutes (per-key TTL)., Record outcome when a trade closes. Updates both the JSON file (legacy) and the…, record_ab_trade_closed(), close_brain(), close_paper(), get_exit_price(), main() (+65 more)

### Community 11 - "mtf_macd_tuner.py"
Cohesion: 0.07
Nodes (54): build_15m_candles_from_1h(), _cached_request(), compute_macd(), ema(), _fast_backtest(), fetch_15m_klines(), fetch_1h_klines(), fetch_4h_klines() (+46 more)

### Community 12 - "hh_hl.py"
Cohesion: 0.17
Nodes (18): _classify_structure(), _compute_atr(), _detect_breakout(), _detect_pullback(), _find_swing_highs_lows(), _get_candles_from_ohlcv_1m(), _get_candles_from_price_history(), Classify current swing structure at the most recent candle. Args: highs: sorted… (+10 more)

### Community 14 - "pump_hunter.py"
Cohesion: 0.07
Nodes (51): add_pump_position(), _cancel_brain_record(), check_pump_exits(), close_all(), _close_brain_record(), _create_brain_record(), detect_vol_explosion(), execute_pump_trade() (+43 more)

### Community 15 - "hl_fill_monitor.py"
Cohesion: 0.14
Nodes (20): detect_new_trades(), get_active_traders(), get_fills_since(), get_trader_positions(), _hl_info(), load_last_fills(), log_fills_batch(), monitor_once() (+12 more)

### Community 16 - "wyckoff.py"
Cohesion: 0.07
Nodes (44): detect_capitulation(), detect_extended_move(), detect_higher_low(), detect_reversal_quality(), detect_sharp_reversal(), Detect higher low formation (bullish divergence after downtrend). Looks for: -…, Detect sharp reversal candle (strong momentum shift). A sharp reversal has: - A…, Master function: detect high-probability reversal setups. Combines all pattern… (+36 more)

### Community 17 - "signal_analyst.py"
Cohesion: 0.07
Nodes (45): analyze_patterns(), extract_lesson(), generate_reflection(), get_lessons(), _load_decisions(), _log(), log_decision(), Update decision with trade outcome after close. (+37 more)

### Community 18 - "guppy.py"
Cohesion: 0.07
Nodes (45): _compute_confidence(), compute_ema(), _compute_ema_mid_history(), compute_group_emas(), detect_cross(), detect_cross_with_setup(), detect_expansion(), detect_guppy_exit() (+37 more)

### Community 19 - "pattern_scanner.py"
Cohesion: 0.09
Nodes (40): load_prices(), Load 1m close prices for a token, oldest first. Last N days only., Run backtest across all tokens and flag types., run_backtest(), _atr_1m(), _atr_from_closes(), detect_ascending_triangle(), detect_bear_flag() (+32 more)

### Community 20 - "brain.py"
Cohesion: 0.15
Nodes (20): trade_open_attempt(), trade_open_failed(), trade_open_success(), add_tag(), add_trade(), get_db_connection(), get_related_thoughts(), get_stats() (+12 more)

### Community 21 - "paths.py"
Cohesion: 0.07
Nodes (17): migrate_is_closed(), Add is_closed=1 to all existing candles_1m rows that lack the column., backfill_tf(), main(), Backfill all historical closed windows for one timeframe. Chunks the backfill…, Database configuration for Hermes trading system. Single source of truth for…, main(), Run live trading via decider_run.py with --live flag (+9 more)

### Community 22 - "HebbianEngine"
Cohesion: 0.14
Nodes (8): main(), HebbianEngine, Create schema if not exists., Add or update a session summary row. Returns row id. Fix 4 (2026-06-24):…, Find sessions that touched this file. Strips .py suffix and matches against…, Find sessions that discussed this coin ticker., Find sessions by discussion_type or summary text match., Dangerous: wipe all data.

### Community 23 - "_get_conn"
Cohesion: 0.09
Nodes (36): clear_hotset(), count_signals(), main(), purge_signals(), run_ai_decider(), cleanup_stale_approved(), clear_cooldown_entry(), get_approved_signals() (+28 more)

### Community 24 - "position_manager.py"
Cohesion: 0.03
Nodes (123): main(), READ-ONLY hot-set enforcer (defunct approval logic — signal_compactor.py is the…, _run_hot_set(), Direction, force_atr_update(), Log an A/B test outcome to W&B (offline) for visual comparison. Also appends a…, record_ab_outcome(), get_open_hype_positions() (+115 more)

### Community 25 - "guppy_signals.py"
Cohesion: 0.10
Nodes (33): _compute_confidence(), compute_ema(), _compute_ema_mid_history(), compute_group_emas(), detect_cross(), detect_cross_with_setup(), detect_expansion(), detect_guppy_exit() (+25 more)

### Community 26 - "zscore_momentum.py"
Cohesion: 0.08
Nodes (37): _backtest_params(), clear_cache(), compute_zscore(), _fast_zscore(), _get_1m_atr(), get_all_token_prices(), get_all_token_prices_full(), _get_latest_prices() (+29 more)

### Community 27 - "run_guppy_signals.py"
Cohesion: 0.10
Nodes (33): add_position(), check_exits(), close_all_positions(), _close_brain_record(), cmd_close_all(), cmd_monitor(), cmd_scan(), cmd_status() (+25 more)

### Community 28 - "backtest_mtf_macd.py"
Cohesion: 0.09
Nodes (24): backtest_token(), evaluate_entry_at(), evaluate_exit_at(), fetch_binance_backward(), fetch_token_candles(), IncrementalMACD, load_local_candles(), MultiTimeFrameMACD (+16 more)

### Community 29 - "close_position"
Cohesion: 0.14
Nodes (21): close_position(), filter_losing_positions(), get_last_run_ts(), get_losing_positions(), load_config(), Return True if enough minutes have passed since last_run_ts., Return list of dicts for open positions with pnl_pct < 0., Compute live pnl_pct from entry_price vs current_price and filter to loss range. (+13 more)

### Community 30 - "mtf_macd_backtest.py"
Cohesion: 0.11
Nodes (32): analyze(), build_filter_grid(), check_exit(), check_exit_4h_regime(), check_exit_any_flip(), check_exit_both_4h1h(), check_exit_histogram_flip(), compute_macd_state() (+24 more)

### Community 31 - "signal_compactor.py"
Cohesion: 0.12
Nodes (21): _do_purge(), _enrich_and_write_signals(), _get_opposing_penalty(), get_regime_1m(), _get_source_weight(), _get_token_wr(), _purge_executed_signals(), Get 1m regime from linear regression of last 50 1m candles. Returns… (+13 more)

### Community 32 - "rs.py"
Cohesion: 0.09
Nodes (33): _atr(), _atr_pct(), _bounce_confirmation(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs_signal(), _find_swing_highs_lows() (+25 more)

### Community 33 - "unified_scanner.py"
Cohesion: 0.09
Nodes (34): get_meta(), Return meta dict — PRIMARY SOURCE is hl_cache.json (written by…, add_all_signals(), get_cached_indicators(), get_cached_prices(), get_fear(), get_gateio_rsi(), get_gateio_signals() (+26 more)

### Community 34 - "SpeedTracker"
Cohesion: 0.09
Nodes (18): _get_speed_tracker(), get_all_speeds(), get_fastest_tokens(), get_tracker(), _now_ts(), speed_tracker.py — Token speed, velocity, acceleration, and momentum…, Fetch current prices + recent 5m candle history from local DB, compute all…, Returns full dict of token → speed data (from last update). (+10 more)

### Community 35 - "cascade_flip.py"
Cohesion: 0.15
Nodes (20): cascade_flip(), _close_paper_position(), _get_db_connection(), insert_post_flip_trade(), Synchronously insert a DB entry for a position opened via cascade flip. Sets…, _load_flip_counts(), Get a SQLite connection to the runtime DB., Close paper trade in DB. Returns True on success. (+12 more)

### Community 36 - "self_learner.py"
Cohesion: 0.12
Nodes (29): _adjust_param(), analyze_and_adjust(), _calculate_pnl(), _calculate_wr(), _check_daily_limit(), _detect_decay(), _find_weakest_param(), _get_current_value() (+21 more)

### Community 37 - "wave_backtest.py"
Cohesion: 0.12
Nodes (27): check_entry(), check_exit(), check_guard_block(), compute_atr(), compute_macd_state(), ema(), generate_all_strategies(), init_results_db() (+19 more)

### Community 38 - "ai_decider.py"
Cohesion: 0.05
Nodes (39): acquire_lock(), clear_ab_cache(), _ema(), execute_trade(), get_calibration_summary(), get_category_multipliers(), get_hype_all_mids_batched(), get_hype_meta_batched() (+31 more)

### Community 39 - "breakout_engine.py"
Cohesion: 0.11
Nodes (27): compute_atr(), compute_levels(), detect_breakout(), detect_breakout_direction(), detect_breakout_for_token(), detect_compression(), detect_volume_pop(), get_candles() (+19 more)

### Community 40 - "signals/ma_cross_5m.py"
Cohesion: 0.12
Nodes (26): _aggregate_5m_from_1m(), _backtest_pair(), detect_cross(), _ema(), _ema_series(), get_5m_candles(), init_tuner_db(), load_params() (+18 more)

### Community 41 - "ma_cross_5m.py"
Cohesion: 0.12
Nodes (23): _aggregate_5m_from_1m(), _backtest_pair(), detect_cross(), _ema(), _ema_series(), get_5m_candles(), init_tuner_db(), load_params() (+15 more)

### Community 42 - "get_cooldown"
Cohesion: 0.07
Nodes (44): get_cooldown(), _is_cooldown_key_active(), Helper: check if a specific token:direction key is active. When checking…, detect_accel_300(), detect_breakout(), detect_velocity_ignition(), _ema_series(), _get_1m_prices() (+36 more)

### Community 43 - "hermes-trades-api.py"
Cohesion: 0.14
Nodes (25): _atomic_write(), _build_hotset_from_db(), _build_open_trades(), _get_current_price(), _get_hotset_from_file(), get_signals_from_db(), get_trades(), live_macd() (+17 more)

### Community 44 - "oc_signal_importer.py"
Cohesion: 0.12
Nodes (25): _compute_macd_histograms(), _compute_rsi(), _compute_rsi_per_tf(), _ema(), _fetch_candles(), _get_fresh_price(), import_mtf_macd_signals(), import_pending_signals() (+17 more)

### Community 45 - "ab_optimizer.py"
Cohesion: 0.12
Nodes (24): _db_conn(), epsilon_greedy_pick(), evolve_test(), get_all_results(), get_best_variant_for_test(), get_evolution_snapshot(), get_exploration_variant_for_test(), _get_variant_stats() (+16 more)

### Community 46 - "signal_quality_tracker.py"
Cohesion: 0.17
Nodes (24): evaluate_expired(), generate_report(), _get_current_price(), _get_entry_price(), _get_recent_signals(), _load_results(), _load_tracked(), main() (+16 more)

### Community 47 - "run"
Cohesion: 0.09
Nodes (25): detect_incomplete_run(), On startup, check for a pipeline run that was interrupted mid-trade. Returns…, execute_trade(), get_current_price(), _get_direction_wr(), get_max_leverage(), _is_guardian_closing(), Execute a trade via brain.py. Returns (success, trade_id_or_msg). (+17 more)

### Community 48 - "blacklist_tester.py"
Cohesion: 0.14
Nodes (23): cmd_evaluate(), cmd_pick(), cmd_remaining(), cmd_status(), evaluate_verdict(), get_tested_tokens(), get_trial_outcomes(), load_blacklists() (+15 more)

### Community 49 - "price_collector.py"
Cohesion: 0.23
Nodes (11): _aggregate_tf(), fetch_all_prices(), _get_active_tokens(), main(), Fetch full token universe + allMids from Hyperliquid. Writes shared HL cache…, Save to SQLite + JSON cache. Returns rows inserted. Filters out delisted tokens…, Gather tokens that need candle data: hot-set + open positions., Aggregate price_history (signals_hermes.db) into a candles table (candles.db).… (+3 more)

### Community 50 - "rs_signals.py"
Cohesion: 0.08
Nodes (34): _atr(), _atr_pct(), _bounce_confirmation(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs_signal(), _find_swing_highs_lows() (+26 more)

### Community 51 - "signal_researcher.py"
Cohesion: 0.13
Nodes (23): backtest_signals(), detect_bollinger_squeeze(), detect_consecutive_candles(), detect_volume_breakout(), evaluate_pattern(), generate_template(), get_candles(), get_tokens() (+15 more)

### Community 52 - "wasp.py"
Cohesion: 0.28
Nodes (23): bug(), check_ab_testing(), check_cooldowns(), check_db_integrity(), check_hotset(), check_mirror(), check_ollama(), check_paper_hl_sync() (+15 more)

### Community 53 - "backtest_hwave_bonus_thresholds.py"
Cohesion: 0.18
Nodes (15): closest_candle_before(), compute_z_at(), get_token_tf_data(), hwave_test(), Returns (direction, avg_z_signed, avg_z_abs, avg_vel) or None. Regime filter…, run_backtest(), stats(), vel_sig_gen() (+7 more)

### Community 54 - "init_db"
Cohesion: 0.12
Nodes (22): init_db(), _mark_migration_done(), Check if legacy migration has already run (idempotent — safe to call on every…, Persist that legacy migration has completed., Initialize both static and runtime DBs with proper schemas., _was_migration_done(), _get_open_pos(), _get_open_pos_dict() (+14 more)

### Community 55 - "backtest_ema20_50"
Cohesion: 0.15
Nodes (14): backtest_ema20_50(), batch_backtest(), _detect_one_direction(), _is_bearish_reversal(), _is_bullish_reversal(), _print_backtest(), Bullish 3-bar close reversal at index idx. Prior bar shows pullback (lower…, Bearish 3-bar close reversal at index idx. Prior bar shows pullback (higher… (+6 more)

### Community 56 - "hl_leaderboard.py"
Cohesion: 0.13
Nodes (22): calculate_score(), detect_pattern(), get_leaderboard(), get_user_fills(), get_user_portfolio(), get_user_state(), _hl_info(), Classify trader style based on actual trade patterns. (+14 more)

### Community 57 - "tl_break.py"
Cohesion: 0.11
Nodes (26): _atr(), _check_trend_alignment(), _check_volume_confirmation(), _count_bounces_with_rejection(), _detect_breakout(), _detect_fakeout(), detect_tl_break(), _detect_trendline() (+18 more)

### Community 58 - "sync_open_trades.py"
Cohesion: 0.16
Nodes (22): add_orphan_recovery_trade(), close_hl_position(), close_paper_trade_db(), find_existing_open_trade(), find_recent_closed_trade(), get_db_connection(), get_open_hl_positions(), get_open_paper_trades() (+14 more)

### Community 59 - "4h_regime_scanner.py"
Cohesion: 0.13
Nodes (21): calculate_r2(), calculate_slope(), calculate_weight_adjustment(), determine_regime(), fetch_candles(), fetch_candles_from_binance(), fetch_candles_from_db(), get_tokens_to_scan() (+13 more)

### Community 60 - "hype_cache.py"
Cohesion: 0.16
Nodes (17): cache_age(), cache_fresh(), fetch_and_cache(), fetch_and_cache_positions(), get_allMids(), get_cached_positions(), Shared Hyperliquid /info cache — single fetch per 60s, shared across all…, Return open positions from cache if fresh (< _POS_CACHE_TTL old). Returns… (+9 more)

### Community 61 - "checkpoint_utils.py"
Cohesion: 0.12
Nodes (21): checkpoint_decider_cycle(), checkpoint_guardian_cycle(), checkpoint_list(), checkpoint_orphan_detected(), checkpoint_read_last(), checkpoint_trade_pending(), checkpoint_write(), clear_workflow_state() (+13 more)

### Community 62 - "hl_wallet_discovery.py"
Cohesion: 0.13
Nodes (21): discover_from_social_media(), discover_from_trading_competitions(), discover_new_sources(), evaluate_wallet(), Evaluate if a wallet is worth tracking., Save a new trader to the database., Save discovery results to log file., Main discovery function. (+13 more)

### Community 63 - "strategy_optimizer.py"
Cohesion: 0.14
Nodes (21): apply_recommendations(), evaluate_results(), get_active_params(), get_closed_trades(), get_open_trade_ids(), get_pg_conn(), init_tables(), Record that a trade opened with specific param values. (+13 more)

### Community 64 - "audit_logger.py"
Cohesion: 0.21
Nodes (15): atr_check(), atr_sl_hit(), atr_tp_hit(), _base(), guardian_cycle(), log_event(), loss_cooldown_set(), _now() (+7 more)

### Community 65 - "backtest_hh_hl.py"
Cohesion: 0.18
Nodes (18): build_structure_series(), check_exit(), compute_atr_series(), compute_stats(), find_swings_upfront(), fmt(), get_candles(), get_swing_prices() (+10 more)

### Community 66 - "context-compactor.py"
Cohesion: 0.14
Nodes (20): acquire_lock(), get_critical_flags_block(), get_live_trading_status(), get_pipeline_status(), get_position_summary(), get_quick_status_line(), get_regime(), get_wasp_status() (+12 more)

### Community 67 - "scrape_all_sources"
Cohesion: 0.17
Nodes (20): Scrape Twitter/X for known HL traders., Scrape GitHub for HL-related repos with wallet addresses., Run a shell command and return output., Scrape all sources for top HL traders., Scrape Dexly leaderboard for top traders., Scrape HyperStats leaderboard for top traders., Scrape Beacon leaderboard for top traders., Scrape SkynetX leaderboard for top traders. (+12 more)

### Community 68 - "ma300_candle_confirm_signals.py"
Cohesion: 0.14
Nodes (18): detect_ma300_candle(), _ema(), _ema_series(), _get_candles_1m(), Detect EMA300 + 2-candle confirmation signal. Args: token: token symbol (e.g.…, Scan all tokens in prices_dict for EMA300 + 2-conf signals. Args: prices_dict:…, Compute EMA(period) from a list of prices (oldest first). Returns the most…, Compute EMA series — returns EMA value at each index (oldest first). Returns a… (+10 more)

### Community 69 - "signal_importer.py"
Cohesion: 0.12
Nodes (20): calculate_confluence(), get_confluence_signals(), get_momentum_state(), get_zscore_tier(), import_fear_signal(), import_rsi_signal(), import_zscore_signal(), _load_momentum() (+12 more)

### Community 70 - "15m_regime_scanner.py"
Cohesion: 0.15
Nodes (19): calculate_r2(), calculate_slope(), determine_regime(), fetch_candles(), fetch_candles_from_binance(), fetch_candles_from_db(), get_tokens_to_scan(), main() (+11 more)

### Community 71 - "log_error"
Cohesion: 0.06
Nodes (37): ai_decide(), ai_decide_batch(), _check_token_budget(), cleanup_stale_signals(), _do_compaction_llm(), get_fear(), get_learned_adjustments(), get_market_zscore() (+29 more)

### Community 72 - "backtest_gap300.py"
Cohesion: 0.14
Nodes (19): compute_series(), get_all_prices(), main(), Group fires into pulses., Run state machine backtest on full price series. Returns events list., run_backtest(), summarize_pulses(), _ema_series() (+11 more)

### Community 73 - "bug_hunter.py"
Cohesion: 0.16
Nodes (13): grep_file(), Return list of (line_num, line) matching pattern., get_fast_signals(), get_registered_signals(), get_slow_signals(), Resolve 'enabled' to bool: if string, look up in hermes_constants; otherwise…, Return only the signals where enabled=True and run is not None., Fast signals — run every minute. (+5 more)

### Community 74 - "candle_db.py"
Cohesion: 0.16
Nodes (19): aggregate_1m_to_tf(), detect_cascade_direction(), fetch_and_store(), fetch_and_store_all_tf(), get_candles(), get_conn(), get_last_ts(), get_latest_price() (+11 more)

### Community 75 - "scan_gap300_state"
Cohesion: 0.18
Nodes (12): _ema_series(), _init_state_table(), _load_state(), Load state for a token. Returns default (no signal) if none found., Save state for a token to DB., State machine scanner for gap-300 signals. Loads existing state for token,…, Return EMA series (oldest first), None for indices < period-1., Return SMA series (oldest first), None for indices < period-1. (+4 more)

### Community 76 - "backtest_breakout.py"
Cohesion: 0.15
Nodes (16): backtest_token(), compute_atr(), compute_levels(), detect_breakout(), detect_breakout_direction(), detect_compression(), get_all_tokens(), get_candles_range() (+8 more)

### Community 77 - "backtest_tl_break.py"
Cohesion: 0.16
Nodes (18): _atr_raw(), compute_atr(), compute_macd(), compute_rsi(), detect_tl_break_baseline(), detect_tl_break_improved(), _linear_regression(), load_candles_5m() (+10 more)

### Community 78 - "detect_ema9_sma20_cross"
Cohesion: 0.17
Nodes (16): backtest_ema9_sma20(), _compute_gap_series(), _compute_slope_series(), detect_ema9_sma20_cross(), _ema_series(), _ema_slope_series(), Compute slope over the last `slope_period` bars for each valid value. slope[i]…, Return (EMA series, slope of EMA series) — both oldest first. (+8 more)

### Community 79 - "counter_flip.py"
Cohesion: 0.19
Nodes (14): get_macd_exit_signal(), Check if a position should be exited based on MACD rules. Returns dict with:…, _check_cascade_direction_flip(), _check_macd_rules_flip(), _check_mtf_alignment_flip(), _get_open_positions(), Cascade direction flip: cascade_entry_signal() says cascade is ACTIVE and its…, MACD rules engine flip: macd histogram has turned against our position. Returns… (+6 more)

### Community 80 - "profit_monster.py"
Cohesion: 0.15
Nodes (20): close_position(), filter_by_pnl(), get_all_open_positions(), is_position_on_hl(), is_token_being_closed_by_guardian(), load_config(), Check if token still has an open position on HL., Check if guardian closing markers include this token. (+12 more)

### Community 81 - "signal_lifecycle.py"
Cohesion: 0.17
Nodes (18): check_state_transition(), get_signal_history(), load_audit(), load_lifecycle(), log(), main(), Load latest audit data., Get historical performance for a signal type. (+10 more)

### Community 82 - "get_realized_pnl"
Cohesion: 0.27
Nodes (9): fetch_hl_prices(), main(), ms(), Convert datetime string or object to Unix milliseconds., Compute size-weighted average price from a list of fill dicts., Fetch fills for token between start_ms and end_ms. Returns dict with…, wavg_price(), get_realized_pnl() (+1 more)

### Community 83 - "candle_tuner.py"
Cohesion: 0.18
Nodes (17): analyze_by_hour(), analyze_by_regime(), analyze_by_state_direction(), analyze_by_token(), analyze_inversion_effectiveness(), analyze_overall(), apply_prompt_fix(), apply_token_override() (+9 more)

### Community 84 - "log_event"
Cohesion: 0.17
Nodes (17): event_summary(), log_api_call(), log_budget_exceeded(), log_checkpoint_recovery(), log_event(), log_hotset_updated(), log_trade_entered(), log_trade_failed() (+9 more)

### Community 85 - "hh_hl_signals.py"
Cohesion: 0.18
Nodes (17): _classify_structure(), _compute_atr(), _detect_breakout(), _detect_pullback(), _find_swing_highs_lows(), _get_candles_from_ohlcv_1m(), _get_candles_from_price_history(), Classify current swing structure at the most recent candle. Args: highs: sorted… (+9 more)

### Community 86 - "record_cooldown_start"
Cohesion: 0.15
Nodes (18): detect_ma_cross(), _ema(), _ema_series(), _get_candles_1m(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for MA cross signals and write to DB. All guards…, Compute EMA(period) from a list of prices (oldest first). Returns the most…, Compute EMA series — returns EMA value at each index (oldest first). Returns a… (+10 more)

### Community 87 - "ab_learner.py"
Cohesion: 0.22
Nodes (16): compute_direction_performance(), compute_evolution_signals(), compute_sl_learnings(), compute_token_regime_performance(), compute_token_stats(), _db_conn(), get_closed_trades(), Global SL distance analysis: which SL distances have highest win rates overall.… (+8 more)

### Community 88 - "vortex_break.py"
Cohesion: 0.15
Nodes (18): _adx(), detect_vortex_break(), _ema(), _get_candles_5m(), _load_cooldowns(), Compute True Range for each candle (oldest first)., Compute Vortex Indicator (VI+, VI-) from OHLCV candles. VI+ = sum of |high[i] -…, Compute ADX (Average Directional Index) from OHLCV candles. Uses Wilder's… (+10 more)

### Community 89 - "top150.py"
Cohesion: 0.17
Nodes (16): get_tradeable_tokens(), Return set of tradeable (non-delisted) token names from HL meta., get_allowed_tokens(), get_binance_volumes(), get_hl_universe(), get_top150(), hl_to_binance_symbol(), load_cache() (+8 more)

### Community 90 - "signal_auditor.py"
Cohesion: 0.18
Nodes (16): compute_edge_score(), get_registry_status(), get_signal_performance(), get_token_breakdown(), log(), main(), map_signal_to_flag(), Map a signal_type name to its *_ENABLED flag in hermes_constants.py. DB signal… (+8 more)

### Community 91 - "signal_quality_autotuner.py"
Cohesion: 0.18
Nodes (16): _apply_changes(), _build_prompt(), _call_opencode(), _get_compactor_weights(), _get_current_params(), _load_results(), _log_tune(), main() (+8 more)

### Community 92 - "signal_rotator.py"
Cohesion: 0.21
Nodes (16): apply_changes(), get_current_regime(), get_registry_status(), load_audit(), log(), main(), map_signal_to_flag(), Select which signals to enable/disable based on regime and performance. (+8 more)

### Community 93 - "fast_momentum.py"
Cohesion: 0.15
Nodes (18): expire_pending_signals(), EXPIRED signals safety-net — DEPRECATED for primary PENDING/APPROVED lifecycle.…, compute_zscore_velocity(), _ema(), _fast_zscore(), get_momentum_stats(), is_reasonable_price(), _log() (+10 more)

### Community 94 - "away_detector.py"
Cohesion: 0.21
Nodes (15): acquire_lock(), call_ceo(), get_debounce_ts(), is_live_trading_enabled(), is_pipeline_healthy(), is_t_away(), load_json(), main() (+7 more)

### Community 95 - "cascade_flip_helpers.py"
Cohesion: 0.18
Nodes (17): clear_expired_evictions(), get_eviction_deadline(), get_flip_k_multiplier(), get_pipeline_cycle(), is_token_evicted(), load_flip_counts(), mark_token_flipped(), cascade_flip_helpers.py ======================= Shared helpers for cascade-flip… (+9 more)

### Community 96 - "error_analyzer.py"
Cohesion: 0.19
Nodes (15): classify_errors(), detect_alerts(), load_known_patterns(), log(), main(), Compare current patterns against known, return alerts., Append alerts to error_alerts.md., Scan last hour of hermes-pipeline journal for errors. (+7 more)

### Community 97 - "hebbian_learner.py"
Cohesion: 0.17
Nodes (14): extract_and_learn(), infer_label(), _load_coin_universe(), Infer label type from a concept name string., Extract entities and learn all co-occurring pairs. If engine is None, just…, Load HL coin universe from signals_hermes.db.ohlcv_1m.token., extract_concepts(), main() (+6 more)

### Community 98 - "Plan: Fix the Penalty System That Inverts Signal Quality"
Cohesion: 0.12
Nodes (15): BUG 1 & 2 Fix: Rebuild the Penalty Chain in `_run_hot_set()`, BUG 3 Fix: Write PnL to DB in `refresh_current_prices()`, Current Behavior, Current Broken Code Flow (lines 1104–1208), Files to Change, Fix, Location, Open Questions for T (+7 more)

### Community 99 - "macd_rules.py"
Cohesion: 0.13
Nodes (19): IntEnum, compute_macd_state(), CrossoverFreshness, _detect_cascade(), ema(), _fetch_binance_candles(), get_macd_bullish_score(), get_macd_entry_signal() (+11 more)

### Community 100 - "kanban_api.py"
Cohesion: 0.20
Nodes (15): delete_project(), get_projects(), health(), load_kanban(), Load kanban data from JSON file. Seed with defaults if missing., Atomically write kanban data to JSON file., Seed kanban.json with current TASKS.md / PROJECTS.md data., Serve the kanban HTML page. (+7 more)

### Community 101 - "evaluate_macd_rules"
Cohesion: 0.19
Nodes (15): evaluate_macd_rules(), _exit_long_signals(), _exit_short_signals(), _flip_long_signals(), _flip_short_signals(), _long_entry_allowed(), MACDState, Given a computed MACDState, evaluate all entry/exit/flip rules. Returns the… (+7 more)

### Community 102 - "detect_ema9_sma20_cross"
Cohesion: 0.17
Nodes (16): backtest_ema9_sma20(), _compute_gap_series(), _compute_slope_series(), detect_ema9_sma20_cross(), _ema_series(), _ema_slope_series(), Compute slope over the last `slope_period` bars for each valid value. slope[i]…, Return (EMA series, slope of EMA series) — both oldest first. (+8 more)

### Community 103 - "ema_angle.py"
Cohesion: 0.21
Nodes (15): _cooldown_ok(), detect_ema_angle(), _ema(), _get_1m_prices(), _log(), _mark_signal(), # NOTE: signal_schema imports this module, so we lazy-import inside functions, Call AFTER add_signal() succeeds to update in-memory cooldown. (+7 more)

### Community 104 - "sync_kanban_tasks.py"
Cohesion: 0.21
Nodes (15): load_kanban(), main(), make_kanban_id(), parse_tasks_md(), Make a stable ID from task text., Read TASKS.md, update kanban.json to match task statuses., Read kanban.json, FULL REWRITE of TASKS.md from parsed state (not in-place…, Use hermes_write_with_lock.py to atomically write a file. (+7 more)

### Community 105 - "trading-checklist.py"
Cohesion: 0.13
Nodes (7): check_hl_sync(), check_pipeline_service(), main(), Run a named check and return (ok: bool, msg: str, issues: list), Check pipeline via timer (onshot services go inactive after run)., Check hl-sync service (long-running Type=simple service)., run_check()

### Community 106 - "backtest_adx_macd.py"
Cohesion: 0.22
Nodes (14): compute_adx_di(), compute_macd(), evaluate_signals(), load_1h_candles(), macd_acceleration(), main(), MACD histogram acceleration: is the histogram momentum increasing? Returns…, Fire LONG when +DI > -DI and ADX > threshold (and rising). Fire SHORT when -DI… (+6 more)

### Community 107 - "param_auto_tuner.py"
Cohesion: 0.22
Nodes (14): analyze_distribution(), _apply_changes(), compute_mfe_mae(), get_closed_trades(), log(), _log_session(), main(), Read a constant value from hermes_constants.py. (+6 more)

### Community 108 - "pipeline_watchdog.py"
Cohesion: 0.21
Nodes (14): add_alert(), check_pipeline_errors(), check_pipeline_lock(), check_signal_production(), check_trade_execution(), log(), main(), Check if trades are being executed. (+6 more)

### Community 109 - "is_solana_only"
Cohesion: 0.15
Nodes (12): _load_hot_rounds(), Load hot signals based on review_count (ai-decider survival passes). A hot…, can_short(), get_all_tradeable_tokens(), get_token_chain(), is_hyperliquid(), is_solana_only(), Check if token is available on Hyperliquid. (+4 more)

### Community 110 - "bollinger_squeeze.py"
Cohesion: 0.22
Nodes (12): _aggregate_candles(), _compute_bb(), _detect_signal(), _get_ticks(), _in_cooldown(), Check if token+direction is in cooldown., Main scan entry point. Called by signals_runner., Fetch recent ticks for a token from price_history. (+4 more)

### Community 111 - "run_backtest"
Cohesion: 0.23
Nodes (9): align_to_master(), detect_xover(), IMACD, load_token_data(), Detect crossover. prev_h=None means no previous bar., Load all TFs from local DB. Returns dict with ts/cl lists., For each master_ts, return index into sub_ts that was current., Incremental MACD with no side-effect crossover detection. (+1 more)

### Community 112 - "backtest_rs_tiers.py"
Cohesion: 0.29
Nodes (13): _atr(), _atr_pct(), _bounce_confirmed(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs_with_touch_count(), _find_swing_highs_lows() (+5 more)

### Community 113 - "rule_based_context_gate"
Cohesion: 0.15
Nodes (14): _ctx_gate_get_market_context(), _ctx_gate_get_momentum(), _ctx_gate_get_phase(), _ctx_gate_get_speed(), _ctx_gate_get_zscore(), _get_recent_prices(), Get last N close prices from get_price_history. Returns list of floats or empty., Get speed percentile — same source as EXEC path (SpeedTracker). CEO 2026-08-02:… (+6 more)

### Community 114 - "mtf_macd.py"
Cohesion: 0.16
Nodes (17): get_macd_params(), Return MACD params for token, falling back to DEFAULT., get_tf_zscores(), Return (z, tier_str) or (None, None)., Z-score across all timeframes. Returns {tf_name: (z, tier)}. Cached for 60s —…, zscore(), get_1h_zscore(), is_delisted() (+9 more)

### Community 115 - "macd_accel.py"
Cohesion: 0.20
Nodes (13): compute_macd_series(), detect_macd_accel(), _ema(), _get_1m_closes(), Detect MACD(8,50,12) crossover with acceleration confirmation. Args: closes:…, Fetch 1m close prices from candles.db (candles_1m table). Returns: list of…, Entry point for signals_runner. Returns count of signals emitted., Return EMA series (oldest first), None for indices < period-1. (+5 more)

### Community 116 - "atr_compression_signals.py"
Cohesion: 0.22
Nodes (12): _compute_atr(), detect_atr_compression_signal(), _get_candles_5m(), _get_last_state(), Read current compression state from runtime DB cache table., Persist compression state to runtime DB., State-machine ATR compression + breakout detector on 5m candles. States:…, Scan all tokens in prices_dict for ATR compression breakouts on 5m. Returns:… (+4 more)

### Community 117 - "hermes-dashboard.py"
Cohesion: 0.21
Nodes (11): cache_data, load_ab_tests(), load_candle_runs(), load_decisions(), load_prediction_accuracy(), load_signal_stats(), Load decisions.jsonl into DataFrame., Load win rate stats from signals DB. (+3 more)

### Community 118 - "hebbian_session_learner.py"
Cohesion: 0.23
Nodes (12): extract_entities(), Extract all typed entities from text. Returns list of (concept_name,…, learn_from_event_log(), learn_from_sessions(), learn_from_text(), main(), parse_session_dump(), Path (+4 more)

### Community 119 - "hl_copy_signal.py"
Cohesion: 0.22
Nodes (12): calculate_confidence(), generate_hl_signal(), get_recent_pro_trades(), get_trader_performance(), Get recent trades from pro traders., Write signal to the signals database for pipeline processing., Main function: detect pro trades and generate pipeline signals., Get trader's historical performance for confidence calculation. (+4 more)

### Community 120 - "is_cooldown_active"
Cohesion: 0.15
Nodes (18): detect_ma_fast_cross(), _ema(), _ema_series(), _get_candles_1m(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for 8/50 MA cross SHORT signals and write to DB. All…, Compute EMA(period) from a list of prices (oldest first). Returns the most…, Compute EMA series — returns EMA value at each index (oldest first). Returns a… (+10 more)

### Community 121 - "obs_dashboard.py"
Cohesion: 0.23
Nodes (12): get_hotset_status(), get_pipeline_health(), get_recent_signals(), get_signal_performance(), get_token_speed_summary(), get_trades_metrics(), main(), Get token speed distribution. (+4 more)

### Community 122 - "pipeline_breadcrumbs.py"
Cohesion: 0.27
Nodes (12): clear_stale(), get_breadcrumbs(), log_fail(), log_start(), log_success(), Return the current breadcrumb state for inspection., Record that a step has started., Record that a step completed successfully. (+4 more)

### Community 123 - "r2_trend_signals.py"
Cohesion: 0.17
Nodes (16): detect_r2_short(), _get_candles_1m(), _ols_params(), _precompute_x(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Scan pre-filtered tokens for R² confirmed downtrend signals. All guards…, Compute OLS slope, intercept, R² from a list of prices (oldest first). Returns…, Precompute x stats for fast rolling OLS. Call once per window size. (+8 more)

### Community 124 - "backtest_ma_cross.py"
Cohesion: 0.29
Nodes (11): calc_ema_series(), ComboStats, find_crosses(), get_candles(), get_tokens(), main(), Fetch 1m candles for a token (oldest first)., EMA series — None before warmup, float after. (+3 more)

### Community 125 - "evaluate_trade"
Cohesion: 0.24
Nodes (12): compute_z(), evaluate_trade(), main(), mtf_alignment(), nearest_5m(), Returns gate result dict for a single trade. entry_ts = unix timestamp of trade…, Z-score of last close vs 20-bar rolling mean. None if < 20 bars., Is z_score becoming more extreme (toward ±2) or reverting toward 0? (+4 more)

### Community 126 - "backtest_bb_bounce.py"
Cohesion: 0.30
Nodes (11): backtest_token(), compute_bb(), compute_rsi(), detect_bb_bounce(), get_1h_trend(), load_candles_1h(), load_candles_5m(), main() (+3 more)

### Community 127 - "backtest_guppy.py"
Cohesion: 0.23
Nodes (9): backtest_token(), _calc_pnl(), compute_stats(), fetch_candles_for_backtest(), backtest_guppy.py — Guppy MMA Historical Backtester…, Backtest top tokens by data availability., Fetch all candles for a token in a time range, ordered oldest→newest., Walk through historical candles for a single token using a rolling window. At… (+1 more)

### Community 128 - "backtest_signal"
Cohesion: 0.30
Nodes (11): backtest_signal(), compute_acceleration(), compute_roc(), compute_vol_ratio(), get_candles_4h_with_vol(), main(), Get 4h candles with volume. Returns (ts, close, volume)., Rate of Change: % change over N periods. (+3 more)

### Community 129 - "backtest_patterns.py"
Cohesion: 0.18
Nodes (9): build_pattern_prompt(), candle_pattern(), detect_support_resistance(), pattern_summary(), Very simple: recent swing highs/lows., Convert pattern list to readable text., Simple RSI-like from recent momentum., Return list of detected patterns in the last 3 candles. (+1 more)

### Community 130 - "detect_rs"
Cohesion: 0.30
Nodes (11): _atr(), _atr_pct(), _bounce_confirmed(), _build_level_touches(), _cluster_levels(), _compute_confidence(), detect_rs(), _find_swing_highs_lows() (+3 more)

### Community 131 - "fetch_binance_candles.py"
Cohesion: 0.24
Nodes (11): fetch_binance_klines(), get_binance_symbol(), get_db_count(), get_db_max_ts(), insert_candles(), main(), Map HL token to Binance symbol., Fetch klines from Binance. All times in milliseconds. (+3 more)

### Community 132 - "hebbian_seed_sessions.py"
Cohesion: 0.26
Nodes (11): extract_entities(), get_connection(), infer_label(), learn_pair(), node_id(), parse_session_file(), Path, Fast entity extraction, returns list of (concept, label_type). (+3 more)

### Community 133 - "hermes-brain-sync.py"
Cohesion: 0.24
Nodes (11): acquire_lock(), append_audit_log(), audit_find_stale(), check_kanban_sync(), main(), Find tasks with stale revisit dates or blocked > 7 days., # TODO: implement, Verify TASKS.md and kanban.json are in sync. (+3 more)

### Community 134 - "hl_copy_tui.py"
Cohesion: 0.27
Nodes (11): draw_fills(), draw_footer(), draw_header(), draw_traders(), get_recent_fills(), get_stats(), get_traders(), main() (+3 more)

### Community 135 - "ma_cross.py"
Cohesion: 0.23
Nodes (11): detect_ma_cross(), _ema(), _ema_series(), _get_candles_1m(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Entry point for signals_runner. Returns count of signals emitted., Compute EMA(period) from a list of prices (oldest first). Returns the most…, Compute EMA series — returns EMA value at each index (oldest first). Returns a… (+3 more)

### Community 136 - "r2_rev.py"
Cohesion: 0.24
Nodes (11): detect_r2_rev_signal(), _get_candles_5m(), _ols_params(), _precompute_x(), Fetch 5m OHLCV candles from candles.db (oldest first). Freshness guard: skip if…, Entry point for signals_runner. Returns count of signals emitted., Compute OLS slope, intercept, R² from a list of prices (oldest first)., Precompute x stats for fast rolling OLS. Call once per window size. (+3 more)

### Community 137 - "backtest_bb_bounce_v2.py"
Cohesion: 0.40
Nodes (10): backtest_token(), compute_bb(), compute_rsi(), detect_bb_bounce(), get_1h_trend(), load_candles_1h(), load_candles_5m(), main() (+2 more)

### Community 138 - "backtest_ma300_candle_confirm.py"
Cohesion: 0.33
Nodes (10): compute_stats(), _ema_series(), find_signals(), get_candles(), get_tokens(), main(), Find MA300 + candle confirmation signals and simulate trades., Compute EMA series — returns EMA value at each index (oldest first). None for… (+2 more)

### Community 139 - "run_pipeline.py"
Cohesion: 0.32
Nodes (7): increment_pipeline_cycle(), Increment and persist the pipeline cycle counter. Called once per pipeline run…, main(), Run a step in the background so the pipeline is not blocked. Used for slow…, # NOTE: --live is NOT passed to step scripts., run(), run_bg()

### Community 140 - "compute_mtf_macd_alignment"
Cohesion: 0.20
Nodes (14): _check_cascade_direction_flip(), _check_macd_rules_flip(), _check_mtf_alignment_flip(), _get_open_positions(), Cascade direction flip: cascade_entry_signal() says cascade is ACTIVE and its…, MACD rules engine flip: macd histogram has turned against our position. Returns…, Read open positions from PostgreSQL brain DB. {TOKEN: direction}., Called by signal_gen.run() every pipeline run. For each open position, run… (+6 more)

### Community 141 - "error_breadcrumbs.py"
Cohesion: 0.22
Nodes (10): BREADCRUMB(), breadcrumb_trace(), check_step_health(), get_breadcrumbs_for_step(), get_last_breadcrumbs(), Get the last N breadcrumbs for inspection., Get last N breadcrumbs for a step prefix (e.g. 'signal_gen')., Check if a pipeline step ran recently. Returns: {'healthy': bool, 'last_run':… (+2 more)

### Community 142 - "hyperliquid-trader.py"
Cohesion: 0.38
Nodes (10): check_sl_tp(), get_all_prices(), load_config(), log_error(), main(), pg_exec(), pg_query(), Execute a SELECT query with parameterized inputs (+2 more)

### Community 143 - "r2_rev_5m_signals.py"
Cohesion: 0.25
Nodes (10): detect_r2_rev_signal(), _get_candles_5m(), _ols_params(), _precompute_x(), Fetch 5m OHLCV candles from candles.db (oldest first). Freshness guard: skip if…, Scan pre-filtered tokens for R² mean reversion signals on 5m. All guards…, Compute OLS slope, intercept, R² from a list of prices (oldest first)., Precompute x stats for fast rolling OLS. Call once per window size. (+2 more)

### Community 144 - "study_winning_combos.py"
Cohesion: 0.29
Nodes (10): classify_sources(), get_recent_trades(), get_signal_sources_for_trade(), pnl_emoji(), Get closed paper trades from brain.trades in the study window., Get the signal sources that contributed to a trade within the window., Separate OpenClaw (mtf-*) from Hermes sources., Build a sortable key string for the source combination. (+2 more)

### Community 145 - "get_ab_params"
Cohesion: 0.20
Nodes (10): _default_ab_params(), get_ab_params(), get_cached_ab_variant(), load_ab_config(), Get cached A/B variant or select new one, Load A/B test configuration, Select a variant for a given A/B test. Uses Thompson sampling from ab_utils…, Get A/B test parameters for a trade. Returns a dict with all relevant params.… (+2 more)

### Community 146 - "archive-trades.py"
Cohesion: 0.22
Nodes (9): archive_to_json(), build_analysis_db(), get_closed_trades(), get_pg_columns(), get_runtime_signal(), Fetch closed trades from PostgreSQL. Returns list of dicts., Archive trades to gzipped JSON lines (one file per day)., Find the best matching signal from signals_hermes_runtime.db for a trade.… (+1 more)

### Community 147 - "backtest_candle.py"
Cohesion: 0.31
Nodes (9): build_prompt(), compute_macd(), compute_rsi(), make_features(), parse_response(), Features from closes up to T-1, used to predict candle T direction., Extract direction from natural language response — tail-biased with regex., run_backtest() (+1 more)

### Community 148 - "binance_volume_collector.py"
Cohesion: 0.24
Nodes (8): _determine_is_closed(), fetch_and_store(), _klines(), Fetch klines from Binance. Returns list of candle dicts or empty list on…, Determine if a candle at timestamp `ts` is closed. Binance klines: the candle…, Main fetch + store loop. Fetches 1m + 5m for all tokens concurrently., Quick sanity check on CHIP candles., verify_chips()

### Community 149 - "daily_git_commit.py"
Cohesion: 0.31
Nodes (9): build_commit_message(), categorize_changes(), get_changed_files(), main(), Run a shell command and return output., Get list of changed files (modified, new, deleted)., Categorize changes for commit message., Build a descriptive commit message. (+1 more)

### Community 150 - "_seed_universe_candles"
Cohesion: 0.17
Nodes (12): _fetch_binance_candles(), _get_candle_progress(), _init_candles_db(), Store candles to candles.db., Load or init the universe token list + cursor., Persist universe token list + cursor., Seed multi-TF candles for the full universe — 1 token per run, all 3 TFs.…, Ensure candles.db has all required tables. (+4 more)

### Community 151 - "fetch_hl_volume.py"
Cohesion: 0.29
Nodes (9): fetch_hl_candles(), fill_volume_gaps(), get_tokens_without_volume(), main(), Fill volume gaps for a single token., Find tokens in candles_1m that have volume=0., Fetch OHLCV candles from Hyperliquid via hyperliquid package. Tries uppercase…, Store candles to candles.db (only fill gaps where volume=0). (+1 more)

### Community 152 - "scan_for_signals"
Cohesion: 0.22
Nodes (10): get_available_tokens(), get_candles(), Fetch candle rows from candles.db. interval: '1m', '5m', '15m', '1h', '4h'…, Return list of tokens available in candles_1m., Scan a single token for guppy signal. Returns signal dict or None., Scan all available tokens in candles_1m for guppy signals. Returns list of…, scan_all_tokens(), scan_token() (+2 more)

### Community 153 - "zscore_pump.py"
Cohesion: 0.30
Nodes (11): _check_divergence(), compute_zscore(), detect_zscore_pump(), _get_1m_prices(), _load_tuner_params(), _log(), Fetch 1m close prices from price_history (signals_hermes.db), oldest first.…, Detect z-score momentum signal given pre-fetched price history. Fire when: -… (+3 more)

### Community 154 - "backtest_combined_momentum_mean_reversion.py"
Cohesion: 0.31
Nodes (6): backtest_signal(), compute_accel(), compute_pct_rank(), get_candles(), Acceleration = change in z-score over ACCEL_WINDOW bars., pct_long = % of prices below current price (suppressed = good for LONG).

### Community 155 - "backtest_zscore_pump_full.py"
Cohesion: 0.36
Nodes (8): _get_token_data(), get_universe(), load_blacklists(), main(), Load closes + pre-compute z-scores for all lookbacks (one-time per token)., Sweep ALL thresholds × directions for one token, one lookback. Returns list of…, run_lookback(), sweep_combo()

### Community 156 - "get_db"
Cohesion: 0.16
Nodes (21): get_db(), init_db(), Get database connection with WAL mode., Create all tables if they don't exist., generate_report(), main(), Run one complete cycle: scan, monitor, report., Run as daemon with periodic cycles. (+13 more)

### Community 157 - "exhaustion.py"
Cohesion: 0.36
Nodes (8): detect_exhaustion(), _ema(), main(), Entry point for signals_runner. Returns count of signals emitted., Compute EMA30 over a list of closing prices., Detect exhaustion reversal signal for a token. exhaustion SHORT: prior…, run(), scan()

### Community 158 - "_secrets.py"
Cohesion: 0.21
Nodes (8): compute_indicators(), get_atr_at(), get_prices_at(), main(), Get n 1m close prices ending at timestamp ts from price_history., Compute ATR(period) from 5m candles at timestamp ts., Compute z_score, RSI, MACD, BB, momentum from close prices. Returns dict., Centralized secret loader — reads from .secrets.local in project root. All…

### Community 159 - "backtest_mtp_zscore.py"
Cohesion: 0.39
Nodes (7): backtest_combo(), compute_stats(), get_candles(), pop_zscore(), Z-score at idx using window bars ending at idx (not including current bar)., Backtest mtp_zscore for ONE token and parameter combo., run_sweep()

### Community 160 - "backtest_threshold"
Cohesion: 0.39
Nodes (7): backtest_threshold(), get_candles(), main(), Get 4h candles sorted oldest→newest. Returns (ts, close)., Compute rolling z-score with given lookback window., direction: 'positive' = z > threshold (expect reversion DOWN = SHORT)…, rolling_zscore()

### Community 161 - "process_delayed_entries"
Cohesion: 0.20
Nodes (10): _apply_inversion(), _load_delayed(), process_delayed_entries(), Apply static + dynamic signal inversion. Returns (new_direction, was_flipped)., Load pending delayed entries., Save pending delayed entries., Check pending delayed-entry signals. For each: if pullback reached OR max_wait…, Check if a signal source should be dynamically inverted based on24h WR. Returns… (+2 more)

### Community 162 - ".learn_pair"
Cohesion: 0.24
Nodes (5): Ensure consistent ordering for symmetric storage., Record that concept_a and concept_b fired together. Increments synapse weight.…, Decrement synapse weight between two concepts (loss learning). Creates the…, Hebbian write-back from a closed trade. Won (pnl_pct > 0) → strengthen all…, Get node id, creating if needed. Updates last_seen.

### Community 163 - "rebuild_ab_results.py"
Cohesion: 0.39
Nodes (7): get_net_pnl(), main(), parse_experiment(), Convert PostgreSQL Decimal/None to float., Extract list of (test_name, variant_id) from experiment JSON/string., Compute net PnL after fees., to_f()

### Community 164 - "rsi_backtest.py"
Cohesion: 0.36
Nodes (7): analyze_group(), classify_signal(), get_trades(), main(), print_result(), Classify a signal string into categories., Analyze a group of trades.

### Community 165 - "signal_decay_detector.py"
Cohesion: 0.43
Nodes (7): disable_signal(), get_signal_performance(), log(), main(), _main_impl(), Query signal_outcomes for 24h performance (dedup, trade_id IS NOT NULL)., Disable a signal by setting its flag to False in hermes_constants.py.

### Community 166 - "check_pipeline_not_stuck"
Cohesion: 0.25
Nodes (8): check_pipeline_not_stuck(), check_stale_locks(), _get_lock_holder_pid(), _pid_alive(), Check if the pipeline lock indicates a stuck pipeline. NOTE (2026-07-13):…, Check if a process is alive., Return list of PIDs holding a lock (via lsof)., Check all Hermes lock files. Fail if > threshold AND holder process is dead.…

### Community 167 - "find_abandoned_trades.py"
Cohesion: 0.43
Nodes (6): characterize(), cluster(), fetch(), main(), Fetch closed trades from PostgreSQL with duration computed., Find clusters: same token+direction within 5min of each other.

### Community 168 - "trace_trade.py"
Cohesion: 0.48
Nodes (6): fetch_audit_lines(), fetch_price_around(), fetch_signal(), fetch_trade(), main(), Return audit-log lines that mention the trade's id within +/- around_seconds of…

### Community 169 - "backfill_price_history_48h.py"
Cohesion: 0.43
Nodes (6): fetch_1m_klines(), hl_to_binance(), main(), process_token(), Fetch 1m klines from Binance covering last 48h. Returns [(ts, close)]., Fetch and store 1m candles for one token. Returns (token, rows_inserted,…

### Community 170 - "backfill_prices.py"
Cohesion: 0.43
Nodes (6): backfill_batch(), fetch_klines(), hl_to_binance(), main(), Map Hyperliquid token → Binance symbol., Fetch 1h klines from Binance. Returns [(timestamp_sec, close_price)].

### Community 171 - "backtest_minimax.py"
Cohesion: 0.52
Nodes (6): call_minimax(), compute_indicators(), load_candles(), load_price_history(), main(), parse_response()

### Community 172 - "backtest_momentum_cross"
Cohesion: 0.48
Nodes (6): backtest_momentum_cross(), get_candles(), main(), Returns list of (z, prev_z) tuples for each price point. prev_z = z from…, LONG: z crosses above +threshold (prev_z < threshold, z >= threshold) SHORT: z…, rolling_zscore()

### Community 173 - "graceful_close.py"
Cohesion: 0.38
Nodes (5): close_hl(), fix_and_close_db(), Market close on Hyperliquid. Returns True on success., Fix entry_price if needed, mark closed in DB. Returns trade info., ts()

### Community 174 - "grid_backtest.py"
Cohesion: 0.43
Nodes (5): compute_adx(), ema(), Compute ADX using Wilder smoothing., run_backtest(), true_range()

### Community 175 - "_close_trade_impl"
Cohesion: 0.22
Nodes (9): trade_close(), close_trade(), _close_trade_impl(), _load_cooldowns(), Record a loss cooldown for token+direction. Guards against duplicates., Close an existing trade. Computes PnL from signal prices (no extra HL API…, Implementation of close_trade. Assumes conn/cur are managed by caller., _record_loss_cooldown() (+1 more)

### Community 176 - "monte_carlo_gate"
Cohesion: 0.38
Nodes (6): _get_returns(), monte_carlo_gate(), monte_carlo_gate_oracle(), Shadow-mode wrapper — always allows but logs what WOULD have been blocked. Use…, Fetch last N trade returns from signal_outcomes., Run Monte Carlo simulation to estimate if a signal type is still profitable.…

### Community 177 - "gap300_5m_signals.py"
Cohesion: 0.31
Nodes (8): detect_gap300_5m(), _ema300_5m(), _get_5m_candles(), Scan tokens for gap300_5m signals. prices_dict: token -> {price, ts} (from…, Compute EMA300 on a 5m close series. Returns same-length list with None for…, Fetch 5m close prices from candles.db, MOST RECENT first, then reverse. Returns…, Detect gap300_5m LONG or SHORT signal on 5m candles only. Returns dict with…, scan_gap300_5m_signals()

### Community 178 - "volume_alert.py"
Cohesion: 0.43
Nodes (6): fmt(), get_futures_symbols(), get_klines(), main(), Fetch all USDT-margined perpetual futures symbols. Retries on truncate., Fetch last N 1-minute klines. Retries on rate limit or truncate.

### Community 179 - "get_directional_vol"
Cohesion: 0.38
Nodes (6): apply_to_confidence(), get_directional_vol(), _neutral_result(), Return a neutral result when we can't get data., Convenience wrapper: fetch directional volume and return (adjusted_confidence,…, Fetch candles and return directional volume analysis. Args: token: Trading…

### Community 180 - "evaluate_trade_1m"
Cohesion: 0.52
Nodes (6): compute_z(), evaluate_trade_1m(), main(), Uses price_history (1m resolution, timestamps in seconds). Speed: % change over…, wave_phase_from_snapshot(), z_trajectory()

### Community 181 - "detect_ma_100_signal"
Cohesion: 0.28
Nodes (9): _compute_atr(), _compute_ma(), detect_ma_100_signal(), ndarray, Resample 1m closes to 5m (every 5th candle)., Simple moving average., ATR from close-only data., Detect 100MA cross signal on 5m data. Args: token: token symbol candles: list… (+1 more)

### Community 182 - "abandoned_trade_root_cause.py"
Cohesion: 0.53
Nodes (5): characterize(), fetch(), main(), Returns (sl_pct_with_sign_convention, is_wrong_side)., sl_pct_and_side()

### Community 183 - "simulate_accel_300_signal.py"
Cohesion: 0.33
Nodes (4): find_cross_bar(), find_latest_below_bar(), Find the latest bar where price was below EMA, starting from start_idx and…, Find the cross bar (most recent transition to direction).

### Community 184 - "backfill_candle_files.py"
Cohesion: 0.53
Nodes (5): backfill_symbol(), _cached_request(), fetch_klines_backward(), main(), Fetch klines from Binance going BACKWARD from current_oldest_ts_ms. Returns…

### Community 186 - "dashboard.sh"
Cohesion: 0.53
Nodes (5): PYTHONPATH, dashboard.sh script, start(), status(), stop()

### Community 187 - "hermes_ab_utils.py"
Cohesion: 0.40
Nodes (5): get_cached_ab_variant(), _get_wandb_run(), Shared A/B testing utilities — canonical Thompson sampling implementation. Both…, Lazily initialize W&B run for Hermes A/B tests (offline, project=hermes-ai)., Get A/B variant for test_name, cached globally per test_name. Token and…

### Community 188 - "_acquire_lock_with_heartbeat"
Cohesion: 0.33
Nodes (6): _acquire_lock_with_heartbeat(), _is_primary_alive(), Check if the primary guardian process is still alive by reading its PID from…, Write heartbeat with PID so other guardians can detect if we're alive., Acquire lock using flock + heartbeat file for stale lock detection., _write_heartbeat()

### Community 189 - "backtest"
Cohesion: 0.47
Nodes (5): backtest(), ema(), Return (win_rate, avg_pnl, n_signals) for SHORT signals only., Load candles from DB, sweep params, store best config per token., run_sweep()

### Community 190 - "Ollama Model Benchmarks"
Cohesion: 0.33
Nodes (5): Ceiling Analysis, Ollama Model Benchmarks, qwen2.5:1.5b (Q4_K_M, 986MB) — PRODUCTION RECOMMENDED, qwen2.5:3b (Q4_K_M, 1.9GB) — NOT VIABLE, Runner Management

### Community 191 - "get_trade_history"
Cohesion: 0.39
Nodes (7): backfill(), get_closed_trades_without_hl_pnl(), get_hl_close_fill(), Get the most recent HL close fill (side=B) for a token after start_time_ms.…, update_trade(), get_trade_history(), Fetch user's fill history from Hyperliquid /info endpoint. Used to sync…

### Community 192 - "backtest_mtp_zscore_full.py"
Cohesion: 0.46
Nodes (7): backtest_one_token(), compute_stats(), get_all_tokens(), get_candles(), pop_zscore(), run_sweep(), save_partial()

### Community 193 - "trim_candle_files.py"
Cohesion: 0.47
Nodes (5): get_tf_tables(), main(), Return {interval: table_name} for all candle tables in candles.db., Trim a single table: keep max_allowed newest rows per token., trim_table()

### Community 194 - "update-git.py"
Cohesion: 0.47
Nodes (5): _get_token(), github_api(), main(), Get token from _secrets first (primary), then ~/.netrc fallback., sh()

### Community 195 - "fetch_klines"
Cohesion: 0.60
Nodes (4): fetch_klines(), hl_to_binance(), main(), Fetch 1h klines from Binance. Returns [(timestamp_sec, close)].

### Community 196 - "backtest_token"
Cohesion: 0.50
Nodes (4): backtest_token(), ols_slope_r2(), Compute slope and R² of closes (y) vs index (x)., Backtest R² regression signal on one token's close series. direction: 'long' or…

### Community 197 - "hermes_file_lock.py"
Cohesion: 0.40
Nodes (4): atomic_write_json(), load_json(), Write JSON data atomically using temp file + os.replace. Prevents corruption…, Load JSON file safely, returning default on any error.

### Community 198 - "wandb-sync.sh"
Cohesion: 0.40
Nodes (4): wandb-sync.sh script, WANDB_API_KEY, WANDB_DIR, WANDB_MODE

### Community 200 - "get_ab_variant"
Cohesion: 0.25
Nodes (8): get_ab_params_for_trade(), get_ab_variant(), Canonical A/B variant selection — delegates to ab_utils.get_ab_variant(). This…, Get all A/B params for a trade using Thompson sampling (via ab_utils). Returns…, get_ab_variant(), _load_ab_config(), Load A/B config from /root/.hermes/config/ab_tests.json., Select A/B variant using Thompson sampling from brain DB (ab_results). Fallback…

### Community 201 - "scan"
Cohesion: 0.39
Nodes (7): detect_exhaustion(), _ema(), main(), Scan all tokens (or single token) and emit exhaustion signals. Args: conf_min:…, Compute EMA30 over a list of closing prices., Detect exhaustion reversal signal for a token. exhaustion SHORT: prior…, scan()

### Community 202 - "trend_purity_signals.py"
Cohesion: 0.39
Nodes (7): detect_trend_purity(), _ema(), main(), Scan all tokens (or single token) and emit trend_purity signals. Args:…, Compute EMA30 over a list of closing prices., Detect trend purity signal for a token. LONG: price consistently above EMA30…, scan()

### Community 203 - "volume_hl_signals.py"
Cohesion: 0.29
Nodes (6): get_candles(), get_tokens(), Returns True if a signal was emitted for this token., Fetch all tokens that have 1m candle data (from signal_schema price list)., Fetch last N 1m candles for token: price from price_history, volume from…, scan_token()

### Community 204 - "main"
Cohesion: 0.29
Nodes (4): main(), Learn all pairs from a set of concepts that fired together. Creates C(n,2)…, Apply decay to old synapses. Returns number of rows affected., Return summary statistics.

### Community 205 - "_call_minimax"
Cohesion: 0.50
Nodes (4): _call_minimax(), _get_minimax_client(), Build minimax OpenAI-compatible client from auth.json., Call minimax MiniMax-M2 model. Returns content or empty string on failure.

### Community 206 - "backtest"
Cohesion: 0.67
Nodes (3): backtest(), ols_slope_r2(), Mean reversion entry: enter when price has deviated significantly from…

### Community 207 - "backtest_fast"
Cohesion: 0.67
Nodes (3): backtest_fast(), ols_slope_r2(), Fast version: skip SAMPLE_RATE bars.

### Community 223 - "detect_ma_100_signal"
Cohesion: 0.33
Nodes (7): _compute_atr(), _compute_ma(), detect_ma_100_signal(), ndarray, Simple moving average. Returns array same length as input (NaN for first…, ATR from close-only data (synthesized as |close[i]-close[i-1]|)., Detect 100MA bounce or cross signal. Args: token: token symbol candles: list of…

### Community 224 - "audit_dependencies.py"
Cohesion: 0.47
Nodes (5): main(), Run pip-audit if installed, return list of findings., Run pip check, return list of incompatibility messages., run_pip_audit(), run_pip_check()

### Community 225 - "get_embedding"
Cohesion: 0.33
Nodes (6): backfill_embeddings(), get_embedding(), Get vector embedding for text using nomic-embed-text, Search memories by semantic similarity (vector search), Backfill embeddings for thoughts without them, semantic_search()

### Community 226 - "store_thought"
Cohesion: 0.33
Nodes (6): call_ollama(), extract_and_store(), Store thought and metadata in database, Main function: extract metadata and store, Call Ollama API to extract metadata. Truncates prompts >3000 tokens., store_thought()

### Community 227 - ".recall"
Cohesion: 0.33
Nodes (3): Estimate historical win rate for a (token, signal) pair from Hebbian memory.…, Given a concept, return top-K associated concepts ranked by weight. Returns…, Returns (-1.0 to +1.0) sentiment from recall(token). Positive = token has…

### Community 228 - "detect_macd_accel"
Cohesion: 0.33
Nodes (6): compute_macd_series(), detect_macd_accel(), _ema(), Detect MACD(8,50,12) crossover with acceleration confirmation. Args: closes:…, Return EMA series (oldest first), None for indices < period-1., Compute MACD(8,50,12) on a closes list. Returns (macd_line, signal_line,…

### Community 229 - "archive-signals.py"
Cohesion: 0.50
Nodes (3): archive_month(), Write rows to a gzipped JSONL file for the given year/month., run_archive()

### Community 231 - "get_fast_group_direction"
Cohesion: 0.50
Nodes (4): get_fast_group_direction(), get_group_slope(), Slope of the group EMA over recent bars. ema_history: list of group midpoints…, Direction of fast group: +1 = rising, -1 = falling, 0 = flat. Uses slope of…

### Community 232 - "_fetch_trades_sync"
Cohesion: 0.50
Nodes (4): _fetch_trades_sync(), prefetch_volume(), Fetch recentTrades for one token (called from background thread)., Batch-fetch recentTrades for all tokens in parallel using threads. Runs in…

### Community 233 - "run_checks"
Cohesion: 0.67
Nodes (3): main(), Run checks. If heal=True, apply fixes for failed checks., run_checks()

## Knowledge Gaps
- **22 isolated node(s):** `PYTHONPATH`, `start-litellm.sh script`, `wandb-sync.sh script`, `WANDB_API_KEY`, `WANDB_DIR` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `log()` connect `log` to `hl-sync-guardian.py`, `add_signal`, `hyperliquid_exchange.py`, `decider_run.py`, `hermes-brain-sync.py`, `candle_predictor.py`, `run_pipeline.py`, `hyperliquid-trader.py`, `pump_hunter.py`, `study_winning_combos.py`, `_get_conn`, `position_manager.py`, `scan_for_signals`, `run_guppy_signals.py`, `close_position`, `signal_compactor.py`, `process_delayed_entries`, `unified_scanner.py`, `ai_decider.py`, `breakout_engine.py`, `ab_optimizer.py`, `run`, `sync_open_trades.py`, `4h_regime_scanner.py`, `_acquire_lock_with_heartbeat`, `backtest_mtp_zscore_full.py`, `context-compactor.py`, `signal_importer.py`, `15m_regime_scanner.py`, `log_error`, `bug_hunter.py`, `profit_monster.py`, `candle_tuner.py`, `ab_learner.py`, `away_detector.py`, `sync_kanban_tasks.py`, `trading-checklist.py`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `add_signal()` connect `add_signal` to `get_momentum_stats`, `signal_schema.py`, `__init__.py`, `ma_cross.py`, `r2_rev.py`, `atr_compression.py`, `compute_mtf_macd_alignment`, `hh_hl.py`, `r2_rev_5m_signals.py`, `wyckoff.py`, `pattern_scanner.py`, `_get_conn`, `position_manager.py`, `zscore_pump.py`, `zscore_momentum.py`, `exhaustion.py`, `rs.py`, `unified_scanner.py`, `breakout_engine.py`, `signals/ma_cross_5m.py`, `ma_cross_5m.py`, `get_cooldown`, `oc_signal_importer.py`, `monte_carlo_gate`, `gap300_5m_signals.py`, `rs_signals.py`, `get_directional_vol`, `init_db`, `tl_break.py`, `ma300_candle_confirm_signals.py`, `signal_importer.py`, `scan`, `trend_purity_signals.py`, `volume_hl_signals.py`, `counter_flip.py`, `hh_hl_signals.py`, `record_cooldown_start`, `vortex_break.py`, `fast_momentum.py`, `ema_angle.py`, `bollinger_squeeze.py`, `mtf_macd.py`, `macd_accel.py`, `atr_compression_signals.py`, `is_cooldown_active`, `r2_trend_signals.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `init_db()` connect `init_db` to `add_signal`, `get_momentum_stats`, `signal_schema.py`, `decider_run.py`, `__init__.py`, `ma_cross.py`, `r2_rev.py`, `hh_hl.py`, `r2_rev_5m_signals.py`, `_get_conn`, `zscore_pump.py`, `rs.py`, `get_cooldown`, `hermes-trades-api.py`, `run`, `price_collector.py`, `rs_signals.py`, `backtest_ema20_50`, `ma300_candle_confirm_signals.py`, `hh_hl_signals.py`, `record_cooldown_start`, `mtf_macd.py`, `is_cooldown_active`, `r2_trend_signals.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **What connects `PYTHONPATH`, `start-litellm.sh script`, `wandb-sync.sh script` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `hl-sync-guardian.py` be split into smaller, more focused modules?**
  _Cohesion score 0.028470111448834854 - nodes in this community are weakly interconnected._
- **Should `add_signal` be split into smaller, more focused modules?**
  _Cohesion score 0.027795031055900622 - nodes in this community are weakly interconnected._
- **Should `get_momentum_stats` be split into smaller, more focused modules?**
  _Cohesion score 0.055152394775036286 - nodes in this community are weakly interconnected._