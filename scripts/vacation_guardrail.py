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

# ── Thresholds (CEO 2026-10-14) ─────────────────────────────────────────────
PNL_24H_PAUSE = -3.00      # Auto-pause if 24h PnL < this
WR_48H_ESCALATE = 40.0     # Escalate if 48h WR < this (after 48h soak)
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

        data = {
            'pnl_24h': float(pnl_24h), 'n_24h': n_24h, 'wr_24h': float(wr_24h or 0),
            'pnl_48h': float(pnl_48h), 'n_48h': n_48h, 'wr_48h': float(wr_48h or 0),
            'checked_at': datetime.now(timezone.utc).isoformat(),
        }

        should_pause = data['pnl_24h'] < PNL_24H_PAUSE
        should_escalate = data['wr_48h'] < WR_48H_ESCALATE and data['n_48h'] >= 30

        return should_pause, should_escalate, data
    finally:
        conn.close()


def pause_trading(reason):
    """Disable live trading via kill switch."""
    try:
        config = {'live_trading': False, 'reason': reason,
                  'ts': int(datetime.now(timezone.utc).timestamp())}
        with open(KILL_SWITCH_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        log(f"🛑 [VACATION-GUARDRAIL] TRADING PAUSED: {reason}")
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
        f"48h: {data['n_48h']}T {data['wr_48h']}% ${data['pnl_48h']:+.2f}")

    if should_pause:
        reason = f"24h PnL ${data['pnl_24h']:.2f} < ${PNL_24H_PAUSE:.2f} threshold"
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
