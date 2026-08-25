#!/usr/bin/env python3
# DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!
# ── DISABLED SIGNALS (65 total) ───────────────────────────────────────────────
# pct_hermes, vel_hermes, hzscore, hmacd, mtf_momentum, momentum, phase_accel,
# fast_momentum, ema_angle, rs, gap_300, ma_cross, ma_cross_5m, hh_hl, guppy,
# macd_accel, trend_purity, ema9_sma20, r2_rev, r2_trend, exhaustion,
# counter_flip, squeeze_cross, zscore_pump, mtp_zscore, ema20_50+, volume_hl+,
# ma300_candle+, ma_cross_5m+/-, gap_300+/-, ema9_sma20+/-, exhaust+/-, guppy+/-,
# ma_cross+/-, r2_rev+/-, r2_trend+/-, trend_purity+/-, ema20_50-/-, fast_mom-,
# momentum+/-, mtf_momentum+/-, oc_*, pump_hunter, hl_copy_trader
# All set to False. See each section below for individual flags.

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
    'ACE','GRIFFAIN','BRETT','XLM','SNX','NIL','IP','TRB','ETHFI','EIGEN','S','VVV','SUI','LAYER','BERA','DYM','MAVIA','MEME','INIT','SOPH','XAI','ZEC','GAS','BLAST','MELANIA','ZETA','SPX','ARK','RUNE','AR',
    # TST, NXPC, CELO, ACE, YZY, ZEREBRO, WLFI, HBAR, MEGA removed 2026-08-07 — no specific block reason
    # TRUMP added 2026-08-08 — political meme coin, high volatility
    # Historical 0% SHORT win rate (2026-04-01 analysis):
    'SOL','MEW',        # avg SHORT pnl: deeply negative, bull market leader
    # HYPE, YGG removed for Batch 5 trial 2026-08-03
    # 0% SHORT win rate — add fresh
    # SYRUP removed for Batch 5 trial 2026-08-03
    # Additional high-beta / recent pumps (shorting pumps = catching knives)
    'POPCAT',  # meme pump history
    'VIRTUAL', 'MELANIA', 'FARTCOIN',  # meme coins
    # 2026-04-01: tokens with negative avg SHORT returns
    'RENDER', 'PORT3',
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
    # AI16Z, BADGER, BLZ, FXS, HPOS removed for Batch 3 trial 2026-08-02
    'RLB', 'RNDR', 'SHIA',
    'MATIC', 'UNIBOT', 'MKR', 'MYRO',
    # 2026-04-04: systematic SHORT losses (net<=$-2.50, phantom trades excluded)
    # ENA removed for Batch 3 trial 2026-08-02
    'PENGU',   # SHORT net: -$4.36 (1 loss: conf-1s -$4.36)
    # 2026-04-10: CFX removed for Batch 3 trial 2026-08-02
    # 2026-04-19: STABLE — block both directions. Stablecoin pairs have no directional
    # thesis and generate phantom trades via guardian_missing closes.
    'STABLE',
    # 2026-04-19: PAXG — block SHORT. TP/SL rejected by HL (asset=187), guardian
    # self-closes on regime breach. No HL SL protection for SHORT entries.
    'PAXG',
    # 2026-04-22: APE — block both directions
    'APE',
    # 2026-04-22: PENDLE, POLYX — block both directions
    'PENDLE', 'POLYX',
    # 2026-04-22: BIO — block both directions
    'BIO',
    # 2026-04-24: REZ, HMSTR, BNB — block both directions (DOGE SHORT immediate ATR
    # self-close issue — tokens with near-zero ATR getting SL=0 from ATR engine, causing
    # instant HARD_SL_CLOSE failures. Blocking both directions until root cause fixed.)
    'REZ', 'HMSTR', 'BNB',
    # 2026-07-21: 48h/72h signal quality analysis — worst performing tokens
    # BANANA, GRASS removed for Batch 3 trial 2026-08-02
    # KNEIRO, KPEPE, PUMP, NOT removed for Batch 5 trial 2026-08-03
    # 2026-08-02: Batch 1 trial RE-BLACKLISTED (48h trial: 0% WR, minimal execution)
    # BABY, STBL: re-blacklisted 2026-08-01 (pre-trial data)
    # MOVE removed for Batch 5 trial 2026-08-03
    # UNI, LINEA, TIA, TURBO, BLUR, FET: re-blacklisted 2026-08-02 (pre-trial data)
    # ORDI, PEOPLE, AIXBT, ZK, CAKE: re-blacklisted 2026-08-02 (no execution during trial)
    # REMOVED 2026-08-12: INSUFFICIENT batch tokens — auto-re-blacklist via token_performance_monitor
    # 'BABY', 'STBL', 'UNI', 'LINEA', 'TIA', 'TURBO', 'BLUR', 'FET',
    # 'ORDI', 'PEOPLE', 'AIXBT', 'ZK', 'CAKE',
    # 2026-08-02: Batch 2 trial — OP kept (4T, 0% WR), rest removed
    'OP',
    # 'COMP', 'CRV', 'IMX', 'SAND', 'NEAR', 'DOT', 'ICP',
    # 'ATOM', 'INJ', 'FIL', 'ETC', 'ARB', 'LDO', 'APT',
    # 'SEI', 'MET', 'DASH', 'WLD',
    # 'ADA', (removed — defunct signals)
    # Batch 3/4/5 INSUFFICIENT — removed 2026-08-12
    # '2Z', 'AI16Z', 'BADGER', 'BANANA', 'BIGTIME', 'BLZ', 'CASHCAT', 'CFX',
    # 'CHIP', 'DOOD', 'ENA', 'FOGO', 'FTT', 'FXS', 'GMT', 'GRAM',
    # 'GRASS', 'HPOS', 'ONDO',
    # 'ALT', 'APEX', 'IO', 'MERL', 'MON', 'NEO', 'POL', 'PURR', 'SKR', 'STX',
    # 'SUSHI', 'USUAL', 'XPL', 'ZEN', 'ZORA', 'ZRO',
    # 'HYPE', 'KNEIRO', 'KPEPE', 'MOVE', 'NOT', 'PUMP', 'SYRUP', 'YGG',
    # 2026-08-05: Trash tokens — consistently lose, fire signals but never profit
    'GALA', 'STRK',
    # 2026-08-06: Worst switch offenders — signals flip direction, both sides lose
    'TAO', 'UMA', 'MOODENG', 'XMR', '0G',
    # 2026-08-07: 5 SL hits in 48h, -$0.28 total — both directions lose
    'KAITO',
    # 2026-08-07: HIP-3 asset, hl_copy SHORT signal — user requested block
    '@107',
    # 2026-08-07: Consistent losers — 48h + all-time net negative
    'TNSR',  # 18T all-time, 28% WR, -$0.22. 48h: 5T, 20% WR, -$0.30
    'VINE',  # 16T all-time, 19% WR, -$0.40. 48h: 5T, 40% WR, -$0.19
    # 2026-08-09: Worst performers (7d) — both directions bleed
    'AAVE',  # 17T 29.4% WR -$0.41
    'SKY',   # 13T 30.8% WR -$0.16
    'PNUT',  # 15T 33.3% WR -$0.13
    # 2026-08-08: Political meme coin, high volatility
    'TRUMP',
    # 2026-08-11: 5 trades, 0% WR, -$0.23 — low-price noise coin, all ATR SL hits
    'MEGA',
    # AUTO-BLACKLISTED 2026-08-12 — 35% WR threshold (5+ trades, 7d)
    'AXS', 'XRP',
    # 2026-08-15: both-direction losers (30d, min 3 trades each side)
    'MOVE',   # 15T 0% WR SHORT, 21T 24% WR LONG — -$1.72
    'PEOPLE', # 22T 18% WR SHORT, 10T 30% WR LONG — -$1.51
    'APEX',   # 24T 25% WR SHORT, 18T 22% WR LONG — -$1.48
    'TIA',    # 12T 33% WR SHORT, 16T 12% WR LONG — -$1.35
    'STBL',   # 9T 11% WR SHORT, 23T 26% WR LONG — -$1.34
    'UNI',    # 16T 6% WR SHORT, 9T 22% WR LONG — -$1.33
    'LINEA',  # 19T 26% WR SHORT, 11T 0% WR LONG — -$1.20
    'FET',    # 14T 7% WR SHORT, 12T 25% WR LONG — -$1.19
    'MORPHO', # 20T 25% WR SHORT, 30T 33% WR LONG — -$1.19
    'ZK',     # 11T 18% WR SHORT, 12T 25% WR LONG — -$1.12
    'ORDI',   # 22T 36% WR SHORT, 21T 24% WR LONG — -$1.07
    'SKR',    # 15T 33% WR SHORT, 15T 33% WR LONG — -$1.08
    # 2026-08-15: 96h both-direction loser
    '2Z',     # 3T 33% WR SHORT, 7T 29% WR LONG — -$0.28
    # 2026-08-24: tl_break SHORT losers — selling the bottom after sharp drops
    'BSV',    # 5T 20% WR, -$0.12. ext=4.4x, entered at bottom of -2.7% drop
    'DASH',   # 4T 25% WR, -$0.02. ext=5.4-5.8x, entered at bottom of -4.6% drop
}
LONG_BLACKLIST = {
    # 2026-04-22: BIO — block both directions
    'ACE','GRIFFAIN','BRETT','XLM','SNX','NIL','IP','TRB','ETHFI','EIGEN','S','VVV','SUI','LAYER','BERA','DYM','MAVIA','MEME','INIT','ZEC','GAS','BLAST','MELANIA','YZY','ZETA','BIO','MEW','PROVE',
    # TST, ACE, KAS removed 2026-08-07 — no specific block reason
    # TRUMP added 2026-08-08 — political meme coin, high volatility
    # PROVE re-blacklisted 2026-08-10 — 25% WR, -0.25% avg PnL, -$0.22 total
    'BOME', 'USTC', 'RSR',
    # 2026-04-24: REZ, HMSTR, BNB — block both directions
    'REZ', 'HMSTR', 'BNB',
    # 2026-07-21: 48h/72h signal quality analysis — worst performing tokens
    # BANANA, GRASS removed for Batch 3 trial 2026-08-02
    # KNEIRO, KPEPE, PUMP, NOT removed for Batch 5 trial 2026-08-03
    # 2026-08-02: Batch 1 trial RE-BLACKLISTED (48h trial: 0% WR, minimal execution)
    # BABY, STBL: re-blacklisted 2026-08-01 (pre-trial data)
    # MOVE removed for Batch 5 trial 2026-08-03
    # UNI, LINEA, TIA, TURBO, BLUR, FET: re-blacklisted 2026-08-02 (pre-trial data)
    # ORDI, PEOPLE, AIXBT, ZK, CAKE: re-blacklisted 2026-08-02 (no execution during trial)
    # REMOVED 2026-08-12: INSUFFICIENT batch tokens — see SHORT_BLACKLIST comment
    # 'BABY', 'STBL', 'UNI', 'LINEA', 'TIA', 'TURBO', 'BLUR', 'FET',
    # 'ORDI', 'PEOPLE', 'AIXBT', 'ZK', 'CAKE',
    # 2026-08-02: Batch 2 trial — OP kept, rest removed
    'OP',
    # 'COMP', 'CRV', 'IMX', 'SAND', 'NEAR', 'DOT', 'ICP',
    # 'ATOM', 'INJ', 'FIL', 'ETC', 'ARB', 'LDO', 'APT',
    # 'SEI', 'MET', 'DASH', 'WLD',
    'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA', 'LOOM',
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    # 2026-04-02: phantom orders via openclaw systemd timers
    'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',
    # 2026-04-02: persistent losing LONG directions (loss cooldown streaks)
    'AERO', 'CHILLGUY', 'LIT', 'ANIME',  # LONG streaks
    # Batch 3/4/5 INSUFFICIENT — removed 2026-08-12
    # 'ADA', '2Z', 'AI16Z', 'BADGER', 'BANANA', 'BIGTIME', 'BLZ', 'CASHCAT', 'CFX',
    # 'CHIP', 'DOOD', 'ENA', 'FOGO', 'FTT', 'FXS', 'GMT', 'GRAM',
    # 'GRASS', 'HPOS', 'ONDO',
    # 'ALT', 'APEX', 'IO', 'MERL', 'MON', 'NEO', 'POL', 'PURR', 'SKR', 'STX',
    # 'SUSHI', 'USUAL', 'XPL', 'ZEN', 'ZORA', 'ZRO',
    # 'HYPE', 'KNEIRO', 'KPEPE', 'MOVE', 'NOT', 'PUMP', 'SYRUP', 'YGG',
    # 2026-08-05: Trash tokens — consistently lose, fire signals but never profit
    'GALA', 'STRK',
    # 2026-08-06: Worst switch offenders — signals flip direction, both sides lose
    'TAO', 'UMA', 'MOODENG', 'XMR', '0G',
    # 2026-08-07: 5 SL hits in 48h, -$0.28 total — both directions lose
    'KAITO',
    # 2026-08-07: HIP-3 asset, hl_copy signal — user requested block
    '@107',
    # 2026-08-07: Consistent losers — 48h + all-time net negative
    'TNSR',  # 18T all-time, 28% WR, -$0.22. 48h: 5T, 20% WR, -$0.30
    'VINE',  # 16T all-time, 19% WR, -$0.40. 48h: 5T, 40% WR, -$0.19
    # 2026-08-09: Worst performers (7d) — both directions bleed
    'AAVE',  # 17T 29.4% WR -$0.41
    'SKY',   # 13T 30.8% WR -$0.16
    'PNUT',  # 15T 33.3% WR -$0.13
    # 2026-08-10: 48h loss clustering — consistently losing
    'AXS',   # 5T 0% WR -$0.19 — all losses
    'LINK',  # 5T 20% WR -$0.18 — mostly losses
    'CELO',  # 4T 50% WR -$0.05 — losses > wins
    # 2026-08-08: Political meme coin, high volatility
    'TRUMP',
    # 2026-08-11: 5 trades, 0% WR, -$0.23 — low-price noise coin, all ATR SL hits
    'MEGA',
    # AUTO-BLACKLISTED 2026-08-12 — 35% WR threshold (5+ trades, 7d)
    'XRP',
    # 2026-08-15: both-direction losers (30d, min 3 trades each side)
    'MOVE',   # 21T 24% WR LONG, 15T 0% WR SHORT — -$1.72
    'PEOPLE', # 10T 30% WR LONG, 22T 18% WR SHORT — -$1.51
    'APEX',   # 18T 22% WR LONG, 24T 25% WR SHORT — -$1.48
    'TIA',    # 16T 12% WR LONG, 12T 33% WR SHORT — -$1.35
    'STBL',   # 23T 26% WR LONG, 9T 11% WR SHORT — -$1.34
    'UNI',    # 9T 22% WR LONG, 16T 6% WR SHORT — -$1.33
    'LINEA',  # 11T 0% WR LONG, 19T 26% WR SHORT — -$1.20
    'FET',    # 12T 25% WR LONG, 14T 7% WR SHORT — -$1.19
    'MORPHO', # 30T 33% WR LONG, 20T 25% WR SHORT — -$1.19
    'ZK',     # 12T 25% WR LONG, 11T 18% WR SHORT — -$1.12
    'ORDI',   # 21T 24% WR LONG, 22T 36% WR SHORT — -$1.07
    'SKR',    # 15T 33% WR LONG, 15T 33% WR SHORT — -$1.08
    # 2026-08-15: 96h both-direction loser
    '2Z',     # 7T 29% WR LONG, 3T 33% WR SHORT — -$0.28
    # 2026-08-24: tl_break losers — block both directions
    'BSV',    # 5T 20% WR, -$0.12
    'DASH',   # 4T 25% WR, -$0.02
}
BROAD_MARKET_TOKENS = {'SOL', 'BTC', 'ETH', 'DOGE', 'XRP', 'ADA', 'AVAX', 'DOT', 'LINK', 'MATIC', 'UNI', 'ATOM'}

# ── Favorites ─────────────────────────────────────────────────────────────────
# Proven performers — high WR + profitable + decent sample.
# Cross-check: no token in SHORT_BLACKLIST or LONG_BLACKLIST.
# AUTO-UPDATED daily by favorites_updater.py.
FAVORITES = {
    'BANANA',
    'BTC',
    'CAKE',
    'ENA',
    'ETH',
    'FIL',
    'GMT',
    'IMX',
    'LDO',
    'NXPC',
    'SYRUP',
    'ZRO'
}

FAVORITES_MULT = 1.2          # Score multiplier in signal_compactor _score_signal()
FAVORITES_SIZE_MULT = 1.5     # Position size multiplier in decider_run ($11 → $16.50)
FAVORITES_RESIDENCY_DECAY = 0.12  # Staleness decay rate for favorites (default 0.2 → 5min, 0.12 → ~8.3min)

# Penalty list — consistent underperformers get deprioritized (not blacklisted).
# Blacklist = never trade. Penalty = tradeable but low priority.
# Auto-updated by favorites_updater.py.
PENALTY_TOKENS = set()
PENALTY_MULT = 0.7              # 30% score penalty in signal_compactor _score_signal()

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
    # 2026-08-03: BLOCK pattern_scanner — 0% WR (0/6), -$0.55 in 24h. No flag mapping
    # in decay detector, blocking at source level is the only kill mechanism.
    'pattern_scanner',
    # bb_bounce re-enabled 2026-08-05 by T — WR=50% after data corruption fix
    # 2026-08-05: BLOCK pattern_wolf — 0% WR (10 trades 7d), -$1.38. No edge found.
    # All variants: pattern_wolf, pattern_wolf_wave_bull, pattern_wolf_wave_bear.
    'pattern_wolf',
    # 2026-08-05: BLOCK accel-300 — 0% WR over 48h, no edge. All variants dead.
    # Covers: accel-300+, accel-300-, accel-300-vel+, accel-300-vel-, accel-300-breakout.
    'accel-300',
    # 2026-08-12: BLOCK hzscore+ standalone — 13T -$0.20 38.5% WR (7d), 6T -$0.09 33% WR (24h).
    # Combos unaffected: hzscore+,return_exhaustion_long 58.3%, hzscore+,mover+ 80%,
    # bb_bounce+,hzscore+ 50%. validate_source() only blocks exact match for single-signal.
    'hzscore+',
    # CEO 2026-08-15: BLOCK return_exhaustion- SHORT — ALL SL hits are losses (0% WR).
    # Affected combos: hzscore-,return_exhaustion- 5T -$0.42, ma100-cross,return_exhaustion- 4T -$0.39,
    # return_exhaustion- 2T -$0.23, return_exhaustion-,tl_break_short 1T -$0.12,
    # return_exhaustion-,vortex_break_short 1T -$0.09. Total: 13T -$1.25.
    # validate_source() blocks combos containing this as component.
    'return_exhaustion-',
}
SERVER_NAME = 'Hermes'
MAX_OPEN_POSITIONS = 5   # max open paper positions

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
SPEED_MIN_THRESHOLD   = 30    # pctl < 30 → token blocked from signal generation (lowered from 35 — critical starvation at 0.33/hr, need accel-300+ entries)
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
VEL_30M_WINDOW = 6    # candles to average for 30m velocity (6 × 5m candle = 30 min)
                        # NOTE: speed_tracker reads candles_5m, so 6 candles = 30min correctly.
                        # Do NOT change to 30 — that would make it 150min on 5m data.
VEL_STALE_THRESHOLD_PCT = 0.05  # % per candle — below this = "flat" for stale detection
                                        # 0.05%/candle × 5 candles ≈ 0.25% total = old 0.2% feel
                                        # but smooths micro-noise from single ref candles
OVEREXTENDED_THRESHOLD  = 3.0  # % — vel must exceed this to be "overextended" (per-candle windowed)
MOMENTUM_EXHAUSTION_THRESHOLD = 0.5  # % — if price moved this much in 30m, don't enter (catches tops)
STALE_WINNER_TIMEOUT_MINUTES = 60  # close winners flat for 60+ min (was 45)
STALE_LOSER_TIMEOUT_MINUTES = 8   # cut losers flat for 8+ min (was 10)
STALE_WINNER_MIN_PROFIT = 0.6    # % profit required to be a "winner" (was 0.8%)
STALE_LOSER_MAX_LOSS   = -0.6   # % loss required to be a "loser" (was -0.8%)

# ── Cascade Flip Constants ──────────────────────────────────────────────────────
# Used by cascade_flip.py and position_manager.py
CASCADE_FLIP_ENABLED = True   # Master toggle — set True to enable cascade flip
CASCADE_FLIP_MAX     = 3      # max flips per token before permanent lockout

# ── Cascade Flip v2 Constants ──────────────────────────────────────────────────
# v2: unified scoring engine with directional momentum + adaptive thresholds
CASCADE_FLIP_V2_ENABLED = True   # v2 toggle — both this AND CASCADE_FLIP_ENABLED must be True

# Scoring weights (sum = 100 max)
CFV2_MTF_MAX_PTS       = 30   # MTF alignment component
CFV2_CASCADE_MAX_PTS   = 25   # cascade active component
CFV2_MACD_MAX_PTS      = 20   # MACD exit signal component
CFV2_MOMENTUM_MAX_PTS  = 25   # momentum confirmation component

# Momentum thresholds
CFV2_VEL_STRONG        = 1.0  # velocity magnitude for full momentum pts
CFV2_VEL_MODERATE      = 0.5  # velocity magnitude for moderate pts

# Post-flip protection
CFV2_POST_FLIP_MIN_CYCLES  = 3     # pipeline cycles before re-evaluation
CFV2_POST_FLIP_COOLDOWN_M  = 15    # minutes between flips on same token

# Flip budget thresholds (adaptive based on win rate)
CFV2_BUDGET_WIN_RATE_HIGH  = 0.60  # above this → budget=5
CFV2_BUDGET_WIN_RATE_LOW   = 0.40  # below this → budget=1
CFV2_BUDGET_DEFAULT        = 3     # default when insufficient data
CFV2_BUDGET_MIN_TRADES     = 3     # minimum trades before adaptive budget kicks in

# ── Trade Sizing Constants ──────────────────────────────────────────────────────
DEFAULT_TRADE_SIZE_USDT = 11.0  # FALLBACK only — actual sizing uses _get_trade_size_usdt()
                                 # (7% of withdrawable balance, scales with account growth).
                                 # This is NOTIONAL (including leverage), not margin.
                                 # At 5x: $11 notional = $2.20 margin risked.
                                 # NOTE: do NOT use this for PnL calculations — use
                                 # hl_notional_usdt (actual HL notional) or
                                 # hype_realized_pnl_usdt (HL ground-truth) instead.
HL_MIN_NOTIONAL_USDT     = 11.0 # HL minimum NOTIONAL ($10 + $1 buffer)

# ── Kelly Criterion Sizing (from Trading Books) ──────────────────────────────
KELLY_ENABLED = False           # Disabled until 50+ trades per signal
KELLY_FRACTION = 0.25          # Quarter-Kelly (conservative: 50% growth, 12% drawdown)
KELLY_MAX_POSITION_PCT = 0.05  # Max 5% of bankroll per trade
KELLY_MIN_POSITION_USDT = 11.0 # HL minimum notional ($10 + $1 buffer)
KELLY_MAX_POSITION_USDT = 20.0 # Maximum $20 per trade (hard cap)
KELLY_MIN_TRADES = 50          # Minimum trades before Kelly activates
KELLY_DRAWDOWN_CIRCUIT_BREAKER = 0.10  # Stop Kelly at 10% drawdown

# ── Signal Quality Gate ───────────────────────────────────────────────────────
SIGNAL_QUALITY_ENABLED = True
SIGNAL_QUALITY_MIN_GRADE = 'C'  # Only trade C or better (A, B, C)
SIGNAL_QUALITY_MIN_SHARPE = 1.0
SIGNAL_QUALITY_MIN_PROFIT_FACTOR = 1.5

# ── Regime Detection ──────────────────────────────────────────────────────────
REGIME_ENABLED = True
REGIME_SIZE_ADJUST = True      # Adjust size based on regime

# ── Phase 1 Extensions (from Position Sizing Spec) ────────────────────────────

# Signal Weighting
SIGNAL_WEIGHT_ENABLED = True
SIGNAL_WEIGHT_A = 1.5          # Grade A: strong edge
SIGNAL_WEIGHT_B = 1.2          # Grade B: good edge
SIGNAL_WEIGHT_C = 1.0          # Grade C: moderate edge
SIGNAL_WEIGHT_D = 0.8          # Grade D: weak edge
SIGNAL_WEIGHT_F = 0.5          # Grade F: no edge

# Drawdown-Responsive Sizing
DRAWDOWN_ENABLED = True
DRAWDOWN_TIER_1_PCT = 0.05     # 5% drawdown → 0.5x size
DRAWDOWN_TIER_1_MULT = 0.5
DRAWDOWN_TIER_2_PCT = 0.10     # 10% drawdown → 0.25x size
DRAWDOWN_TIER_2_MULT = 0.25

# Portfolio Heat Limit
PORTFOLIO_HEAT_ENABLED = True
MAX_PORTFOLIO_HEAT = 0.15      # Max 15% total risk
DEFAULT_STOP_DISTANCE = 0.02   # Default 2% stop distance for heat calc

# Conservative Mode
CONSERVATIVE_MODE_ENABLED = False
CONSERVATIVE_MODE_MULTIPLIER = 0.5

# ── Support & Resistance Signal Constants ─────────────────────────────────────
# Used by rs_signals.py (top-level) and signals/rs.py (signals/ scanner)
# NOTE: signals/rs.py had hardcoded values that diverged from this file.
#       All RS constants are now centralized here.
RS_SIGNAL_TYPE       = 'support_resistance'
RS_LOOKBACK_CANDLES  = 4700   # candles to analyze (~3+ days of 1m)
RS_LEVEL_LOOKBACK    = 300     # swing high/low detection window
RS_ATR_PERIOD         = 30     # ATR lookback for proximity normalization
RS_CLUSTER_ATR       = 1.0   # cluster levels within 1.0 * ATR of each other
RS_PROXIMITY_K       = 4.0    # fire if price within 4.0 * ATR of a level (was 3.0 — ASTER setup needed K=3.47; 4.0 gives breathing room for low-vol tokens)
RS_MIN_TOUCHES       = 30       # minimum touches for valid level (was 120 — only 4 tokens passed; 30 lets 85% qualify including ASTER)
RS_DECIDER_MIN_TOUCHES = 30    # minimum touches for decider to approve (synced with RS_MIN_TOUCHES)
RS_TOUCH_HARD_CAP       = 200  # block signals when touch_count >= 200 — (was 120 which was blocking the best-performing SHORT bucket at 151-200 tc: 66.7% WR avg +2.0% PnL; 201-300 zone is the natural ceiling at 17.4% WR)
RS_LEVEL_BROKEN_LOOKBACK = 200  # candles to check for level-invalidation (was hardcoded 20) — ~8hrs on 1m; catches support/resistance flips
RS_DECIDER_ZBONUS_TOUCHES = 20  # relaxed threshold (20 vs 30) when |z_score| > 2.5 — strong momentum offsets weak level
RS_DECIDER_ZBONUS_ZSCORE = 2.5  # z-score threshold for relaxed touch requirement
RS_DECIDER_CONF_PENALTY = 15   # confidence point deduction when touches below threshold
RS_DECIDER_CONF_FLOOR  = 60   # effective confidence below this → trade is blocked (was 55)
RS_BROKEN_SHORT_ENABLED = False  # DISABLED 2026-07-21 — broken support SHORT = 26.5% WR (53/200), massive drag
RS_BROKEN_RESISTANCE_LONG_ENABLED = False  # DISABLED — broken resistance LONG fires when price breaks through resistance, expecting bounce, but momentum is bearish and price continues down (BLUR/BRETT loss pattern)
RS_COOLDOWN_HOURS    = 10    # cooldown between RS signals per token+direction (was 8h)
RS_MIN_CONFIDENCE    = 88     # minimum confidence (was 85 — stronger signals)
RS_MAX_CONFIDENCE    = 88     # R&S is structural — cap below momentum signals

# Recency weighting — fresh levels outperform ancient ones
RS_RECENCY_WINDOW    = 100    # lookback for recency-weighted touch count
RS_RECENCY_BOOST_K   = 3.0   # multiplier: each recent touch counts as K ancient touches

# Bounce confirmation — what counts as a "touch" off a level
RS_BOUNCE_LOOKBACK   = 200     # was 6, candles to check for bounce confirmation
RS_BOUNCE_THRESH_ATR = 0.33  # touch: price came within 0.33 * ATR(14) of the level (was 1.0 — touch gate was 0.2ATR but bounce required 3x that to confirm, structurally impossible; 0.33 makes touch=0.067ATR and bounce follow-through achievable at 0.025% absolute)
RS_ATR_DIST_FALLBACK   = 999  # fallback value for atr_dist when atr_pct is 0 (degenerate) — used in signal dict
RS_SOURCE_PREFIX     = 'rs'  # signal source prefix for logging

# ── ATR TP/SL Constants ────────────────────────────────────────────────────────
# Used by position_manager.py and self_close_watcher.py for ATR-based SL/TP
#
# Trailing SL / TP — _collect_atr_updates / tpsl_utils.compute_atr_sl_tp
# TUNED 2026-07-28: trailing SL with breakeven floor is the real profit protector
# Analysis: SL width barely matters when trailing+breakeven is active.
# Best combo: SL=0.8%, TP=1.5%, trail_act=0.25%, trail_dist=0.20% → +11.25% PnL, 57% WR
ATR_SL_MIN             = 0.012   # 1.2% floor — REVERTED from 1.5% (CEO Aug 25). auto_1hr data: 1.5% WORSENED hit rate 49.4%→60%, avg loss -$6.09. Wider SL = trades run into bigger losses before stopping. Problem is entry quality, not SL width. Monitor: atr_sl_hit %, avg loss.
ATR_SL_MAX             = 0.030  # 3.0% cap — widened from 2.5% 2026-08-16. ATR_SL dominant drag: 45T -$3.32 (avg loss -0.75%). Wider SL gives trades room to reach PM_TRAIL activation (+0.40%). Monitor: ATR_SL hit count (should ↓ from 45/48h), PM_TRAIL capture rate (should ↑). Revert if avg loss widens without fewer hits.
ATR_TP_MIN             = 0.008   # 0.80% floor — match realistic MFE (was 1.2%, too far)
ATR_TP_MAX             = 0.020   # 2.00% cap — widened 2026-08-07 (was 1.5%) to maintain R:R with wider SL (2.5%). Trailing handles profit-taking.
ATR_TP_K_MULT          = 2.0    # TP = 2.0x SL — CEO 2026-08-16 eval: REVERTED from 2.5. 2.5x made TP unreachable (only 1 ATR_TP hit/48h). 2.0x more realistic. PM_TRAIL handles profit-taking, but ATR_TP as secondary exit needs reachable target. Monitor: ATR_TP hit count (should ↑ from 1), R:R (should hold >0.75:1).
# Only push SL/TP to HL when delta exceeds this threshold
ATR_UPDATE_THRESHOLD   = 0.0015  # 0.15% — delta gate for HL order updates

# Acceleration-phase trailing — _collect_atr_updates (first candle against us, we're out)
ATR_SL_MIN_ACCEL   = 0.003  # 0.30% floor — allow trailing to lock in profits. CEO directive: do NOT change
# Was 0.5% — too wide, prevented trailing from locking in profits
# Lower than TRAILING_DISTANCE_PCT (0.20%) so trailing takes over
ATR_TP_MIN_ACCEL   = 0.005   # 0.50% floor — still capture quick wins

# Initial entry SL/TP — get_trade_params (fallback when no ATR available)
ATR_SL_MIN_INIT    = 0.012  # 1.2% — REVERTED from 1.5%. MUST match ATR_SL_MIN
ATR_SL_MAX_INIT    = 0.030  # 3.0% — widened from 2.5%. MUST match ATR_SL_MAX
SL_PCT_FALLBACK    = 0.012  # 1.2% if ATR unavailable (matched to ATR_SL_MIN)
TP_PCT_FALLBACK    = 0.030  # 3.0% fallback target (2:1 R:R with 1.5% SL)
STOP_LOSS_DEFAULT  = 0.012  # 1.2% hard fallback (matched to ATR_SL_MIN)
SL_PCT_MIN        = 0.012  # 1.2% minimum SL for any trade (hard floor, matched to ATR_SL_MIN)
CUT_LOSER_PNL     = -2.0   # close trade at -2.0% PnL (used by cut_loser + guardian hard-stop)

# ── Trailing Activation — brain.py / decider_run.py
# CEO 2026-08-05: widened from 0.10% — trades killed on first pullback noise
# 2026-08-14: widened per r2_trend_long trailing SL plan — 30-trade multi-token validation
#   activation: 0.40%→0.80% (wait for trend to establish before trailing)
#   distance: 0.80%→2.00% (survives 1.88% max drawdown observed in 2Z wave analysis)
#   R:R improved from 0.39:1 to ~1.25:1 on trailing exits
TRAILING_ACTIVATION_PCT = 0.0040  # 0.40% — FINALIZED 2026-08-16 eval: kept. PM_TRAIL handles most exits; this is fallback for non-PM_TRAIL trades.
TRAILING_DISTANCE_PCT   = 0.0100  # 1.00% — trailing SL distance from peak (tightened from 2.0% — 2.0% was too far, only 29% of trades locked profit. 1.0% locks profit on 59% of trades)

# ── Loss Cooldown Constants
# Incremental: streak=1 → 10min, streak=2 → 20min, streak=3 → 40min, ...
# Formula: hours = min(LOSS_COOLDOWN_BASE * 2^(streak-1), LOSS_COOLDOWN_MAX)
# Synced: hl-sync-guardian.py, position_manager.py, cascade_flip.py, signal_schema.py
LOSS_COOLDOWN_BASE     = 20 / 60   # 20 min for 1st consecutive loss (was 15 min)
LOSS_COOLDOWN_MAX      = 90 / 60   # cap at 90 min after 3+ consecutive losses (was 60 min)
WIN_COOLDOWN_MINUTES   = 3         # block same direction for 3 min after a win (was 5)

# ── ATR k Multiplier Constants ────────────────────────────────────────────────
# Base k: _atr_multiplier(atr_pct) — volatility-driven SL/TP scaling
# atr_pct = ATR / entry_price
#   < 1%  → k=1.0  (low volatility — tight stops)
#   > 3%  → k=2.5  (high volatility — wide stops)
#   1–3%  → k=2.0  (normal — balanced stops)
ATR_K_INITIAL      = 1.2   # initial SL only (reverted to original)
ATR_K_LOW_VOL      = 0.8   # trailing/accel SL — atr_pct < 1% (was 0.5 — effective SL=0.4%, noise-level. 0.8 gives min 0.96% SL)
ATR_K_NORMAL_VOL   = 1.0   # trailing/accel SL — 1.0% <= atr_pct <= 1.5%
ATR_K_HIGH_VOL     = 0.25  # trailing/accel SL — atr_pct > 1.5% (EXTREME regime)
ATR_PCT_LOW_THRESH = 0.01  # 1%
ATR_PCT_HIGH_THRESH= 0.015  # 1.5% — matches EXTREME regime threshold

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
# 2026-06-25 retune: raised from 0.04-0.06 to 0.4-0.6 (10x) — old values were clobbered
# by ATR_SL_MIN_ACCEL floor / ATR_SL_MAX cap (see Bug #3 in tpsl-profit-capture plan).
# New values produce k in 0.2-0.3 range after multiplying by base_k (0.5-1.0).
K_PHASE_ACCEL_STALL     = 0.6    # stalling + accelerating = momentum fading, snap out (was 0.06)
K_PHASE_ACCEL_FAST      = 0.5    # fast momentum (pctl>=70) but first reversal = out (was 0.05)
K_PHASE_ACCEL_SLOW      = 0.4    # low speed = no room needed, stay tight (was 0.04)
# EXHAUSTION phase: 1.25–1.5× (old) → 0.3-0.5 (new — tighter trailing, locks profit)
K_PHASE_EXH_STALL       = 0.5    # stalling exhaustion = snap out faster (was 0.02)
K_PHASE_EXH_FAST        = 0.4    # fast momentum (was 0.03)
K_PHASE_EXH_SLOW        = 0.3    # slow momentum (was 0.02)
# EXTREME phase: 1.5× max (old) → 0.2-0.3 (new — tightest trailing)
K_PHASE_EXT_STALL       = 0.3    # stalling extreme (was 0.01)
K_PHASE_EXT_FAST        = 0.2    # fast extreme (was 0.02)

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

# ── Phase Entry Filter ────────────────────────────────────────────────────────
# Blocks signal entries during inappropriate market phases.
# Based on surfing.md: "Don't chase exhausted waves, don't enter whitewater."
# Data: 2572 PostgreSQL trades analyzed 2026-07-28
#
# accel_300 (momentum): block during exhaustion/extreme (move already done)
# inv_accel_300 (reversion): block during quiet/building (move not exhausted yet)
PHASE_ENTRY_FILTER_ENABLED = False  # DISABLED 2026-08-04 — phase data often unknown, blocking valid signals

# accel_300: which phases are ALLOWED (momentum entry)
# Block: exhaustion, extreme
ACCEL_300_ALLOWED_PHASES = {'quiet', 'building', 'accelerating'}

# inv_accel_300: which phases are ALLOWED (mean reversion entry)
# Block: quiet, building
INVERSE_ACCEL_300_ALLOWED_PHASES = {'decelerating', 'bottoming', 'falling', 'accelerating'}  # FIX: match speed_tracker phases (was 'exhaustion','extreme' — never matched)
INVERSE_ACCEL_300_CAUTION_PHASES = set()  # all phases allowed

# ── Context Gate ───────────────────────────────────────────────────────────────
# Two-layer gate before trade execution: rule-based (free) → LLM-based (quota).
# Only fires when signal has passed ALL other filters (dead-hours, phase, position).
CONTEXT_GATE_ENABLED = True          # master switch
CONTEXT_GATE_LLM_ENABLED = True      # LLM fallback (rule-based always runs first)
CONTEXT_GATE_LLM_MODEL = 'opencode-go/mimo-v2.5'  # model for context gate LLM calls (switched from minimax/MiniMax-M3 2026-08-10)
CONTEXT_GATE_SPEED_MIN = 20          # below this → SKIP (no wave)
CONTEXT_GATE_Z_COUNTER_TREND = 1.5   # z-score contradicting signal + low speed → SKIP
CONTEXT_GATE_Z_RANGING = 0.5         # |z| below this = ranging
CONTEXT_GATE_RANGING_SPEED = 25      # ranging + low speed → SKIP
CONTEXT_GATE_SPEED_CONFIRM = 70      # z + speed both strong → GO (no LLM needed)
CONTEXT_GATE_CACHE_TTL = 300         # seconds to cache LLM decision for same token+signal
CONTEXT_GATE_LLM_TIMEOUT = 35        # seconds before LLM call times out
CONTEXT_GATE_FAIL_OPEN = True        # if LLM fails, allow trade (don't block good setups)

# ── Global Signal Filters (FIX 2026-07-31) ────────────────────────────────────
# Applied to ALL signals at context gate. Based on winning trade analysis:
# Winners: speed>50%, momentum>25, RSI 30-70, z-score neutral
# BUT: Best trades had EXTREME z when speed confirmed direction
# Key insight: Extreme z + high speed = reversal (win), Extreme z + low speed = chasing (lose)
SIGNAL_FILTER_ENABLED = True         # master switch for all filters below
SIGNAL_FILTER_SPEED_MIN = 40  # CEO 2026-08-16: RAISED from 30. ATR_SL 37T/48h 2.7% WR -$2.45 dominates. Higher speed min = fewer but better entries. NEUTRAL override at15 unchanged.
SIGNAL_FILTER_NEUTRAL_SPEED_MIN = 15  # CEO 2026-08-15 — STARVATION FIX: relaxed speed filter in NEUTRAL regime (102/104 tokens flat). 30 still blocks most NEUTRAL signals. 15 lets low-momentum signals through when regime is flat.
SIGNAL_FILTER_MOMENTUM_MIN = 25      # block signals when momentum < this (winners avg 29)
SIGNAL_FILTER_RSI_MIN = 30           # block SHORT when RSI < this (oversold = bounce risk)
SIGNAL_FILTER_RSI_MAX = 80           # block LONG when RSI > this (overbought) - was 70, raised to allow reversals
SIGNAL_FILTER_Z_MIN = -1.5           # block LONG when z < this AND speed < 50% (chasing)
SIGNAL_FILTER_Z_MAX = 1.5            # block SHORT when z > this AND speed < 50% (chasing)

# ── Global Spike Filter ────────────────────────────────────────────────────
# Block SHORT entries after recent bullish 5m candle (spike → consolidation → bad SHORT)
# Backtested: spike>0.3% + RSI<30 blocks 2x more losers than winners (0.5x ratio)
SPIKE_FILTER_ENABLED = True
SPIKE_FILTER_5M_THRESHOLD = 0.3      # % — block SHORT if last 3 5m candles had bullish candle > this
SPIKE_FILTER_RSI_THRESHOLD = 30      # block SHORT when RSI < this (oversold = bounce risk)

# ── Z-Score + Acceleration Alignment (surfing.md quadrants) ───────────────
# Hard block trades where z-score and acceleration disagree with direction.
# CEO backtested: misaligned = 23.8% WR, aligned = 76.4% WR (52pt gap).
ZSCORE_ACCEL_ENABLED = True
ZSCORE_ACCEL_Z_THRESHOLD = 0.5       # z-score threshold for alignment check
ZSCORE_ACCEL_ACCEL_THRESHOLD = 0.005 # acceleration threshold (0.5% hourly)
ZSCORE_ACCEL_PENALTY = 0.7           # used if soft penalty mode enabled

# ── Short Velocity Filter (global) ───────────────────────────────────────
# Block SHORT when price is rising or last 3 candles are green.
# Backtested: vel>0.1% OR last3_green>=3 → 12% WR (losers), kept → 89% WR.
# SHORT-only filter — does NOT apply to LONG.
SHORT_VEL_FILTER_ENABLED = True
SHORT_VEL_FILTER_VEL_THRESHOLD = 0.3   # % — block SHORT if 5h velocity > this (raised from 0.1% — was blocking SHORTs on noise)
SHORT_VEL_FILTER_GREEN_THRESHOLD = 5   # CEO 2026-08-16 — STARVATION FIX: 3 green candles blocked BCH SHORT (vel=-0.056%, last3g=3). 5 green candles = stronger signal SHORT is counter-trend. Monitor: SHORT WR (should stay ≥50%), daily trades (must ↑).

# ── Weather Vane: Directional Outcome Tracker ─────────────────────────────
# Detects regime shifts by monitoring trade outcomes per direction.
# Fires when 3+ of last 5 trades in same direction are losses within 30min.
# Faster than regime scanners (leading indicator vs lagging slope).
DIRECTIONAL_OUTCOME_ENABLED = True
DIRECTIONAL_OUTCOME_WINDOW = 5            # last N trades per direction
DIRECTIONAL_OUTCOME_TIME_WINDOW = 15      # minutes (rolling window — tightened from 30 for faster detection)
DIRECTIONAL_OUTCOME_LOSS_THRESHOLD = 3    # N losses in window to trigger
DIRECTIONAL_OUTCOME_WR_THRESHOLD = 40     # backup: WR below this also triggers
DIRECTIONAL_OUTCOME_PENALTY = 0.7         # score multiplier (milder for first deploy)
DIRECTIONAL_OUTCOME_MIN_TRADES = 3        # minimum trades before activating
DIRECTIONAL_OUTCOME_RECOVERY_WR = 45      # hysteresis: WR% required to deactivate suppression
# Velocity tiers: tiered penalty based on loss_velocity (losses/total).
# Higher velocity = faster deterioration = stronger penalty.
DIRECTIONAL_OUTCOME_VELOCITY_ENABLED = True
DIRECTIONAL_OUTCOME_VELOCITY_TIERS = {
    0.6: 0.0,   # severe (3+/5 losses) → hard block (upgraded from 0.5x penalty — regime-transition-analysis-2026-08-24)
    0.4: 0.5,   # moderate (2/5) → strong penalty (upgraded from 0.7x)
}
# Integral: long-window catch for slow bleeds that don't hit short-window threshold.
DIRECTIONAL_OUTCOME_INTEGRAL_ENABLED = True
DIRECTIONAL_OUTCOME_INTEGRAL_WINDOW = 240     # minutes (4 hours)
DIRECTIONAL_OUTCOME_INTEGRAL_THRESHOLD = 5    # losses in long window to trigger
DIRECTIONAL_OUTCOME_INTEGRAL_PENALTY = 0.8    # milder than short-window penalty
# Direction Lock: after severe loss (3+/5), lock direction for N minutes.
# Prevents re-entry during clear bad streaks — no unsuppression during lock.
DIRECTIONAL_OUTCOME_LOCK_ENABLED = True
DIRECTIONAL_OUTCOME_LOCK_MINUTES = 30         # lock duration after severe failure
DIRECTIONAL_OUTCOME_LOCK_VELOCITY = 0.6       # loss_velocity threshold for lock activation (matches 0.6 tier)

# ── Position Shield (Weather Vane Component 2) ─────────────────────────────
# Tighten trailing stops on counter-regime LOSING positions when Weather Vane fires.
# Winners left alone — trailing already protecting them.
WEATHER_VANE_SHIELD_ENABLED = True
WEATHER_VANE_SHIELD_TRAILING_PCT = 0.0030   # 0.30% tightened from default 2.00%
WEATHER_VANE_SHIELD_MAX_HOLD_MIN = 30       # force-close if still open after this
WEATHER_VANE_SHIELD_LOSING_ONLY = True      # only shield positions with pnl < 0

# ── HL Reconciliation Post-Mortem ──────────────────────────────────────────
# Automated PnL reconciliation: compare DB trades against HL fills every N hours.
# Auto-corrects divergences > threshold. Catches calc_notional bugs, fee errors,
# and any other PnL discrepancies between local DB and HL ground truth.
HL_RECONCILIATION_ENABLED = True
HL_RECONCILIATION_INTERVAL_HOURS = 4        # how often to run
HL_RECONCILIATION_DIVERGENCE_THRESHOLD = 5.0  # % divergence to auto-fix
HL_RECONCILIATION_LOOKBACK_HOURS = 6        # DB trade window to check
HL_RECONCILIATION_MATCH_WINDOW_MINUTES = 5  # HL fill matching tolerance

# ── Tide Detection (Weather Vane v4) ───────────────────────────────────────
# BTC 3h momentum as fastest lagging indicator for regime shift detection.
# Bearish tide: BTC 3h falling + SHORT WR > 55% → suppress LONG
# Bullish tide: BTC 3h rising + SHORT WR < 45% → suppress SHORT
TIDE_ENABLED = True
TIDE_PENALTY = 0.7
TIDE_BTC_MOM_WINDOW = 3          # hours for BTC momentum
TIDE_BTC_MOM_FALLING = -0.1      # % — below this = falling
TIDE_BTC_MOM_RISING = 0.1        # % — above this = rising
TIDE_SHORT_WR_WINDOW = 10        # trades for confirmation
TIDE_SHORT_WR_THRESHOLD_HIGH = 55
TIDE_SHORT_WR_THRESHOLD_LOW = 45

# ── BTC Flash Crash Filter v2 (2026-08-22, overhaul 2026-08-24) ──────────────
# Multi-layer crash detection using leading indicators:
#   Layer 1: Dynamic price crash (ATR-scaled, not fixed %)
#   Layer 2: Volume spike detection (selling pressure before price breaks)
#   Layer 3: Multi-asset contagion (ETH/SOL leading BTC down)
#   Layer 4: Price acceleration (velocity increasing downward)
#   Layer 5: Position protection (ATR-aware MAE guard for existing LONGs)
# Module: btc_crash_filter.py
BTC_CRASH_BLOCK_ENABLED = True

# Layer 1: Dynamic price threshold (ATR-scaled)
BTC_CRASH_BLOCK_BASE_THRESHOLD = -1.5   # % — base threshold at baseline ATR
BTC_CRASH_BLOCK_BASELINE_ATR = 0.8      # % — ATR% at which base threshold applies
BTC_CRASH_BLOCK_MIN_THRESHOLD = -1.0    # % — tightest threshold (low vol, crashes hurt more)
BTC_CRASH_BLOCK_MAX_THRESHOLD = -2.5    # % — widest threshold (high vol, normal swings)
BTC_CRASH_BLOCK_THRESHOLD = -1.5        # DEPRECATED — kept for backward compat, use BASE_THRESHOLD

# Layer 2: Volume spike detection
BTC_CRASH_VOL_SPIKE_ENABLED = True
BTC_CRASH_VOL_SPIKE_THRESHOLD = 3.0     # x — current volume must be 3x+ of 20-bar average

# Layer 3: Multi-asset contagion
BTC_CRASH_CONTAGION_ENABLED = True
BTC_CRASH_CONTAGION_THRESHOLD = 0.30    # % — ETH must fall 0.30%+ more than BTC in 5m

# Layer 4: Acceleration detection
BTC_ACCEL_ENABLED = True
BTC_ACCEL_VEL_THRESHOLD = -0.15         # % — min velocity per 1m candle to trigger
BTC_ACCEL_WINDOW = 2                    # bars to compare acceleration (vel_now < vel_prev)
BTC_ACCEL_BLOCK_DURATION = 5            # minutes to block entries after trigger

# Layer 5: Position protection (ATR-aware MAE guard)
# NOTE: CL_MAE_GUARD_ENABLED is defined below with the legacy MAE guard constants.
# CL_MAE_GUARD_BASE_THRESHOLD scales with ATR (replaces fixed CL_MAE_GUARD_THRESHOLD).
CL_MAE_GUARD_BASE_THRESHOLD = 0.020     # 2.0% base — scales with ATR (conservative start, was 2.5%)
                                         # RAISED from 2.5% to 2.0% 2026-08-23 — tighter crash protection
                                         # If profitable after 7d, consider tightening to 1.5%.
CL_MAE_GUARD_BTC_CRASH_MULTIPLIER = 0.6 # Tighten threshold by 40% when BTC is crashing (cut faster)

# Layer 6: Multi-Alt Divergence (cascade early warning)
# Detects alt-specific weakness before BTC cascades.
# When 3+ alts diverge >0.3% below BTC in 5 minutes, block new LONG entries.
# Backtested 7d: 10 triggers (1.43/day), net +$1.92 improvement.
MULTI_ALT_DIVERGENCE_ENABLED = True
MULTI_ALT_BTC_5M_THRESHOLD = -0.5     # % — BTC must be falling to activate check
MULTI_ALT_DIVERGENCE_THRESHOLD = -0.3  # % — alt must underperform BTC by this much
MULTI_ALT_MIN_WEAK_ALTS = 3           # number of weak alts to trigger signal
MULTI_ALT_BLOCK_DURATION_MIN = 10     # minutes to block LONG entries after trigger
MULTI_ALT_REFERENCE_ALTS = ['ETH', 'SOL', 'XRP', 'DOGE', 'AVAX', 'DOT', 'LINK', 'UNI']

# Layer 7: BTC 30m Momentum Filter (regime-transition-analysis-2026-08-24)
# Blocks entries when BTC 30m momentum is rising (SHORT) or falling (LONG).
# Catches V-reversals that TIDE (3h window) misses entirely.
# Would have prevented 3/6 losing SHORT entries in Aug 24 incident.
BTC_MOMENTUM_FILTER_ENABLED = True
BTC_MOMENTUM_WINDOW = 30                    # minutes — momentum lookback
BTC_MOMENTUM_RISING_THRESHOLD = 0.15        # % — block SHORT if BTC 30m momentum > this
BTC_MOMENTUM_FALLING_THRESHOLD = -0.15      # % — block LONG if BTC 30m momentum < this
BTC_MOMENTUM_BLOCK_DURATION_MIN = 10        # minutes to block entries after trigger

# ── Volatility Floor Filter ───────────────────────────────────────────────────
# Block low-volatility entries — no energy = no trade.
# Backtested 14d: SHORT vol<0.30% → blocks 78T (41% WR), keeps 47T (74% WR), net +$1.79.
VOL_FLOOR_ENABLED = True
VOL_FLOOR_THRESHOLD = 0.15             # CEO 2026-08-16 — STARVATION FIX: 0.30% killed every signal in NEUTRAL regime (102/104 tokens, low vol). 0.15% keeps safety net but unblocks signal flow. Monitor: daily trades (must ↑ from 0), vol-floor blocks (should ↓).

# ── Confidence Filter ────────────────────────────────────────────────────────
# Block trades with confidence >= threshold. 90+ trades are the worst performers
# (48.7% WR, -$1.45 PnL over 7d). The signal fires on extended moves — by the
# time confidence reaches 90+, the easy move is done and you're buying the top.
# Plan: conf-filter-plan.md (2026-08-19)
CONF_FILTER_ENABLED = True
CONF_FILTER_MAX = 89                    # block if confidence >= this value (raised from 85 — 90+ tier now +$1.91/7d without ct-hot+, 95+ tier most profitable)

# ── Time-of-Day Block ────────────────────────────────────────────────────────
# Penalty during 01:00-06:00 UTC (Asian session close, low-liquidity pre-market).
# 83T 33W (39.8%) -$1.34 in this window (conf-filter-plan.md, 2026-08-19).
# Changed from hard block to 0.7x penalty (2026-08-22) — hard block was too aggressive.
TIME_BLOCK_ENABLED = True               # Penalty during 01-06 UTC (was hard block, re-enabled as penalty 2026-08-22)
TIME_BLOCK_START = 1                    # UTC hour (inclusive)
TIME_BLOCK_END = 6                      # UTC hour (exclusive: blocks 01:00-05:59)
TIME_BLOCK_PENALTY = 0.7                # Score multiplier during dead zone (matches tide penalty)

# ── Per-Token WR Filter ──────────────────────────────────────────────────────
# Block tokens with WR below this threshold AND >= MIN_SAMPLE trades.
# Used by signal_compactor (HOTSET-FILTER) and decider_run (direction WR).
# Lower = more permissive (more trades, but more losers).
TOKEN_WR_THRESHOLD = 30               # min WR% to allow (LOWERED from 40 — reduce trade starvation, 2026-08-02)
TOKEN_WR_MIN_SAMPLE = 10              # min trades before filter applies (was 5, raised 2026-08-03 — 5 trades is statistically meaningless)

# ── Wrong-Side Learning Gate ─────────────────────────────────────────────────
# Penalty and skip threshold for tokens with wrong-side entry history.
# Softened 2026-08-03: was -15 penalty / 55 skip threshold — too aggressive,
# blocking ~80% of hot-set candidates. Now -10 / 50 (matches MIN_EXEC_CONFIDENCE).
WRONG_SIDE_PENALTY = 10               # confidence penalty when wrong-side detected
WRONG_SIDE_SKIP_THRESHOLD = 50        # skip if adjusted conf below this (= MIN_EXEC_CONFIDENCE)

# ── Similar Setup Lookup (Historical Trade Recall) ───────────────────────────
# Queries PostgreSQL for past trades with same signal+direction+market conditions.
# WR < hard_block → SKIP, WR 30-49% → confidence penalty (advisory).
SIMILAR_SETUP_LOOKUP_ENABLED = True
SIMILAR_SETUP_MIN_SAMPLE = 3          # need >= 3 similar trades to act
SIMILAR_SETUP_HARD_BLOCK_WR = 30      # <30% WR with >=5 similar → hard SKIP
SIMILAR_SETUP_HARD_BLOCK_MIN_N = 5    # minimum n for hard block
SIMILAR_SETUP_PENALTY_40 = 20         # WR 40-49% → -20 confidence (was -10, too lenient for losing setups)
SIMILAR_SETUP_PENALTY_30 = 25         # WR 30-39% → -25 confidence (was -15, low WR needs stronger suppression)
SIMILAR_SETUP_RSI_BAND = 15           # RSI ± this for "similar"
SIMILAR_SETUP_CACHE_TTL = 300         # 5 min cache per token+source+direction+tier

# ── Hard vs Soft Guardrails ──────────────────────────────────────────────────
# Rule-based gate = hard block (SKIP = real skip, trade blocked)
# LLM gate = soft advisory (WARN = confidence penalty, not block)
LLM_CONFIDENCE_PENALTY = 15           # penalty applied when LLM returns WARN

# ── Hebbian WR Estimate ──────────────────────────────────────────────────────
# Uses brain.db (token ↔ signal) Hebbian weight to estimate historical WR.
# Soft advisory: adjusts confidence, never blocks. Pass on low data.
HEBBIAN_BOOST_WR = 0.60               # est WR >= 60% with n>=3 → +5 confidence
HEBBIAN_BOOST_AMOUNT = 5              # confidence bonus when boost triggers
HEBBIAN_BOOST_MIN_N = 3               # minimum co-occurrences to trust boost
HEBBIAN_PENALTY_WR = 0.30             # est WR <= 30% with n>=5 → -10 confidence
HEBBIAN_PENALTY_AMOUNT = 10           # confidence penalty when penalty triggers
HEBBIAN_PENALTY_MIN_N = 5             # minimum co-occurrences to trust penalty
HEBBIAN_CACHE_TTL = 600               # 10 min — Hebbian changes only on close

# ── Phase 3a: Token Sentiment ────────────────────────────────────────────────
TOKEN_SENTIMENT_ENABLED = True         # enabled 2026-08-02 — 10.2% of historical trades on chronic loser tokens (BSV, STBL, etc.)
TOKEN_SENTIMENT_K = 20                 # top-K recall concepts to evaluate
TOKEN_SENTIMENT_SKIP_THRESHOLD = -0.7  # sentiment <= this → SKIP (chronic loser)
TOKEN_SENTIMENT_HARD_SKIP_THRESHOLD = -0.85  # sentiment <= this → hard skip (very strong negative)
TOKEN_SENTIMENT_BOOST_THRESHOLD = 0.7  # sentiment >= this → +3 confidence boost
TOKEN_SENTIMENT_BOOST_AMOUNT = 3       # confidence boost on positive sentiment

# ── Wrong-side stall detection ────────────────────────────────────────────────
WRONG_SIDE_AVG_PCT_THRESH = 1.0   # wrong-side trigger: avg counter move >= 1.5%

# ── Pause switches ─────────────────────────────────────────────────────────────
# Flip to True to disable without restarting anything. Flip back to False to re-enable.
MACD_EXIT_PAUSED = True   # Disable macd_rules.py exit signals (ATR TP/SL handles closes)
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

# ── CHoCH (Change of Character) ────────────────────────────────────────────────
HH_HL_CHOCH_BASE_CONFIDENCE = 70   # higher base — CHoCH is a stronger reversal signal
HH_HL_CHOCH_STRUCT_BONUS_MAX = 10  # bonus for clean 4-swing structure
HH_HL_CHOCH_RECENCY_BONUS_MAX = 6  # bonus for fresh flip
HH_HL_CHOCH_MAX_BARS_SINCE   = 15  # reject if flip is older than this many bars

# ── Profit Monster ─────────────────────────────────────────────────────────────
# profit_monster.py — closes medium-profit positions (2-5%) at random intervals.
# Never touches losing positions.
# ── Profit Monster — Two-Tier Take-Profit ──────────────────────────────────────
# Tier 1: Quick scalp — lower profit, fires frequently
PM_TIER1_MIN_PCT    = 0.5    # min profit % to close
PM_TIER1_MAX_PCT    = 2.0    # max profit % to close
PM_TIER1_MAX_CLOSE  = 2      # max positions to close per wake
PM_TIER1_SKIP_TOP_PCT = 0    # don't touch top X% most profitable (0 = disabled)
PM_TIER1_FIRE_WINDOWS = {"A": (1, 3), "B": (3, 6)}   # minutes between fires

# Tier 2: Runner — higher profit, fires less frequently
PM_TIER2_MIN_PCT    = 2.0    # min profit % to close
PM_TIER2_MAX_PCT    = 5.0    # max profit % to close
PM_TIER2_MAX_CLOSE  = 1      # max positions to close per wake
PM_TIER2_SKIP_TOP_PCT = 0   # don't touch top 20% — let best runners go
PM_TIER2_FIRE_WINDOWS = {"A": (5, 10), "B": (10, 20)}  # minutes between fires

# Tier T: Trailing profit — marks trades in profit, trails peak, exits on weakness
PM_TRAIL_ENABLED     = True   # act 0.40%, dist 0.20%. Floor = +0.20%.
PM_TRAIL_ACTIVATE_PCT = 0.004  # 0.40%
PM_TRAIL_DISTANCE_PCT = 0.002  # 0.20%
PM_TRAIL_MIN_HOLD    = 2      # minimum minutes before trailing activates
PM_TRAIL_FIRE_WINDOWS = {"A": (0.25, 0.5), "B": (0.5, 1)}  # check every 15-30s group A, 30-60s group B

PM_DRY_RUN          = False  # global kill switch
PM_DEFAULT_NOTIONAL  = 11.0  # default margin per trade (USDT) — used when DB amount_usdt unavailable
# Signals bypassed by profit_monster — these trades get regular ATR SL/TP only.
# Matches any signal containing the prefix (e.g. 'atr-spike+,rs-s36' matches 'atr-spike').
PROFIT_MONSTER_BYPASS_SIGNALS = (
    'atr-spike', 'r2-trend-long', 'ct-hot+', 'ct-hot-',
    'hl_copy_trader',  # copy trader exit correlation — handled by hl_fill_monitor
    'hzscore',  # CEO: bypass profit_monster trail — hzscore trades get regular ATR SL/TP only
    'bb_bounce+',   # 71.9% WR, +0.89% avg — proven, ride ATR SL not PM Trail
    'confluence',   # meta-signal, proven — persistence + compounding validation
    'stop_hunt_reversal',  # 50% WR, -0.15% avg — break-even, no PM Trail benefit
)
STALE_ROTATION_ENABLED = False  # PAUSED 2026-08-04 — closing trades too aggressively, needs tuning

# ── Time / Peak Exit Kill Switches ──────────────────────────────────────────────
# position_manager.py — controls time-based and peak-reversal exits.
# Both had 0% WR across 7 trades (2026-08-01 analysis). Disabling to let
# ATR SL/TP and trailing handle exits instead.
TIME_EXIT_ENABLED = False   # DISABLED 2026-08-01 — 0% WR (0/4), closing positions at small losses
PEAK_EXIT_ENABLED = False   # DISABLED 2026-08-01 — 0% WR (0/3), locking in losses on reversals

# ── Cut Loser v2 ──────────────────────────────────────────────────────────────
# cut_loser.py — Two-tier loss cutting + trailing loss. Mirror of profit_monster.
# Tier 1 (Quick Cut): catches small losses fast. Tier 2 (Deep Cut): handles bigger bleeds.
# Trailing Loss: tracks worst point, cuts on recovery failure.
CUT_LOSER_ENABLED      = True   # master switch

# Tier 1: Quick Cut — -0.3% to -1.0%, fires frequently
CL_TIER1_MIN_PCT      = -2.0    # floor (don't cut deeper than this in T1)
CL_TIER1_MAX_PCT      = -1.0    # ceiling (start cutting at -1.0%)
CL_TIER1_MAX_CLOSE    = 2       # max positions to close per wake
CL_TIER1_SKIP_BOTTOM_PCT = 10   # don't touch bottom 10% worst losers
CL_TIER1_FIRE_WINDOWS = {"A": (1, 3), "B": (3, 6)}

# Tier 2: Deep Cut — -1.0% to -3.0%, fires less frequently
CL_TIER2_MIN_PCT      = -5.0    # floor
CL_TIER2_MAX_PCT      = -2.0    # ceiling (T1 handles above this)
CL_TIER2_MAX_CLOSE    = 1       # max positions to close per wake
CL_TIER2_SKIP_BOTTOM_PCT = 20   # don't touch bottom 20% — let ATR SL handle catastrophic
CL_TIER2_FIRE_WINDOWS = {"A": (3, 6), "B": (6, 12)}

# Trailing Loss — mirror of PM_TRAIL (inverted logic)
CL_TRAIL_ENABLED        = False
CL_TRAIL_ACTIVATE_PCT   = -1.0   # -1.0% — reverted from -0.5% (cut-loser needs room before trailing)
CL_TRAIL_RECOVER_PCT    = 0.15   # cut if recovers 0.15% from worst then drops back
CL_TRAIL_MIN_HOLD       = 2      # minimum minutes before trailing activates
CL_TRAIL_FIRE_WINDOWS   = {"A": (0.5, 1), "B": (1, 2)}

# MAE Guard — cut_loser.py (runs every wake, immediate crash protection)
# If price drops more than MAE_GUARD_THRESHOLD from highest_price, cut immediately.
# Catches mass crashes (WLFI -41%, MET -21%, ETH -13%) before ATR SL triggers.
# Runs BEFORE tiers — highest priority.
CL_MAE_GUARD_ENABLED    = True   # RE-ENABLED 2026-08-23 — ATR-aware version scales dynamically
                                 # Conservative 2.0% base. Monitor 7d: if net positive, tighten to 1.5%.
CL_MAE_GUARD_THRESHOLD  = 0.020  # 2.0% — legacy fallback (must match BASE_THRESHOLD for ATR-aware code)
# Legacy constants (keep for backward compat / guardian)
LOSS_MIN_PCT           = -3.0   # deprecated → use CL_TIER2_MIN_PCT
LOSS_MAX_PCT           = -0.5   # deprecated → use CL_TIER1_MAX_PCT
CUT_LOSER_MAX_CLOSE    = 1      # deprecated → use CL_TIER1_MAX_CLOSE
SKIP_BOTTOM_PCT        = 0      # deprecated → use CL_TIER1_SKIP_BOTTOM_PCT
CUT_LOSER_FIRE_WINDOWS = {"A": (1, 3), "B": (3, 6)}  # deprecated

# ── Signal Kill Switches ───────────────────────────────────────────────────────
# Master kill switches for each signal family. True = signal can fire.
# False = signal is blocked at BOTH add_signal() (Layer 2) AND decider_run (Layer 3).
# Individual +/- variants controlled by *_PLUS_ENABLED / *_MINUS_ENABLED flags below.
#
# NEVER_REENABLE_FLAGS: signal_rotator.py checks this set and SKIPS re-enabling
# any flag listed here. Use for signals that have been permanently disabled by
# manual decision (CEO/developer) — prevents the rotator's auto-enable logic
# from overriding a deliberate kill-switch decision.
NEVER_REENABLE_FLAGS = {
    'INVERSE_ACCEL_300_ENABLED',
    'INVERSE_ACCEL_300_PLUS_ENABLED',
    'INVERSE_ACCEL_300_MINUS_ENABLED',
    'ACCEL_300_ENABLED',           # 0% WR over 48h, no edge — permanently dead
    'ACCEL_300_PLUS_ENABLED',      # 0% WR over 48h — permanently dead
    'ACCEL_300_MINUS_ENABLED',     # 15% WR, -$1.26 in 7d — permanently dead
    'ACCEL_300_BREAKOUT_ENABLED',  # 0% WR (0/3) — permanently dead
    'ACCEL_300_VELOCITY_IGNITION_ENABLED',  # 0% WR (10 trades), -$4.97 — permanently dead
    'ACCEL_300_VELOCITY_PLUS_ENABLED',  # permanently dead
    'ACCEL_300_VELOCITY_MINUS_ENABLED', # permanently dead
    'PATTERN_WOLF_ENABLED',       # 0% WR (10 trades 7d), -$1.38 — permanently dead
    'PATTERN_SCANNER',            # CEO 2026-08-04 — 0% WR, no flag mapping, permanently dead
    'VEL_HERMES_ENABLED',         # CEO 2026-08-04 — 0% WR (12 trades 7d), permanently dead
    'VEL_HERMES_PLUS_ENABLED',    # 31% WR, negative PnL, permanently dead
    'VEL_HERMES_MINUS_ENABLED',   # 45% WR but avg PnL marginal — manually killed, rotator must not re-enable
    'TL_BREAK_ENABLED',           # CEO 2026-08-07 — 33.3% WR (66 trades 7d), -$1.33. hemorrhaging.
    'TL_BREAK_PLUS_ENABLED',      # CEO 2026-08-07 — master TL_BREAK killed
    'TL_BREAK_MINUS_ENABLED',     # SIGNAL REPORTER 2026-08-25 — 28.6% WR, -$0.32 (24h), 7T. NEVER_REENABLE.
    'ZSCORE_RISING_ENABLED',      # CEO 2026-08-07 — 38.6% WR (44 trades 7d), -$1.37. No edge.
    'ZSCORE_RISING_PLUS_ENABLED', # CEO 2026-08-07 — master ZSCORE_RISING killed
    'ZSCORE_RISING_MINUS_ENABLED',# CEO 2026-08-07 — master ZSCORE_RISING killed
    # HZSCORE_MINUS_ENABLED — RE-ENABLED 2026-08-22 by T (signal starvation fix)
    # HZSCORE_PLUS_ENABLED — RE-ENABLED 2026-08-22 by T (signal starvation fix)
    'PCT_HERMES_PLUS_ENABLED',    # CEO 2026-08-07 — historical 100% WR, but combo signals bleeding (-$33.83 standalone)
    'VORTEX_BREAK_PLUS_ENABLED',  # SIGNAL REPORTER 2026-08-09 — vortex_break_long: 22.2% WR (9 trades 24h), -$0.18. Compounds hemorrhaging.
    'WAVE_CATCHER_PLUS_ENABLED',  # SIGNAL REPORTER 2026-08-15 — 33.3% WR, -$0.34 (24h). LONG dead.
    'WAVE_CATCHER_MINUS_ENABLED', # CEO KILLED 2026-08-16 — 25% WR -$0.09. No edge.
    'WAVE_CATCHER_ENABLED',       # CEO KILLED 2026-08-17 — both variants dead. Master switch.
    'MOMENTUM_LEADERBOARD_PLUS_ENABLED',  # SIGNAL REPORTER 2026-08-15 — 28.6% WR, -$0.15 (24h). LONG dead.
    'MOMENTUM_LEADERBOARD_ENABLED',       # SIGNAL REPORTER 2026-08-20 — 28.6% WR, -$0.15 (7d). Both directions dead.
    'MOMENTUM_LEADERBOARD_MINUS_ENABLED', # SIGNAL REPORTER 2026-08-20 — SHORT never produced meaningful trades.
    'RANGE_BREAKOUT_PLUS_ENABLED',  # SIGNAL REPORTER 2026-08-15 — 25% WR, -$0.41 (7d). LONG dead.

    'ACCEL_300_STANDALONE_BYPASS_ENABLED',  # CEO 2026-08-17 — 40T/7d 55% WR -$0.30. Net negative. NEVER_REENABLE.
    'STOP_HUNT_REVERSAL_LONG_ENABLED',      # CEO 2026-08-21 — 10T/7d 60% WR -$0.04 break-even, 48h 50% -$0.10 deteriorating. NEVER_REENABLE.
    'STOP_HUNT_REVERSAL_LONG_PLUS_ENABLED', # CEO 2026-08-21 — same. NEVER_REENABLE.
    'COIN_TRACKER_HOT_ENABLED',         # ORCHESTRATOR 2026-08-25 — 36.4% WR, -$3.65/7d. Without it: system +$1.30/7d. NEVER_REENABLE.
    'COIN_TRACKER_HOT_PLUS_ENABLED',    # SIGNAL REPORTER 2026-08-24 — 28.6% WR, -$0.49 (24h), 14T. NEVER_REENABLE.
    'COIN_TRACKER_HOT_MINUS_ENABLED',   # SIGNAL REPORTER 2026-08-24 — 0% WR (6T), -$0.34. NEVER_REENABLE.
    'HZSCORE_MINUS_ENABLED',  # SIGNAL REPORTER 2026-08-23 — 8T/24h 37.5% WR -$0.35, avg loser 2x avg winner. NEVER_REENABLE.
    'HL_COPY_SIGNAL_PLUS_ENABLED',  # SIGNAL REPORTER 2026-08-25 — 30% WR, -$0.74 (24h), 10T. Copy delay. NEVER_REENABLE.
}
PCT_HERMES_ENABLED       = False  # disabled 2026-05-06 — signals now fire via signals_runner (scripts/signals/)
PCT_HERMES_PLUS_ENABLED  = False   # pct-hermes+ — 100% WR, +$2.31, only good pct variant
PCT_HERMES_MINUS_ENABLED = False  # CEO 2026-08-09 — 25% WR, -$0.15/7d. All SHORT combos negative.
VEL_HERMES_ENABLED       = False  # CEO 2026-08-04 — KILLED. 0% WR (12 trades 7d), -$1.61. No edge.
VEL_HERMES_PLUS_ENABLED  = False  # vel-hermes+ — 31% WR, avg=-0.127%, blocked
VEL_HERMES_MINUS_ENABLED = False  # AUTO-DISABLED by signal_decay_detector   # RE-ENABLED 2026-08-04 — signal diversity, zscore_rising at 0   # vel-hermes- — 45% WR, +0.404% avg, re-test enabled
HZSCORE_ENABLED          = True  # CEO KILLED 2026-08-17 — both directions dead. Plus: 32T ~38% WR -$0.47/7d (standalone + combos). Minus: 35T 54.3% WR -$0.22/7d.
HZSCORE_PLUS_ENABLED     = True   # RE-ENABLED 2026-08-22 by T — signal starvation fix. Was: 32T ~38% WR -$0.47/7d.
HZSCORE_MINUS_ENABLED    = False  # SIGNAL REPORTER 2026-08-23 — 8T/24h 37.5% WR -$0.35, avg loser 2x avg winner. Auto-rotation failed (was re-enabled 2026-08-22). NEVER_REENABLE.
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
ACCEL_300_LOOKBACK        = 30   # bars ago when price was on the other side of EMA300 — for LONG (was 100 → tightened 2026-06-08)
ACCEL_300_LOOKBACK_SHORT  = 500  # much longer lookback for SHORT — handles sustained bleeds where cross is far in the past (was 30)
ACCEL_300_PERSISTENCE_BARS = 7    # min bars gap must persist (was 10 — catch moves earlier in weak trends)
ACCEL_300_MIN_GAP_GROWTH = -0.05  # allow gap narrowing up to 0.05% (was 0.005 — too strict for ranging market)
ACCEL_300_MIN_GAP_EXPANSION = 0.01 # price must be this much farther from EMA than at cross bar (gap expansion gate — both directions)
ACCEL_300_MIN_GAP_PCT     = 0.20 # minimum gap above/below EMA300 to fire — was hardcoded in accel_300.py (was 0.15 → tightened 2026-05-11)
ACCEL_300_MIN_GAP_PCT_LONG = 0.35   # min EMA gap % for LONG (was 0.50 — too tight for current low-vol market)
ACCEL_300_MIN_GAP_PCT_SHORT = 0.35  # min EMA gap % for SHORT (was 0.50 — symmetric)
ACCEL_300_MIN_GAP_GROWTH_SHORT = -0.10  # allow slight gap narrowing for SHORT (was 0.06)
ACCEL_300_COOLDOWN_BARS   = 10   # dedup: only fire once per N bars per token+direction (was 12 → tightened 2026-05-11)
ACCEL_300_LOOKBACK_1M     = 700  # 1m prices to fetch per token (warmup + detection window)
ACCEL_300_ENABLED        = False  # DISABLED 2026-08-13 10:30 — 19T today 36.8% WR -$0.73, 12/19 ATR SL hits. Re-enabled yesterday but deteriorated.
ACCEL_300_COOLDOWN_MIN    = 1    # minutes between signals per token+direction
ACCEL_300_REGIME_SLOPE_PCT = 0.05    # RE-RAISED 2026-08-25 — was 0.01%. SHORT signals blocked at 0.03-0.06% slopes.
ACCEL_300_SLOPE_WINDOW     = 20    # bars over which to compute regime slope (simple linear regression)
ACCEL_300_MIN_ATR_PCT      = 0  # disabled — backtest shows ATR alone can't separate winners from losers (overlap 0.07-0.25%)
ACCEL_300_STALE_BARS = 15   # max bars since EMA cross for LONG (was 25 — fresher signals, catch moves earlier)
ACCEL_300_STALE_BARS_SHORT = 15   # max bars since EMA cross for SHORT (was 25 — fresher signals)
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

# ── Inverse Accel-300 (Mean Reversion) ───────────────────────────────────────
# Fires when price is overextended from EMA300 and starting to revert.
# Opposite of accel_300: SHORT when price far above EMA300 and falling,
# LONG when price far below EMA300 and rising.
# TUNED 2026-07-27: enter earlier (smaller gap), block overextended (max_gap),
# require stronger reversion confirmation. 0% WR on gap>=0.15% → cap at 0.8%.
INVERSE_ACCEL_300_MIN_GAP_PCT_LONG = 1.5    # min gap below EMA300 to fire LONG (was 2.0 — low-vol market needs lower threshold)
INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT = 1.5   # min gap above EMA300 to fire SHORT (was 2.0 — same rationale)
# NOTE: inv-accel-300- is DISABLED (INVERSE_ACCEL_300_MINUS_ENABLED=False ) but still executing
# due to kill switch bypass bug (25th consecutive analysis). Gap raised to 5.0%
# as defense-in-depth — if signal fires despite kill switch, at least filter marginal entries.
INVERSE_ACCEL_300_REVERSION_BARS = 2          # min bars of gap narrowing (was 3 — reduce starvation, let signal fire sooner)
INVERSE_ACCEL_300_REVERSION_THRESHOLD = 0.05 # min gap narrowing % to confirm reversion (was 0.08 — lower threshold for more entries)
INVERSE_ACCEL_300_COOLDOWN_BARS = 15         # cooldown between signals per token+direction
INVERSE_ACCEL_300_LOOKBACK_1M = 700          # 1m prices to fetch per token
INVERSE_ACCEL_300_MAX_GAP_PCT = 5.0          # don't fire if gap is too extreme (RAISED to 5.0 — match MIN_GAP defense-in-depth)
# 1h trend filter: skip if price moved >0.5% against reversion direction in last hour
INVERSE_ACCEL_300_TREND_FILTER_PCT = 0.30    # max 1h move against reversion direction (was 0.50 — too lenient)
# ── Accel-300 Chop Filter (signals/accel_300.py) ─────────────────────────────────
# Suppress signals in choppy/ranging markets — all 3 conditions must be true to block
ACCEL_300_CHOP_CROSS_GAP_PCT   = 0.10  # gap at cross bar must be >= this
ACCEL_300_CHOP_EMA_ANGLE_PCT   = 0.04  # 50-bar EMA angle must be >= this
ACCEL_300_CHOP_AVG_GAP_PCT     = 0.50  # avg gap magnitude over 50 bars must be >= this
ACCEL_300_CHOP_LOOKBACK        = 50   # bars used for EMA angle and avg-gap chop checks

# ── Accel-300 Ultra-Fast Breakout (signals/accel_300.py) ──────────────────────
# Fires on high-velocity breakouts BEFORE persistence confirms the trend.
# Backtested: 78% WR, +1.60% avg PnL on STX (11 signals in 3 days).
ACCEL_300_BREAKOUT_ENABLED     = True   # re-enabled 2026-08-12 — confidence raised to 80
ACCEL_300_BREAKOUT_VELOCITY    = 1.0    # min price move % in 5 bars (1.0% = fast breakout)
ACCEL_300_BREAKOUT_GAP_MIN     = 0.5    # min gap % from EMA60 (was 1.0 — too restrictive)
ACCEL_300_BREAKOUT_TREND_EMA   = 200    # LONG only above this EMA, SHORT only below
ACCEL_300_BREAKOUT_VOL_MULT    = 1.5    # volume must be > N * 20-bar average
ACCEL_300_BREAKOUT_COOLDOWN    = 8      # bars between signals per token (40min = 8 * 5m)
ACCEL_300_BREAKOUT_CONFIDENCE  = 80     # base confidence for breakout signals

# ── Velocity Ignition (FIX 2026-07-31) ────────────────────────────────────────
# Catches the FIRST strong momentum bar after EMA300 cross — enters 15-20 min
# earlier than persistence mode. Key for moves like MOVE 2026-07-31.
ACCEL_300_VELOCITY_IGNITION_ENABLED   = False  # DISABLED 2026-08-01 — 0% WR (10 trades), -$4.97 total. Fires on first bar spike that reverses.
ACCEL_300_VELOCITY_PLUS_ENABLED      = False # RE-ENABLED 2026-08-04 — signal diversity
ACCEL_300_VELOCITY_MINUS_ENABLED     = False # RE-ENABLED 2026-08-04 — signal diversity
ACCEL_300_VELOCITY_IGNITION_THRESHOLD = 1.5    # last bar must be > N x average bar change
ACCEL_300_VELOCITY_IGNITION_MIN_GAP   = 0.30   # min gap % from EMA300 (lower than persistence 0.50)
ACCEL_300_VELOCITY_IGNITION_MIN_GAP_GROWTH = 0.02  # gap must grow over 3 bars (positive = widening)
ACCEL_300_VELOCITY_IGNITION_MAX_CROSS_AGE  = 15    # cross must be within N bars (fresh move)

GAP_300_ENABLED          = False  # gap-300+ — 14.3% WR, -$1.52, worst active loser
GAP_300_PLUS_ENABLED      = False
GAP_300_MINUS_ENABLED     = False

# ── Pattern Scanner Toggles (pattern_scanner.py) ─────────────────────────────
PATTERN_FLAG_ENABLED       = False  # CEO 2026-08-04 — 0% WR, no edge, permanently disabled
PATTERN_MICRO_FLAG_ENABLED = False   # DISABLED 2026-08-02 — matches master flag
PATTERN_TRIANGLE_ENABLED   = False  # CEO 2026-08-04 — 0% WR, no edge, permanently disabled
PATTERN_WOLF_ENABLED       = False  # CEO 2026-08-05 — 0% WR (10 trades 7d), -$1.38. No edge found.
PATTERN_CHANNEL_ENABLED    = False   # DISABLED 2026-08-02 — matches master flag
MA_CROSS_ENABLED         = False   # ma_cross (short only historically)
MA_CROSS_PLUS_ENABLED     = False  # ma_cross+ — catastrophic losses
MA_CROSS_MINUS_ENABLED    = False  # CEO 2026-08-09 — all ma100-cross SHORT combos bleeding (-$0.84/7d)
MA_CROSS_5M_ENABLED       = False
MA_CROSS_5M_PLUS_ENABLED   = False  # ma_cross_5m+ — WR=19%, blocked in blacklist
MA_CROSS_5M_MINUS_ENABLED = False
TL_BREAK_ENABLED         = False  # KILLED 2026-08-25 — 33.3% WR (66 trades 7d), -$1.33. hemorrhaging.
ATR_COMPRESSION_ENABLED  = False  # CEO 2026-08-05 — 0% WR (48h). DISABLED.

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
HH_HL_PLUS_ENABLED            = True    # hh_hl+ LONG (breakout/pullback)
HH_HL_MINUS_ENABLED           = True    # hh_hl- SHORT (breakout/pullback)
HH_HL_CHOCH_ENABLED           = True    # CHoCH reversal signals (separate from breakout/pullback)
HH_HL_CHOCH_PLUS_ENABLED      = True    # choch+ bullish flip (LH_LL→HH_HL)
HH_HL_CHOCH_MINUS_ENABLED     = True    # choch- bearish flip (HH_HL→LH_LL)
MA300_CANDLE_ENABLED     = False
MA300_CANDLE_PLUS_ENABLED     = False    # ma300_candle_confirm+ LONG
MA300_CANDLE_MINUS_ENABLED   = True    # ma300_candle_confirm- SHORT
MACD_ACCEL_ENABLED       = False
MACD_ACCEL_PLUS_ENABLED       = False    # macd_accel+ LONG
MACD_ACCEL_MINUS_ENABLED      = True    # macd_accel- SHORT
# ── MACD Divergence (5m pivot divergence) ─────────────────────────────────────
# macd_divergence.py — detects price/MACD histogram pivot divergence on 5m candles
MACD_DIVERGENCE_ENABLED          = True    # master kill-switch
MACD_DIVERGENCE_PLUS_ENABLED     = False   # CEO KILLED 2026-08-23 — 4T/7d 25% WR -$0.40. Dead signal, no edge.
MACD_DIVERGENCE_MINUS_ENABLED    = True    # macd-div- SHORT (bearish divergence)
MACD_DIV_FAST                    = 12      # MACD fast EMA period
MACD_DIV_SLOW                    = 26      # MACD slow EMA period
MACD_DIV_SIGNAL_PERIOD           = 9       # MACD signal line period
MACD_DIV_SWING_LOOKBACK          = 5       # bars on each side to confirm a pivot (5m needs wider window)
MACD_DIV_MIN_PIVOT_DIST          = 10      # minimum bars between two pivots (50min for 5m candles)
MACD_DIV_MIN_PRICE_CHANGE_PCT    = 0.01    # minimum price change between pivots (1%)
MACD_DIV_MIN_HIST_SLOPE          = 0.0     # minimum histogram slope for confirmation
MACD_DIV_LOOKBACK_BARS           = 100     # 5m candles to fetch (~8h of data)
MACD_DIV_CONF_BASE               = 72      # base confidence (counter-trend = lower base)
MACD_DIV_CONF_FLOOR              = 60      # min confidence
MACD_DIV_CONF_CAP                = 88      # max confidence (system ceiling)
MACD_DIV_STRONG_PRICE_PCT        = 0.03    # strong divergence: >3% price change
MACD_DIV_STRONG_HIST_RATIO       = 0.5     # strong divergence: >50% hist recovery/decline
MACD_DIV_MEDIUM_PRICE_PCT        = 0.015   # medium divergence: >1.5% price change
MACD_DIV_MEDIUM_HIST_RATIO       = 0.3     # medium divergence: >30% hist recovery/decline
MACD_DIV_RSI_FLOOR               = 40      # don't SHORT when RSI 5m < 40 (oversold = bounce risk)
R2_REV_ENABLED           = False  # r2_rev — blocked in blacklist
R2_REV_PLUS_ENABLED           = False   # r2_rev+ LONG
R2_REV_MINUS_ENABLED          = False   # r2_rev- SHORT
R2_TREND_ENABLED         = True   # master kill switch for r2_trend SHORT
R2_TREND_SHORT_ENABLED   = True   # RE-ENABLED 2026-08-20 — RSI inversion fix + MIN_SLOPE enforcement + threshold tightening. CEO_PROTECTED
R2_TREND_SHORT_MIN_SLOPE    = -0.003  # maximum slope % (negative = downtrend) — LEGACY, now overridden by normalized check
R2_TREND_SHORT_MIN_SLOPE_PCT = 0.0001  # minimum slope magnitude as % of price per candle (0.01%) — normalized, fair across all price levels
R2_TREND_SHORT_MIN_R2       = 0.70    # minimum R² threshold (raised from 0.60 — match LONG, filter weak trends)
R2_TREND_SHORT_MIN_RSI      = 30      # min RSI — don't short when oversold (bounce risk). FIXED: was MAX_RSI=65 (inverted, blocked best short setups)
R2_TREND_SHORT_MIN_SPEED    = 30      # min speed percentile — require downward momentum
R2_TREND_SHORT_MIN_BB_POS   = 0.15    # min BB position — don't short at band bottom (bounce risk)
R2_TREND_SHORT_BLOCK_STALE  = True    # block signals on stale tokens
R2_TREND_SHORT_MAX_ACCEL    = 0.005   # block SHORT when price_acceleration > this (overextended)
R2_TREND_SHORT_MIN_PRE_MOVE = 0.0     # min pre-entry move % — block SHORT when price rising before entry
R2_TREND_SHORT_MIN_BARS     = 3       # min bars since trend started — raised from 2, match LONG (2 = fading moves)
SHORT_NEUTRAL_BLOCK_ENABLED = True    # CEO 2026-08-22 — block SHORT in NEUTRAL regime (0% WR, -1.12/7d). No SHORT edge in flat market.
R2_TREND_LONG_ENABLED        = True    # r2_trend_long — new LONG variant, catches slow grinds (R²>0.6, slope>0)
R2_TREND_LONG_MIN_SLOPE     = 0.003   # minimum slope (absolute) to fire — LEGACY, now overridden by normalized check
R2_TREND_LONG_MIN_SLOPE_PCT = 0.0001  # minimum slope as % of price per candle (0.01%) — normalized, fair across all price levels
R2_TREND_LONG_MIN_R2        = 0.70    # minimum R² threshold (raised from 0.60 — filter weaker trends)
R2_TREND_LONG_MAX_RSI       = 75      # max RSI — don't buy overbought (chasing)
R2_TREND_LONG_MIN_SPEED     = 30      # min speed percentile — require some momentum
R2_TREND_LONG_MAX_BB_POS    = 0.85    # max BB position — don't chase at band top
R2_TREND_LONG_BLOCK_STALE   = True    # block signals on stale tokens (no momentum)
R2_TREND_LONG_MAX_ACCEL    = 0.005   # block LONG when price_acceleration > this (overextended, about to reverse)
R2_TREND_LONG_MIN_PRE_MOVE = 0.3     # min pre-entry move % — block LONG when price dropping before entry (dead-cat bounces). RAISED 2026-08-19 from 0.2 — r2-trend-long3 11T/7d ATR_SL avg MFE +0.12% (dead-cat bounces peaking 0.12% then stopping out). Winners peak 0.65%. RAISED 2026-08-18 from 0.1. RAISED 2026-08-15 from 0.0.
# ── Slow Grind SHORT (catches gradual downtrends with low volatility) ──────
# slow_grind_short.py — detects grinding declines (GMT, HBAR patterns)
SLOW_GRIND_SHORT_ENABLED = True    # master kill-switch
SLOW_GRIND_SHORT_MIN_R2 = 0.55    # minimum R² threshold (confirmed trend, not chop)
SLOW_GRIND_SHORT_MIN_SLOPE_PCT = 0.0002  # minimum slope magnitude as % of price per candle (0.02%)
SLOW_GRIND_SHORT_MAX_ATR_PCT = 0.8  # max ATR% — grinding = low volatility, not spiking
SLOW_GRIND_SHORT_RSI_MIN = 35      # min RSI — don't short oversold (bounce risk)
SLOW_GRIND_SHORT_RSI_MAX = 55      # max RSI — don't short overbought (not a grind)
SLOW_GRIND_SHORT_MIN_EMA_SEPARATION = 0.1  # min % separation below EMA20 (not just barely below)
SLOW_GRIND_SHORT_CONF_BASE = 65    # base confidence
SLOW_GRIND_SHORT_CONF_CAP = 88     # max confidence (system ceiling)
SLOW_GRIND_SHORT_COOLDOWN_HOURS = 3  # per token cooldown
SLOW_GRIND_SHORT_R2_BONUS_MAX = 15   # max R² bonus in confidence scoring
SLOW_GRIND_SHORT_SLOPE_BONUS_MAX = 10  # max slope bonus in confidence scoring
SLOW_GRIND_SHORT_SLOPE_NORM = 0.001  # slope normalization factor (0.1%)
SLOW_GRIND_SHORT_EMA_BONUS_MAX = 10  # max EMA separation bonus
SLOW_GRIND_SHORT_EMA_NORM = 0.5    # EMA separation normalization factor (0.5%)
SLOW_GRIND_SHORT_ATR_LOW_THRESHOLD = 0.3  # ATR% below this gets bonus (pure grind)
SLOW_GRIND_SHORT_ATR_LOW_BONUS = 5   # bonus for low ATR
SLOW_GRIND_SHORT_RSI_OVERSOLD_PENALTY_THRESHOLD = 40  # RSI below this gets penalty
SLOW_GRIND_SHORT_RSI_OVERSOLD_PENALTY = 5  # penalty for oversold RSI
TREND_PURITY_ENABLED     = False
TREND_PURITY_PLUS_ENABLED    = False    # trend_purity+ LONG
TREND_PURITY_MINUS_ENABLED   = True    # trend_purity- SHORT
VOLUME_HL_ENABLED        = False  # CEO 2026-08-05 — 0% WR (48h). DISABLED.
VOLUME_HL_PLUS_ENABLED        = False    # volume_hl+ LONG
VOLUME_HL_MINUS_ENABLED       = True    # volume_hl- SHORT
EMA20_50_PLUS_ENABLED         = False    # ema20_50+ LONG
EMA20_50_MINUS_ENABLED        = False    # ema20_50- SHORT
MACD_1M_PLUS_ENABLED          = True    # macd_1m+ LONG
MACD_1M_MINUS_ENABLED         = True    # macd_1m- SHORT
ACCEL_300_PLUS_ENABLED        = False # self_learner 2026-08-05 — DISABLED. 0% WR over 48h. No edge.
ACCEL_300_MINUS_ENABLED       = True    # RE-ENABLED 2026-08-17 per user. Had 13-win streak Aug 12.
INVERSE_ACCEL_300_ENABLED     = False    # CEO KILLED 2026-08-04 21:05 — 11% WR combined, -$2.78 in 7d. NEVER_REENABLE.
INVERSE_ACCEL_300_PLUS_ENABLED  = False  # PERMANENT — 0% WR (0/2 dedup), -$0.51. Falling knife catcher.
INVERSE_ACCEL_300_MINUS_ENABLED = False   # CEO KILLED 2026-08-04 21:05 — 11% WR, -$22.91 in 7d. In NEVER_REENABLE.
COUNTER_FLIP_PLUS_ENABLED     = True    # counter_flip+ LONG
COUNTER_FLIP_MINUS_ENABLED    = True    # counter_flip- SHORT
HMACD_MTF_PLUS_ENABLED        = True    # hmacd_mtf+ LONG
HMACD_MTF_MINUS_ENABLED       = True    # hmacd_mtf- SHORT
RS_ENABLED               = True   # re-enabled 2026-08-06 — RS_MIN_TOUCHES lowered to 30, RS_PROXIMITY_K raised to 4.0
RS_PLUS_ENABLED               = True   # re-enabled 2026-08-06 — support bounce LONG
RS_MINUS_ENABLED              = True   # re-enabled 2026-08-06 — resistance rejection SHORT
TL_BREAK_PLUS_ENABLED         = False  # CEO KILLED 2026-08-07 — master TL_BREAK killed
TL_BREAK_MINUS_ENABLED        = False  # KILLED 2026-08-25 — 28.6% WR, -$0.32 (24h), 7T. NEVER_REENABLE.

# ── Rotator Protection ──────────────────────────────────────────────────────
# Signals in this list are NEVER auto-rotated by signal_rotator.py
# Used for signals we explicitly upgraded/tuned — old cumulative data is stale
ROTATOR_PROTECTED_FLAGS = [
    'BB_BOUNCE_ENABLED',        # confluence signal — 100% WR with hzscore+, standalone WR stale
]

# ── CEO Protection ──────────────────────────────────────────────────────────
# Flags the CEO automation CANNOT toggle. Prevents regression when CEO
# independently investigates same issues as human session.
# Format: flag_name -> (reason, date_added)
CEO_PROTECTED_FLAGS = {
    'CONFLUENCE_REQUIRED': ('Core quality gate — CEO toggled this during paralysis, causing regression', '2026-08-06'),
    'LIVE_TRADING_ENABLED': ('Runtime kill switch — only T can change', '2026-08-06'),
    'ROTATOR_PROTECTED_FLAGS': ('Prevents stale data kills on upgraded signals', '2026-08-06'),
    'BB_BOUNCE_ENABLED': ('Confluence signal — CEO keeps killing it, needs to stay on for testing', '2026-08-06'),
    'SIGNALS_REGISTRY': ('CEO commented out bb_bounce from signals/__init__.py on 2026-08-05 — signals must only be removed via NEVER_REENABLE_FLAGS', '2026-08-06'),
    'PM_TRAIL_ACTIVATE_PCT': ('Profit monster trail activation — CEO changed without authorization 2026-08-16', '2026-08-17'),
    'PM_TRAIL_DISTANCE_PCT': ('Profit monster trail distance — CEO changed without authorization 2026-08-16', '2026-08-17'),
    'ACCEL_300_MINUS_ENABLED': ('Winning SHORT signal — 13-win streak Aug 12. CEO killed, user re-enabled', '2026-08-17'),
    'RANGE_BREAKOUT_SHORT_ENABLED': ('Winning SHORT signal — 11-win streak Aug 12. CEO killed, user re-enabled', '2026-08-17'),
    'R2_TREND_LONG_ENABLED': ('Winning LONG signal — 8/17 wins in LONG streak. Must stay enabled', '2026-08-17'),
    'BB_BOUNCE_PLUS_ENABLED': ('Winning LONG signal — 5/17 wins in LONG streak. Must stay enabled', '2026-08-17'),
    'R2_TREND_SHORT_ENABLED': ('SHORT signal — CEO killed 2026-08-20 (0% WR). Under review with RSI fix + threshold tightening. Only T can re-enable', '2026-08-20'),
    'TIME_BLOCK_ENABLED': ('Re-enabled 2026-08-22 as penalty (0.7x) — was hard block. CEO_PROTECTED', '2026-08-22'),
}

# ── Research/Testing Flags — NOBODY CAN TOUCH ──────────────────────────────
# These flags are in research/testing mode. NO automation can modify them.
# Only human (T) can change these. CEO, signal reporter, self_learner all blocked.
# Format: flag_name -> (reason, date_added)
RESEARCH_FLAGS = {
    'COIN_TRACKER_HOT_ENABLED': ('KILLED 2026-08-25 — 36.4% WR, -$3.65/7d. NEVER_REENABLE.', '2026-08-25'),
    'COIN_TRACKER_HOT_PLUS_ENABLED': ('Research/testing — MACD%, Z-score, BB, speed, accel filters', '2026-08-22'),
    'COIN_TRACKER_HOT_MINUS_ENABLED': ('Research/testing — SHORT enabled with same filters', '2026-08-22'),
    'COIN_TRACKER_HOT_MIN_COMPOSITE': ('Research/testing — composite threshold 57', '2026-08-22'),
    'COIN_TRACKER_HOT_MIN_SPEED_PCT': ('Research/testing — speed filter min 30%', '2026-08-22'),
    'COIN_TRACKER_HOT_MAX_SPEED_PCT': ('Research/testing — speed filter max 85%', '2026-08-22'),
    'COIN_TRACKER_HOT_MIN_ACCEL': ('Research/testing — acceleration filter -0.01', '2026-08-22'),
    'COIN_TRACKER_HOT_CLUSTER_MIN': ('Research/testing — cluster count 1.0', '2026-08-22'),
    'COIN_TRACKER_HOT_RECENCY_MIN': ('Research/testing — recency weight 0.35', '2026-08-22'),
}

# ── Session Lock ────────────────────────────────────────────────────────────
# When this file exists with content "active", CEO skips parameter changes.
# Human session creates it at start, removes at end.
# CEO checks this before modifying hermes_constants.py
SESSION_LOCK_FILE = '/tmp/hermes-session-active.lock'
SESSION_LOCK_TTL = 3600  # lock expires after 1 hour (safety net)

# ── Squeeze Cross Signal ──────────────────────────────────────────────────────
# squeeze_cross.py — EMA(5)×EMA(180) cross + ATR squeeze + widening gap
# Backtested: 71% WR, +2.36% avg PnL on 3-day 1m data
SQUEEZE_CROSS_ENABLED       = False  # DISABLED 2026-07-28: 0% WR on LONG, 40% on SHORT — no edge
SQUEEZE_CROSS_PLUS_ENABLED  = False    # squeeze_cross+ LONG — DISABLED 2026-08-02: matches master flag
SQUEEZE_CROSS_MINUS_ENABLED = False    # squeeze_cross- SHORT — DISABLED 2026-08-02: matches master flag

# ── Bollinger Squeeze Signal ─────────────────────────────────────────────────
# bollinger_squeeze.py — BB squeeze + breakout from price_history ticks
BOLLINGER_SQUEEZE_ENABLED = False  # DISABLED 2026-08-01 — 0% WR (4 trades), -$2.41. Dominant signal but all losers.
BOLLINGER_SQUEEZE_PLUS_ENABLED  = False    # bb-squeeze+ LONG — DISABLED 2026-08-02: matches master flag
BOLLINGER_SQUEEZE_MINUS_ENABLED = False    # bb-squeeze- SHORT — DISABLED 2026-08-02: matches master flag
BOLLINGER_SQUEEZE_PERIOD       = 20       # SMA window for Bollinger Bands
BOLLINGER_SQUEEZE_MULT         = 2.0      # stddev multiplier
BOLLINGER_SQUEEZE_THRESH       = 0.04     # bandwidth < 4% = squeeze
BOLLINGER_SQUEEZE_MIN_BARS     = 6        # min bars in squeeze before breakout valid
BOLLINGER_SQUEEZE_BREAK_PCT    = 0.15     # price must cross band by this % for confirmation
BOLLINGER_SQUEEZE_CANDLE_SEC   = 300      # candle period in seconds (300 = 5m)
BOLLINGER_SQUEEZE_LOOKBACK_H   = 6        # hours to look back for squeeze formation
BOLLINGER_SQUEEZE_COOLDOWN_MIN = 30       # min minutes between signals per token+direction

# bb_bounce.py — mean reversion for ranging markets
BB_BOUNCE_ENABLED = True    # confluence signal — 100% WR with hzscore+ (3/3 trades)
BB_BOUNCE_PLUS_ENABLED = True # RE-ENABLED 2026-08-17 per user. Part of winning LONG streaks.
BB_BOUNCE_MINUS_ENABLED = False   # bb_bounce- SHORT — DISABLED 2026-08-07: 40% WR, -$4.61% over 7d. Confluence (bb_bounce+hzscore+) stays enabled.
BB_BOUNCE_SHORT_ENABLED = True    # bb_bounce_short — SHORT-specific with regime filter, tighter RSI, volume confirm

# ── Standalone Bypass Signals ──────────────────────────────────────────────
# Signals that can bypass the confluence gate (single-source allowed).
# Backtested and proven edge when firing solo.
# Used in signal_compactor.py at 7 locations (confluence gate + preserve filter).
# CEO 2026-08-12 — removed 'hzscore' (standalone LONG 11T -$0.16 36.4% WR 24h, combos profitable)
# CEO 2026-08-17 — removed 'accel-300' (40T/7d 55% WR -$0.30, net negative), 'wave_catcher' (killed), 'range_breakout_short' (killed)
# CEO 2026-08-25 — removed 'hl_copy_trader' (5T/8h 0% WR -$2.41. Copy delay = enters after move over. Requires confluence to fire.)
STANDALONE_BYPASS_SIGNALS = (
    'stop_hunt_reversal_long',
    'spike_exhaustion_short', 'bb_bounce', 'bb-bounce-short',
    'range_breakout', 'range_breakout_short',
    'continuation', 'continuation_long', 'continuation_short',
    'accel-300',
    'return_exhaustion_short', 'return-exhaustion-short',
    'hzscore', 'return_exhaustion_long',
    'r2l-long', 'r2-trend-long', 'r2-trend-short',
    'tl_break_long', 'tl_break_short',
    'atr-spike',
    'ct-hot',
    'liq-hunt',  # liquidation cluster contrarian — structural, regime-agnostic
    'macd-div',  # MACD divergence — counter-trend, works solo
    'confluence',  # meta-signal — validates persistence + compounding of first-order signals
)

# range_finder.py — range-bound mean reversion (flat BB, multi-touch)
RANGE_FINDER_ENABLED = False  # CEO 2026-08-16: DISABLED. 9T/7d 33.3% WR -$0.14. R:R 0.12:1 (avg win +0.05% vs avg loss -0.43%). Never captures gains. Drags down all combos (hzscore+,range_finder+ and bb_bounce+,range_finder+ both bleeding). Re-enable when R:R >1:1.
RANGE_FINDER_PLUS_ENABLED = False # TESTING 2026-08-15 — re-enabled for testing. Was disabled 2026-08-10 (20T -$0.44). Monitor winrate.
RANGE_FINDER_MINUS_ENABLED = False   # CEO KILLED 2026-08-16 — 3T 0% WR -$0.12 (48h SHORT). Bleeds both directions. Re-enable only in confirmed downtrend.
RANGE_FINDER_SHORT_ENABLED = False   # CEO KILLED 2026-08-16 — range_finder SHORT dead. All range_finder variants disabled.

# range_breakout.py — breakout from tight range with retest confirmation
RANGE_BREAKOUT_ENABLED = False   # CEO KILLED 2026-08-16 — 8T 25% WR -$0.41 (7d). All variants dead.
RANGE_BREAKOUT_PLUS_ENABLED = False   # SIGNAL REPORTER 2026-08-15 — 8T 25% WR -$0.41 (7d). Kill LONG.
RANGE_BREAKOUT_MINUS_ENABLED = False # range_breakout- SHORT — DISABLED, use range_breakout_short instead
RANGE_BREAKOUT_SHORT_ENABLED = False  # AUTO_KILLED 2026-08-17 — 0% WR 3T (0W 3L -$0.17). Below threshold at 2T for 3+ cycles, now 3T confirmed.
RANGE_BREAKOUT_SHORT_EMA_PERIOD = 200  # EMA period for trend filter — block SHORT above this EMA
RANGE_BREAKOUT_BB_PERIOD = 30        # Bollinger Band period
RANGE_BREAKOUT_BB_STDDEV = 1.8       # Band width (1.8σ, matches range_finder)
RANGE_BREAKOUT_BB_WIDTH_MAX = 0.04   # Max band width % to consider range-bound (4%)
RANGE_BREAKOUT_BB_SLOPE_MAX = 0.001  # Max BB middle slope per candle (flat bands)
RANGE_BREAKOUT_LOOKBACK = 100        # 5m candles to analyze (8+ hours)
RANGE_BREAKOUT_TOUCH_MIN = 3         # Min band touches to confirm range
RANGE_BREAKOUT_TOUCH_WINDOW = 50     # Lookback for counting touches
RANGE_BREAKOUT_RETEST_PCT = 0.3      # tightened 2026-08-12 — enter earlier on retest
RANGE_BREAKOUT_BOUNCE_MIN = 0.03     # tightened 2026-08-12 — less bounce required
RANGE_BREAKOUT_BREAKOUT_WINDOW = 15  # tightened 2026-08-12 — look further back for breakout
RANGE_BREAKOUT_INVALIDATION_WINDOW = 5  # Candles to check for invalidation
RANGE_BREAKOUT_COOLDOWN_HOURS = 2    # Cooldown per token+direction
RANGE_BREAKOUT_CONF_BASE = 70        # Base confidence — bumped 2026-08-12 08:27 from 65, range_breakout+ 28.6% WR
RANGE_BREAKOUT_CONF_CAP = 88         # Max confidence (system ceiling)
RANGE_BREAKOUT_RSI_LONG_MAX = 70     # Skip LONG if RSI above this (overextended)
RANGE_BREAKOUT_RSI_SHORT_MIN = 30    # Skip SHORT if RSI below this (overextended)

# Mean-reversion velocity gate — block entries when price still trending against signal
MEAN_REVERSION_VEL_ENABLED = True
MEAN_REVERSION_VEL_THRESHOLD = 0.15   # CEO 2026-08-25 — tightened from 0.3. bb_bounce+ 8T/8h 12.5% WR -$2.02 — catches dead cat bounces in downtrends. 0.3% was too loose.
MEAN_REVERSION_VEL_THRESHOLD_SHORT = 0.6  # block SHORT if 15m velocity > 0.6% (price spiking against SHORT — higher threshold because spikes reverse faster)

# Spike exhaustion filter — block entries after sharp 5m moves (likely exhausted)
# Applied to range_breakout, hzscore, bb_bounce to prevent chasing spikes
SPIKE_EXHAUSTION_VEL_5M_THRESHOLD = 0.5  # block if abs(5m velocity) > 0.5% (spike exhaustion)

# Signal staleness — reject trade if price moved too far since signal fired
# Prevents entering after opportunity has passed (e.g., bb_bounce fires near lower BB,
# price rallies to upper BB by execution time)
SIGNAL_STALENESS_PRICE_PCT = 0.25  # block if price moved >0.25% since signal (bb_bounce-specific)
SIGNAL_STALENESS_MAX_AGE_MIN = 3   # max minutes between signal generation and execution

# EMA periods
SQUEEZE_CROSS_EMA_FAST      = 5       # fast EMA period
SQUEEZE_CROSS_EMA_SLOW      = 180     # slow EMA period
SQUEEZE_CROSS_LOOKBACK      = 250     # candle lookback (EMA_SLOW + buffer)
# ATR squeeze
SQUEEZE_CROSS_ATR_PERIOD    = 20      # ATR calculation period
SQUEEZE_CROSS_ATR_RATIO     = 0.9     # ATR < ratio × avg → squeeze
SQUEEZE_CROSS_ATR_AVG_WIN   = 50      # rolling average window for ATR
# Gap widening
SQUEEZE_CROSS_WIDEN_BARS    = 3       # gap must be widening over last N bars
# Cooldown
SQUEEZE_CROSS_COOLDOWN      = 60      # bars between signals per token+direction
# Confidence scoring
SQUEEZE_CROSS_CONF_BASE     = 70      # base confidence
SQUEEZE_CROSS_CONF_SQZ      = 10      # bonus for deep squeeze
SQUEEZE_CROSS_CONF_WIDEN    = 5       # bonus for strong widening
SQUEEZE_CROSS_CONF_MAX      = 90      # confidence cap

COUNTER_FLIP_ENABLED     = False   # controlled by counter_flip_signal.py independently

# ── Wyckoff Accumulation/Distribution Signal ────────────────────────────────
# wyckoff.py — detects Wyckoff accumulation springs (LONG) and distribution
# upthrusts (SHORT) using volume and price structure analysis on 5m candles.
WYCKOFF_ENABLED = False   # CEO 2026-08-05 — 0% WR (48h). DISABLED.
WYCKOFF_PLUS_ENABLED = True     # wyckoff+ LONG (accumulation spring)
WYCKOFF_MINUS_ENABLED = True    # wyckoff- SHORT (distribution upthrust)

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

# ── Pump Catcher (momentum breakout signal) ────────────────────────────────────
# Catches early-stage momentum breakouts by detecting price acceleration.
# Unlike pump_hunter (reversion/fade), this RIDES the spike via LONG entries.
# Replaces dead volume-based detection with price-based velocity + acceleration.
PUMP_CATCHER_ENABLED        = True   # master kill-switch
PUMP_CATCHER_PLUS_ENABLED   = True   # LONG entries
PUMP_CATCHER_MINUS_ENABLED  = False  # SHORT entries — disabled initially (catch pumps only)
# Detection thresholds
PUMP_CATCHER_VELOCITY_MIN   = 0.5    # min % move in 3 bars to qualify as explosive
PUMP_CATCHER_VELOCITY_BARS  = 3      # bar window for velocity computation
PUMP_CATCHER_ACCEL_MIN      = 0.0    # min acceleration (current velocity - prior velocity)
PUMP_CATCHER_TREND_EMA      = 20     # EMA period for trend filter (price must be above)
PUMP_CATCHER_RSI_MAX        = 75     # max RSI — skip if overbought
PUMP_CATCHER_RSI_MIN        = 30     # min RSI — skip if oversold
PUMP_CATCHER_RSI_PERIOD     = 14     # RSI computation period
# TP/SL — asymmetric (ride winners, cut losers)
PUMP_CATCHER_TP_PCT         = 3.0    # take profit at 3% from entry
PUMP_CATCHER_SL_PCT         = 1.0    # stop loss at 1% from entry
PUMP_CATCHER_TRAILING_ACTIVATE = 1.5 # activate trailing stop at +1.5%
PUMP_CATCHER_TRAILING_DISTANCE = 0.8 # trail by 0.8% from peak
# Confidence scoring
PUMP_CATCHER_CONFIDENCE_BASE = 60    # base confidence
PUMP_CATCHER_CONFIDENCE_CAP  = 88    # max confidence
# Dedup and risk
PUMP_CATCHER_COOLDOWN_BARS  = 10     # bars between signals per token (~10 min on 1m)
PUMP_CATCHER_MAX_POSITIONS  = 3      # max concurrent pump-catcher positions
PUMP_CATCHER_MIN_PRICE_ROWS = 30     # minimum 1m bars for EMA/RSI computation

# DEPRECATED — zscore_pump_hunter.py is disabled.
# Pipeline-integrated version is signals/zscore_pump.py (uses tpsl_utils via signal_compactor).
ZSCORE_PUMP_ENABLED        = True  # True = old standalone would fire (BLOCKED — use signals/zscore_pump.py)
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
ZSCORE_RISING_ENABLED     = False  # CEO KILLED 2026-08-07 — 38.6% WR (44 trades 7d), -$1.37. No edge.
ZSCORE_RISING_PLUS_ENABLED = False  # CEO KILLED 2026-08-07 — master ZSCORE_RISING killed
ZSCORE_RISING_MINUS_ENABLED = False # Re-enabled 2026-08-05. WR=41% (17 trades 7d), +$0.03.
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
FAST_MOMENTUM_MINUS_ENABLED = True  # Re-enabled 2026-08-10 — backtested: 0.08 accel threshold = 80% WR

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
CONFLUENCE_REQUIRED = True   # DO NOT DISABLE — paralysis was caused by 5min expiry (now 10min) and dead hours (now fixed)
CONFLUENCE_NEUTRAL_RELAX = True  # CEO 2026-08-16: In NEUTRAL regime (102/104 tokens flat), allow single-type signals through. Addresses signal starvation (21T today, need 30+). Does NOT disable confluence for trending regimes.

# ── Accel-300 Standalone Bypass ──────────────────────────────────────────────
# When a single-source accel-300 has very high confidence, bypass confluence gate.
# Problem: confluence gate blocks pure accel-300 signals (no RS co-signal) even when
# accel-300 is very strong. Strong accel-300 alone should sometimes fire.
ACCEL_300_STANDALONE_BYPASS_ENABLED = False  # CEO KILLED 2026-08-17 — 40T/7d 55% WR -$0.30. Net negative despite PM_TRAIL capturing winners. ATR_SL kills losers. Never reenable without proven edge.
ACCEL_300_STANDALONE_BYPASS_CONFIDENCE = 70  # minimum confidence for standalone bypass

# ── Dead-Hours Entry Filter ───────────────────────────────────────────────────
# Block entries during low-liquidity hours (whitewater, no wave).
# Surfing principle: "You can't force a wave — you read it, position yourself."
#
# Data basis (2572 PostgreSQL trades, 2026-07-28):
# - inv-accel-300-: Dead=17.2% WR vs Active=37.8% WR → block during dead hours
# - inv-accel-300+: Dead=18.8% WR vs Active=31.0% WR → block during dead hours
# - accel-300+:     Dead=16.7% WR vs Active=33.3% WR → block during dead hours
# - accel-300-:     Dead=50.5% WR vs Active=47.8% WR → DO NOT block (performs better)
#
# Config:
#   DEAD_HOURS_ENABLED = master toggle (False = no filtering at all)
#   DEAD_HOURS_START/END = hour range in UTC
#   DEAD_HOURS_SIGNALS = list of signal prefixes to block during dead hours
#   DEAD_HOURS_DEFAULT = True = block ALL signals not in list, False = only block listed signals
DEAD_HOURS_ENABLED = False  # disabled 2026-08-07 — past 24h showed dead hours can be productive
DEAD_HOURS_START = 3   # 03:00 UTC
DEAD_HOURS_END = 8     # 08:00 UTC
DEAD_HOURS_SIGNALS = [
    # ALLOWLIST — only these signals fire during dead hours (DEFAULT=True blocks everything else)
    'accel-300-',       # 50% WR during dead hours
    'zscore-rising',    # 239 signals/hr — primary signal source
    'vel-hermes',       # active signal with wins
    'hzscore',          # added 2026-08-06 — confluence signal, 100% WR (1 trade) during dead hours
    'return_exhaustion', # added 2026-08-06 — was blocked, caused LTC hot-set stall
    'ma100-cross',      # added 2026-08-06 — CC SHORT blocked by dead hours
    'vortex_break',     # added 2026-08-06 — CC SHORT blocked by dead hours
]
DEAD_HOURS_DEFAULT = True  # True = block ALL signals not in allowlist (was False — only blocked 4 signals, dead hours WR=16%)

# ── Targeted Signal Inversion ──────────────────────────────────────────────────
# Invert direction for specific signals that are statistically proven losers.
# Replaces the old _FLIP_SIGNALS global flip (tested 2026-07-28, gave 13.8% WR — worse).
#
# Data basis: 200 closed trades analyzed 2026-07-28.
# inv-accel-300+ LONG:  77 trades, 29% WR, -3.59% total → flip LONG→SHORT
# accel-300+ LONG:       9 trades, 22% WR, -1.53% total → flip LONG→SHORT
#
# WHY NOT INVERT inv-accel-300- SHORT (23% WR, -6.17%)?
# Inverting SHORT→LONG means catching a falling knife (price below EMA300 and falling).
# Only invert after monitoring confirms the inverted direction works.
SIGNAL_INVERSION_ENABLED = False  # Disabled 2026-07-28 — phase-aware entry should handle this
SIGNAL_INVERSION_MAP = {
    'inv-accel-300+': True,    # 77 trades, 29% WR → flip LONG→SHORT
    'accel-300+':     True,    # 9 trades, 22% WR → flip LONG→SHORT
    # KEEP these (do NOT invert):
    # 'accel-300-':  — 16 trades, 62% WR — best signal
    # 'sqx+'        — already disabled via SQUEEZE_CROSS_ENABLED=False
    # 'sqx-'        — 10 trades, 40% WR — borderline, don't invert yet
    # 'inv-accel-300-' — 66 trades, 23% WR — worst signal, but invert→LONG is catching falling knife
}

# ── Dynamic Signal Inversion (WR-based auto-invert) ────────────────────────────
# Automatically inverts signals whose 24h win-rate drops below threshold.
# Complementary to SIGNAL_INVERSION_MAP (static overrides).
# Queries signal_outcomes DB at trade time — no extra scripts needed.
DYNAMIC_INVERSION_ENABLED = True        # master toggle for auto-inversion
INVERT_WR_THRESHOLD = 30                # auto-invert when WR < this %
INVERT_MIN_TRADES = 5                   # need at least this many trades before inverting
INVERT_LOOKBACK_HOURS = 24              # performance window (hours)
INVERT_CACHE_TTL = 300                  # cache WR lookups for 5 min (seconds)
# Signals to monitor for auto-inversion (signal_type values from signal_outcomes).
# If a signal's WR drops below threshold, its direction is flipped at execution.
INVERT_SIGNALS = [
    'zscore-rising+',       # currently 0% WR — will auto-invert LONG→SHORT
    'zscore-rising-',       # currently 0% WR — will auto-invert SHORT→LONG
    # tl_break_long/short removed 2026-08-06 — 100% WR, dynamic inversion was
    # flipping good signals to wrong direction (31.6% of trades inverted)
    # Add more signal types here as needed:
    # 'velocity+',
    # 'velocity-',
]

# ── Trend Alignment Filter ─────────────────────────────────────────────────
# Block signals that don't align with 1H EMA trend direction.
# Backtest: 275 trades → 74 trades, PnL -$4.05 → +$3.28
TREND_FILTER_ENABLED = True
TREND_FILTER_TIMEFRAME = '15m'
TREND_FILTER_EMA_FAST = 20
TREND_FILTER_EMA_SLOW = 50
TREND_FILTER_NEUTRAL_PCT = 0.3225 # EMA spread % for neutral zone — narrowed from 0.5 by self_learner (more restrictive)
TREND_FILTER_CACHE_TTL = 300    # cache EMA values for 5 min

# ── Macro Deployment Gate ─────────────────────────────────────────────────
# Check market conditions before trading. Adjust position sizing.
MACRO_GATE_ENABLED = True
MACRO_HIGH_VOL_THRESHOLD = 0.05  # 5% ATR = high volatility → STOP
MACRO_LOW_WR_THRESHOLD = 30      # WR < 30% → REDUCE
MACRO_REDUCE_SIZE_MULT = 0.5     # 50% sizing when REDUCE

# ── Self-Learning System ─────────────────────────────────────────────────
# Auto-detect signal decay and adjust parameters (scientific method)
SELF_LEARNER_ENABLED = True
SELF_LEARNER_MIN_TRADES = 10    # Need at least 10 trades to judge
SELF_LEARNER_WR_THRESHOLD = 0.30  # Below this = tighten filters
SELF_LEARNER_WR_TARGET = 0.40     # Target win rate
SELF_LEARNER_PARAM_STEP = 0.05    # 5% per iteration
SELF_LEARNER_MAX_ADJUSTMENTS = 3  # Max changes per day
SELF_LEARNER_MIN_BETWEEN = 15    # Min trades between changes

# ── Persistent Decision Log ──────────────────────────────────────────────
# Log every trade decision with reasoning, learn from outcomes
DECISION_LOG_ENABLED = True
DECISION_LOG_PATH = '/root/.hermes/data/decisions.json'
DECISION_LOG_MAX_ENTRIES = 1000
DECISION_LOG_CACHE_TTL = 300

# ── Vortex Break Signal (NEW 2026-08-05) ──────────────────────────────────────
# vortex_break.py — Vortex Indicator + ADX trend confirmation
# Uses true range (high-low) directional movement, not price closes.
# Catches trend inception via VI crossover + ADX strength filter.
VORTEX_BREAK_ENABLED = True    # master kill-switch — enabled for paper observation (self_learner 2026-08-05)
VORTEX_BREAK_PLUS_ENABLED = False   # SIGNAL REPORTER 2026-08-09 — vortex_break_long LONG: 22.2% WR (9 trades 24h), -$0.18. 7d: 25 trades, 44% WR, -$0.19. Compounds hemorrhaging. KILLED.
VORTEX_BREAK_MINUS_ENABLED = False   # CEO 2026-08-10 — sub-threshold, cluttering hotset. bb-bounce-short,hzscore- handles SHORT side.
VORTEX_BREAK_MIN_CONFIDENCE = 80    # CEO 2026-08-05 — lowered from 95 for paper testing

# ── Return Exhaustion Signal (NEW 2026-08-05) ────────────────────────────────
# return_exhaustion.py — percentile exhaustion + momentum divergence
# Catches turning points when short-term returns are at statistical extremes
# AND fast/slow momentum diverge (fast turning while slow hasn't caught up).
RETURN_EXHAUSTION_ENABLED = False    # auto_1hr 2026-08-18 — 3T/0%WR -$0.21, auto-kill threshold crossed
RETURN_EXHAUSTION_PLUS_ENABLED = True    # return_exhaustion+ LONG (extreme negative)
RETURN_EXHAUSTION_MINUS_ENABLED = False  # CEO 2026-08-08 — 14 trades, -$0.64 across combos. hemorrhaging like hzscore-.
RETURN_EXHAUSTION_SHORT_ENABLED = True   # return_exhaustion_short — SHORT-specific with regime filter, tighter percentile/RSI, volume
RETURN_EXHAUSTION_MIN_CONFIDENCE = 90  # raised 2026-08-07 (was 70) — 48h data: <90 conf = 37.5% WR, 90+ = 72% WR

# ── Engulfing Candle Signal ──────────────────────────────────────────────
# engulfing.py — Detect large single-candle moves after tight consolidation
# Based on MORPHO observation: 0.22% drop in 1 min after range compression
ENGULFING_ENABLED = True
ENGULFING_PLUS_ENABLED = True           # LONG (bullish engulfing)
ENGULFING_MINUS_ENABLED = True          # SHORT (bearish engulfing)
ENGULFING_MIN_MOVE = 0.15               # min candle move % to qualify
ENGULFING_PRIOR_RANGE = 0.10            # max prior N-candle range % (tight consolidation)
ENGULFING_LOOKBACK = 5                  # candles to check for prior range
ENGULFING_VOLUME_RATIO = 1.5            # volume must be 1.5x average
ENGULFING_CONF_BASE = 75               # base confidence
ENGULFING_CONF_CAP = 88               # max confidence

# ── 100MA Cross Signal ─────────────────────────────────────────────────────
# ma_100_cross.py — Trend reversal at 100-period moving average
# Backtested 14d: SHORT 51.4% WR +0.022%, LONG 46.7% WR +0.010%
# Best on high-ATR tokens (ATR% >= 0.04%)
MA_100_CROSS_ENABLED = False          # DISABLED — replaced by ma_100_cross_long + ma_100_cross_short
MA_100_CROSS_PLUS_ENABLED = False     # CEO 2026-08-10: ma100-cross+,vortex_break_long 5T -$0.14 20% WR (24h), 6T -$0.11 33% WR (7d). bb_bounce+,range_finder+ LONG carries system.
MA_100_CROSS_MINUS_ENABLED = False  # CEO 2026-08-10: all ma100-cross SHORT combos 0% WR in 24h. bb-bounce-short and choch-5 handle SHORT side.     # Re-enabled 2026-08-08 — new ma_100_cross_short.py with tighter params

# ── HL Copy Trading ───────────────────────────────────────────────────────────
# hl_copy_trader.py — Track top Hyperliquid traders and copy their trades
# All HL trades are on-chain and public via API.
HL_COPY_TRADING_ENABLED = False     # Master kill-switch — disabled until tested
HL_COPY_WALLETS = []                # Manual wallet list (populated by leaderboard scan)
HL_COPY_MAX_POSITION_PCT = 0.10    # Max 10% of account per copy trade
HL_COPY_MAX_DRAWDOWN = 0.15        # Stop copying at 15% drawdown
HL_COPY_MIN_SCORE = 70             # Minimum trader score to copy
HL_COPY_POLL_INTERVAL = 30         # Seconds between fill polls
HL_COPY_MAX_DAILY_TRADES = 50      # Daily trade limit
HL_COPY_MAX_MONITORED = 20         # Max traders to actively monitor (reduces API calls: 20 × 2 = 40 calls/cycle vs 268 × 2 = 536)
HL_COPY_REPORT_PATH = "/var/www/hermes/data/hl_copy_report.md"
HL_COPY_DASHBOARD_PATH = "/var/www/hermes/dashboard/hl_copy.html"

# ── HL Copy Trading Signal ────────────────────────────────────────────────────
# hl_copy_signal.py — Generates signals from pro trader activity
HL_COPY_SIGNAL_ENABLED = False      # auto_1hr KILLED 2026-08-25 — 12T/25%WR/-$1.13/24h. PLUS/MINUS already CEO-killed. Base signal last hl_copy standing, hemorrhaging. NEVER_REENABLE.
HL_COPY_SIGNAL_PLUS_ENABLED = False  # SIGNAL REPORTER 2026-08-25 — 30% WR, -$0.74 (24h), 10T. Copy delay = enters after move over. NEVER_REENABLE.
HL_COPY_SIGNAL_MINUS_ENABLED = False   # CEO KILLED 2026-08-25 — 6T/7d 0% WR -$0.76, ALL ATR_SL exits. LONG side is backbone (+$2.07/7d 52.4% WR). SHORT has no edge in copy-trading.
HL_COPY_SIGNAL_MIN_SCORE = 70      # Minimum trader score to generate signal
HL_COPY_SIGNAL_MIN_CONFIDENCE = 60 # Minimum confidence for signal
HL_COPY_SIGNAL_MAX_CONFIDENCE = 95 # Maximum confidence for signal
HL_COPY_SIGNAL_LOOKBACK_MINUTES = 30 # How far back to look for trades (30min catches more clusters)
HL_COPY_SIGNAL_MAX_PER_CYCLE = 5   # Max signals per cycle (avoid noise)

# ── Copy Trader Cluster Bonus ────────────────────────────────────────────────
# When multiple pro traders all buy the same coin within the lookback window,
# boost confidence AND position size — it's higher conviction (cluster confluence).
HL_COPY_CLUSTER_ENABLED = True      # master switch for cluster bonus
HL_COPY_CLUSTER_MIN_SIZE = 2        # minimum traders in cluster to fire signal (2+ = at least 2 traders agree)
HL_COPY_CLUSTER_BONUS_PER_TRADER = 3  # +3 confidence per additional trader in cluster
HL_COPY_CLUSTER_MAX_BONUS = 15       # cap cluster bonus at +15 (prevents overconfidence)
HL_COPY_CLUSTER_SIZE_MULT = 0.25    # +25% position size per additional trader (e.g., 3 traders → 1.5x)

# ── Copy Trader Exit Correlation & Weighting ─────────────────────────────────
COPY_TRADE_EXIT_ENABLED = True          # master switch for trader exit correlation
COPY_TRADE_EXIT_TIMEOUT_MIN = 120       # fallback to normal exit after 2 hours
COPY_TRADE_MAX_OPEN = 10               # max concurrent copy trades
COPY_TRADE_WEIGHT_MIN = 0.1           # minimum copy weight (heavily penalized traders)
COPY_TRADE_WEIGHT_MAX = 2.0           # maximum copy weight (best performers)
COPY_TRADE_WEIGHT_MIN_TRADES = 5      # minimum trades before weight adjusts
COPY_BAD_HOURS_ENABLED = False          # disabled — we're 24/7 live, improve entries not block hours
COPY_BAD_HOURS = [14, 18, 20]           # UTC hours with poor copy WR (25-40%) — inactive

# ── Momentum Leaderboard Signal ─────────────────────────────────────────────
# momentum_leaderboard.py — scans for biggest movers, rides continuation or fades overextension
MOMENTUM_LEADERBOARD_ENABLED = False           # SIGNAL REPORTER 2026-08-20 — 28.6% WR, -$0.15 (7d). Both directions dead. NEVER_REENABLE.
MOMENTUM_LEADERBOARD_PLUS_ENABLED = False      # SIGNAL REPORTER 2026-08-15 — 7T 28.6% WR -$0.15 (24h). LONG dead.
MOMENTUM_LEADERBOARD_MINUS_ENABLED = False     # SIGNAL REPORTER 2026-08-20 — SHORT never produced meaningful trades. Kill with master.
MOMENTUM_LEADERBOARD_TOP_N = 10               # top movers to evaluate
MOMENTUM_LEADERBOARD_MOVE_MIN = 1.0           # min move_score % — lowered from 3.0 (was too strict)
MOMENTUM_LEADERBOARD_COOLDOWN_MIN = 30        # per token+direction cooldown
MOMENTUM_LEADERBOARD_RET_WINDOWS = (6, 5, 12) # candles lookback for 5m/15m/1h (1h widened to 12h)
MOMENTUM_LEADERBOARD_OVEREXTENDED_PCT = 4.0   # % — fade opposing signal when abs(ret_5m) exceeds this (blow-off only)
MOMENTUM_LEADERBOARD_FAST_VEL = 0.3           # % per candle — threshold for "fast" velocity (fade decisions)
MOMENTUM_LEADERBOARD_ELITE_VEL = 0.5          # % per candle — threshold for elite velocity (confidence bonus)
MOMENTUM_LEADERBOARD_CONF_PENALTY_PCT = 2.0   # % — confidence penalty when abs(ret_5m) exceeds this
MOMENTUM_LEADERBOARD_CONF_BASE = 80           # base confidence — higher for high-conviction movers
MOMENTUM_LEADERBOARD_CONF_FLOOR = 60          # minimum confidence
MOMENTUM_LEADERBOARD_CONF_CAP = 90            # maximum confidence (matches system ceiling)

# ── Continuation V2 (smart re-entry after profitable close) ─────────────
# continuation.py V2 — assess trend state, fire same-dir or fade exhaustion
CONTINUATION_ENABLED = True   # V2 re-enabled 2026-08-25 — smart direction, exhaustion detection
CONTINUATION_PLUS_ENABLED = True   # re-enter LONG after LONG close
CONTINUATION_MINUS_ENABLED = True  # re-enter SHORT after SHORT close
CONTINUATION_MIN_PNL = 0.3                    # % — minimum PnL to trigger re-entry
CONTINUATION_WINDOW_SEC = 1800                # seconds after close to scan (30 min, was 300s/5min in V1)
TREND_MOMENTUM_NEAR_SMA_ENABLED = False      # KILLED 2026-08-12 13:05 UTC — 4T 0W 0% WR -$0.37 in 24h. Contrarian flip didn't help.
TREND_MOMENTUM_NEAR_SMA_PLUS_ENABLED = False  # LONG direction — killed with base (2026-08-12 13:05)
TREND_MOMENTUM_NEAR_SMA_MINUS_ENABLED = False # SHORT direction — killed with base (2026-08-12 13:05)
TREND_MOMENTUM_NEAR_SMA_MOMENTUM_THRESHOLD = 0.005  # 0.5% min 5-period momentum
TREND_MOMENTUM_NEAR_SMA_DIST_SMA_MAX = 0.005        # 0.5% max distance from SMA
TREND_MOMENTUM_NEAR_SMA_SMA_PERIOD = 20             # SMA lookback
TREND_MOMENTUM_NEAR_SMA_MOMENTUM_PERIOD = 5         # momentum lookback
TREND_MOMENTUM_NEAR_SMA_CONF_BASE = 70              # base confidence
TREND_MOMENTUM_NEAR_SMA_CONF_STRONG_MOM = 10        # +10 if momentum > 1%
TREND_MOMENTUM_NEAR_SMA_CONF_CLOSE_SMA = 5          # +5 if within 0.2% of SMA
TREND_MOMENTUM_NEAR_SMA_CONF_CAP = 95               # max confidence

# ── stop_hunt_reversal_long — catch violent long after stop hunt ──────────
STOP_HUNT_REVERSAL_LONG_ENABLED = False   # CEO KILLED 2026-08-21 — 10T/7d 60% WR -$0.04 (break-even), 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38. NEVER_REENABLE.
STOP_HUNT_REVERSAL_LONG_PLUS_ENABLED = False  # CEO KILLED 2026-08-21 — same as master. NEVER_REENABLE.
STOP_HUNT_REVERSAL_LONG_DROP_THRESHOLD = 0.005       # 0.5% min drop to qualify as stop hunt (backtested optimal)
STOP_HUNT_REVERSAL_LONG_DROP_WINDOW = 5              # candles to look for the drop
STOP_HUNT_REVERSAL_LONG_REVERSAL_BODY_MIN = 0.005    # 0.5% min green body for reversal (RAISED from 0.3% — filters weak doji reversals that are noise, not conviction)
STOP_HUNT_REVERSAL_LONG_CONF_BASE = 75               # base confidence
STOP_HUNT_REVERSAL_LONG_CONF_STRONG_REVERSAL = 5     # +5 if reversal body > 1%
STOP_HUNT_REVERSAL_LONG_CONF_CAP = 95                # max confidence

# ── spike_exhaustion_short — SHORT after violent spike exhausts ───────────
SPIKE_EXHAUSTION_SHORT_ENABLED = True
SPIKE_EXHAUSTION_SHORT_MINUS_ENABLED = True
SPIKE_EXHAUSTION_SHORT_SPIKE_THRESHOLD = 0.025       # 2.5% min spike to fade
SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW = 5              # candles to look for spike
SPIKE_EXHAUSTION_SHORT_STALL_CANDLES = 3             # candles without new high = stall
SPIKE_EXHAUSTION_SHORT_CONF_BASE = 80                # base confidence (high conviction)
SPIKE_EXHAUSTION_SHORT_CONF_CAP = 95                 # max confidence
SPIKE_EXHAUSTION_SHORT_LARGE_SPIKE = 0.03            # >3% spike = extra confidence
SPIKE_EXHAUSTION_SHORT_MIN_LOOKBACK = 3              # min candles to detect spike
SPIKE_EXHAUSTION_SHORT_COOLDOWN_HOURS = 2            # per token+direction cooldown
STOP_HUNT_REVERSAL_LONG_LARGE_HUNT = 0.02            # >2% drop = extra confidence
STOP_HUNT_REVERSAL_LONG_STRONG_REVERSAL = 0.01       # >1% reversal body = extra confidence
STOP_HUNT_REVERSAL_LONG_COOLDOWN_HOURS = 2           # per token+direction cooldown
STOP_HUNT_REVERSAL_LONG_TREND_SLOPE_MIN = 0.0        # min 1m slope over last 30 candles — block LONG when slope < 0 (downtrend)
STOP_HUNT_REVERSAL_LONG_TREND_WINDOW = 30            # candles for linear regression slope check — 30 balances responsiveness vs noise (20 filters valid reversals, 50 too sluggish)

# ── Liquidation Hunt Signal (signals/liquidation_hunt.py) ────────────────────
LIQUIDATION_HUNT_ENABLED              = True    # master kill-switch
LIQUIDATION_HUNT_PLUS_ENABLED         = True    # LONG direction
LIQUIDATION_HUNT_MINUS_ENABLED        = True    # SHORT direction
LIQUIDATION_HUNT_COOLDOWN_HOURS       = 3       # per token+direction cooldown
LIQUIDATION_HUNT_MIN_CLUSTER_USD      = 5000    # minimum cluster notional value ($) to fire
LIQUIDATION_HUNT_MIN_SCORE            = 30      # minimum composite score (0-100) to fire
LIQUIDATION_HUNT_CONF_BASE            = 70      # base confidence
LIQUIDATION_HUNT_CONF_CAP             = 88      # max confidence (system ceiling)
LIQUIDATION_HUNT_STALE_SECONDS        = 900     # data older than this (sec) is stale (15 min)

# ── Liquidation Map Scanner (liquidation_map.py) ────────────────────────────
STOP_HUNT_DISTANCE_PCT = 2.0                 # max distance (%) from price to cluster to trigger signal
STOP_HUNT_MIN_CLUSTER_USD = 5000             # minimum cluster notional value ($) to matter
STOP_HUNT_MIN_SCORE = 30                     # minimum composite score (0-100) to fire signal
LIQ_MAP_SCAN_INTERVAL = 300                  # seconds between full liquidation map scans (5 min)
LIQ_MAP_MAX_WALLETS = 200                    # cap wallet universe to avoid rate limits
LIQ_MAP_BIN_PCT = 0.005                      # liquidation bin size as fraction of price (0.5%)

CONTINUATION_TRIGGER_REASONS = (              # which close reasons trigger scan
    'profit-monster', 'profit-monster-T1', 'profit-monster-trail',
    'profit_monster', 'atr_tp_hit',
)
# V2 trend analysis parameters
CONTINUATION_EMA_PERIOD = 50                  # EMA period for gap calculation (1m candles)
CONTINUATION_SLOPE_PERIOD = 20                # bars for linear regression slope (1m)
CONTINUATION_VELOCITY_PERIOD = 10             # bars for velocity (rate of change, 1m)
CONTINUATION_GAP_THRESHOLD = 0.3              # % — gap above/below EMA to consider "extended"
CONTINUATION_SLOPE_THRESHOLD = 0.01           # % per bar — min slope to consider trend alive
CONTINUATION_VELOCITY_THRESHOLD = 0.005       # % per bar — min velocity to consider momentum alive
# V2 exhaustion detection
CONTINUATION_EXHAUST_RSI_LONG = 75            # RSI > this on 1h = LONG exhaustion → reverse
CONTINUATION_EXHAUST_RSI_SHORT = 25           # RSI < this on 1h = SHORT exhaustion → reverse
CONTINUATION_EXHAUST_ZSCORE = 2.0             # |z| > this on 1h = exhaustion → reverse
CONTINUATION_EXHAUST_GAP_PCT = 1.5            # % — gap above EMA + velocity dying = exhaustion
# V2 wave control
CONTINUATION_WAVE_COOLDOWN_SEC = 7200         # seconds to count recent continuations (2 hours)
CONTINUATION_WAVE_MAX = 3                     # max continuation signals per token in window
# V2 confidence
CONTINUATION_CONF_BASE = 80
CONTINUATION_CONF_FLOOR = 65
CONTINUATION_CONF_CAP = 90
CONTINUATION_CONF_EXHAUST_BONUS = 5           # +5 for exhaustion fade (high conviction reversal)
CONTINUATION_CONF_TREND_BONUS = 4             # +4 for strong trend continuation
CONTINUATION_CONF_WAVE_PENALTY = 5            # -5 per wave beyond wave 1 (diminishing returns)
CONTINUATION_COOLDOWN_MIN = 60                # per-token cooldown (longer than normal)
# V2 additional tunables
CONTINUATION_PULLBACK_THRESHOLD = 1.0         # % — max pullback since close to still fire
CONTINUATION_CONF_ORIG_HIGH = 3               # +conf when original signal conf >= 90
CONTINUATION_CONF_ORIG_MED = 1                # +conf when original signal conf >= 85
CONTINUATION_CONF_1H_ALIGN = 3                # +conf when 1h trend aligned
CONTINUATION_CONF_1H_RET_THRESHOLD = 0.5      # % — 1h return threshold for alignment bonus

# ── ATR Spike Signal (atr_spike.py) ─────────────────────────────────────
# Catch staged LONG moves from ATR compression. Quality over quantity.
ATR_SPIKE_ENABLED              = True    # master kill-switch
ATR_SPIKE_PLUS_ENABLED         = True    # LONG direction
ATR_SPIKE_COMPRESSION_MAX_PCT  = 0.07    # ATR% threshold for compression (relaxed from 0.05; catches genuinely compressed tokens)
ATR_SPIKE_COMPRESSION_MIN_BARS = 4       # minimum candles in compression (relaxed from 5)
ATR_SPIKE_BREAKOUT_MIN_PCT     = 0.15    # minimum candle % move to trigger (relaxed from 0.3; ~93rd percentile for BTC)
ATR_SPIKE_TREND_FILTER         = True    # require EMA20 > EMA50 on 1h (changed from 15m — too noisy)
ATR_SPIKE_TREND_TIMEFRAME      = '1h'    # timeframe for trend filter ('1h' or '15m')
ATR_SPIKE_EMA_PROXIMITY_PCT    = 1.0     # max distance from EMA20 (relaxed from 0.5; still selective)
ATR_SPIKE_SL_PCT               = 0.75    # hard stop-loss %
ATR_SPIKE_CONF_BASE            = 70      # base confidence
ATR_SPIKE_CONF_PCT_BOOST       = 10      # extra conf per 0.1% above breakout threshold
ATR_SPIKE_CONF_CAP             = 88      # max confidence (system ceiling)
ATR_SPIKE_COOLDOWN_MIN         = 60      # minutes between fires per token

# ── Hebbian autonomous gate ─────────────────────────────────────────────
HEBBIAN_GATE_ENABLED = True                   # master switch for autonomous decisions
HEBBIAN_AUTO_APPROVE_WR = 0.60               # WR >= this → auto-approve
HEBBIAN_AUTO_REJECT_WR = 0.30                # WR <= this → auto-reject
HEBBIAN_AUTO_MIN_N = 5                       # standard threshold
HEBBIAN_AUTO_MIN_N_HIGH_CONF = 3             # high-confidence threshold (exit_profit ratio > 10)
HEBBIAN_HIGH_CONF_EXIT_RATIO = 10.0          # exit_profit/SL ratio for high-confidence tier
HEBBIAN_EXIT_PROFIT_BOOST = 5                # +conf when exit_profit dominant
HEBBIAN_EXIT_SL_PENALTY = 8                  # -conf when exit_sl dominant
HEBBIAN_EXIT_SL_AUTO_REJECT_RATIO = 0.2      # profit/SL ratio below this → auto-reject
HEBBIAN_EXIT_SL_AUTO_REJECT_MIN_N = 5        # minimum SL exits for this rule
HEBBIAN_COMBO_PART_BOOST = 3                 # +conf when combo parts both have high WR
HEBBIAN_TOKEN_WR_BOOST = 3                   # ±conf based on token history
HEBBIAN_TOKEN_WR_MIN_N = 5                   # minimum exit events for token-level estimate
HEBBIAN_TOKEN_WR_RATIO_HIGH = 3.0            # profit/SL ratio threshold for boost
HEBBIAN_TOKEN_WR_RATIO_LOW = 0.5             # profit/SL ratio threshold for penalty
HEBBIAN_CIRCUIT_BREAKER_WR = 0.45            # if auto-decision WR drops below, disable gate
HEBBIAN_CIRCUIT_BREAKER_N = 50               # minimum auto-decisions before circuit breaker
HEBBIAN_CIRCUIT_BREAKER_COOLDOWN_SEC = 14400 # 4 hours cooldown when tripped

# ── Wave Catcher — catch violent spikes in both directions ──────────────────
WAVE_CATCHER_ENABLED            = False   # CEO KILLED 2026-08-17 — both variants dead (+37.5% WR -$0.42, -25% WR -$0.09). Master switch.
WAVE_CATCHER_PLUS_ENABLED       = False   # CEO KILLED 2026-08-14 — 8T -$0.42 37.5% WR LONG. SHORT profitable (+$0.15).
WAVE_CATCHER_MINUS_ENABLED      = False   # CEO KILLED 2026-08-16 — 4T/48h 25% WR -$0.09. No edge.
WAVE_CATCHER_VELOCITY_THRESHOLD = 0.40    # % per bar — minimum velocity to trigger (backtested optimal)
WAVE_CATCHER_VELOCITY_WINDOW    = 3       # bars to measure velocity
WAVE_CATCHER_EMA_PERIOD         = 60      # EMA for trend confirmation
WAVE_CATCHER_MIN_ATR            = 0.05    # % — minimum ATR to trade (lowered from 0.10 — ATR lags spikes)
WAVE_CATCHER_ZSCORE_MAX         = 1.5     # max z-score — don't chase overextended
WAVE_CATCHER_CONF_BASE          = 75      # base confidence
WAVE_CATCHER_CONF_CAP           = 90      # max confidence
WAVE_CATCHER_COOLDOWN_HOURS     = 0.5     # 30 min cooldown
WAVE_CATCHER_TREND_FILTER_BARS  = 30      # bars to check trend direction (30min for 1m candles) — blocks dead-cat bounces

# ── Coin Tracker Hot — signal when coin_tracker detects hot setup ────────────
COIN_TRACKER_HOT_ENABLED            = False   # KILLED 2026-08-25 orchestrator — 36.4% WR, -$3.65/7d. Without it: system +$1.30/7d. NEVER_REENABLE.
COIN_TRACKER_HOT_PLUS_ENABLED       = False   # KILLED 2026-08-24 — 28.6% WR, -$0.49 (24h), 14T. 0% WR -$0.57 (6h).
COIN_TRACKER_HOT_MINUS_ENABLED      = False   # KILLED 2026-08-24 — 0% WR (6T), -$0.34. NEVER_REENABLE.
COIN_TRACKER_HOT_SETUP_THRESHOLD    = 25      # minimum setup_score to fire
COIN_TRACKER_HOT_CLUSTER_MIN        = 1.0     # minimum cluster count for direction (lowered from 3.0 — was blocking valid signals). RESEARCH_FLAGS
COIN_TRACKER_HOT_RECENCY_MIN        = 0.35    # minimum recency weight (0-1) (lowered from 0.6 — was blocking valid signals). RESEARCH_FLAGS
COIN_TRACKER_HOT_CONF_BASE          = 72      # base confidence
COIN_TRACKER_HOT_CONF_CAP           = 88      # max confidence
COIN_TRACKER_HOT_COOLDOWN_HOURS     = 0.167   # per token+direction cooldown (10 minutes)
COIN_TRACKER_HOT_MIN_COMPOSITE      = 63      # net score threshold — raised to 63 (was 57). CEO_PROTECTED
COIN_TRACKER_HOT_MIN_COMPOSITE_SHORT = 55     # SHORT-specific: raised to 55 (was 50). CEO_PROTECTED
# Momentum filters — prevent entries against the trend (added 2026-08-22, scaled 2026-08-22, tightened 2026-08-22)
COIN_TRACKER_HOT_MIN_MACD_PCT      = -0.00005 # MACD histogram as % of price must be > this for LONG (avoids bearish entries)
COIN_TRACKER_HOT_MAX_Z_SCORE        = 1.2      # Z-score must be < this for LONG (avoids overbought entries — tightened from 1.8)
COIN_TRACKER_HOT_MAX_BB_POSITION    = 0.75     # BB position must be < this for LONG (avoids upper band entries — tightened from 0.85)
# Speed & acceleration filters — prevent chasing extremes (added 2026-08-22)
COIN_TRACKER_HOT_MIN_SPEED_PCT      = 20       # Speed percentile must be > this (widened from 30 — was blocking valid signals). RESEARCH_FLAGS
COIN_TRACKER_HOT_MAX_SPEED_PCT      = 95       # Speed percentile must be < this (widened from 85 — was blocking valid signals). RESEARCH_FLAGS
# Extension filters — prevent entries when price already extended (added 2026-08-24)
COIN_TRACKER_HOT_MIN_ZSCORE_LONG    = -0.5     # For LONG: Z-score must be > this (avoid catching falling knives)
COIN_TRACKER_HOT_MAX_ZSCORE_SHORT   = -0.5     # For SHORT: Z-score must be < this (avoid shorting oversold)
COIN_TRACKER_HOT_MIN_BB_LONG        = 0.4      # For LONG: BB position must be > this (avoid lower band entries)
COIN_TRACKER_HOT_MAX_BB_SHORT       = 0.6      # For SHORT: BB position must be < this (avoid upper band entries)
COIN_TRACKER_HOT_MIN_ACCEL          = -0.01    # Price acceleration must be > this (avoid decelerating entries)

# ── Chain Fire — fire on follower tokens when leader tokens pump ─────────────
# chain_fire.py — correlate engine learns which tokens pump together
CHAIN_FIRE_ENABLED = True                # master kill-switch
CHAIN_FIRE_PLUS_ENABLED = True           # LONG direction
CHAIN_FIRE_MINUS_ENABLED = True          # SHORT direction
CHAIN_FIRE_MIN_LIFT = 1.5               # minimum lift ratio (chain must be 50%+ better than base)
CHAIN_FIRE_MIN_CONFIDENCE = 0.60         # minimum Bayesian confidence from correlation engine
CHAIN_FIRE_MIN_CO_FIRES = 5             # minimum historical co-firings to trust the chain
CHAIN_FIRE_MAX_LEADER_AGE_SECS = 1800    # leader must have fired within 30min (1800s)
CHAIN_FIRE_COOLDOWN_HOURS = 4           # per-follower cooldown after chain fire
CHAIN_FIRE_MAX_PER_CYCLE = 3            # max chain signals per pipeline run (prevent flooding)

# ── signal_confluence (meta-signal) ────────────────────────────────────────
# signal_confluence.py — detects persistence + compounding of first-order signals
# over a 30-minute rolling window. Fires every 5 min (slow signal).
SIGNAL_CONFLUENCE_ENABLED              = True   # master kill-switch
SIGNAL_CONFLUENCE_PLUS_ENABLED         = True   # LONG direction
SIGNAL_CONFLUENCE_MINUS_ENABLED        = True   # SHORT direction
SIGNAL_CONFLUENCE_WINDOW_MINUTES       = 30     # rolling lookback window
SIGNAL_CONFLUENCE_PERSISTENCE_MAX_DRAWDOWN = 0.03  # 3% — price reversal kills the signal
SIGNAL_CONFLUENCE_MIN_FAVORABLE_MOVE = 0.005  # 0.5% — price must move this much in favorable direction to confirm
SIGNAL_CONFLUENCE_MIN_COMPOUND         = 2      # min unique sources to fire (2=low conf, 3+=high conf)
SIGNAL_CONFLUENCE_CONFIDENCE_THRESHOLD = 45     # min score to fire
SIGNAL_CONFLUENCE_2SRC_CONFIDENCE      = 55     # confidence for 2-source compounding (lower quality)
SIGNAL_CONFLUENCE_3SRC_CONFIDENCE      = 75     # confidence for 3-source compounding (high quality)
SIGNAL_CONFLUENCE_4SRC_CONFIDENCE      = 88     # confidence for 4+ source compounding (max quality)
SIGNAL_CONFLUENCE_RECENCY_WINDOW_MINUTES = 10   # most recent signal must be < N min old for bonus
SIGNAL_CONFLUENCE_COMPOUND_WEIGHT      = 30     # points per unique source (2 sources = 75 conf, 3+ = 88 capped)
SIGNAL_CONFLUENCE_SURVIVED_BONUS       = 10     # points if earliest signal survived
SIGNAL_CONFLUENCE_RECENCY_BONUS        = 5      # points if most recent signal < 10 min old
SIGNAL_CONFLUENCE_COOLDOWN_HOURS       = 1      # per-token+direction cooldown after fire
SIGNAL_CONFLUENCE_MAX_PRICE_AGE        = 10     # skip tokens with price data older than N minutes

# ── Risk-Reward Engine ─────────────────────────────────────────────────────
# risk_reward_engine.py — structural R:R evaluation gate (replaces basic rr_gate)
# Uses multi-source S/R map + liquidity clusters + volatility width for smarter
# R:R assessment. Shadow mode for initial rollout.
#
# Data sources: volatility_gate.get_atr_pct(), candles.db, liquidation_clusters.json
# Reuses: rs_signals._find_swing_highs_lows(), liquidation_map.get_sr_levels()
RR_ENGINE_ENABLED            = True    # master switch
RR_ENGINE_SHADOW             = True    # True = log only, don't block (validate thresholds)
RR_ENGINE_FORCE              = False   # True = actually block (switch after shadow period)
RR_ENGINE_FAIL_OPEN          = True    # missing data = pass (never kill pipeline)

# R:R minimums (regime-adjusted)
RR_ENGINE_MIN_RATIO_FLAT     = 2.5     # FLAT regime (<0.48% ATR) — low energy, need bigger reward
RR_ENGINE_MIN_RATIO_NORMAL   = 2.0     # NORMAL regime (0.48-1.0% ATR) — standard
RR_ENGINE_MIN_RATIO_HIGH     = 1.5     # HIGH regime (1.0-1.5% ATR) — volatile, wider SL OK
RR_ENGINE_MIN_RATIO_EXTREME  = 2.0     # EXTREME regime (>1.5% ATR) — only specific signals trade here

# SL placement
RR_ENGINE_SL_ATR_MULT        = 1.0     # base SL = 1.0 × ATR
RR_ENGINE_SL_STRUCTURAL_BUFFER = 0.002 # extend SL 0.2% beyond structural level (avoid stop hunts)

# TP placement
RR_ENGINE_TP_MIN_PCT         = 0.005   # 0.5% minimum TP distance
RR_ENGINE_TP_MAX_PCT_NORMAL  = 0.025   # 2.5% max for NORMAL regime
RR_ENGINE_TP_MAX_PCT_FLAT    = 0.030   # 3.0% max for FLAT regime (low vol = wider structural range)
RR_ENGINE_TP_MAX_PCT_HIGH    = 0.020   # 2.0% max for HIGH regime
RR_ENGINE_TP_MAX_PCT_EXTREME = 0.020   # 2.0% max for EXTREME regime
RR_ENGINE_TP_ATR_MULT        = 2.0     # fallback TP = 2.0 × ATR (when no S/R target)

# S/R detection (candle swings)
RR_ENGINE_SR_CLUSTER_ATR     = 1.0     # merge levels within 1.0 × ATR of each other
RR_ENGINE_SR_LOOKBACK        = 300     # candles for swing detection (same as RS_LOOKBACK_CANDLES)
RR_ENGINE_SR_MIN_TOUCHES     = 3       # minimum touches for valid level (lower than RS signal's 5 — engine needs richer data)
RR_ENGINE_SR_RECENCY_HALF_LIFE = 100   # candles for exponential recency decay

# Liquidity proximity
RR_ENGINE_LIQ_MAX_DIST       = 2.0     # % — only consider clusters within 2% of price
RR_ENGINE_LIQ_CASCADE_RISK_THRESH = 0.5 # cascade risk above this → widen SL
RR_ENGINE_LIQ_MAGNET_BONUS   = 10      # score bonus for trading toward cluster
RR_ENGINE_LIQ_FIGHT_PENALTY  = -10     # score penalty for fighting cluster flow

# Scoring
RR_ENGINE_MIN_SCORE          = 50      # minimum composite score to pass (C grade)
RR_ENGINE_BLOCK_SCORE        = 35      # hard block below this (D/F grade)

# Bollinger Band width (for volatility assessment)
RR_ENGINE_BB_PERIOD          = 20
RR_ENGINE_BB_STDDEV          = 1.8     # matches range_finder.py and bb_bounce.py
RR_ENGINE_BB_SQUEEZE_THRESH  = 0.04    # BB width < 4% = squeeze

# Caching
RR_ENGINE_CACHE_TTL          = 300     # 5 min cache for S/R map and vol width per token
