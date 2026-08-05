#!/usr/bin/env python3
"""
Blacklist Tester — rotate blacklisted tokens in/out for 48h trials.

Usage:
    python3 scripts/blacklist_tester.py evaluate   # evaluate completed trials
    python3 scripts/blacklist_tester.py pick       # pick next batch to test
    python3 scripts/blacklist_tester.py start      # remove tokens from blacklist for trial
    python3 scripts/blacklist_tester.py status     # show current trial status
    python3 scripts/blacklist_tester.py remaining  # show untested tokens
    python3 scripts/blacklist_tester.py cleanup    # auto-cleanup: only perma-block repeat offenders

Rules (lenient - first chance given):
    - WR >= 40% AND PnL > -2%  → KEEP (remove permanently)
    - WR < 20% OR PnL < -5%    → RE-BLACKLIST (but track failures)
    - WR 20-40%                 → EXTEND 24h
    - < 3 trades                → INSUFFICIENT (extend or drop)
    - PERMA-BLOCK: 3+ failures → permanent blacklist (never test again)
"""
import sys, os, sqlite3, re, json
from datetime import datetime, timedelta

HERMES_DATA = os.environ.get('HERMES_DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
TEST_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'automation', 'blacklist_test_log.md')
TRIAL_HISTORY = os.path.join(HERMES_DATA, 'blacklist_trial_history.json')

# Tokens to NEVER test — structural issues, not performance
SKIP_TOKENS = {
    'BTC', 'ETH', 'SOL', 'STABLE', 'PAXG',
    'FTM', 'CANTO', 'MANTA', 'PANDORA', 'JELLY', 'FRIEND',
    'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    'SAGE', 'SAMO', 'DUST', 'HNT', 'LOOM',
    'BOME', 'OX', 'ORBS', 'LAUNCHCOIN', 'NEIROETH', 'NFTI', 'OMNI',
    'RLB', 'RNDR', 'SHIA', 'MATIC', 'UNIBOT', 'MKR', 'MYRO',
    'REZ', 'HMSTR', 'BNB',
    'APE', 'PENDLE', 'POLYX', 'BIO',
    'GRIFFAIN','BRETT','XLM','SNX','NIL','IP','TRB','ETHFI','EIGEN',
    'S','VVV','SUI','LAYER','BERA','DYM','MAVIA','MEME','INIT','SOPH',
    'XAI','ZEC','GAS','BLAST','MELANIA','ZETA','SPX','DOGE','ARK','RUNE','AR',
    'TST','NXPC','TRUMP','CELO','ACE','YZY','ZEREBRO','WLFI','HBAR','MEGA',
    'MEW','POPCAT','VIRTUAL','FARTCOIN','RENDER','PORT3',
    'USTC','RSR','MINA','ENA','PENGU','CFX',
    'KAS','PROVE','AERO','CHILLGUY','LIT','ANIME',
}

BATCH_SIZE = 20
TRIAL_HOURS = 48
MAX_FAILURES = 3  # Perma-block after 3 failures


def load_trial_history() -> dict:
    """Load trial history (how many times each token has failed)."""
    try:
        with open(TRIAL_HISTORY) as f:
            return json.load(f)
    except:
        return {}

def save_trial_history(history: dict):
    """Save trial history."""
    tmp_path = TRIAL_HISTORY + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(history, f, indent=2)
    os.replace(tmp_path, TRIAL_HISTORY)

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
        if stripped.startswith('SHORT_BLACKLIST') and '=' in stripped and '{' in stripped:
            in_short, in_long = True, False
        elif stripped.startswith('LONG_BLACKLIST') and '=' in stripped and '{' in stripped:
            in_long, in_short = True, False
        elif stripped.startswith(('BROAD_MARKET_TOKENS', 'SIGNAL_SOURCE_BLACKLIST', '#')):
            if '}' in stripped:
                in_short, in_long = False, False
            continue

        if in_short or in_long:
            if '}' in stripped:
                in_short, in_long = False, False
                continue
            for token in stripped.split("'"):
                token = token.strip().rstrip(',')
                if token and token.isupper() and len(token) <= 6 and token.isalpha():
                    (short if in_short else long).add(token)
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


def evaluate_verdict(trades, wins, net_pnl, failure_count=0):
    """Apply lenient verdict logic. Returns (verdict, reason)."""
    if trades < 3:
        return 'INSUFFICIENT', f'{trades} trades'
    
    wr = 100.0 * wins / trades
    
    # Good performance → KEEP
    if wr >= 40 and net_pnl > -2.0:
        return 'KEEP', f'{wr:.0f}% WR, ${net_pnl:.2f}'
    
    # Very bad performance → RE-BLACKLIST
    if wr < 20 or net_pnl < -5.0:
        if failure_count >= MAX_FAILURES:
            return 'PERMA-BLOCK', f'{wr:.0f}% WR, ${net_pnl:.2f}, {failure_count} failures'
        return 'RE-BLACKLIST', f'{wr:.0f}% WR, ${net_pnl:.2f}'
    
    # Borderline → EXTEND
    if 20 <= wr < 40:
        return 'EXTEND', f'{wr:.0f}% WR, ${net_pnl:.2f}'
    
    # Default: re-blacklist
    if failure_count >= MAX_FAILURES:
        return 'PERMA-BLOCK', f'{wr:.0f}% WR, ${net_pnl:.2f}, {failure_count} failures'
    return 'RE-BLACKLIST', f'{wr:.0f}% WR, ${net_pnl:.2f}'


def parse_test_log():
    """Parse blacklist_test_log.md → list of {batch, tokens: {token: {start, verdict}}}."""
    if not os.path.exists(TEST_LOG):
        return []
    with open(TEST_LOG) as f:
        content = f.read()

    batches = []
    current_batch = None

    for line in content.splitlines():
        m = re.match(r'## Batch (\d+).*Started (\d{4}-\d{2}-\d{2})', line)
        if m:
            current_batch = {
                'num': int(m.group(1)),
                'start': m.group(2),
                'tokens': {},
            }
            batches.append(current_batch)
            continue

        if current_batch is None:
            continue

        if line.startswith('|') and not line.startswith('| Token') and not line.startswith('|---'):
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 7 and cols[0] and cols[0] != 'Token':
                token = cols[0].strip()
                verdict = cols[6].strip() if cols[6] else ''
                start = cols[1].strip() if cols[1] else ''
                current_batch['tokens'][token] = {'start': start, 'verdict': verdict}

        if line.strip().startswith('Removed from both'):
            continue
        if current_batch and not line.startswith('#') and not line.startswith('**') and not line.startswith('|') and not line.startswith('-') and not line.startswith('Removed') and line.strip():
            tokens_raw = [t.strip() for t in line.split(',') if t.strip()]
            if tokens_raw and all(t.replace(' ', '').isupper() or t == '' for t in tokens_raw):
                for token in tokens_raw:
                    token = token.strip()
                    if token and token.isupper() and token not in current_batch['tokens']:
                        current_batch['tokens'][token] = {'start': current_batch['start'], 'verdict': 'PENDING'}

    return batches


def get_tested_tokens():
    """Return set of tokens that actually completed a trial."""
    batches = parse_test_log()
    tested = set()
    for b in batches:
        for token, info in b['tokens'].items():
            v = info['verdict'].lower()
            if info['start'] and 'pre-trial' not in v and info['verdict'] not in ('RE-BLACKLIST', 'PENDING'):
                tested.add(token)
            elif 'wr' in v or 'execution' in v or 'insufficient' in v:
                tested.add(token)
    return tested


def pick_next_batch(short_blacklist, long_blacklist):
    """Pick tokens to test next."""
    candidates = (short_blacklist | long_blacklist) - SKIP_TOKENS
    candidates = {t for t in candidates if t.isalpha() and t.isupper() and len(t) <= 6}

    tested = get_tested_tokens()
    candidates -= tested

    # Remove perma-blocked tokens
    history = load_trial_history()
    perma_blocked = {t for t, h in history.items() if h.get('failures', 0) >= MAX_FAILURES}
    candidates -= perma_blocked

    # Prioritize: both dirs > short-only > long-only
    both = candidates & short_blacklist & long_blacklist
    short_only = (candidates & short_blacklist) - long_blacklist
    long_only = (candidates & long_blacklist) - short_blacklist

    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()

    batch = []
    for pool in [both, short_only, long_only]:
        for token in sorted(pool):
            if len(batch) >= BATCH_SIZE:
                break
            cur.execute("SELECT COUNT(*) FROM signal_outcomes WHERE token = ?", (token,))
            total = cur.fetchone()[0]
            batch.append((token, total))
        if len(batch) >= BATCH_SIZE:
            break

    conn.close()
    return batch[:BATCH_SIZE]


def cmd_evaluate():
    """Evaluate all completed trials and produce verdicts."""
    batches = parse_test_log()
    history = load_trial_history()
    now = datetime.utcnow()

    for batch in batches:
        trial_start = batch['start']
        try:
            start_dt = datetime.strptime(trial_start, '%Y-%m-%d')
        except ValueError:
            continue

        trial_end = start_dt + timedelta(hours=TRIAL_HOURS)
        pending = {t: i for t, i in batch['tokens'].items() if not i['verdict'].startswith(('KEEP', 'RE-BLACKLIST', 'PERMA-BLOCK'))}

        if pending and now < trial_end:
            print(f"Batch {batch['num']}: STILL ACTIVE (ends {trial_end.strftime('%Y-%m-%d %H:%M')})")
            for token, info in sorted(pending.items()):
                trades, wins, net_pnl = get_trial_outcomes(token, trial_start)
                wr = 100.0 * wins / trades if trades > 0 else 0
                print(f"  {token:8s} | {trades:3d} trades | {wr:5.1f}% WR | ${net_pnl:+7.2f}")
            print()
            continue

        print(f"Batch {batch['num']} — COMPLETED (started {trial_start}):")
        verdicts = []
        for token, info in sorted(batch['tokens'].items()):
            if info['verdict'].startswith(('KEEP', 'RE-BLACKLIST', 'PERMA-BLOCK')):
                continue
            trades, wins, net_pnl = get_trial_outcomes(token, trial_start)
            failure_count = history.get(token, {}).get('failures', 0)
            verdict, reason = evaluate_verdict(trades, wins, net_pnl, failure_count)
            verdicts.append((token, trades, wins, net_pnl, verdict, reason))
            
            # Update history
            if token not in history:
                history[token] = {'failures': 0, 'trials': 0}
            history[token]['trials'] = history[token].get('trials', 0) + 1
            if verdict in ('RE-BLACKLIST', 'PERMA-BLOCK'):
                history[token]['failures'] = history[token].get('failures', 0) + 1
            
            status = verdict
            print(f"  {token:8s} | {trades:3d} trades | {wins:2d} wins | ${net_pnl:+7.2f} | {status:14s} | {reason}")

        if verdicts:
            keeps = sum(1 for v in verdicts if v[4] == 'KEEP')
            rebl = sum(1 for v in verdicts if v[4] == 'RE-BLACKLIST')
            perm = sum(1 for v in verdicts if v[4] == 'PERMA-BLOCK')
            ext = sum(1 for v in verdicts if v[4] == 'EXTEND')
            insuf = sum(1 for v in verdicts if v[4] == 'INSUFFICIENT')
            print(f"  Summary: {keeps} KEEP, {rebl} RE-BLACKLIST, {perm} PERMA-BLOCK, {ext} EXTEND, {insuf} INSUFFICIENT")
        else:
            print("  All tokens already decided.")
        print()
    
    save_trial_history(history)


def cmd_pick():
    """Pick next batch of tokens to test."""
    short_bl, long_bl = load_blacklists()
    batch = pick_next_batch(short_bl, long_bl)

    if not batch:
        print("No remaining tokens to test.")
        return []

    both = [(t, n) for t, n in batch if t in short_bl and t in long_bl]
    short_only = [(t, n) for t, n in batch if t in short_bl and t not in long_bl]
    long_only = [(t, n) for t, n in batch if t in long_bl and t not in short_bl]

    print(f"Next batch ({len(batch)} tokens):")
    if both:
        print(f"  Both dirs ({len(both)}): {', '.join(f'{t}({n}t)' for t, n in both)}")
    if short_only:
        print(f"  SHORT only ({len(short_only)}): {', '.join(f'{t}({n}t)' for t, n in short_only)}")
    if long_only:
        print(f"  LONG only ({len(long_only)}): {', '.join(f'{t}({n}t)' for t, n in long_only)}")

    return [t for t, _ in batch]


def cmd_remaining():
    """Show untested tokens still in blacklist."""
    short_bl, long_bl = load_blacklists()
    candidates = (short_bl | long_bl) - SKIP_TOKENS
    candidates = {t for t in candidates if t.isalpha() and t.isupper() and len(t) <= 6}
    tested = get_tested_tokens()
    
    # Remove perma-blocked
    history = load_trial_history()
    perma_blocked = {t for t, h in history.items() if h.get('failures', 0) >= MAX_FAILURES}
    
    remaining = sorted(candidates - tested - perma_blocked)

    print(f"Untested tokens remaining: {len(remaining)}")
    print(f"Perma-blocked: {len(perma_blocked)}")
    for t in remaining:
        in_s = 'S' if t in short_bl else ' '
        in_l = 'L' if t in long_bl else ' '
        print(f"  {t:10s} [{in_s}{in_l}]")
    return remaining


def cmd_status():
    """Show current trial status for all batches."""
    short_bl, long_bl = load_blacklists()
    history = load_trial_history()
    print(f"SHORT_BLACKLIST: {len(short_bl)} tokens")
    print(f"LONG_BLACKLIST: {len(long_bl)} tokens")
    print(f"Perma-blocked: {sum(1 for h in history.values() if h.get('failures', 0) >= MAX_FAILURES)}")

    batches = parse_test_log()
    now = datetime.utcnow()

    for batch in batches:
        trial_start = batch['start']
        try:
            start_dt = datetime.strptime(trial_start, '%Y-%m-%d')
        except ValueError:
            continue
        trial_end = start_dt + timedelta(hours=TRIAL_HOURS)
        status = 'ACTIVE' if now < trial_end else 'COMPLETED'
        print(f"\nBatch {batch['num']}: {status} (started {trial_start}, {len(batch['tokens'])} tokens)")

        for token, info in sorted(batch['tokens'].items()):
            trades, wins, net_pnl = get_trial_outcomes(token, trial_start)
            wr = 100.0 * wins / trades if trades > 0 else 0
            failures = history.get(token, {}).get('failures', 0)
            fail_str = f" [{failures} fails]" if failures > 0 else ""
            print(f"  {token:8s} | {trades:3d} trades | {wr:5.1f}% WR | ${net_pnl:+7.2f} | {info['verdict']}{fail_str}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'evaluate':
        cmd_evaluate()
    elif cmd == 'pick':
        cmd_pick()
    elif cmd == 'start':
        batch = cmd_pick()
        if batch:
            print(f"\nTo start trial: remove these from blacklists in hermes_constants.py")
    elif cmd == 'status':
        cmd_status()
    elif cmd == 'remaining':
        cmd_remaining()
    else:
        print(f"Usage: {sys.argv[0]} [evaluate|pick|start|status|remaining]")
