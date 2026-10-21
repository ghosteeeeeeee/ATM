#!/usr/bin/env python3
"""shadow_mode_analysis.py — Comprehensive shadow-mode data analysis.

Analyzes shadow_trades.db for trends, winners, losers, and gate/filter impact.
Produces a full report with actionable insights.

Usage:
  python3 scripts/shadow_mode_analysis.py                    # Full analysis
  python3 scripts/shadow_mode_analysis.py --gates            # Gate/filter analysis only
  python3 scripts/shadow_mode_analysis.py --winners          # Winners/losers only
  python3 scripts/shadow_mode_analysis.py --exit-engines     # Exit engine comparison only
  python3 scripts/shadow_mode_analysis.py --regimes          # Regime analysis only
  python3 scripts/shadow_mode_analysis.py --tokens           # Token analysis only
  python3 scripts/shadow_mode_analysis.py --confidence       # Confidence analysis only
  python3 scripts/shadow_mode_analysis.py --rsi              # RSI analysis only
  python3 scripts/shadow_mode_analysis.py --hold-times       # Hold time analysis only
  python3 scripts/shadow_mode_analysis.py --flip-candidates  # Find flip candidates
  python3 scripts/shadow_mode_analysis.py --summary          # One-line summary

Output DB: brain/shadow_trades.db (read-only)
"""
import sys
import os
import sqlite3
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'shadow_trades.db')


def log(msg):
    print(msg, flush=True)


def get_db():
    conn = sqlite3.connect(SHADOW_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def full_analysis():
    """Run all analyses."""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("=" * 80)
        log("SHADOW MODE COMPREHENSIVE ANALYSIS")
        log("=" * 80)
        
        # Overall stats
        total = cur.execute("SELECT COUNT(*) FROM shadow_trades").fetchone()[0]
        closed = cur.execute("SELECT COUNT(*) FROM shadow_trades WHERE closed=1").fetchone()[0]
        
        r = cur.execute("""
            SELECT COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg,
              ROUND(AVG(mfe_pct),2) avg_mfe,
              ROUND(AVG(mae_pct),2) avg_mae
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
        """).fetchone()
        
        log(f"\nTotal signals: {total} | Closed: {closed} | With PnL: {r['n']}")
        log(f"Win Rate: {r['wr']}% | Total PnL: {r['total']}% | Avg PnL: {r['avg']}%")
        log(f"Avg MFE: {r['avg_mfe']}% | Avg MAE: {r['avg_mae']}%")
        
        # Direction
        log("\n--- DIRECTION ---")
        for r in cur.execute("""
            SELECT direction, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY direction
        """):
            log(f"  {r['direction']:5} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
        
        # Exit engines
        log("\n--- EXIT ENGINES ---")
        for r in cur.execute("""
            SELECT first_exit_engine, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND first_exit_engine IS NOT NULL
            GROUP BY first_exit_engine ORDER BY total DESC
        """):
            log(f"  {r['first_exit_engine']:25} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
        
        # Hold time
        log("\n--- HOLD TIME ---")
        for r in cur.execute("""
            SELECT CASE 
              WHEN first_exit_hold_minutes < 15 THEN '<15m'
              WHEN first_exit_hold_minutes < 30 THEN '15-30m'
              WHEN first_exit_hold_minutes < 60 THEN '30-60m'
              WHEN first_exit_hold_minutes < 120 THEN '1-2h'
              WHEN first_exit_hold_minutes < 240 THEN '2-4h'
              ELSE '>4h'
            END bucket, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY bucket ORDER BY bucket
        """):
            log(f"  {r['bucket']:8} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
        
        # Top winners
        log("\n--- TOP 15 WINNING SIGNALS (n>=10) ---")
        for r in cur.execute("""
            SELECT source, direction, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY source, direction HAVING COUNT(*) >= 10
            ORDER BY total DESC LIMIT 15
        """):
            log(f"  {r['source']:40} {r['direction']:5} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
        
        # Bottom losers
        log("\n--- BOTTOM 15 LOSING SIGNALS (n>=10) ---")
        for r in cur.execute("""
            SELECT source, direction, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY source, direction HAVING COUNT(*) >= 10
            ORDER BY total ASC LIMIT 15
        """):
            log(f"  {r['source']:40} {r['direction']:5} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
        
        # Gate analysis
        log("\n--- GATE IMPACT ---")
        for r in cur.execute("""
            SELECT gate_name, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades 
            WHERE closed=1 AND gate_blocked=1 AND gate_name IS NOT NULL AND net_pnl_pct IS NOT NULL
            GROUP BY gate_name HAVING COUNT(*) >= 10
            ORDER BY total
        """):
            verdict = "HELPING" if r['total'] < -50 else ("HURTING" if r['total'] > 50 else "NEUTRAL")
            log(f"  {r['gate_name']:30} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% {verdict}")
        
        # Confidence bands
        log("\n--- CONFIDENCE BANDS ---")
        for r in cur.execute("""
            SELECT CASE 
              WHEN confidence < 60 THEN '<60'
              WHEN confidence < 70 THEN '60-69'
              WHEN confidence < 80 THEN '70-79'
              ELSE '80+' 
            END band, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY band ORDER BY band
        """):
            log(f"  {r['band']:8} n={r['n']:5} WR={r['wr']:5.1f}% avg={r['avg']:+.3f}%")
        
        # RSI bands
        log("\n--- RSI BANDS ---")
        for r in cur.execute("""
            SELECT CASE 
              WHEN json_extract(context, '$.rsi_14') < 30 THEN '<30 (oversold)'
              WHEN json_extract(context, '$.rsi_14') < 40 THEN '30-40'
              WHEN json_extract(context, '$.rsi_14') < 50 THEN '40-50'
              WHEN json_extract(context, '$.rsi_14') < 60 THEN '50-60'
              WHEN json_extract(context, '$.rsi_14') < 70 THEN '60-70'
              ELSE '>70 (overbought)'
            END band, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL 
              AND json_extract(context, '$.rsi_14') IS NOT NULL
            GROUP BY band ORDER BY band
        """):
            log(f"  {r['band']:20} n={r['n']:5} WR={r['wr']:5.1f}% avg={r['avg']:+.3f}%")
        
        # Direction x Regime
        log("\n--- DIRECTION x REGIME ---")
        for r in cur.execute("""
            SELECT direction, json_extract(context, '$.vol_regime') vol, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY direction, vol HAVING COUNT(*) >= 50
            ORDER BY avg DESC
        """):
            log(f"  {r['direction']:5} {r['vol']:10} n={r['n']:5} WR={r['wr']:5.1f}% avg={r['avg']:+.3f}%")
        
        # Tokens
        log("\n--- TOP 10 TOKENS (n>=20) ---")
        for r in cur.execute("""
            SELECT token, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY token HAVING COUNT(*) >= 20
            ORDER BY total DESC LIMIT 10
        """):
            log(f"  {r['token']:10} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}%")
        
        log("\n--- BOTTOM 10 TOKENS (n>=20) ---")
        for r in cur.execute("""
            SELECT token, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY token HAVING COUNT(*) >= 20
            ORDER BY total ASC LIMIT 10
        """):
            log(f"  {r['token']:10} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}%")
        
        # Shadow bypass analysis (T directive 2026-10-21)
        log("\n--- SHADOW BYPASS SIGNALS (disabled signals being simulated) ---")
        for r in cur.execute("""
            SELECT source, direction, 
              json_extract(context, '$.shadow_bypass_stage') stage,
              COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg,
              json_extract(context, '$.shadow_bypass_reason') reason
            FROM shadow_trades 
            WHERE closed=1 AND net_pnl_pct IS NOT NULL 
              AND json_extract(context, '$.shadow_bypass') = 1
            GROUP BY source, direction, stage
            ORDER BY stage, total DESC
        """):
            log(f"  Stage {r['stage'] or '?'} | {r['source']:30} {r['direction']:5} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
            if r['reason']:
                log(f"    Reason: {r['reason'][:80]}")
        
        # Flip candidates
        log("\n--- FLIP CANDIDATES (WR<35%, n>=30) ---")
        for r in cur.execute("""
            SELECT source, direction, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(mfe_pct),2) avg_mfe,
              ROUND(AVG(mae_pct),2) avg_mae
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY source, direction 
            HAVING COUNT(*) >= 30 AND 100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*) < 35
            ORDER BY total ASC LIMIT 10
        """):
            log(f"  {r['source']:40} {r['direction']:5} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% MFE={r['avg_mfe']:+.1f}% MAE={r['avg_mae']:+.1f}%")
        
        log("\n" + "=" * 80)
    finally:
        conn.close()


def gate_analysis():
    """Gate/filter analysis only."""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("=" * 80)
        log("GATE/FILTER ANALYSIS")
        log("=" * 80)
        
        log("\n--- GATE IMPACT (which gates are helping vs hurting?) ---")
        log(f"  {'Gate':30} {'n':>6} {'WR':>6} {'Total':>10} {'Avg':>10} {'Verdict':>12}")
        log("-" * 80)
        
        for r in cur.execute("""
            SELECT gate_name, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades 
            WHERE closed=1 AND gate_blocked=1 AND gate_name IS NOT NULL AND net_pnl_pct IS NOT NULL
            GROUP BY gate_name HAVING COUNT(*) >= 10
            ORDER BY total
        """):
            verdict = "HELPING" if r['total'] < -50 else ("HURTING" if r['total'] > 50 else "NEUTRAL")
            log(f"  {r['gate_name']:30} {r['n']:6} {r['wr']:5.1f}% {r['total']:+10.1f}% {r['avg']:+10.3f}% {verdict:>12}")
        
        # Single vs multi-source
        log("\n--- SINGLE vs MULTI-SOURCE ---")
        for r in cur.execute("""
            SELECT CASE 
              WHEN source LIKE '%,%' THEN 'Multi-source'
              ELSE 'Single-source'
            END as st, COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
            GROUP BY st
        """):
            log(f"  {r['st']:15} n={r['n']:5} WR={r['wr']:5.1f}% total={r['total']:+8.1f}% avg={r['avg']:+.3f}%")
        
        log("\n" + "=" * 80)
    finally:
        conn.close()


def summary():
    """One-line summary."""
    conn = get_db()
    try:
        cur = conn.cursor()
        r = cur.execute("""
            SELECT COUNT(*) n,
              ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
              ROUND(SUM(net_pnl_pct),1) total,
              ROUND(AVG(net_pnl_pct),3) avg
            FROM shadow_trades WHERE closed=1 AND net_pnl_pct IS NOT NULL
        """).fetchone()
        log(f"Shadow: {r['n']} closed, WR={r['wr']}%, total={r['total']}%, avg={r['avg']}%")
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description='Shadow-Mode Analysis')
    ap.add_argument('--full', action='store_true', help='Full analysis (default)')
    ap.add_argument('--gates', action='store_true', help='Gate/filter analysis')
    ap.add_argument('--summary', action='store_true', help='One-line summary')
    args = ap.parse_args()
    
    if args.summary:
        summary()
    elif args.gates:
        gate_analysis()
    else:
        full_analysis()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
