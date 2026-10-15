#!/usr/bin/env python3
"""
vacation_guardrail.py — Hard safety net for T-on-vacation mode.

Checks 24h PnL and 48h WR. Auto-pauses live trading if thresholds breached.
Runs via systemd timer every 30 minutes.

CEO mandate (2026-10-14): "Do not leave without it. It is the only hard
safety net — the day-14 kill criteria don't exist as code until #10 ships."
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2
from paths import HERMES_DATA
from hermes_log import log

# ── Thresholds (CEO 2026-10-14 + own-conclusions gap fix) ───────────────────
PNL_24H_PAUSE = -3.00      # Auto-pause if 24h PnL < this
WR_48H_ESCALATE = 40.0     # Escalate if 48h WR < this (after 48h soak)
WR_7D_PAUSE = 35.0         # Auto-pause if 7d WR < this (plan kill criterion — was NOT coded)
WR_7D_MIN_TRADES = 50      # Need 50+ trades before 7d WR is meaningful
KILL_SWITCH_PATH = os.path.join(WWW_DATA := '/var/www/hermes/data', 'hype_live_trading.json')
ALERT_PATH = os.path.join(HERMES_DATA, '..', 'automation', 'ceo', 'vacation_alerts.json')


def check_guardrails():
    """Check PnL and WR thresholds. Returns (should_pause, should_escalate, data)."""
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    try:
        # 24h PnL
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(pnl_usdt), 0), COUNT(*),
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1)
            FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
        """)
        pnl_24h, n_24h, wr_24h = cur.fetchone()

        # 48h WR
        cur.execute("""
            SELECT COALESCE(SUM(pnl_usdt), 0), COUNT(*),
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1)
            FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '48 hours'
        """)
        pnl_48h, n_48h, wr_48h = cur.fetchone()

        # 7d WR (plan kill criterion — own-conclusions gap fix)
        cur.execute("""
            SELECT COALESCE(SUM(pnl_usdt), 0), COUNT(*),
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1)
            FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '7 days'
        """)
        pnl_7d, n_7d, wr_7d = cur.fetchone()

        data = {
            'pnl_24h': float(pnl_24h), 'n_24h': n_24h, 'wr_24h': float(wr_24h or 0),
            'pnl_48h': float(pnl_48h), 'n_48h': n_48h, 'wr_48h': float(wr_48h or 0),
            'pnl_7d': float(pnl_7d), 'n_7d': n_7d, 'wr_7d': float(wr_7d or 0),
            'checked_at': datetime.now(timezone.utc).isoformat(),
        }

        should_pause = (data['pnl_24h'] < PNL_24H_PAUSE or
                       (data['wr_7d'] < WR_7D_PAUSE and data['n_7d'] >= WR_7D_MIN_TRADES))
        should_escalate = data['wr_48h'] < WR_48H_ESCALATE and data['n_48h'] >= 30

        return should_pause, should_escalate, data
    finally:
        conn.close()


def pause_trading(reason):
    """Disable live trading: close positions + stop pipeline timers.

    BUG-HUNTER BLOCKER FIX (2026-10-14): the JSON write alone was a no-op —
    is_live_trading_enabled() reads only the static constant (commit 28215e7e
    removed JSON consultation due to ghost trades). This fix uses
    disable_live_trading() (closes HL positions + saves flags) AND stops
    the pipeline/decider systemd timers so no new trades can open.
    """
    import subprocess
    try:
        # 1. Close all open HL positions + save flags
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hyperliquid_exchange import disable_live_trading
        result = disable_live_trading()
        closed = result.get('closed_positions', [])
        log(f"🛑 [VACATION-GUARDRAIL] Closed {len(closed)} HL positions: {closed}")

        # 2. Stop pipeline + decider timers (prevent new trades)
        for timer in ['hermes-pipeline.timer', 'hermes-decider.timer']:
            r = subprocess.run(['systemctl', 'stop', timer],
                             capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                log(f"🛑 [VACATION-GUARDRAIL] Stopped {timer}")
            else:
                log(f"⚠️ [VACATION-GUARDRAIL] Could not stop {timer}: {r.stderr.strip()}", 'WARN')

        # 3. Also stop the guardrail timer itself (avoid re-trigger)
        subprocess.run(['systemctl', 'stop', 'hermes-vacation-guardrail.timer'],
                      capture_output=True, timeout=10)

        log(f"🛑 [VACATION-GUARDRAIL] TRADING PAUSED (positions closed + timers stopped): {reason}")
        return True
    except Exception as e:
        log(f"❌ [VACATION-GUARDRAIL] Failed to pause: {e}", 'ERROR')
        return False


def write_alert(level, message, data):
    """Write alert to vacation_alerts.json for CEO/T to read."""
    try:
        os.makedirs(os.path.dirname(ALERT_PATH), exist_ok=True)
        alerts = []
        if os.path.exists(ALERT_PATH):
            with open(ALERT_PATH) as f:
                alerts = json.load(f)
        alerts.append({
            'level': level, 'message': message, 'data': data,
            'ts': datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 50 alerts
        alerts = alerts[-50:]
        with open(ALERT_PATH, 'w') as f:
            json.dump(alerts, f, indent=2)
    except Exception:
        pass


def main():
    should_pause, should_escalate, data = check_guardrails()

    log(f"📊 [VACATION-GUARDRAIL] 24h: {data['n_24h']}T {data['wr_24h']}% ${data['pnl_24h']:+.2f} | "
        f"48h: {data['n_48h']}T {data['wr_48h']}% ${data['pnl_48h']:+.2f} | "
        f"7d: {data['n_7d']}T {data['wr_7d']}% ${data['pnl_7d']:+.2f}")

    if should_pause:
        reasons = []
        if data['pnl_24h'] < PNL_24H_PAUSE:
            reasons.append(f"24h PnL ${data['pnl_24h']:.2f} < ${PNL_24H_PAUSE:.2f}")
        if data['wr_7d'] < WR_7D_PAUSE and data['n_7d'] >= WR_7D_MIN_TRADES:
            reasons.append(f"7d WR {data['wr_7d']}% < {WR_7D_PAUSE}% ({data['n_7d']}T)")
        reason = "; ".join(reasons)
        pause_trading(reason)
        write_alert('CRITICAL', f'TRADING PAUSED: {reason}', data)
    elif should_escalate:
        reason = f"48h WR {data['wr_48h']}% < {WR_48H_ESCALATE}% with {data['n_48h']} trades"
        log(f"⚠️ [VACATION-GUARDRAIL] ESCALATE: {reason}")
        write_alert('WARNING', f'Early escalation: {reason}', data)
    else:
        write_alert('INFO', 'Guardrails OK', data)


if __name__ == '__main__':
    main()
