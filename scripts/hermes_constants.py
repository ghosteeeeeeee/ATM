#!/usr/bin/env python3
# DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!

import os

# ── Base directories (mirrored from paths.py — single source for path constants) ──
HERMES_DATA = os.environ.get(
    'HERMES_DATA_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
)
WWW_DATA = os.environ.get('WWW_DATA_DIR', '/var/www/hermes/data')

# ── Derived: DB paths ─────────────────────────────────────────────────────────
RUNTIME_DB     = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

# ── Derived: JSON / state files ──────────────────────────────────────────────
LOSS_COOLDOWN_FILE   = os.path.join(HERMES_DATA, 'loss_cooldowns.json')
FLIP_COUNTS_FILE     = os.path.join(WWW_DATA, 'flip_counts.json')

# ── Live Trading Toggle ───────────────────────────────────────────────────────
# Master kill switch — True = live trading enabled, False = paper only.
# DO NOT OUCH - If it is set to false then disable all real-money execution across the entire system - there is probably a critical bug.
# If this is set to false then DO NOT re-anble it, ask T, don't change any related flag unless T says so.
LIVE_TRADING_ENABLED = True

SHORT_BLACKLIST = {
    # High-volatility / inverse-beta tokens (shorting meme coins = lottery)
    'XLM','SNX','NIL','DYDX','IP','TRB','ETHFI','OP','EIGEN','COMP','NEAR','S','VVV','DOT','ICP','IMX','ATOM','SUI','LAYER','INJ','FIL','BERA','ETC','DYM','MAVIA','MEME','INIT','SOPH','XAI','ZEC','GAS','BLAST','MELANIA','BTC','ZETA','SPX','DOGE','ARK','CRV','RUNE','AR',
    'TST','NXPC','ARB','TRUMP','LDO','APT','CELO','SEI',
    'ACE','YZY','ZEREBRO','WLFI','HBAR','MEGA',
    # Historical 0% SHORT win rate (2026-04-01 analysis):
    'SOL','MEW',        # avg SHORT pnl: deeply negative, bull market leader
    'XPL','ZRO','NEO','GMT','FTT','HYPE',
    'YGG','IO','USUAL','FOGO',
    # 0% SHORT win rate — add fresh
    'POL','DOOD','SYRUP',
    # Additional high-beta / recent pumps (shorting pumps = catching knives)
    'POPCAT',  # meme pump history
    'VIRTUAL', 'MELANIA', 'FARTCOIN',  # meme coins
    # 2026-04-01: tokens with negative avg SHORT returns
    'RENDER', 'WLD', 'PORT3',
    # 2026-04-01: sketchy volume and price action
    'BOME',
    # 2026-04-01: persistent losses on both sides
    'USTC',   # both sides losing: avg LONG=-4.5%, avg SHORT=-0.3%
    'RSR',    # both sides losing: avg LONG=-3.5%, avg SHORT=-1.1%
    # Solana chain tokens — indexed on HL but NOT tradeable (orders fail silently,
    # guardian opens/closes phantom positions). Block both directions.
    'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA', 'LOOM',
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    'SAGE', 'SAMO', 'DUST', 'HNT',
    # 2026-04-02: phantom orders — tokens generating guardian_missing closes via
    # openclaw systemd timers firing. Add to both SHORT and LONG blacklists.
    'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',
    # 2026-04-02: persistent losing SHORT directions (loss cooldown streak)
    'MINA',   # SHORT: streak=2, 4h cooldown, persistent losses
    # 2026-04-02: phantom positions — guardian_missing loop (all +0.00%)
    'RLB', 'RNDR', 'SHIA', 'AI16Z', 'BADGER', 'BLZ', 'FXS',
    'HPOS', 'MATIC', 'UNIBOT', 'MKR', 'MYRO',
    # 2026-04-04: systematic SHORT losses (net<=$-2.50, phantom trades excluded)
    'ENA',     # SHORT net: -$5.41 (1 loss: conf-1s -$5.41)
    'PENGU',   # SHORT net: -$4.36 (1 loss: conf-1s -$4.36)
    # 2026-04-10: CFX — persistent losses on SHORT, phantom order issues on HL
    'CFX',
    # 2026-04-11: SAND — blocklisted both directions
    'SAND',
    # 2026-04-19: STABLE — block both directions. Stablecoin pairs have no directional
    # thesis and generate phantom trades via guardian_missing closes.
    'STABLE',
    # 2026-04-19: PAXG — block SHORT. TP/SL rejected by HL (asset=187), guardian
    # self-closes on regime breach. No HL SL protection for SHORT entries.
    'PAXG',
    # 2026-04-22: APE — block both directions
    'APE',
    # 2026-04-22: CRV — block both directions
    'CRV',
    # 2026-04-22: PENDLE, POLYX — block both directions
    'PENDLE', 'POLYX',
    # 2026-04-22: BIO — block both directions
    'BIO',
    # 2026-04-24: REZ, HMSTR, BNB — block both directions (DOGE SHORT immediate ATR
    # self-close issue — tokens with near-zero ATR getting SL=0 from ATR engine, causing
    # instant HARD_SL_CLOSE failures. Blocking both directions until root cause fixed.)
    'REZ', 'HMSTR', 'BNB',
}
LONG_BLACKLIST = {
    # 2026-04-22: BIO — block both directions
    'XLM','SNX','NIL','DYDX','IP','TRB','ETHFI','OP','EIGEN','COMP','NEAR','S','VVV','DOT','ICP','IMX','ATOM','SUI','LAYER','INJ','FIL','BERA','ETC','DYM','MAVIA','MEME','INIT','ZEC','GAS','BLAST','MELANIA','YZY','ZETA','BIO','DOGE','MEW',
    'TST','SEI', 'ACE', 'KAS', 'PROVE', 'BOME', 'USTC', 'RSR',
    # 2026-04-24: REZ, HMSTR, BNB — block both directions
    'REZ', 'HMSTR', 'BNB',
    # Solana chain tokens — indexed on HL but NOT tradeable
    'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA', 'LOOM',
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    # 2026-04-02: phantom orders via openclaw systemd timers
    'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',
    # 2026-04-02: persistent losing LONG directions (loss cooldown streaks)
    'AERO', 'CHILLGUY', 'LIT', 'DOT', 'ANIME',  # LONG streaks
}
BROAD_MARKET_TOKENS = {'SOL', 'BTC'}

# Signal source blocklist — block ENTIRE signal sources that are broken/baselined
# Blocked sources will be filtered out at the signal_schema.py level before hotset
SIGNAL_SOURCE_BLACKLIST = {
    # COMMENTED OUT 2026-05-05 — Redundant with Layer 2 kill-switches in signal_schema.py add_signal().
    # Kept for reference during testing.
    # NOTE (2026-04-18): 'hzscore' removed from blacklist — compute_score never generates
    # it solo (always 'momentum'). Only hzscore+/hzscore- are written via _run_mtf_macd_signals
    # as directional sub-sources in merged signals, which are not in the blacklist.
    # 'hzscore' was blocking hzscore+,hzscore- combos that historically had 58% WR.
    # 'rsi-confluence',  # 0% WR across 7+ trades — suppress entirely
    # 'rsi_confluence',  # same source, underscore variant (signal_type field)
    # 2026-04-18: BLOCK rsi as a component — it adds no predictive value (mtf-momentum,rsi
    # has 56.7% rejection rate). It contaminates good signals and hurts win rate.
    # 'rsi',
    # 2026-04-13: Solo sources with no independent confirmation — block at trade entry.
    # pct-hermes,vel-hermes combo is tracked in SCORING_TABLE for boost purposes.
    # Both pct-hermes and vel-hermes are individually BLOCKED in SIGNAL_SOURCE_BLACKLIST
    # (solo sources with no independent confirmation). The combo survives because the
    # blacklist only matches individual entries, not compound source strings.
    # BUG FIX (2026-04-13): bare pct-hermes = combo-only, never solo. Block it here so it
    # can't slip through the hot-set preservation filter (ai_decider.py line 1742).
    # 2026-04-19: BLOCKED — solo source with no independent confirmation (overturned 2026-05-05)
    # vel-hermes- unblocked for re-test: 45% WR, +0.404% avg PnL — our best avg SHORT signal.
    # vel-hermes+ stays blocked: WR=31%, avg=-0.127%, negative total PnL.
    # NOTE: 'vel-hermes' bare sentinel removed — vel-hermes+/vel-hermes- now handled individually.
    # 'vel-hermes+',  # kept blocked: 31% WR, -0.127% avg, negative total PnL
    # vel-hermes- intentionally NOT here — test re-enabled 2026-05-05
    # FIX (2026-04-18): hwave removed — compute_score never generates bare hwave.
    # Only hwave+/hwave- are written as directional sub-sources in merged signals.
    # hwave was blocking hwave+,hwave- combos that historically had good WR.
    # 'rsi-hermes',
    # 'hmacd_bare+-',  # bare MTF disagreement — both + and - present (merge artifact)
    # 'hmacd_bare-+',  # bare MTF disagreement — both - and + present (merge artifact)
    # NOTE: hzscore+,hzscore- merge artifacts are now IMPOSSIBLE because
    # _run_mtf_macd_signals generates directional suffixes (+/-) per direction.
    # Both + and - for same token+direction can't coexist to merge.
    # 2026-04-20: support_resistance blocked — underperforming in backtest
    #'support_resistance',
    # 'conf-1s',
    # 2026-04-19: BLOCK hzscore- and bare hzscore — losing signal, blocks itself out
    # 2026-04-20: hzscore+ UNBLOCKED — directional variant with independent confirmation
    # 2026-04-20: hzscore+ BLOCKED again — combining with ma_fast produces wrong direction
    #'hzscore-',   # hzscore-/vel-hermes- and all combos — bad WR
    #'hzscore+',   # wrong direction when combined with ma_fast SHORT
    # 'hzscore',    # bare hzscore (no directional suffix)
    # 2026-04-19: BLOCK pattern_scanner — too many false positives, kills win rate
    # 'pattern_scanner',
    # 2026-04-20: BLOCK pct-hermes- directional variant — solo source, no independent confirmation
    # pct-hermes- fires SHORT at price near BOTTOM of range (catches falling knives). Block it.
    # pct-hermes+ is CONTROLLED BY FLAG (PCT_HERMES_PLUS_ENABLED=True) — 100% WR, +$2.31.
    # Also add exact-match entries so they block even in multi-signal combos
    # (e.g. 'hzscore+,pct-hermes-' would bypass without this).
    # 'pct-hermes-',
    # 'pct-hermes+' REMOVED from blacklist 2026-05-05 — Layer 2 flag PCT_HERMES_PLUS_ENABLED controls it
    # 'pct-hermes',   # bare — combo-only; controlled by PCT_HERMES_ENABLED
    # 2026-04-20: BLOCK ma_cross — longs catastrophic (-1800 to -4000% net), shorts marginal.
    # Golden/death cross too lagging. Confirmed via 163-token backtest: 8/50 SHORT >> 10/200.
    #'ma-cross',
    # 2026-04-22: BLOCK r2_rev — losing signal source, removed from active trading
    # 'r2_rev',
    # 2026-04-26: BLOCK oc-zscore-v9 +/- variants — external signal at minimum threshold
    # (val=2.0 = exactly the threshold, barely above floor), conf=81%, cannot verify
    # OC's internal z-score calc (lookback unknown, data source unknown). Being
    # conflated by the compactor with valid signals to hit 99% confidence, masking
    # mediocre signal strength. Blocks all directional variants.
    # 'oc-zscore-v9+',
    # 'oc-zscore-v9-',
    # 'oc-zscore-v9',
    # 2026-04-27: BLOCK oc-mtf-rsi — underperforming signal, no edge in backtest
    # 'oc-mtf-rsi',
    # 'oc-mtf-rsi+',
    # 'oc-mtf-rsi-',
    # 'oc-mtf-macd+',
    # 2026-05-05: BLOCK gap-300- — 14.3% WR, -1.52% PnL across 7 trades. Worst active loser.
    # 'gap-300-',
    # 'gap300-5m+',
    # 'gap300-5m-',
    # 'gap-300+',
    # 2026-05-05: BLOCK fast-momentum- — losing signal (controlled by FAST_MOMENTUM_ENABLED flag)
    # 'fast-momentum-',
    # 2026-05-05: BLOCK ma-cross-5m+ — WR=19%, avg=-0.185%, total=-$3.88 across 21 trades.
    # ma-cross-5m- (SHORT) has WR=56% avg=+0.68% so only block LONG variant.
    # 'ma-cross-5m+',
    # 2026-05-05: BLOCK hhh-long4/hhh-long5 — WR=22-33%, negative total PnL across 15 trades.
    # hhh-short4/5 remain unblocked (proven SHORT combos).
    # 'hhh-long4',
    # 'hhh-long5',
    # 2026-05-05: BLOCK vel-hermes+ — WR=31%, avg=-0.127%, negative total PnL.
    # vel-hermes- is already blocked via bare 'vel-hermes' base match.
    # 'vel-hermes+',
    # 2026-05-05: pct-hermes+ REMOVED from blacklist — 100% WR, +$2.31 on 3 trades.
    # Controlled by PCT_HERMES_PLUS_ENABLED flag. pct-hermes- remains blocked (catches knives).
    # 2026-05-05: pct-hermes bare sentinel REMOVED — now controlled by *_ENABLED flags.
    # pct-hermes+ unblocked above, pct-hermes- remains blocked via line below.
    # 'pct-hermes-',
    # 'pct-hermes',   # bare — combo-only, no standalone value; blocked via *_ENABLED
}
SERVER_NAME = 'Hermes'
MAX_OPEN_POSITIONS = 5   # max open paper positions across all enforcement points

# ── Scanner Position Limits ─────────────────────────────────────────────────────
# Unified limits for scanner slot allocation (unified_scanner.py)
# These prevent over-concentration in any single category
MAX_HYPE_POSITIONS = 5   # max open positions in top-hype tokens
MAX_SOL_POSITIONS  = 5   # max open positions in SOL-tier tokens
MAX_TOTAL_POSITIONS = 10  # max total open positions across all tokens

# ── Speed Tracker Constants ──────────────────────────────────────────────────────
# Centralized speed/momentum thresholds — used by signal_gen.py, decider_run.py,
# position_manager.py, and speed_tracker.py.
# SPEED FEATURE: filters slow/stale tokens from signal generation and hot-set.
SPEED_MIN_THRESHOLD   = 50    # pctl < 20 → token blocked from signal generation
SPEED_BOOST_THRESHOLD = 70    # pctl >= 70 → entry threshold lowered 5% (easier entry)
SPEED_BOOST_FACTOR   = 0.95  # multiply entry threshold by this (lower = easier)
SPEED_HOTSET_WEIGHT  = 0.25  # 25% weight for speed in hot-set effective_conf calculation
                              # Formula: speed_pts = (speed_pctl - 50) / 100 × SPEED_HOTSET_WEIGHT × sig_conf
SPEED_HOTSET_THRESHOLD = 80   # pctl >= 80 → qualifies for speed-based hot-set boost
SPEED_ABS_MIN_THRESHOLD = 2.5  # % — absolute speed floor per 5m bar. Tokens with
                              # abs_speed < this are blocked regardless of percentile.
                              # Derived from retrospective: abs_speed >= 2.5% turns the
                              # system profitable (58 trades, 41% WR, +11.86% net).
                              # The percentile gate (SPEED_MIN_THRESHOLD=20) and the abs
                              # gate are BOTH applied — token must pass BOTH checks.
SPEED_HOTSET_BONUS   = 0.15  # +15% score boost for pctl >= 80 (legacy, used in compaction)
# ── Velocity Window Params (speed_tracker.py) ──────────────────────────────────
# Windowed avg replaces single-point vel_5m to avoid noise from one ref candle.
# vel_5m is now the MEAN of the last VEL_5M_WINDOW candle returns (per-candle %).
# STALE threshold is also per-candle, so it needs to be much smaller than the
# old 0.2% single-point value (which measured total move over 5 candles).
VEL_5M_WINDOW  = 5    # candles to average for 5m velocity  (5 = 5 min for 1m data)
VEL_15M_WINDOW = 15   # candles to average for 15m velocity (15 = 15 min for 1m data)
VEL_STALE_THRESHOLD_PCT = 0.05  # % per candle — below this = "flat" for stale detection
                                        # 0.05%/candle × 5 candles ≈ 0.25% total = old 0.2% feel
                                        # but smooths micro-noise from single ref candles
OVEREXTENDED_THRESHOLD  = 3.0  # % — vel must exceed this to be "overextended" (per-candle windowed)
STALE_WINNER_TIMEOUT_MINUTES = 30  # close winners flat for 30+ min
STALE_LOSER_TIMEOUT_MINUTES = 15   # cut losers flat for 15+ min
STALE_WINNER_MIN_PROFIT = 1.0    # % profit required to be a "winner"
STALE_LOSER_MAX_LOSS   = -1.0   # % loss required to be a "loser"

# ── Cascade Flip Constants ──────────────────────────────────────────────────────
# Used by cascade_flip.py and position_manager.py
CASCADE_FLIP_ENABLED = False  # Master toggle — set True to enable cascade flip
CASCADE_FLIP_MAX     = 3      # max flips per token before permanent lockout

# ── Trade Sizing Constants ──────────────────────────────────────────────────────
DEFAULT_TRADE_SIZE_USDT = 11.0  # local DB signal-level default for amount_usdt
                                 # NOTE: do NOT use this for PnL calculations — use
                                 # hl_notional_usdt (actual HL notional) or
                                 # hype_realized_pnl_usdt (HL ground-truth) instead.
HL_MIN_NOTIONAL_USDT     = 11.0 # HL minimum notional ($10 + $1 buffer)

# ── Support & Resistance Signal Constants ─────────────────────────────────────
# Used by rs_signals.py (top-level) and signals/rs.py (signals/ scanner)
# NOTE: signals/rs.py had hardcoded values that diverged from this file.
#       All RS constants are now centralized here.
RS_SIGNAL_TYPE       = 'support_resistance'
RS_LOOKBACK_CANDLES  = 4700   # candles to analyze (~3+ days of 1m)
RS_LEVEL_LOOKBACK    = 300     # swing high/low detection window
RS_ATR_PERIOD         = 30     # ATR lookback for proximity normalization
RS_CLUSTER_ATR       = 1.0   # cluster levels within 1.0 * ATR of each other
RS_PROXIMITY_K       = 0.70   # fire if price within 0.70 * ATR of a level
RS_MIN_TOUCHES       = 5      # minimum touches for valid level (was 3)
RS_DECIDER_MIN_TOUCHES = 80   # minimum touches for decider to approve — below this, trade is penalized/blocked (was 150)
RS_TOUCH_HARD_CAP       = 120  # block signals when touch_count >= 120 — exhausted/trampled levels have 0% WR above this (was 150, raised to 180 but still too high)
RS_LEVEL_BROKEN_LOOKBACK = 200  # candles to check for level-invalidation (was hardcoded 20) — ~8hrs on 1m; catches support/resistance flips
RS_DECIDER_ZBONUS_TOUCHES = 50  # relaxed threshold (50 vs 100) when |z_score| > 2.5 — strong momentum offsets weak level
RS_DECIDER_ZBONUS_ZSCORE = 2.5  # z-score threshold for relaxed touch requirement
RS_DECIDER_CONF_PENALTY = 15   # confidence point deduction when touches below threshold
RS_DECIDER_CONF_FLOOR  = 60   # effective confidence below this → trade is blocked (was 55)
RS_BROKEN_SHORT_ENABLED = True  # DISABLED — broken support fires SHORT but price often continues up, counter-trend trap (29% WR); better path: broken support → LONG on recovery instead
RS_BROKEN_RESISTANCE_LONG_ENABLED = True  # DISABLED — broken resistance LONG fires when price breaks through resistance, expecting bounce, but momentum is bearish and price continues down (BLUR/BRETT loss pattern)
RS_COOLDOWN_HOURS    = 4      # cooldown between RS signals per token+direction (signals/rs.py uses 4h)
RS_MIN_CONFIDENCE    = 50     # minimum confidence (global floor)
RS_MAX_CONFIDENCE    = 88     # R&S is structural — cap below momentum signals

# Recency weighting — fresh levels outperform ancient ones
RS_RECENCY_WINDOW    = 100    # lookback for recency-weighted touch count
RS_RECENCY_BOOST_K   = 3.0   # multiplier: each recent touch counts as K ancient touches

# Bounce confirmation — what counts as a "touch" off a level
RS_BOUNCE_LOOKBACK   = 6     # candles to check for bounce confirmation
RS_BOUNCE_THRESH_ATR = 1.00  # touch: price came within 1.00 * ATR(14) of the level
RS_ATR_DIST_FALLBACK   = 999  # fallback value for atr_dist when atr_pct is 0 (degenerate) — used in signal dict
RS_SOURCE_PREFIX     = 'rs'  # signal source prefix for logging

# ── ATR TP/SL Constants ────────────────────────────────────────────────────────
# Used by position_manager.py and self_close_watcher.py for ATR-based SL/TP
#
# Trailing SL / TP — _collect_atr_updates / tpsl_utils.compute_atr_sl_tp
ATR_SL_MIN             = 0.007   # 0.50% floor
ATR_SL_MAX             = 0.012    # 1% cap
ATR_TP_MIN             = 0.015  # 1.5% floor
ATR_TP_MAX             = 0.05    # 5% cap
ATR_TP_K_MULT          = 1.25   # TP tighter than SL: k_tp = k × 1.25
# Only push SL/TP to HL when delta exceeds this threshold
ATR_UPDATE_THRESHOLD   = 0.0015  # 0.15% — delta gate for HL order updates

# Acceleration-phase trailing — _collect_atr_updates (first candle against us, we're out)
ATR_SL_MIN_ACCEL   = 0.015   # 0.50% floor — was 0.30%, raised to stop cutting winners
ATR_TP_MIN_ACCEL   = 0.015   # 0.50% floor — book profit fast

# Initial entry SL/TP — get_trade_params (fallback when no ATR available)
ATR_SL_MIN_INIT    = 0.01  # 0.05% — new trades get breathing room (no acceleration squeeze)
ATR_SL_MAX_INIT    = 0.015  # 0.07% — new trade SL cap
SL_PCT_FALLBACK    = 0.01   # 1.5% if ATR unavailable
TP_PCT_FALLBACK    = 0.03    # 8% fallback target
STOP_LOSS_DEFAULT  = 0.01   # 1.5% hard fallback
SL_PCT_MIN        = 0.01    # 1% minimum SL for any trade (hard floor)

# ── Loss Cooldown Constants
# Incremental: streak=1 → 10min, streak=2 → 20min, streak=3 → 40min, ...
# Formula: hours = min(LOSS_COOLDOWN_BASE * 2^(streak-1), LOSS_COOLDOWN_MAX)
# Synced: hl-sync-guardian.py, position_manager.py, cascade_flip.py, signal_schema.py
LOSS_COOLDOWN_BASE     = 10 / 60   # 10 min for 1st consecutive loss (streak=1)
LOSS_COOLDOWN_MAX      = 40 / 60   # cap at 40 min after 3+ consecutive losses
WIN_COOLDOWN_MINUTES   = 5         # block same direction for 5 min after a win

# ── ATR k Multiplier Constants ────────────────────────────────────────────────
# Base k: _atr_multiplier(atr_pct) — volatility-driven SL/TP scaling
# atr_pct = ATR / entry_price
#   < 1%  → k=1.0  (low volatility — tight stops)
#   > 3%  → k=2.5  (high volatility — wide stops)
#   1–3%  → k=2.0  (normal — balanced stops)
ATR_K_INITIAL      = 1.2   # initial SL only — wider than trailing k, floor at MIN_SL_INIT (0.50%)
ATR_K_LOW_VOL      = 0.5   # trailing/accel SL — atr_pct < 1%
ATR_K_NORMAL_VOL   = 1.0  # trailing/accel SL — 1.25% <= atr_pct <= 3%
ATR_K_HIGH_VOL     = 0.25   # trailing/accel SL — atr_pct > 3%
ATR_PCT_LOW_THRESH = 0.01  # 1%
ATR_PCT_HIGH_THRESH= 0.015  # 3%

# ── ATR Fallback ───────────────────────────────────────────────────────────────
# Used when real ATR cannot be fetched (e.g., unprotectable coins first-seen).
# Represents a mid-range ATR assumption — NORMAL_VOL tier.
ATR_PCT_FALLBACK    = 0.03  # 2% assumed ATR — fallback when atr_cache returns None

# ── Trend Purity Signal ───────────────────────────────────────────────────────
# trend_purity_signals.py — tighter params = fires sooner
TP_MIN_GAP_PCT           = 0.15  # was 0.30 — price must be this far above EMA to fire LONG
TP_PURITY_THRESH         = 0.45  # was 0.55 — fraction of lookback bars above EMA
TP_LOOKBACK              = 15    # was 20   — shorter window = faster reaction
TP_SHORT_CRASH_THRESH     = -0.75 # was -1.0 — gap_pct must be >= this below EMA to fire SHORT
TP_SHORT_UPTREND_PURITY   = 0.60  # was 0.65 — uptrend purity needed before crash SHORT fires

# Candle staleness threshold for signal generators (seconds)
# Both volume_1m and volume_hl must use the same value to ensure consistent
# signal quality filtering across all volume-based signals.
CANDLES_STALENESS_SEC = 120   # 2 minutes — candles older than this are skipped

# Phase tiers for _atr_sl_k_scaled (string phase → numeric tier)
PHASE_TIER_NEUTRAL      = 0
PHASE_TIER_BUILDING     = 1
PHASE_TIER_ACCELERATING = 2
PHASE_TIER_EXHAUSTION   = 3
PHASE_TIER_EXTREME      = 4

# Phase-to-k multipliers applied on top of base k from _atr_multiplier
# ACCELERATING phase: mult < 1.0 — first candle against us, we're out
K_PHASE_ACCEL_STALL     = 0.06   # stalling + accelerating = momentum fading, snap out
K_PHASE_ACCEL_FAST      = 0.05   # fast momentum (pctl>=70) but first reversal = out
K_PHASE_ACCEL_SLOW      = 0.04   # low speed = no room needed, stay tight
# EXHAUSTION phase: 1.25–1.5×
K_PHASE_EXH_STALL       = 0.02   # stalling exhaustion = snap out faster
K_PHASE_EXH_FAST        = 0.03   # fast momentum
K_PHASE_EXH_SLOW        = 0.02   # slow momentum
# EXTREME phase: 1.5× max
K_PHASE_EXT_STALL       = 0.01   # stalling extreme
K_PHASE_EXT_FAST        = 0.02   # fast extreme

# Phase percentile thresholds — ONE source for phase classification
# Used by signal_gen.detect_phase() and tpsl_utils._phase_from_pct()
# Must be consistent across both — change once, system-wide effect
PHASE_BUILDING     = 60    # percentile ≥60 → momentum starting
PHASE_ACCELERATING  = 70   # percentile ≥75 → strong momentum
PHASE_EXHAUSTION    = 88   # percentile ≥88 → late phase, watch for exit
PHASE_EXTREME       = 95   # percentile ≥95 → exhaustion/mean-reversion territory
PHASE_NEUTRAL       = 50   # percentile ≥50 → neutral (no strong direction)
PHASE_VEL_STALL_THRESH = 0.0  # velocity ≤ 0 = stalling (negative velocity at accel+ phase)
PHASE_ACCEL_FAST_THRESH = 70  # speed_percentile ≥70 → fast momentum branch in _atr_sl_k_scaled

# ── Wrong-side stall detection ────────────────────────────────────────────────
WRONG_SIDE_AVG_PCT_THRESH = 1.0   # wrong-side trigger: avg counter move >= 1.5%

# ── Pause switches ─────────────────────────────────────────────────────────────
# Flip to True to disable without restarting anything. Flip back to False to re-enable.
MACD_EXIT_PAUSED = False   # Disable macd_rules.py exit signals (ATR TP/SL handles closes)
REGIME_BULL_FLIP_ENABLED = False  # Disable regime_bull_flip exit (fires too often on short timeframe)

# ── HH_HL Signal (Higher Highs / Higher Lows structure) ────────────────────────
# hh_hl_signals.py — swing structure detection on 1m close prices
# NOTE: price_history is close-only (open=high=low=close per row), so swing
# detection uses rolling proxy high/low of closes. window=4 is the minimum
# viable half-width for close-only data — produces ~50-80 swings per 300 candles.
HH_HL_LOOKBACK          = 200   # candles for swing detection (200 = ~3h20m at 1m)
HH_HL_SWING_WINDOW      = 4     # half-width for proxy high/low (min viable for close-only)
HH_HL_MIN_SEP           = 3     # minimum candle separation between consecutive swings
HH_HL_BREAKOUT_THRESHOLD = 0.0015   # price must exceed prior swing by this fraction (0.15%)
                                          # FIX (2026-05-12): raised from 0.0005 (0.05%) to 0.0015 (0.15%)
                                          # 0.05% was too loose — BERA @ $0.40 only needs $0.0002 to trigger,
                                          # catching micro-noise at tops/bottoms of bounces. 0.15% = $0.0006
                                          # for BERA, $0.0368 for COMP — requires genuine structural breakout.
HH_HL_ATR_ENTRY_MIN     = 0.5   # breakout candle must be >= 0.5x ATR
HH_HL_SL_ATR_MULT       = 1.5   # SL = entry +/- SL_ATR_MULT * ATR
HH_HL_TP_ATR_MULT       = 3.0   # TP = entry + TP_ATR_MULT * ATR
HH_HL_MAX_HOLD_BARS     = 20    # auto-close if neither SL nor TP hit in this many bars
HH_HL_MAX_BARS_SINCE    = 10    # reject signal if breakout is older than this many bars
HH_HL_SHORT_RANGE_TOP_ATR = 0.5  # SHORT blocked if price > 20-bar high minus this many ATRs
                                        # FIX (2026-05-12): raised from 1.0 to 0.5 ATR. 1 ATR was too permissive —
                                        # BERA at 37% up in range cleared it. 0.5 ATR is tighter, shorts only fire
                                        # when truly near the bottom of the range.
HH_HL_LONG_RANGE_BOTTOM_ATR = 0.5 # LONG blocked if price < 20-bar low plus this many ATRs
                                        # Same rationale as SHORT — only enter LONGs with room to run.
HH_HL_COOLDOWN_MIN      = 15    # minutes between signals per token
HH_HL_CONFIDENCE_FLOOR  = 50
HH_HL_CONFIDENCE_CAP    = 88
HH_HL_BASE_CONFIDENCE    = 62
HH_HL_STRUCT_BONUS_MAX  = 15    # per consecutive HH/HL pair
HH_HL_BREAKOUT_BONUS_MAX = 12   # bonus for strong breakout
HH_HL_RECENCY_BONUS_MAX = 8     # bonus for fresh signals

# ── Profit Monster ─────────────────────────────────────────────────────────────
# profit_monster.py — closes medium-profit positions (2-5%) at random intervals.
# Never touches losing positions.
PROFIT_MIN_PCT    = 0.8    # 0.5% floor — take profit at 0.5% and above
PROFIT_MAX_PCT    = 5.0    # 2.0% ceiling — don't hold for big moves
MAX_CLOSE_PER_WAKE = 3
SKIP_TOP_PCT      = 0     # don't touch the top 20% most profitable
FIRE_WINDOWS = {
    "A": (1, 3),     # 5-8 min — take profit faster
    "B": (8, 12),    # 8-12 min — slightly slower but still frequent
}

# ── Cut Loser ─────────────────────────────────────────────────────────────────
# cut_loser.py — closes medium-loss positions (-0.5% to -3%) at random intervals.
# Never touches profitable positions. Fire intervals A/B tested (10-15min vs 20-30min).
CUT_LOSER_ENABLED      = True
LOSS_MIN_PCT           = -3.0   # cut positions down to this threshold (more negative)
LOSS_MAX_PCT           = -0.5   # only cut if loss is <= -0.5% (don't cut tiny drawdowns)
CUT_LOSER_MAX_CLOSE    = 1      # max positions to close per wake
SKIP_BOTTOM_PCT        = 0      # don't touch the bottom 10% worst losers (let them recover)
CUT_LOSER_FIRE_WINDOWS = {
    "A": (5, 10),    # 5-10 min — cut faster
    "B": (10, 18),   # 10-18 min — slightly slower but still frequent
}

# ── Signal Kill Switches ───────────────────────────────────────────────────────
# Master kill switches for each signal family. True = signal can fire.
# False = signal is blocked at BOTH add_signal() (Layer 2) AND decider_run (Layer 3).
# Individual +/- variants controlled by *_PLUS_ENABLED / *_MINUS_ENABLED flags below.
PCT_HERMES_ENABLED       = False  # disabled 2026-05-06 — signals now fire via signals_runner (scripts/signals/)
PCT_HERMES_PLUS_ENABLED  = False   # pct-hermes+ — 100% WR, +$2.31, only good pct variant
PCT_HERMES_MINUS_ENABLED = True   # pct-hermes- — 46.2% WR in hzscore+,pct-hermes-,vel-hermes- combo (best SHORT)
VEL_HERMES_ENABLED       = False  # disabled 2026-05-06 — signals now fire via signals_runner (scripts/signals/)
VEL_HERMES_PLUS_ENABLED  = False  # vel-hermes+ — 31% WR, avg=-0.127%, blocked
VEL_HERMES_MINUS_ENABLED = True   # vel-hermes- — 45% WR, +0.404% avg, re-test enabled
HZSCORE_ENABLED          = False  # disabled 2026-05-06 — signals now fire via signals_runner (scripts/signals/)
HZSCORE_PLUS_ENABLED     = True   # hzscore+ — 31.3% WR, +13.92% PnL
HZSCORE_MINUS_ENABLED    = True   # hzscore- — 0% WR, -$1.14 (mixed, keep enabled for now)
HMACD_ENABLED            = False  # disabled 2026-05-06 — signals now fire via signals_runner (scripts/signals/)
HMACD_PLUS_ENABLED       = True   # hmacd_bare+ and hmacd_mtf+ LONG — kill-switch for LONG direction
HMACD_MINUS_ENABLED      = True   # hmacd_bare- and hmacd_mtf- SHORT — kill-switch for SHORT direction
# ── MTF MACD (extracted from signal_gen.py, fires via signals_runner) ──────────
# hmacd_bare (signals/hmacd.py): pure 15m+1H histogram agreement, no z-score filter
# hmacd_mtf  (signals/mtf_macd.py): z-score threshold + histogram agreement + cascade boosts
# Both use: HMACD_ENABLED / HMACD_PLUS_ENABLED / HMACD_MINUS_ENABLED flags.
# Migrated from signal_gen.py inline — now fire via signals_runner (scripts/signals/).
# Registry scripts removed Layer 1 guards; Layer 2 (add_signal) handles per-source filtering.
# Actual kill-switch for momentum/mtf-momentum is now in the Momentum Killswitches section below.
# NOTE: Lines 373-384 removed 2026-05-06 — were duplicate with inconsistent values.
# See Momentum Killswitches section for current authoritative values.

MIN_GAP_PCT_LONG         = 0.15  # minimum gap above EMA300 to fire LONG (was0.15 — lowered for mid-cap tokens like ZORA/FET max gap ~0.14%)
MIN_GAP_PCT_SHORT        = 0.15  # minimum gap below EMA300 to fire SHORT (was 0.30 → 0.20 for flat market)
# ── Accel-300 Behavioral Params (accel_300_signals.py) ─────────────────────────
ACCEL_300_PERIOD          = 300  # EMA(300) on 1m prices
ACCEL_300_LOOKBACK        = 30   # bars ago when price was on the other side of EMA300 (was 100 → tightened 2026-06-08 to match actual signal behavior)
ACCEL_300_PERSISTENCE_BARS = 2   # must be persistently above/below EMA for this many consecutive bars (was 4 → tightened 2026-06-08)
ACCEL_300_MIN_GAP_GROWTH  = 0.05 # gap must grow by at least this % vs PERSISTENCE_BARS ago (was 0.01 → tightened 2026-06-08 to match actual signal behavior)
ACCEL_300_MIN_GAP_EXPANSION = 0.01 # price must be this much farther from EMA than at cross bar (gap expansion gate — both directions)
ACCEL_300_MIN_GAP_PCT     = 0.20 # minimum gap above/below EMA300 to fire — was hardcoded in accel_300.py (was 0.15 → tightened 2026-05-11)
ACCEL_300_MIN_GAP_PCT_LONG  = 0.20  # keep existing — accel-300+ gap threshold
ACCEL_300_MIN_GAP_PCT_SHORT = 0.25   # NEW — tighter for SHORT only: 0.25 vs 0.20 for LONG (accel-300- has 40% WR vs 55% for accel-300+)
ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07  # NEW — stricter growth for SHORT (was 0.05 global) — SHORT side gets false breakouts that reverse
ACCEL_300_COOLDOWN_BARS   = 10   # dedup: only fire once per N bars per token+direction (was 12 → tightened 2026-05-11)
ACCEL_300_LOOKBACK_1M     = 700  # 1m prices to fetch per token (warmup + detection window)
ACCEL_300_ENABLED        = True   # accel-300+ — PRIMARY signal
ACCEL_300_COOLDOWN_MIN    = 1    # minutes between signals per token+direction
ACCEL_300_REGIME_SLOPE_PCT = 0.003  # minimum slope %/bar to fire LONG (>0) or SHORT (<0) — was hardcoded 0.015
ACCEL_300_SLOPE_WINDOW     = 20    # bars over which to compute regime slope (simple linear regression)
ACCEL_300_STALE_BARS       = 60   # max bars since EMA cross (bars_since_cross) — older = stale, skip (was 80 → tightened 2026-06-09)
ACCEL_300_STALE_BARS_SHORT  = 55   # NEW — stricter stale gate for SHORT only: SHORT side has 40% WR vs 55% for LONG, needs earlier entry
ACCEL_300_STALE_LOOKBACK   = 400  # detection bar must be within N bars of latest bar — older = stale, skip
ACCEL_300_MARGINAL_ACCEL_BARS = 3   # bars_since_cross threshold — only enforce marginal acceleration check above this (fire early on breakout)
ACCEL_300_BARS_UNKNOWN      = 999  # sentinel value when cross_bar is unknown (not found)
ACCEL_300_BAR_GAP_THRESH_SEC = 150  # bar-to-bar gap guard: threshold = max(this, mean_gap + 3*std_gap) — skip if data gap exceeds this many seconds
ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.50  # newest bar gap must be >= this fraction of signal bar gap (1.0 = no decay allowed, 0.5 = 50% decay allowed)
ACCEL_300_CROSS_LOOKBACK     = 100  # primary cross-bar search window: look this many bars back from signal bar (fallback searches to index 0)
# Token allowlist — only fire accel-300+ on tokens with >=50% historical WR
# (empty set = no filter, fire on all tokens)
ACCEL_300_TOKEN_ALLOWLIST = set()  # (empty set = no filter, fire on all tokens)
# Block accel-300+ if any of these co-signals are already present
ACCEL_300_BLOCK_COSIGS = {'ma-cross-5m+', 'pct-hermes+'}  # 16.7% / 35.7% WR
# ── Accel-300 Chop Filter (signals/accel_300.py) ─────────────────────────────────
# Suppress signals in choppy/ranging markets — all 3 conditions must be true to block
ACCEL_300_CHOP_CROSS_GAP_PCT   = 0.10  # gap at cross bar must be >= this
ACCEL_300_CHOP_EMA_ANGLE_PCT   = 0.04  # 50-bar EMA angle must be >= this
ACCEL_300_CHOP_AVG_GAP_PCT     = 0.50  # avg gap magnitude over 50 bars must be >= this
ACCEL_300_CHOP_LOOKBACK        = 50   # bars used for EMA angle and avg-gap chop checks

GAP_300_ENABLED          = False  # gap-300+ — 14.3% WR, -$1.52, worst active loser
GAP_300_PLUS_ENABLED      = False
GAP_300_MINUS_ENABLED     = False
MA_CROSS_ENABLED         = False   # ma_cross (short only historically)
MA_CROSS_PLUS_ENABLED     = False  # ma_cross+ — catastrophic losses
MA_CROSS_MINUS_ENABLED    = True
MA_CROSS_5M_ENABLED       = False
MA_CROSS_5M_PLUS_ENABLED   = False  # ma_cross_5m+ — WR=19%, blocked in blacklist
MA_CROSS_5M_MINUS_ENABLED = False
TL_BREAK_ENABLED         = False   # diagonal trendline breakout (new)
ATR_COMPRESSION_ENABLED  = True

# ── Per-Direction Signal Killswitches ─────────────────────────────────────────
# For each signal: _PLUS_ENABLED controls LONG, _MINUS_ENABLED controls SHORT.
# Default True so existing signals continue working. Set False to block one direction.
ATR_COMPRESSION_PLUS_ENABLED   = True    # atr_compression+ LONG
ATR_COMPRESSION_MINUS_ENABLED  = True    # atr_compression- SHORT
EMA9_SMA20_ENABLED       = False
EMA9_SMA20_PLUS_ENABLED         = False    # ema9_sma20+ LONG
EMA9_SMA20_MINUS_ENABLED        = True    # ema9_sma20- SHORT
EXHAUSTION_ENABLED       = False
EXHAUSTION_PLUS_ENABLED        = False    # exhaustion+ LONG
EXHAUSTION_MINUS_ENABLED       = True    # exhaustion- SHORT
GUPPY_ENABLED            = False
GUPPY_PLUS_ENABLED             = False   # guppy+ LONG
GUPPY_MINUS_ENABLED            = False   # guppy- SHORT
HH_HL_ENABLED            = False   # HH/HL breakout + pullback structure
HH_HL_PLUS_ENABLED            = True    # hh_hl+ LONG
HH_HL_MINUS_ENABLED           = True    # hh_hl- SHORT
MA300_CANDLE_ENABLED     = False
MA300_CANDLE_PLUS_ENABLED     = False    # ma300_candle_confirm+ LONG
MA300_CANDLE_MINUS_ENABLED   = True    # ma300_candle_confirm- SHORT
MACD_ACCEL_ENABLED       = False
MACD_ACCEL_PLUS_ENABLED       = False    # macd_accel+ LONG
MACD_ACCEL_MINUS_ENABLED      = True    # macd_accel- SHORT
R2_REV_ENABLED           = False  # r2_rev — blocked in blacklist
R2_REV_PLUS_ENABLED           = False   # r2_rev+ LONG
R2_REV_MINUS_ENABLED          = False   # r2_rev- SHORT
R2_TREND_ENABLED         = False
R2_TREND_PLUS_ENABLED        = False   # r2_trend+ LONG (was single flag only, SHORT only)
R2_TREND_MINUS_ENABLED       = False    # r2_trend- SHORT
TREND_PURITY_ENABLED     = False
TREND_PURITY_PLUS_ENABLED    = False    # trend_purity+ LONG
TREND_PURITY_MINUS_ENABLED   = True    # trend_purity- SHORT
VOLUME_HL_ENABLED        = True
VOLUME_HL_PLUS_ENABLED        = False    # volume_hl+ LONG
VOLUME_HL_MINUS_ENABLED       = True    # volume_hl- SHORT
EMA20_50_PLUS_ENABLED         = False    # ema20_50+ LONG
EMA20_50_MINUS_ENABLED        = False    # ema20_50- SHORT
MACD_1M_PLUS_ENABLED          = True    # macd_1m+ LONG
MACD_1M_MINUS_ENABLED         = True    # macd_1m- SHORT
ACCEL_300_PLUS_ENABLED        = True    # accel_300+ LONG
ACCEL_300_MINUS_ENABLED       = True    # accel_300- SHORT
COUNTER_FLIP_PLUS_ENABLED     = True    # counter_flip+ LONG
COUNTER_FLIP_MINUS_ENABLED    = True    # counter_flip- SHORT
HMACD_MTF_PLUS_ENABLED        = True    # hmacd_mtf+ LONG
HMACD_MTF_MINUS_ENABLED       = True    # hmacd_mtf- SHORT
RS_ENABLED               = True   # support_resistance
RS_PLUS_ENABLED               = True    # rs+ LONG
RS_MINUS_ENABLED              = True    # rs- SHORT
TL_BREAK_PLUS_ENABLED         = True    # tl_break+ LONG
TL_BREAK_MINUS_ENABLED        = True    # tl_break- SHORT

COUNTER_FLIP_ENABLED     = False   # controlled by counter_flip_signal.py independently

# ── EMA300 Angle Signal ────────────────────────────────────────────────────────
# ema_angle.py — detects when EMA300 starts lifting from flat (LONG setup)
# or flattening from steep (SHORT setup). Fires when angle crosses steep territory
# with positive momentum. Designed as confluence signal, always pairs with another.
#
# LONG (ema-angle+): flat → steep transition using arctan(Δprice_20 / price) in RADIANS
#   STEEP threshold = 0.5 rad (26.6°)  |  CEILING = 1.0 rad (45°)  |  FLAT_WINDOW = 10 bars
#   NOTE: T specified 0.5-1.0 rad directly as the thresholds
#   was_flat: all angles < 0.5 rad for last FLAT_WINDOW bars
#   is_steep: angle >= 0.5 rad AND < 1.0 rad
#   accelerating: angle_speed > EMA_ANGLE_MIN_SPEED
#
# SHORT (ema-angle-): angle <= p25 (25th percentile) with negative speed — unchanged
#
EMA_ANGLE_LOOKBACK          = 500   # candles for angle history and EMA300
EMA_ANGLE_SLOPE_PERIOD      = 20    # bars for slope calculation
EMA_ANGLE_SPEED_PERIOD      = 10    # bars for angle speed (rolling diff)
EMA_ANGLE_PERCENTILE_LONG   = 75    # p75 for LONG — angle must be this steep (unused, radian threshold used)
EMA_ANGLE_PERCENTILE_SHORT  = 25    # p25 for SHORT — angle must be this flat
EMA_ANGLE_STEEP_THRESHOLD_RAD = 0.5   # 30° — minimum angle for LONG steep territory (radians)
EMA_ANGLE_CEILING_RAD         = 1.0   # 45° — ceiling, don't fire into parabolic (radians)
EMA_ANGLE_FLAT_WINDOW         = 10    # bars to check was_flat before crossing
EMA_ANGLE_MIN_SPEED           = 0.00001  # minimum angle_speed (radians over speed_period) — must be positive for LONG
EMA_ANGLE_MIN_BARS          = 310   # minimum bars needed for EMA300 + angle calc
EMA_ANGLE_COOLDOWN_MIN      = 1    # minutes between signals per token+direction
EMA_ANGLE_ENABLED           = False
EMA_ANGLE_PLUS_ENABLED      = True   # ema-angle+ LONG
EMA_ANGLE_MINUS_ENABLED     = True   # ema-angle- SHORT
EMA_ANGLE_CONFIDENCE_BASE   = 62   # base confidence (structural bonus adds on top)
EMA_ANGLE_STEEP_BONUS_MAX   = 15   # max bonus when angle is in extreme territory
EMA_ANGLE_MOMENTUM_BONUS_MAX = 10   # max bonus when angle_speed is very high
EMA_ANGLE_RECENCY_BONUS_MAX = 8    # max bonus for fresh signals

# ── OpenClaw Signal Killswitches ───────────────────────────────────────────────
# oc_signal_importer.py reads OC workspace files and calls add_signal().
# Set to False to block all OC signal sources from entering the Hermes pipeline.
OC_MTF_MACD_ENABLED    = False  # oc-mtf-macd+, oc-mtf-macd- — BLOCKED
OC_RSI_ENABLED         = False  # oc-rsi+, oc-rsi- — BLOCKED (rsi only, no edge)
OC_MTF_RSI_ENABLED     = False  # oc-mtf-rsi+, oc-mtf-rsi- — BLOCKED in blacklist
OC_PENDING_ENABLED     = False  # oc-pending-breakout, oc-pending-* — BLOCKED

# ── Momentum Killswitches ──────────────────────────────────────────────────────
# NOTE: momentum+/momentum- had NO Layer 2 kill-switch in signal_schema.py add_signal().
# Adding here. Registry scripts (scripts/signals/) removed their Layer 1 guards,
# so Layer 2 is the only gate.
MOMENTUM_ENABLED          = False  # momentum bare — BLOCKED (no independent confirmation)
MOMENTUM_PLUS_ENABLED     = False  # momentum+ — BLOCKED
MOMENTUM_MINUS_ENABLED    = False  # momentum- — BLOCKED

# MTF Momentum: bare blocked, directional variants pass (keep directionality)
MTF_MOMENTUM_ENABLED      = False  # mtf_momentum bare — BLOCKED
MTF_MOMENTUM_PLUS_ENABLED = False  # BLOCKED 2026-05-06 — poison co-signal, 0% WR in combos
MTF_MOMENTUM_MINUS_ENABLED = False  # BLOCKED 2026-05-06 — poison co-signal, 0% WR in combos

# Phase Accel: same situation as momentum — removed Layer 1 guard from registry scripts
PHASE_ACCEL_ENABLED        = False  # phase_accel bare — BLOCKED
PHASE_ACCEL_PLUS_ENABLED   = True   # phase-accel+ — PASS (was not blacklisted)
PHASE_ACCEL_MINUS_ENABLED  = True   # phase-accel- — PASS (was not blacklisted)

# ── Standalone Executor Killswitches ───────────────────────────────────────────
# pump_hunter and zscore_pump are standalone executors — they manage their own
# positions and bypass the signal pipeline. Killswitches here prevent them from
# firing if enabled/disabled state gets out of sync after reboot.
PUMP_HUNTER_ENABLED        = False  # set False to block pump_hunter from firing
# DEPRECATED — zscore_pump_hunter.py is disabled.
# Pipeline-integrated version is signals/zscore_pump.py (uses tpsl_utils via signal_compactor).
ZSCORE_PUMP_ENABLED        = False  # True = old standalone would fire (BLOCKED — use signals/zscore_pump.py)
# Z-Score Pump (pipeline-integrated signal — migrated from standalone zscore_pump_hunter.py)
ZSCORE_PUMP_NEW_ENABLED    = False   # master kill-switch for signals/zscore_pump.py (new pipeline)
ZSCORE_PUMP_PLUS_ENABLED   = True   # zscore-pump+ LONG — PASS
ZSCORE_PUMP_MINUS_ENABLED  = True   # zscore-pump- SHORT — PASS
ZSCORE_PUMP_LOOKBACK       = 150     # default lookback bars for z-score computation
ZSCORE_PUMP_THRESHOLD           = 3.0    # was 2.2 — structural moves at 100-bar lookback
ZSCORE_PUMP_DIVERGENCE_VEL_THD  = -0.5   # was -0.3 — sharper rejection of tired moves
ZSCORE_PUMP_COOLDOWN_BARS  = 5     # bars before re-fire allowed (~10 min on 1m)
ZSCORE_PUMP_MIN_SIGNALS_FOR_TUNED = 15  # tokens need this many tuned signals before using tuned params
ZSCORE_PUMP_USE_TUNER        = False   # True = use tuned params from zscore_momentum_tuner.db; False = always use hermes_constants defaults

# ── Z-Score Divergence Filter ─────────────────────────────────────────────────
# When z-score is extremely elevated then CRASHING while price still makes marginal
# new highs = negative divergence = imminent reversal trap. These params gate it.
ZSCORE_PUMP_DIVERGENCE_ENABLED = True   # reject signals with negative divergence
ZSCORE_PUMP_DIVERGENCE_LOOKBACK = 30   # short-term lookback for spot momentum check (separate from signal lookback)
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.5  # z above this = overextended on spot lookback
ZSCORE_PUMP_DIVERGENCE_BARS     = 5     # need this many declining z-velocity bars to confirm

# ── MTP-ZScore (Multi-Timeperiod Z-Score) ───────────────────────────────────────
# Trend-following signal: ALL 3/3 periods (50/100/150-bar) must agree on direction.
# abs(z) used ONLY for bounds check; direction always from sign (z>0=LONG, z<0=SHORT).
MTP_ZSCORE_ENABLED         = False    # master kill-switch
MTP_ZSCORE_PLUS_ENABLED    = True    # LONG
MTP_ZSCORE_MINUS_ENABLED   = True    # SHORT

# Lookback periods (bars)
MTP_ZSCORE_LB_SHORT        = 14      # short/fast period
MTP_ZSCORE_LB_MID          = 50     # medium period
MTP_ZSCORE_LB_LONG         = 150     # long/structural period

# Per-period Z-Score bounds
# If |z| is BELOW Z_MIN → reject (not meaningful for this period)
MTP_ZSCORE_LB_SHORT        = 50     # short/structural period (was 14 — too fast, noise)
MTP_ZSCORE_LB_MID          = 100    # medium period (was 50)
MTP_ZSCORE_LB_LONG         = 150    # long/structural period
Z_SHORT_Z_MIN              = 1.5    # was 2.0 — 3x more signals, same/better WR
Z_SHORT_Z_MAX              = 5.0    # was 3.0 — cap only true blow-offs
Z_MID_Z_MIN                = 1.5    # was 2.0
Z_MID_Z_MAX                = 4.5    # was 3.0
Z_LONG_Z_MIN               = 1.5    # was 2.0
Z_LONG_Z_MAX               = 4.0   # was 3.0
MTP_ZSCORE_MIN_AGREE       = 3       # 3/3 — ALL periods must vote same direction
MTP_ZSCORE_BASE_CONF       = 80
MTP_ZSCORE_CONF_BONUS      = 5
MTP_ZSCORE_COOLDOWN_BARS   = 20     # was 5 — prevent signal spam

# ── Z-Score Rising (Momentum Onset Signal) ─────────────────────────────────────
# Fires when z-score CROSSES above threshold AND is rising (velocity > 0).
# Designed to catch pump starts while avoiding noise from persistently elevated z.
# Logic: prev_z < TH <= cur_z AND (cur_z - prev_z) > 0 → rising momentum onset
ZSCORE_RISING_ENABLED     = True   # master kill-switch
ZSCORE_RISING_PLUS_ENABLED = True   # LONG (z crossing above TH, rising)
ZSCORE_RISING_MINUS_ENABLED = True  # SHORT (z crossing below -TH, falling)
ZSCORE_RISING_LOOKBACK     = 20     # bars for z-score computation
ZSCORE_RISING_THRESHOLD    = 2.5    # z must cross this threshold
ZSCORE_RISING_VEL_BARS     = 5      # lookback for z-velocity (cur_z - z_N_bars_ago)
ZSCORE_RISING_COOLDOWN_BARS = 10    # bars before re-fire (~10 min on 1m)
ZSCORE_RISING_MAX_BARS     = 200    # max bars to load per token from DB
ZSCORE_RISING_CONF_MIN     = 50.0  # minimum confidence score
ZSCORE_RISING_CONF_SCALE   = 5.0   # confidence = conf_min + abs(z_curr) * scale
ZSCORE_RISING_CONF_MAX     = 95.0  # maximum confidence score

# ── Hot-Set Gate ────────────────────────────────────────────────────────────────
FAST_MOMENTUM_ENABLED     = False  # fast_momentum bare — BLOCKED
FAST_MOMENTUM_PLUS_ENABLED = True  # fast-momentum+ — PASS (was not blacklisted)
FAST_MOMENTUM_MINUS_ENABLED = False # fast-momentum- — BLOCKED (losing signal)

# ── Hot-Set Gate ──────────────────────────────────────────────────────────────
# HOTSET_ENABLED=True  → hot-set is the gate (default). Signals must survive
#                         signal_compactor compaction cycles before executing.
# HOTSET_ENABLED=False → hot-set bypass. The next PENDING signal that fires
#                         (after blacklist/cooldown/regime checks) executes
#                         immediately without surviving hot-set cycles.
HOTSET_ENABLED = True
# HH_HL_ENABLED — see Signal Family Killswitches section (line ~398)

# ── Confluence Gate ───────────────────────────────────────────────────────────
# When True (default): single-source signals are blocked from hot-set (require 2+ sources).
# When False: single-source signals are allowed to pass through.
CONFLUENCE_REQUIRED = True

# ── Accel-300 Standalone Bypass ──────────────────────────────────────────────
# When a single-source accel-300 has very high confidence, bypass confluence gate.
# Problem: confluence gate blocks pure accel-300 signals (no RS co-signal) even when
# accel-300 is very strong. Strong accel-300 alone should sometimes fire.
ACCEL_300_STANDALONE_BYPASS_ENABLED = False  # TEMPORARILY DISABLED — was firing too many weak pure-accel signals (40% WR)
ACCEL_300_STANDALONE_BYPASS_CONFIDENCE = 70  # kept for reference (not used when disabled)
