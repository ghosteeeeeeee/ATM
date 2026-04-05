#!/usr/bin/env python3
"""
Tokens - Single Source of Truth
All token lists consolidated here. Import from anywhere.
"""

# ============================================
# SOLANA-ONLY TOKENS (Raydium, LONG only, 1x)
# Exist on Solana, NOT on Hyperliquid
# ============================================
SOLANA_ONLY_TOKENS = {
    # Memecoins
    'BONK', 'WEN', 'POPCAT', 'GOAT', 'BOME', 'WIF', 'PEPE', 'MOG', 'BOOK', 
    'MOTHER', 'BADGER', 'APE', 'KAITO', 'HAYSTACK', 'SILLY', 'CHILL', 'MRL', 
    'BURN', 'BABYDOGE', 'DEGEN', 'BANANA', 'W', 'NOT', 'CATI', 'VINE', 'MOODENG', 
    'AI16Z', 'MEW', 'PNUT', 'CHILLGUY', 'MYRO', 'AIXBT', 'SYRUP', 'PUMP', 
    'GRIFFAIN', 'HAWK', 'ALCH', 'FMONEY', 'BIGTIME', 'GRASS',
    # Solana infrastructure
    'JTO', 'JUP', 'RAY', 'ORCA', 'SRM', 'STEP', 'MAPS', 'MNGO', 'DRIFT', 
    'GMX', 'HNT', 'WLD', 'BLUR', 'GMT', 'HOOK', 'RDNT', 'PENDLE', 'GMR', 
    'RARE', 'XRD', 'STX', 'YGG', 'MAGIC', 'TNSR', 'METIS', 'KAS', 'BLZ', 
    'VDR', 'WHALE', 'JLP', 'WZRD', 'AERO', 'LISTA', 'PIXEL', 'MAV', 'CYBER',
    'ALT', 'CC', 'BNT', 'MNT', 'SOL',
    # Additional Solana tokens
    'TRUMP', 'TURBO', 'GMT', 'DOOD', 'BABY', 'COMBO', 'NIGHT', 'SNAIL', 'PLANK',
    'SYS', 'DEMU', 'MIND', 'BOM', 'BINKY', 'SHIB', 'FLOKI', 'WOJAK', 'PONKE',
    'SANTAS', 'GRIN', 'WAGMI', 'HBB', 'PORTAL', 'SKL', 'IMPCAT', 'CATVM', 
    'CATINU', 'ALPH', 'ACT', 'NEO', 'MKR', 'SUSHI', 'CRV', '1INCH', 'AAVE',
    'COMP', 'LDO', 'SNX', 'ENS', 'NEXO', 'BUSD', 'TUSD', 'PAXG', 'WBTC',
    'REN', 'ZEN', 'KEEP', 'YFI', 'ALPHA', 'COTI', 'CHZ', 'ENJ', 'MANA',
    'SAND', 'AXS', 'THETA', 'FLOW', 'ALICE', 'DYDX', 'LUNA', 'UST', 'ANC',
    'KLAY', 'BNB', 'ZEC', 'XMR', 'DASH', 'ETC', 'RPL', 'CVX', 'SPELL',
    'RETH', 'CBETH', 'STETH', 'KSM', 'FOR', 'BAKE', 'WAXP', 'TFUEL', 'ONE',
}

# ============================================
# HYPERLIQUID TOKENS (Perps, LONG+SHORT, up to 20x)
# Available on Hyperliquid
# ============================================
HYPERLIQUID_TOKENS = {
    'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'LINK', 'MATIC', 'ATOM',
    'LTC', 'UNI', 'FIL', 'APT', 'ARB', 'OP', 'INJ', 'SEI', 'SUI', 'TIA',
    'NEAR', 'FTM', 'ALGO', 'VET', 'THETA', 'AAVE', 'MKR', 'SNX', 'LDO',
    'COMP', 'CRV', 'SUSHI', 'YFI', 'BAND', 'KNC', 'COTI', 'CELR', 'RLC',
    'ICX', 'ZIL', 'ENJ', 'MANA', 'SAND', 'GALA', 'FLOW', 'ALICE', 'DYDX',
    'GMX', 'RDNT', 'RUNE', 'ZEC', 'XMR', 'DASH', 'ETC', 'MINA', 'KSM', 'BNB',
    'HYPE', 'PEPE', 'SHIB', 'FLOKI', 'BONK', 'GOAT', 'BOME', 'POPCAT', 'MOG', 
    'BOOK', 'MOTHER', 'MEW', 'AI16Z', 'GRIFFAIN', 'DEGEN', 'SILLY', 'WLD',
    # Additional Hyperliquid tokens
    'IMX', 'BLUR', 'APE', 'PENDLE', 'RARE', 'NEO', 'TRX', 'XLM', 'ALPHA',
    'REEF', 'ENS', '1INCH', 'AAVE', 'SNX', 'LDO', 'RPL', 'CVX', 'FXS',
    'LRC', 'QNT', 'LSK', 'QTUM', 'AURORA', 'KAVA', 'WAVES', 'ZEC', 'DASH',
    'EGLD', 'HBAR', 'IOTA', 'XTZ', 'NEO', 'ONT', 'ZIL', 'KCS', 'FTM',
    'ONE', 'ROSE', 'SC', 'ZEN', 'SCRT', 'KAVA', 'BAND', 'CTSI', 'ANT',
    'NMR', 'PAXG', 'WBTC', 'REN', 'KEEP', 'YFI', 'BAL', 'NEXO', 'USDC',
    'TUSD', 'BUSD', 'MKR', 'AAVE', 'SNX', 'COMP', 'LEND', 'SUSHI',
}

# ============================================
# EXCLUDED FROM HYPERLIQUID (not available for trading)
# ============================================
HYPERLIQUID_EXCLUDE = {
    'SAND', 'MANA', 'AXS', 'ALICE', 'SXP', 'KAVA', 'CTSI', 'OGN', 'BAND',
    'ANT', 'NMR', 'PAXG', 'WBTC', 'REN', 'SBTC', 'tBTC', 'XEC', 'RUNE',
}

# ============================================
# WRAPPED TOKENS (exist on multiple chains)
# Prefer Hyperliquid for these
# ============================================
PREFER_HYPERLIQUID_TOKENS = {
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT',
    'MATIC', 'ARB', 'OP', 'LINK', 'UNI', 'ATOM', 'LTC', 'FIL', 'APT',
    'NEAR', 'INJ', 'FTM', 'SAND', 'MANA', 'AXS', 'GALA', 'AAVE', 'CRV',
}

# ============================================
# TOKEN BLACKLIST (trading disabled)
# ============================================
TOKEN_BLACKLIST = {
    'SKR',  # Worst performer
}

# ============================================
# Helper Functions
# ============================================

def is_solana_only(token: str) -> bool:
    """Check if token is Solana-only (Raydium, LONG only)."""
    token = token.upper()
    if token in SOLANA_ONLY_TOKENS:
        return True
    # If not on Hyperliquid and not excluded, treat as Solana
    if token not in HYPERLIQUID_TOKENS and token not in HYPERLIQUID_EXCLUDE:
        return True
    return False

def is_hyperliquid(token: str) -> bool:
    """Check if token is available on Hyperliquid."""
    token = token.upper()
    if token in HYPERLIQUID_EXCLUDE:
        return False
    if token in HYPERLIQUID_TOKENS:
        return True
    return False

def get_token_chain(token: str) -> str:
    """Determine the best chain for a token. Returns 'HYPERLIQUID', 'SOLANA', or 'NONE'."""
    token = token.upper()
    
    if token in TOKEN_BLACKLIST:
        return 'NONE'
    
    if token in HYPERLIQUID_EXCLUDE:
        return 'NONE'
    
    if token in SOLANA_ONLY_TOKENS:
        return 'SOLANA'
    
    if token in HYPERLIQUID_TOKENS:
        return 'HYPERLIQUID'
    
    # Unknown token - default to Hyperliquid
    return 'HYPERLIQUID'

def can_short(token: str) -> bool:
    """Check if shorting is allowed for this token."""
    token = token.upper()
    if token in SOLANA_ONLY_TOKENS:
        return False
    if token in HYPERLIQUID_EXCLUDE:
        return False
    return True

def get_all_tradeable_tokens():
    """Get all tokens that can be traded."""
    all_tokens = SOLANA_ONLY_TOKENS | HYPERLIQUID_TOKENS
    return all_tokens - TOKEN_BLACKLIST - HYPERLIQUID_EXCLUDE

if __name__ == '__main__':
    print(f'Solana-only: {len(SOLANA_ONLY_TOKENS)} tokens')
    print(f'Hyperliquid: {len(HYPERLIQUID_TOKENS)} tokens')
    print(f'Excluded: {len(HYPERLIQUID_EXCLUDE)} tokens')
    print(f'Blacklisted: {len(TOKEN_BLACKLIST)} tokens')
    print(f'Total tradeable: {len(get_all_tradeable_tokens())} tokens')
