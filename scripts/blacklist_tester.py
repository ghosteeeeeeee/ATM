#!/usr/bin/env python3
"""
Blacklist Tester — rotate blacklisted tokens in/out for 48h trials.

Usage:
    python3 scripts/blacklist_tester.py evaluate   # evaluate completed trials
    python3 scripts/blacklist_tester.py pick       # pick next batch to test
    python3 scripts/blacklist_tester.py start      # remove tokens from blacklist for trial
    python3 scripts/blacklist_tester.py status     # show current trial status

Rules:
    - WR >= 40% AND PnL > -2%  → KEEP (remove permanently)
    - WR < 30% OR PnL < -5%    → RE-BLACKLIST
    - WR 30-40%                 → EXTEND 24h
    - < 3 trades                → INSUFFICIENT (extend or drop)
"""
import sys, os, sqlite3, json
from datetime import datetime, timedelta
from collections import defaultdict

HERMES_DATA = os.environ.get('HERMES_DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
)
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
TEST_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'automation', 'blacklist_test_log.md')

# Tokens to NEVER test — structural issues, not performance
SKIP_TOKENS = {
    'BTC', 'ETH', 'SOL',           # too large, spread issues
    'STABLE', 'PAXG',              # stablecoins
    'FTM', 'CANTO', 'MANTA',       # Solana chain, untradeable on HL
    'PANDORA', 'JELLY', 'FRIEND',  # Solana chain
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    'SAGE', 'SAMO', 'DUST', 'HNT', 'LOOM',
    # Structural blacklist reasons (not performance) — skip these
    'BOME',    # sketchy volume
    'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',  # phantom orders
    'RLB', 'RNDR', 'SHIA', 'MATIC', 'UNIBOT', 'MKR', 'MYRO',  # phantom positions
    'REZ', 'HMSTR', 'BNB',  # ATR self-close bug
    'APE', 'PENDLE', 'POLYX', 'BIO',  # block both dirs (structural)
    'GRIFFAIN','BRETT','XLM','SNX','NIL','IP','TRB','ETHFI','EIGEN',
    'S','VVV','SUI','LAYER','BERA','DYM','MAVIA','MEME','INIT','SOPH',
    'XAI','ZEC','GAS','BLAST','MELANIA','ZETA','SPX','DOGE','ARK','RUNE','AR',
    'TST','NXPC','TRUMP','CELO','ACE','YZY','ZEREBRO','WLFI','HBAR','MEGA',
    'SOL','MEW','POPCAT','VIRTUAL','FARTCOIN','RENDER','PORT3',
    'USTC','RSR','MINA','ENA','PENGU','CFX',
    'KAS','PROVE','AERO','CHILLGUY','LIT','ANIME',
}

BATCH_SIZE = 20
TRIAL_HOURS = 48

# Read blacklist from hermes_constants.py (canonical source)
def load_blacklists():
    """Parse SHORT_BLACKLIST and LONG_BLACKLIST from hermes_constants.py."""
    const_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')
    short, long = set(), set()
    with open(const_path) as f:
        content = f.read()
    
    in_short = False
    in_long = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('SHORT_BLACKLIST'):
            in_short = True
            in_long = False
        elif stripped.startswith('LONG_BLACKLIST'):
            in_long = True
            in_short = False
        elif stripped.startswith('BROAD_MARKET_TOKENS') or stripped.startswith('SIGNAL_SOURCE_BLACKLIST') or stripped.startswith('#'):
            if in_short or in_long:
                # Check if this line is a closing brace
                if '}' in stripped:
                    in_short = False
                    in_long = False
                continue
        
        if (in_short or in_long):
            if '}' in stripped:
                in_short = False
                in_long = False
                continue
            # Extract tokens from line: 'TOKEN', 'TOKEN2', ...
            for token in stripped.split("'"):
                token = token.strip().rstrip(',')
                if token and token.isupper():
                    if in_short:
                        short.add(token)
                    else:
                        long.add(token)
    return short, long


def get_trial_outcomes(token, trial_start):
    """Query signal_outcomes for a token since trial_start."""
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as trades,
               SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
               ROUND(SUM(pnl_usdt), 2) as net_pnl
        FROM signal_outcomes
        WHERE token = ? AND created_at >= ?
    """, (token, trial_start))
    row = cur.fetchone()
    conn.close()
    if not row or row[0] == 0:
        return 0, 0, 0.0
    trades, wins, net_pnl = row
    return trades, wins or 0, net_pnl or 0.0


def evaluate_verdict(trades, wins, net_pnl):
    """Apply verdict logic. Returns (verdict, reason)."""
    if trades < 3:
        return 'INSUFFICIENT', f'{trades} trades'
    wr = 100.0 * wins / trades
    if wr >= 40 and net_pnl > -2.0:
        return 'KEEP', f'{wr:.0f}% WR, ${net_pnl:.2f}'
    if wr < 30 or net_pnl < -5.0:
        return 'RE-BLACKLIST', f'{wr:.0f}% WR, ${net_pnl:.2f}'
    if 30 <= wr < 40:
        return 'EXTEND', f'{wr:.0f}% WR, ${net_pnl:.2f}'
    return 'RE-BLACKLIST', f'{wr:.0f}% WR, ${net_pnl:.2f}'


def load_test_log():
    """Parse blacklist_test_log.md for active trials."""
    if not os.path.exists(TEST_LOG):
        return []
    trials = []
    with open(TEST_LOG) as f:
        content = f.read()
    
    # Parse table rows with dates
    for line in content.splitlines():
        if line.startswith('|') and not line.startswith('| Token') and not line.startswith('|---'):
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 2:
                token = cols[0]
                if cols[1] and '-' in cols[1]:
                    try:
                        start = datetime.strptime(cols[1].strip(), '%Y-%m-%d %H:%M')
                        trials.append({
                            'token': token,
                            'trial_start': start.isoformat(),
                            'verdict': cols[6] if len(cols) > 6 else ''
                        })
                    except ValueError:
                        pass
    
    # Also parse comma-separated token lists (Batch 2+ format)
    import re
    for match in re.finditer(r'Removed from both.*?:\s*\n([A-Z,\s]+)', content):
        tokens = [t.strip() for t in match.group(1).split(',') if t.strip()]
        for token in tokens:
            if not any(t['token'] == token for t in trials):
                trials.append({
                    'token': token,
                    'trial_start': '2026-08-02',
                    'verdict': 'RE-BLACKLIST'
                })
    
    return trials


def pick_next_batch(short_blacklist, long_blacklist):
    """Pick tokens to test next. Prioritize tokens in both blacklists."""
    candidates = (short_blacklist | long_blacklist) - SKIP_TOKENS
    
    # Load existing trials to skip re-tested tokens
    existing = load_test_log()
    already_tested = {t['token'] for t in existing}
    candidates -= already_tested
    
    # Prioritize: both dirs > short-only > long-only
    both = candidates & short_blacklist & long_blacklist
    short_only = candidates & short_blacklist - long_blacklist
    long_only = candidates & long_blacklist - short_blacklist
    
    # Skip tokens with < 5 trades total (not enough data to judge)
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    
    batch = []
    for pool in [both, short_only, long_only]:
        for token in sorted(pool):
            if len(batch) >= BATCH_SIZE:
                break
            cur.execute("SELECT COUNT(*) FROM signal_outcomes WHERE token = ?", (token,))
            total = cur.fetchone()[0]
            if total >= 3:  # need at least some data to justify testing
                batch.append(token)
        if len(batch) >= BATCH_SIZE:
            break
    
    conn.close()
    return batch[:BATCH_SIZE]


def cmd_evaluate():
    """Evaluate completed trials and produce verdicts."""
    short_bl, long_bl = load_blacklists()
    
    # Load test log for active trials
    if not os.path.exists(TEST_LOG):
        print("No test log found. Nothing to evaluate.")
        return
    
    with open(TEST_LOG) as f:
        content = f.read()
    
    # Parse batch 2 tokens (most recent active trial)
    batch2_tokens = set()
    in_batch2 = False
    for line in content.splitlines():
        if 'Batch 2' in line and 'Started' in line:
            in_batch2 = True
            continue
        if in_batch2 and line.strip().startswith(('Removed', '**Note', '##')):
            break
        if in_batch2 and not line.startswith('#') and not line.startswith('**') and not line.startswith('|') and not line.startswith('-'):
            # This line should be the token list
            tokens = [t.strip() for t in line.split(',') if t.strip()]
            batch2_tokens.update(tokens)
    
    if not batch2_tokens:
        # Fallback: hardcode from log
        batch2_tokens = {'COMP','CRV','DYDX','IMX','SAND','NEAR','DOT','ICP','ATOM','INJ','FIL','ETC','ARB','OP','LDO','APT','SEI','MET','DASH','WLD'}
    
    print(f"Evaluating {len(batch2_tokens)} Batch 2 tokens...")
    print(f"Trial started: 2026-08-02")
    print()
    
    verdicts = []
    for token in sorted(batch2_tokens):
        trades, wins, net_pnl = get_trial_outcomes(token, '2026-08-02')
        verdict, reason = evaluate_verdict(trades, wins, net_pnl)
        verdicts.append((token, trades, wins, net_pnl, verdict, reason))
        status = 'KEEP' if verdict == 'KEEP' else ('RE-BLACKLIST' if verdict == 'RE-BLACKLIST' else verdict)
        print(f"  {token:8s} | {trades:3d} trades | {wins:2d} wins | ${net_pnl:+7.2f} | {status:14s} | {reason}")
    
    # Count verdicts
    keeps = sum(1 for v in verdicts if v[4] == 'KEEP')
    rebl = sum(1 for v in verdicts if v[4] == 'RE-BLACKLIST')
    ext = sum(1 for v in verdicts if v[4] == 'EXTEND')
    insuf = sum(1 for v in verdicts if v[4] == 'INSUFFICIENT')
    
    print(f"\nSummary: {keeps} KEEP, {rebl} RE-BLACKLIST, {ext} EXTEND, {insuf} INSUFFICIENT")
    return verdicts


def cmd_pick():
    """Pick next batch of tokens to test."""
    short_bl, long_bl = load_blacklists()
    batch = pick_next_batch(short_bl, long_bl)
    
    print(f"Next batch ({len(batch)} tokens):")
    both = [t for t in batch if t in short_bl and t in long_bl]
    short_only = [t for t in batch if t in short_bl and t not in long_bl]
    long_only = [t for t in batch if t in long_bl and t not in short_bl]
    
    if both:
        print(f"  Both dirs ({len(both)}): {', '.join(both)}")
    if short_only:
        print(f"  SHORT only ({len(short_only)}): {', '.join(short_only)}")
    if long_only:
        print(f"  LONG only ({len(long_only)}): {', '.join(long_only)}")
    
    return batch


def cmd_status():
    """Show current trial status."""
    short_bl, long_bl = load_blacklists()
    print(f"SHORT_BLACKLIST: {len(short_bl)} tokens")
    print(f"LONG_BLACKLIST: {len(long_bl)} tokens")
    
    # Show batch 2 status
    batch2 = {'COMP','CRV','DYDX','IMX','SAND','NEAR','DOT','ICP','ATOM','INJ','FIL','ETC','ARB','OP','LDO','APT','SEI','MET','DASH','WLD'}
    print(f"\nBatch 2 active: {len(batch2)} tokens (started 2026-08-02)")
    print(f"  Trial window: {TRIAL_HOURS}h (ends ~2026-08-04)")
    
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    for token in sorted(batch2):
        cur.execute("""
            SELECT COUNT(*) as trades,
                   SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(pnl_usdt), 2) as net_pnl
            FROM signal_outcomes
            WHERE token = ? AND created_at >= '2026-08-02'
        """, (token,))
        row = cur.fetchone()
        trades, wins, net_pnl = row[0], row[1] or 0, row[2] or 0.0
        wr = 100.0 * wins / trades if trades > 0 else 0
        print(f"  {token:8s} | {trades:3d} trades | {wr:5.1f}% WR | ${net_pnl:+7.2f}")
    conn.close()


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'evaluate':
        cmd_evaluate()
    elif cmd == 'pick':
        cmd_pick()
    elif cmd == 'start':
        batch = cmd_pick()
        print(f"\nTo start trial: remove these from blacklists in hermes_constants.py")
    elif cmd == 'status':
        cmd_status()
    else:
        print(f"Usage: {sys.argv[0]} [evaluate|pick|start|status]")
