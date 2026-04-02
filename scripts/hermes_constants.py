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
    'ZEC',    # SHORT: persistent loss cooldown
    # 2026-04-02: manual additions (no trade history, blocking by token type)
    'BNB',    # major token, inverse-beta behavior, not tradeable on HL
    # 2026-04-02: phantom positions — guardian_missing loop (all +0.00%)
    'RLB', 'RNDR', 'SHIA', 'AI16Z', 'BADGER', 'BLZ', 'FXS',
    'HPOS', 'MATIC', 'UNIBOT', 'MKR', 'MYRO',
}
LONG_BLACKLIST = {
    'SEI', 'ACE', 'KAS', 'PROVE', 'BOME', 'USTC', 'RSR',
    # Solana chain tokens — indexed on HL but NOT tradeable
    'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA', 'LOOM',
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    # 2026-04-02: phantom orders via openclaw systemd timers
    'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',
    # 2026-04-02: persistent losing LONG directions (loss cooldown streaks)
    'AERO', 'CHILLGUY', 'LIT', 'DOT', 'ANIME',  # LONG losing streaks
    # 2026-04-02: manual additions
    'BIO', 'TAO', 'GAS',   # blocking both directions: no trade history, high-risk profiles
}
BROAD_MARKET_TOKENS = {'SOL', 'BTC'}
SERVER_NAME = 'Hermes'
