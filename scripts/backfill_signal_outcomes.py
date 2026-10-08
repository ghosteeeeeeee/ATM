#!/usr/bin/env python3
"""Backfill signal_outcomes learning columns from PostgreSQL trades.

Trade-learning P0 completion: rows written before 2026-10-04 (or by the old
guardian path) lack exit_reason / mfe_pct / mae_pct / entry_rsi_band / regime /
signal_type / thesis_*. Join by trade_id and fill NULLs only.

Freeze-safe: data-layer only, no trading behavior.

Usage: python3 scripts/backfill_signal_outcomes.py [--days 90] [--dry-run]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB
from _secrets import BRAIN_DB_DICT


def _rsi_band(rsi):
    try:
        from signal_schema import rsi_band_label
        return rsi_band_label(rsi)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=90)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    import sqlite3
    import psycopg2

    # signal_outcomes lives in SQLite only — pull trade_ids first, then PG.
    sconn = sqlite3.connect(RUNTIME_DB, timeout=10)
    try:
        scur = sconn.cursor()
        scur.execute(
            """
            SELECT DISTINCT trade_id FROM signal_outcomes
            WHERE trade_id IS NOT NULL
              AND created_at > datetime('now', ?)
            """,
            (f'-{args.days} days',),
        )
        trade_ids = [r[0] for r in scur.fetchall()]
    finally:
        sconn.close()
    print(f"signal_outcomes trade_ids in window: {len(trade_ids)}")
    if not trade_ids:
        return 0

    pg = psycopg2.connect(**BRAIN_DB_DICT)
    try:
        cur = pg.cursor()
        cur.execute(
            """
            SELECT id, signal, exit_reason, mfe_pct, mae_pct, entry_rsi_14,
                   COALESCE(NULLIF(volatility_regime, ''), NULLIF(regime, '')),
                   confidence
            FROM trades
            WHERE status = 'closed'
              AND id = ANY(%s)
            """,
            (trade_ids,),
        )
        rows = cur.fetchall()
    finally:
        pg.close()

    def _f(v):
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    print(f"PG closed trades matching those ids: {len(rows)}")

    conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    try:
        c = conn.cursor()
        updated = 0
        for (tid, signal, exit_reason, mfe, mae, rsi, regime, conf) in rows:
            mfe, mae, conf = _f(mfe), _f(mae), _f(conf)
            c.execute(
                """
                SELECT signal_type, exit_reason, mfe_pct, mae_pct,
                       entry_rsi_band, regime, thesis_validated, thesis_mfe, confidence
                FROM signal_outcomes WHERE trade_id = ?
                """,
                (tid,),
            )
            so = c.fetchone()
            if not so:
                continue
            so_sig, so_er, so_mfe, so_mae, so_band, so_reg, so_tv, so_tm, so_conf = so
            new_sig = so_sig if so_sig and so_sig != 'unknown' else (signal or so_sig)
            new_er = so_er if so_er else exit_reason
            new_mfe = so_mfe if so_mfe is not None else mfe
            new_mae = so_mae if so_mae is not None else mae
            new_band = so_band if so_band else _rsi_band(rsi)
            new_reg = so_reg if so_reg else regime
            new_conf = so_conf if so_conf not in (None, 0) else conf
            new_tv = so_tv
            new_tm = so_tm
            if new_mfe is not None and new_tv is None:
                new_tv = 1 if float(new_mfe) > 0 else 0
                new_tm = round(float(new_mfe), 4)
            elif new_mfe is not None and new_tm is None:
                new_tm = round(float(new_mfe), 4)

            if (
                new_sig != so_sig
                or new_er != so_er
                or new_mfe != so_mfe
                or new_mae != so_mae
                or new_band != so_band
                or new_reg != so_reg
                or new_tv != so_tv
                or new_tm != so_tm
                or new_conf != so_conf
            ):
                updated += 1
                if args.dry_run:
                    print(f"  DRY trade_id={tid} {signal} er={new_er} mfe={new_mfe} band={new_band} reg={new_reg}")
                else:
                    c.execute(
                        """
                        UPDATE signal_outcomes
                        SET signal_type = ?, exit_reason = ?, mfe_pct = ?, mae_pct = ?,
                            entry_rsi_band = ?, regime = ?, thesis_validated = ?,
                            thesis_mfe = ?, confidence = COALESCE(confidence, ?)
                        WHERE trade_id = ?
                        """,
                        (
                            new_sig, new_er, new_mfe, new_mae, new_band, new_reg,
                            new_tv, new_tm, new_conf, tid,
                        ),
                    )
        if not args.dry_run:
            conn.commit()
        print(f"Updated (or would update) {updated} signal_outcomes rows")

        # Coverage report
        c.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN exit_reason IS NOT NULL THEN 1 ELSE 0 END),
                   SUM(CASE WHEN mfe_pct IS NOT NULL THEN 1 ELSE 0 END),
                   SUM(CASE WHEN entry_rsi_band IS NOT NULL THEN 1 ELSE 0 END),
                   SUM(CASE WHEN trade_id IS NOT NULL THEN 1 ELSE 0 END)
            FROM signal_outcomes
            """
        )
        n, er, mfe, band, tidn = c.fetchone()
        print(f"signal_outcomes total={n} exit_reason={er} mfe={mfe} rsi_band={band} has_trade_id={tidn}")
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
