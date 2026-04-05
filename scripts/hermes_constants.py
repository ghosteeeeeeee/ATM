#!/usr/bin/env python3
SHORT_BLACKLIST = {
    # High-volatility / inverse-beta tokens (shorting meme coins = lottery)
    'SUI','FET','SPX','ARK','TON','ONDO','CRV','RUNE','AR',
    'NXPC','DASH','ARB','TRUMP','LDO','NEAR','APT','CELO','SEI',
    'ACE','YZY','ZEREBRO','WLFI','HBAR','MEGA',
    # Historical 0% SHORT win rate (2026-04-01 analysis):
    'SOL',        # avg SHORT pnl: deeply negative, bull market leader
    'XPL','ZRO','NEO','GMT','FTT','HYPE','XLM','DOGE','MERL',
    'YGG','IO','USUAL','FOGO',
    # 0% SHORT win rate — add fresh
    'POL','DOOD','ADA','SYRUP',
    # Additional high-beta / recent pumps (shorting pumps = catching knives)
    'POPCAT',  # meme pump history
    'VIRTUAL', 'MELANIA', 'FARTCOIN',  # meme coins
    # 2026-04-01: tokens with negative avg SHORT returns
    'RENDER', 'WLD', 'PORT3', 'JUP',
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
    # 2026-04-02: manual additions (no trade history, blocking by token type)
    'BNB',    # major token, inverse-beta behavior, not tradeable on HL
    # 2026-04-02: phantom positions — guardian_missing loop (all +0.00%)
    'RLB', 'RNDR', 'SHIA', 'AI16Z', 'BADGER', 'BLZ', 'FXS',
    'HPOS', 'MATIC', 'UNIBOT', 'MKR', 'MYRO',
    # 2026-04-02: HMSTR — phantom SHORT, manually closed, catastrophic history
    'HMSTR',
    # 2026-04-03: PNUT — 4 SHORT losses, 0 wins, 3+ consecutive (2026-03-31),
    # net SHORT pnl: -$1.92. LONG direction healthy (+$6.34).
    'PNUT',
    # 2026-04-04: systematic SHORT losses (net<=$-2.50, phantom trades excluded)
    'ENA',     # SHORT net: -$5.41 (1 loss: conf-1s -$5.41)
    'PENGU',   # SHORT net: -$4.36 (1 loss: conf-1s -$4.36)
}
LONG_BLACKLIST = {
    'SEI', 'ACE', 'KAS', 'PROVE', 'BOME', 'USTC', 'RSR',
    # Solana chain tokens — indexed on HL but NOT tradeable
    'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA', 'LOOM',
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    # 2026-04-02: phantom orders via openclaw systemd timers
    'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',
    # 2026-04-02: persistent losing LONG directions (loss cooldown streaks)
    'AERO', 'CHILLGUY', 'LIT', 'DOT', 'ANIME',  # LONG streaks
    # 2026-04-03: SHORT blacklist additions
    'S',       # SHORT net: -$3.46 (1 loss, 0 wins, conf-1s 99%)
    'MAV',     # SHORT net: -$1.92 (1 loss); 2 SHORT losses total incl. decider
    'TURBO',   # SHORT net: -$5.47 (1 loss, conf-3s 99%)
    # 2026-04-03: LONG blacklist additions
    'IP',      # LONG net: -$12.21 (3 losses: conf-1s $3.63, decider $4.95 conf=0!, speed $2.63)
    'SUSHI',   # LONG net: -$8.51 (2 losses: conf-3s $6.42, conf-2s $2.09)
    'XAI',     # LONG net: -$4.92 (3 losses: conf-1s $1.69, conf-2s $1.61, brain $1.62, 2026-04-03)
    'ZEN',     # LONG net: -$26.81 (decider $26.81 conf=0 phantom, conf-1s $0.01)
    # 2026-04-03: systematic SHORT losses (3/3 trades lost, net >=-$2.50)
    'BABY',  # SHORT net: -$8.68 total (3 losses: conf-2s -$1.01, conf-3s -$5.76, decider -$1.92)
    # 2026-04-03: LTC LONG blacklist — net loss -$4.70, 3 consecutive losses
    # HL fills: +$0.001 (1 win). Signal outcomes: -$4.42 (3 losses: decider -$0.10,
    # conf-3s -$4.04, conf-1s -$0.28). Brain DB: -$0.28 (trailing_exit). PENDING: 2.
    'LTC',
    # 2026-04-03: systematic LONG losses (>=-$2.50 net on LONG direction)
    'SKR',   # LONG net: -$5.67 (2 losses: manual_close $3.07, trailing_exit $2.60, 2026-04-03)
    'KAITO', # LONG net: -$4.81 (2026-04-03)
    'COMP',  # LONG net: -$5.26 (2 losses: conf-1s $2.71, conf-2s $2.55)
    'ETC',   # LONG net: -$2.95 (3 trades: brain trailing_exit -$1.49, conf-2s +$0.03, conf-4s -$1.49)
    # 2026-04-02: manual additions
    'BIO', 'TAO', 'GAS',   # blocking both directions: no trade history, high-risk profiles
    # 2026-04-02: HMSTR — phantom SHORT, manually closed, catastrophic history
    'HMSTR',
    # 2026-04-04: LONG blacklist additions (net<=$-2.50, phantom trades excluded)
    '0G',       # LONG net: -$5.04 (1 loss: conf-3s -$5.04)
    '2Z',       # LONG net: -$2.90 (1 loss: trailing_exit -$2.90)
    'AIXBT',    # LONG net: -$5.12 (1 loss: conf-1s -$5.12)
    'BERA',     # LONG net: -$4.09 (1 loss: conf-3s -$4.09)
    'BLUR',     # LONG net: -$5.04 (1 loss: conf-1s -$5.04)
    'BSV',      # LONG net: -$4.53 (1 loss: trailing_exit -$4.53)
    'DYM',      # LONG net: -$3.73 (1 loss: conf-3s -$3.73)
    'GRASS',    # LONG net: -$12.64 (2 losses: conf-1s -$8.42, trailing_exit -$4.22)
    'GRIFFAIN', # LONG net: -$3.05 (2 losses: guardian_missing -$1.45, -$1.60)
    'MAVIA',    # LONG net: -$2.91 (2 losses: guardian_missing -$0.55, trailing_exit -$2.36)
    'MON',      # LONG net: -$4.70 (2 losses: trailing_exit -$4.10, guardian_missing -$0.60)
    'OP',       # LONG net: -$4.48 (1 loss: conf-3s -$4.48)
    'POLYX',    # LONG net: -$3.65 (1 loss: conf-1s -$3.65)
    'PROMPT',   # LONG net: -$11.98 (3 losses: conf-3s -$7.54, -$2.24, -$2.20)
    'REZ',      # LONG net: -$3.96 (2 losses: trailing_exit -$3.84, guardian_missing -$0.12)
    'XMR',      # LONG net: -$3.64 (1 loss: conf-1s -$3.64)
    'ZETA',     # LONG net: -$5.29 (1 loss: trailing_exit -$5.29)
}
BROAD_MARKET_TOKENS={'SOL', 'BTC'}

# Combined blocklist: tokens blocked from hot-set for ANY direction
# = SHORT_BLACKLIST ∪ LONG_BLACKLIST
HOTSET_BLOCKLIST = SHORT_BLACKLIST | LONG_BLACKLIST
SERVER_NAME = 'Hermes'
