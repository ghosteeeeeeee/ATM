
#!/usr/bin/env python3
# DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!
SHORT_BLACKLIST = {
    # High-volatility / inverse-beta tokens (shorting meme coins = lottery)
    'BTC','ZETA','SPX','DOGE','ARK','CRV','RUNE','AR',
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
    # 2026-04-22: CHIP — block both directions
    'CHIP',
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
    'CHIP','ZETA','BIO','DOGE','MEW',
    'TST','SEI', 'ACE', 'KAS', 'PROVE', 'BOME', 'USTC', 'RSR',
    # 2026-04-24: REZ, HMSTR, BNB — block both directions
    'REZ', 'HMSTR', 'BNB',
    # 2026-04-28: accel-300+ blocked as signal source — add ONDO to LONG_BLACKLIST
    'ONDO',
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
    # NOTE (2026-04-18): 'hzscore' removed from blacklist — compute_score never generates
    # it solo (always 'momentum'). Only hzscore+/hzscore- are written via _run_mtf_macd_signals
    # as directional sub-sources in merged signals, which are not in the blacklist.
    # 'hzscore' was blocking hzscore+,hzscore- combos that historically had 58% WR.
    'rsi-confluence',  # 0% WR across 7+ trades — suppress entirely
    'rsi_confluence',  # same source, underscore variant (signal_type field)
    # 2026-04-18: BLOCK rsi as a component — it adds no predictive value (mtf-momentum,rsi
    # has 56.7% rejection rate). It contaminates good signals and hurts win rate.
    'rsi',
    # 2026-04-13: Solo sources with no independent confirmation — block at trade entry.
    # pct-hermes,vel-hermes combo is tracked in SCORING_TABLE for boost purposes.
    # Both pct-hermes and vel-hermes are individually BLOCKED in SIGNAL_SOURCE_BLACKLIST
    # (solo sources with no independent confirmation). The combo survives because the
    # blacklist only matches individual entries, not compound source strings.
    # BUG FIX (2026-04-13): bare pct-hermes = combo-only, never solo. Block it here so it
    # can't slip through the hot-set preservation filter (ai_decider.py line 1742).
    'pct-hermes',
    'vel-hermes',  # 2026-04-19: all variants blocked — solo source with no independent confirmation
    'vel-hermes+', # same — directional suffix doesn't add confluence value
    'vel-hermes-', # same
    # FIX (2026-04-18): hwave removed — compute_score never generates bare hwave.
    # Only hwave+/hwave- are written as directional sub-sources in merged signals.
    # hwave was blocking hwave+,hwave- combos that historically had good WR.
    'rsi-hermes',
    'hmacd+-',    # MTF disagreement — both + and - present (merge artifact)
    'hmacd-+',    # MTF disagreement — both - and + present (merge artifact)
    # NOTE: hzscore+,hzscore- merge artifacts are now IMPOSSIBLE because
    # _run_mtf_macd_signals generates directional suffixes (+/-) per direction.
    # Both + and - for same token+direction can't coexist to merge.
    # 2026-04-20: support_resistance blocked — underperforming in backtest
    'support_resistance',
    'conf-1s',
    # 2026-04-19: BLOCK hzscore- and bare hzscore — losing signal, blocks itself out
    # 2026-04-20: hzscore+ UNBLOCKED — directional variant with independent confirmation
    # 2026-04-20: hzscore+ BLOCKED again — combining with ma_fast produces wrong direction
    'hzscore-',   # hzscore-/vel-hermes- and all combos — bad WR
    'hzscore+',   # wrong direction when combined with ma_fast SHORT
    'hzscore',    # bare hzscore (no directional suffix)
    # 2026-04-19: BLOCK pattern_scanner — too many false positives, kills win rate
    'pattern_scanner',
    # 2026-04-20: BLOCK pct-hermes- directional variant — solo source, no independent confirmation
    'pct-hermes-',
    # 2026-04-20: BLOCK ma_cross — longs catastrophic (-1800 to -4000% net), shorts marginal.
    # Golden/death cross too lagging. Confirmed via 163-token backtest: 8/50 SHORT >> 10/200.
    'ma-cross',
    # 2026-04-22: BLOCK r2_rev — losing signal source, removed from active trading
    'r2_rev',
    # 2026-04-26: BLOCK oc-zscore-v9 +/- variants — external signal at minimum threshold
    # (val=2.0 = exactly the threshold, barely above floor), conf=81%, cannot verify
    # OC's internal z-score calc (lookback unknown, data source unknown). Being
    # conflated by the compactor with valid signals to hit 99% confidence, masking
    # mediocre signal strength. Blocks all directional variants.
    'oc-zscore-v9+',
    'oc-zscore-v9-',
    'oc-zscore-v9',
    # 2026-04-27: BLOCK oc-mtf-rsi — underperforming signal, no edge in backtest
    'oc-mtf-rsi',
    'oc-mtf-rsi+',
    'oc-mtf-rsi-',
    'oc-mtf-macd+',
}
SERVER_NAME = 'Hermes'
MAX_OPEN_POSITIONS = 3   # max open paper positions across all enforcement points

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
SPEED_MIN_THRESHOLD   = 20    # pctl < 20 → token blocked from signal generation
SPEED_BOOST_THRESHOLD = 70    # pctl >= 70 → entry threshold lowered 5% (easier entry)
SPEED_BOOST_FACTOR   = 0.95  # multiply entry threshold by this (lower = easier)
SPEED_HOTSET_WEIGHT  = 0.25  # 25% weight for speed in hot-set effective_conf calculation
                              # Formula: speed_pts = (speed_pctl - 50) / 100 × SPEED_HOTSET_WEIGHT × sig_conf
SPEED_HOTSET_THRESHOLD = 80   # pctl >= 80 → qualifies for speed-based hot-set boost
SPEED_HOTSET_BONUS   = 0.15  # +15% score boost for pctl >= 80 (legacy, used in compaction)
STALE_VELOCITY_THRESHOLD = 0.2  # % — below this = "flat" for stale detection
STALE_WINNER_TIMEOUT_MINUTES = 30  # close winners flat for 30+ min
STALE_LOSER_TIMEOUT_MINUTES = 15   # cut losers flat for 15+ min
STALE_WINNER_MIN_PROFIT = 1.0    # % profit required to be a "winner"
STALE_LOSER_MAX_LOSS   = -1.0   # % loss required to be a "loser"

# ── Cascade Flip Constants ──────────────────────────────────────────────────────
# Used by cascade_flip.py and position_manager.py
CASCADE_FLIP_ENABLED = False  # Master toggle — set True to enable cascade flip
CASCADE_FLIP_MAX     = 3      # max flips per token before permanent lockout
MIN_NOTIONAL      = 11.0 # HL minimum notional ($10 + $1 buffer)

# ── Support & Resistance Signal Constants ─────────────────────────────────────
# Used by rs_signals.py — primary signal for structural S&R level detection
RS_SIGNAL_TYPE       = 'support_resistance'
RS_LOOKBACK_CANDLES  = 4700   # candles to analyze (~3+ days of 1m)
RS_LEVEL_LOOKBACK    = 20     # swing high/low detection window
RS_ATR_PERIOD         = 14     # ATR lookback for proximity normalization
RS_CLUSTER_ATR       = 0.50   # cluster levels within 0.50 * ATR of each other
RS_PROXIMITY_K       = 1.20   # fire if price within 1.2 * ATR of a level
RS_MIN_TOUCHES       = 2      # minimum historical touches for valid level
RS_COOLDOWN_HOURS    = 4      # cooldown between RS signals per token+direction
RS_MIN_CONFIDENCE    = 50     # minimum confidence (global floor)
RS_MAX_CONFIDENCE    = 88     # R&S is structural — cap below momentum signals

# ── ATR TP/SL Constants ────────────────────────────────────────────────────────
# Used by position_manager.py and self_close_watcher.py for ATR-based SL/TP
#
# Trailing SL / TP — _compute_dynamic_sl / _compute_dynamic_tp
ATR_SL_MIN     = 0.005   # 0.50% floor
ATR_SL_MAX     = 0.02    # 2% cap
ATR_TP_MIN     = 0.0075  # 0.75% floor
ATR_TP_MAX     = 0.05    # 5% cap
ATR_TP_K_MULT  = 1.25   # TP tighter than SL: k_tp = k × 1.25

# Acceleration-phase trailing — _collect_atr_updates (first candle against us, we're out)
ATR_SL_MIN_ACCEL   = 0.002   # 0.20% floor — super tight
ATR_TP_MIN_ACCEL   = 0.005   # 0.50% floor — book profit fast

# Initial entry SL/TP — get_trade_params (fallback when no ATR available)
ATR_SL_MIN_INIT    = 0.005  # 0.05% — new trades get breathing room (no acceleration squeeze)
ATR_SL_MAX_INIT    = 0.005  # 0.05% — new trade SL cap
SL_PCT_FALLBACK    = 0.015   # 1.5% if ATR unavailable
TP_PCT_FALLBACK    = 0.08    # 8% fallback target
STOP_LOSS_DEFAULT  = 0.015    # 3% hard fallback

# ── ATR k Multiplier Constants ────────────────────────────────────────────────
# Base k: _atr_multiplier(atr_pct) — volatility-driven SL/TP scaling
# atr_pct = ATR / entry_price
#   < 1%  → k=1.0  (low volatility — tight stops)
#   > 3%  → k=2.5  (high volatility — wide stops)
#   1–3%  → k=2.0  (normal — balanced stops)
ATR_K_LOW_VOL      = 1.0   # atr_pct < 1%
ATR_K_NORMAL_VOL   = 1.25   # 1.25% <= atr_pct <= 3%
ATR_K_HIGH_VOL     = 1.5   # atr_pct > 3%
ATR_PCT_LOW_THRESH = 0.01  # 1%
ATR_PCT_HIGH_THRESH= 0.03  # 3%

# ── ATR Fallback ───────────────────────────────────────────────────────────────
# Used when real ATR cannot be fetched (e.g., unprotectable coins first-seen).
# Represents a mid-range ATR assumption — NORMAL_VOL tier.
ATR_PCT_FALLBACK    = 0.02  # 2% assumed ATR — fallback when atr_cache returns None

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
K_PHASE_ACCEL_STALL     = 0.15   # stalling + accelerating = momentum fading, snap out
K_PHASE_ACCEL_FAST      = 0.05   # fast momentum (pctl>=70) but first reversal = out
K_PHASE_ACCEL_SLOW      = 0.10   # low speed = no room needed, stay tight
# EXHAUSTION phase: 1.25–1.5×
K_PHASE_EXH_STALL       = 0.25   # stalling exhaustion = snap out faster
K_PHASE_EXH_FAST        = 0.15   # fast momentum
K_PHASE_EXH_SLOW        = 0.10   # slow momentum
# EXTREME phase: 1.5× max
K_PHASE_EXT_STALL       = 0.10   # stalling extreme
K_PHASE_EXT_FAST        = 0.05   # fast extreme

# ── Wrong-side stall detection ───────────────────────────────────────────────
WRONG_SIDE_AVG_PCT_THRESH = 1.5   # wrong-side trigger: avg counter move >= 1.5%

# ── Pause switches ─────────────────────────────────────────────────────────────
# Flip to True to disable without restarting anything. Flip back to False to re-enable.
MACD_EXIT_PAUSED = False   # Disable macd_rules.py exit signals (ATR TP/SL handles closes)
