#!/usr/bin/env python3
"""
Post-run report for candle_predictor.py.

Parses /var/log/candle-predictor.log to find the most recent run's start
boundary, then queries predictions.db to summarize accuracy, errors, and
DB-vs-log cross-check. Prints a single JSON object to stdout.

Usage:
    python3 scripts/post_run_report.py
    python3 scripts/post_run_report.py --pretty

Designed to be re-runnable by the tuner agent and any cron job that wants
a deterministic accuracy snapshot after a candle_predictor run. Safe to
run while the predictor is mid-flight — the boundary detection just picks
the last "Candle Predictor Starting" header that has appeared so far.

Reads:
    /var/log/candle-predictor.log
    /root/.hermes/data/predictions.db
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

LOG_PATH = Path("/var/log/candle-predictor.log")
DB_PATH = Path("/root/.hermes/data/predictions.db")
LOCK_PATH = Path("/tmp/candle-predictor.lock")

START_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[INFO\] =+ Candle Predictor Starting",
    re.M,
)
SUMMARY_RE = re.compile(r"=== Predicted (\d+) tokens, (\d+) inverted ===")
OVERALL_RE = re.compile(r"Overall accuracy:\s*(\d+)/(\d+)\s*=\s*([\d.]+)%")
INVERTED_RE = re.compile(r"Inverted predictions:\s*(\d+)/(\d+)\s*=\s*([\d.]+)% accuracy")


def _parse_log():
    text = LOG_PATH.read_text(errors="replace")
    starts = list(START_RE.finditer(text))
    if not starts:
        return None, None, text
    boundary = starts[-1]
    return boundary.group("ts"), text[boundary.start():], text


def _db_stats(start_epoch: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        run = conn.execute(
            """SELECT COUNT(*) n, COALESCE(SUM(was_inverted), 0) inv,
                      MIN(prediction_time) minpt, MAX(prediction_time) maxpt
               FROM predictions WHERE prediction_time >= ?""",
            (start_epoch,),
        ).fetchone()
        dirs = conn.execute(
            """SELECT direction, COUNT(*) n FROM predictions
               WHERE prediction_time >= ? GROUP BY direction""",
            (start_epoch,),
        ).fetchall()
        return {
            "total": int(run["n"] or 0),
            "inverted": int(run["inv"] or 0),
            "min_epoch": run["minpt"],
            "max_epoch": run["maxpt"],
            "directions": {r["direction"]: int(r["n"]) for r in dirs},
        }
    finally:
        conn.close()


def _accuracy_window(n: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """SELECT COUNT(*) n, SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) good
               FROM (
                   SELECT correct FROM predictions
                   WHERE correct IS NOT NULL
                   ORDER BY prediction_time DESC, id DESC LIMIT ?
               )""",
            (n,),
        ).fetchone()
        total = int(row["n"] or 0)
        good = int(row["good"] or 0)
        return {
            "n": total,
            "correct": good,
            "accuracy": round(100 * good / total, 1) if total else None,
        }
    finally:
        conn.close()


def _accuracy_split(n: int, col: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""SELECT {col} k, COUNT(*) n,
                       SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) good
                FROM (
                    SELECT {col}, correct FROM predictions
                    WHERE correct IS NOT NULL
                    ORDER BY prediction_time DESC, id DESC LIMIT ?
                )
                GROUP BY {col} ORDER BY {col}""",
            (n,),
        ).fetchall()
    finally:
        conn.close()
    out = {}
    for r in rows:
        key = str(r["k"])
        if col == "was_inverted":
            key = "INVERTED" if int(r["k"] or 0) else "NORMAL"
        total = int(r["n"])
        good = int(r["good"] or 0)
        out[key] = {
            "n": total,
            "correct": good,
            "accuracy": round(100 * good / total, 1) if total else None,
        }
    return out


def _trend_200():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT correct FROM predictions WHERE correct IS NOT NULL
               ORDER BY prediction_time DESC, id DESC LIMIT 400"""
        ).fetchall()
    finally:
        conn.close()
    vals = [int(r["correct"]) for r in rows]

    def acc(v):
        return round(100 * sum(v) / len(v), 1) if v else None

    return {
        "latest_200": {"n": len(vals[:200]), "accuracy": acc(vals[:200])},
        "previous_200": {"n": len(vals[200:400]), "accuracy": acc(vals[200:400])},
    }


def build_report():
    start_ts, block, _ = _parse_log()
    if not start_ts:
        return {"error": "No run start found in log", "log_path": str(LOG_PATH)}

    summary = SUMMARY_RE.search(block or "")
    overall = OVERALL_RE.search(block or "")
    inverted = INVERTED_RE.search(block or "")

    errors = [ln for ln in (block or "").splitlines() if "[ERROR]" in ln]
    warns = [ln for ln in (block or "").splitlines() if "[WARN]" in ln]
    low_acc = [ln for ln in (block or "").splitlines() if "very low accuracy" in ln]
    missing_price = [ln for ln in (block or "").splitlines() if "no price data" in ln]

    start_epoch = int(time.mktime(time.strptime(start_ts, "%Y-%m-%d %H:%M:%S")))
    db_run = _db_stats(start_epoch)

    return {
        "start": start_ts,
        "summary": (
            {
                "predicted": int(summary.group(1)),
                "inverted": int(summary.group(2)),
            }
            if summary
            else None
        ),
        "startup_baseline": {
            "overall": (
                {
                    "correct": int(overall.group(1)),
                    "total": int(overall.group(2)),
                    "accuracy": float(overall.group(3)),
                }
                if overall
                else None
            ),
            "inverted": (
                {
                    "correct": int(inverted.group(1)),
                    "total": int(inverted.group(2)),
                    "accuracy": float(inverted.group(3)),
                }
                if inverted
                else None
            ),
        },
        "log_health": {
            "errors": len(errors),
            "warnings": len(warns),
            "low_accuracy_skips": len(low_acc),
            "missing_price_skips": len(missing_price),
            "error_lines": errors[:20],
            "warning_lines": warns[:20],
        },
        "db_run": db_run,
        "accuracy_windows": {str(n): _accuracy_window(n) for n in (50, 200, 500, 1000)},
        "latest_200_direction": _accuracy_split(200, "direction"),
        "latest_200_inversion": _accuracy_split(200, "was_inverted"),
        "trend_200_blocks": _trend_200(),
        "lock_exists": LOCK_PATH.exists(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pretty", action="store_true", help="Indent JSON output")
    args = ap.parse_args()
    report = build_report()
    indent = 2 if args.pretty else None
    json.dump(report, sys.stdout, indent=indent)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()