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
}
LONG_BLACKLIST = {'SEI', 'ACE', 'KAS', 'PROVE', 'BOME', 'USTC', 'RSR'}  # trade analysis 2026-04-01
BROAD_MARKET_TOKENS = ['ETH', 'SOL', 'BTC']
SERVER_NAME = 'Hermes'
