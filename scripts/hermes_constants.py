#!/usr/bin/env python3
SHORT_BLACKLIST = {
    'SUI','FET','SPX','ARK','TON','ONDO','CRV','RUNE','AR',
    'NXPC','DASH','ARB','TRUMP','LDO','NEAR','APT','CELO','SEI',
    'ACE','YZY','ZEREBRO','WLFI','HBAR','MEGA',
    # Trade analysis 2026-04-01 (SHORTs with 0 wins, avg < -50%):
    'SOL','XPL','ZRO','NEO','GMT','FTT','HYPE','XLM','DOGE','MERL',
    'YGG','IO','USUAL','FOGO'
}
LONG_BLACKLIST = {'SEI', 'ACE', 'KAS', 'PROVE'}  # trade analysis 2026-04-01
BROAD_MARKET_TOKENS = ['ETH', 'SOL', 'BTC']
SERVER_NAME = 'Hermes'
