#!/usr/bin/env python3
"""Blacklist Tester — evaluate trial results, update blacklists, start new batches.

Runs as: python3 automation/blacklist_tester.py [--evaluate] [--start-batch N] [--dry-run]

--evaluate:       Evaluate completed trials (default if no args)
--start-batch N:  Start batch N of new trials
--dry-run:        Print changes without modifying files
"""
import sys
import os
import re
import sqlite3
from datetime import datetime, timedelta

HERMES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTANTS_PATH = os.path.join(HERMES_ROOT, 'scripts', 'hermes_constants.py')
LOG_PATH = os.path.join(HERMES_ROOT, 'automation', 'blacklist_test_log.md')
RUNTIME_DB = os.path.join(HERMES_ROOT, 'data', 'signals_hermes_runtime.db')

# Verdict thresholds
MIN_TRADES = 3
KEEP_WR = 40
KEEP_PNL_MIN = -2.0
REBLACKLIST_WR = 30
REBLACKLIST_PNL = -5.0
TRIAL_HOURS = 48

# Tokens to NEVER test (structural issues)
SKIP_TOKENS = {'BTC', 'ETH', 'SOL'}  # too large, spread issues

# Batch 1 tokens (already in trial)
BATCH_1 = {'UNI', 'LINEA', 'TIA', 'TURBO', 'BABY', 'BLUR', 'FET', 'ORDI', 'PEOPLE', 'AIXBT', 'ZK', 'CAKE', 'STBL'}

# Batch 2 candidate list (from hermes_constants additional blacklist, ordered by priority)
BATCH_2_CANDIDATES = [
    'COMP', 'CRV', 'DYDX', 'FTM', 'GALA', 'IMX', 'SAND',
    'NEAR', 'DOT', 'ICP', 'ATOM', 'INJ', 'FIL', 'ETC',
    'ARB', 'OP', 'LDO', 'APT', 'SEI',
]

# Additional blacklisted tokens to test in later batches (from SHORT_BLACKLIST)
ADDITIONAL_CANDIDATES = [
    'MET', 'DASH', 'GRIFFAIN', 'BRETT', 'XLM', 'SNX', 'NIL',
    'IP', 'TRB', 'ETHFI', 'EIGEN', 'S', 'VVV', 'SUI',
    'LAYER', 'BERA', 'DYM', 'MAVIA', 'MEME', 'INIT', 'SOPH',
    'XAI', 'ZEC', 'GAS', 'BLAST', 'MELANIA', 'ZETA', 'SPX',
    'DOGE', 'ARK', 'RUNE', 'AR', 'TST', 'NXPC', 'TRUMP',
    'CELO', 'ACE', 'YZY', 'ZEREBRO', 'WLFI', 'HBAR', 'MEGA',
    'MEW', 'XPL', 'ZRO', 'NEO', 'GMT', 'FTT', 'HYPE',
    'YGG', 'IO', 'USUAL', 'FOGO', 'POL', 'DOOD', 'SYRUP',
    'POPCAT', 'VIRTUAL', 'FARTCOIN', 'RENDER', 'WLD', 'PORT3',
    'BOME', 'USTC', 'RSR', 'MINA', 'ENA', 'PENGU', 'CFX',
    'KNEIRO', 'SUSHI', 'BANANA', 'KPEPE', 'GRASS', 'MON',
    'BIGTIME', 'PUMP', 'CHIP', 'ZORA', 'ONDO', 'CASHCAT',
    'LTC', 'SKY', '2Z', 'MERL', 'GRAM', 'ADA', 'NOT',
    # LONG_BLACKLIST only (not in SHORT_BLACKLIST):
    'AERO', 'CHILLGUY', 'LIT', 'ANIME',
]


def load_blacklists():
    """Parse SHORT_BLACKLIST and LONG_BLACKLIST from hermes_constants.py."""
    with open(CONSTANTS_PATH, 'r') as f:
        content = f.read()

    def extract_set(var_name):
        # Find the set definition — handle multi-line with comments
        pattern = rf'{var_name}\s*=\s*\{{(.*?)\}}'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return set()
        raw = match.group(1)
        # Extract quoted strings
        return set(re.findall(r"'([A-Z0-9_]+)'", raw))

    short = extract_set('SHORT_BLACKLIST')
    long = extract_set('LONG_BLACKLIST')
    return short, long


def get_trial_outcomes(token, trial_start):
    """Query signal_outcomes for a token since trial_start."""
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as trades,
               SUM(is_win) as wins,
               SUM(pnl_usdt) as total_pnl,
               ROUND(100.0 * SUM(is_win) / COUNT(*), 1) as wr
        FROM signal_outcomes
        WHERE token = ? AND created_at >= ?
    """, (token, trial_start))
    row = cur.fetchone()
    conn.close()
    if row and row[0] > 0:
        return {
            'trades': row[0],
            'wins': row[1] or 0,
            'total_pnl': row[2] or 0.0,
            'wr': row[3] or 0.0,
        }
    return None


def evaluate_verdict(stats):
    """Apply verdict logic to trial stats."""
    if stats is None or stats['trades'] < MIN_TRADES:
        return 'INSUFFICIENT_DATA'
    if stats['wr'] >= KEEP_WR and stats['total_pnl'] > KEEP_PNL_MIN:
        return 'KEEP'
    if stats['wr'] < REBLACKLIST_WR or stats['total_pnl'] < REBLACKLIST_PNL:
        return 'RE-BLACKLIST'
    if 30 <= stats['wr'] < 40:
        return 'EXTEND'
    # Edge case: WR 40%+ but PnL <= -2% — still bad
    return 'RE-BLACKLIST'


def evaluate_batch1():
    """Evaluate batch 1 trials (started 2026-08-01)."""
    trial_start = '2026-08-01 12:55'
    results = []
    for token in sorted(BATCH_1):
        stats = get_trial_outcomes(token, trial_start)
        verdict = evaluate_verdict(stats)
        results.append({
            'token': token,
            'trial_start': trial_start,
            'trades': stats['trades'] if stats else 0,
            'wr': stats['wr'] if stats else 0,
            'total_pnl': stats['total_pnl'] if stats else 0,
            'verdict': verdict,
        })
    return results


def pick_batch2():
    """Pick next 20 tokens to test, excluding already-tested and structural skips."""
    # Get tokens already in trial or previously tested
    tested = BATCH_1.copy()
    # Filter candidates
    candidates = [t for t in BATCH_2_CANDIDATES if t not in tested and t not in SKIP_TOKENS]
    return candidates[:20]


def update_log(results, batch_num=None, trial_start=None, mode='evaluate'):
    """Append results to blacklist_test_log.md."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    lines = []
    if mode == 'evaluate' and results:
        lines.append(f"\n## Batch 1 — Evaluated {now}\n")
        lines.append("| Token | Trades | WR | PnL | Verdict |")
        lines.append("|-------|--------|-----|-----|---------|")
        for r in results:
            lines.append(f"| {r['token']} | {r['trades']} | {r['wr']}% | ${r['total_pnl']:.2f} | {r['verdict']} |")
        # Summary
        keep = [r for r in results if r['verdict'] == 'KEEP']
        rebl = [r for r in results if r['verdict'] == 'RE-BLACKLIST']
        ext = [r for r in results if r['verdict'] == 'EXTEND']
        insuf = [r for r in results if r['verdict'] == 'INSUFFICIENT_DATA']
        lines.append(f"\n**Summary:** {len(keep)} KEEP, {len(rebl)} RE-BLACKLIST, {len(ext)} EXTEND, {len(insuf)} INSUFFICIENT_DATA\n")
    elif mode == 'start_batch' and results:
        lines.append(f"\n## Batch {batch_num} — Started {now} ({TRIAL_HOURS}h trial)\n")
        lines.append("| Token | Trial Start | Verdict |")
        lines.append("|-------|-------------|---------|")
        for r in results:
            lines.append(f"| {r['token']} | {trial_start} | PENDING |")
    return '\n'.join(lines)


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    evaluate = '--evaluate' in args or not any(a.startswith('--start-batch') for a in args)
    start_batch = None
    for i, a in enumerate(args):
        if a == '--start-batch' and i + 1 < len(args):
            start_batch = int(args[i + 1])

    short_bl, long_bl = load_blacklists()

    if evaluate:
        print("=== Batch 1 Evaluation ===")
        results = evaluate_batch1()
        for r in results:
            flag = '✓' if r['verdict'] == 'KEEP' else '✗' if r['verdict'] == 'RE-BLACKLIST' else '~'
            print(f"  {flag} {r['token']:6s}  trades={r['trades']:3d}  WR={r['wr']:5.1f}%  PnL=${r['total_pnl']:+.2f}  → {r['verdict']}")

        keep = [r['token'] for r in results if r['verdict'] == 'KEEP']
        rebl = [r['token'] for r in results if r['verdict'] == 'RE-BLACKLIST']
        ext = [r['token'] for r in results if r['verdict'] == 'EXTEND']

        print(f"\nKEEP (remove from blacklist): {keep or 'none'}")
        print(f"RE-BLACKLIST (add back): {rebl}")
        print(f"EXTEND (keep in trial): {ext}")

        if not dry_run:
            log_entry = update_log(results, mode='evaluate')
            with open(LOG_PATH, 'a') as f:
                f.write(log_entry)
            print(f"\nLog updated: {LOG_PATH}")

    if start_batch is not None:
        print(f"\n=== Starting Batch {start_batch} ===")
        batch_tokens = pick_batch2()
        trial_start = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        print(f"Tokens to trial ({len(batch_tokens)}): {batch_tokens}")
        print(f"Trial start: {trial_start}")
        print(f"These tokens will be REMOVED from both SHORT_BLACKLIST and LONG_BLACKLIST.")

        if not dry_run:
            log_entry = update_log(batch_tokens, batch_num=start_batch, trial_start=trial_start, mode='start_batch')
            with open(LOG_PATH, 'a') as f:
                f.write(log_entry)
            print(f"Log updated: {LOG_PATH}")
            print("\nACTION REQUIRED: Manually update hermes_constants.py to remove these tokens from blacklists.")
        else:
            print("(dry-run — no files modified)")


if __name__ == '__main__':
    main()
