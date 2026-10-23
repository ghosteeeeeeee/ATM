#!/usr/bin/env python3
"""trend_ownership_2026-10-23.py — selfcheck for brain_auditor #107's momentum_cache.trend fix.

Before the fix, 15m_regime_scanner.py:297 and 4h_regime_scanner.py:289 both wrote
momentum_cache.trend with different thresholds on different timeframes; last writer won
and the 15m scanner won ~96x/day. This asserts the ownership split holds in the source
AND in the live SQL behaviour.

Usage: python3 brain/analysis/trend_ownership_2026-10-23.py --selfcheck
"""

import ast
import os
import sys

sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT  # noqa: E402

SCRIPTS = '/root/.hermes/scripts'


def writers_of_trend():
    """Parse both scanners; return (15m_writes_trend: bool, 4h_writes_trend: bool)."""
    out = {}
    for name in ('15m_regime_scanner.py', '4h_regime_scanner.py'):
        src = open(os.path.join(SCRIPTS, name)).read()
        tree = ast.parse(src)
        hits = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and 'momentum_cache' in node.value:
                sql = node.value
                if 'INSERT INTO momentum_cache' in sql and 'trend' in sql.split('ON CONFLICT')[0]:
                    hits += 1
                if 'ON CONFLICT' in sql:
                    set_clause = sql.split('ON CONFLICT')[1]
                    if 'trend' in set_clause:
                        hits += 1
        out[name] = hits
    return out


def live_roundtrip():
    """Insert a scratch row, run the 15m writer's SQL shape, assert trend is untouched."""
    import psycopg2
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    scratch = '__TREND_OWNERSHIP_TEST__'
    try:
        cur.execute("DELETE FROM momentum_cache WHERE token=%s", (scratch,))
        cur.execute(
            "INSERT INTO momentum_cache (token, slope_4h, regime_4h, trend, updated_at) "
            "VALUES (%s, %s, %s, %s, NOW())",
            (scratch, 0.5, 'LONG_BIAS', 'uptrend'))
        # the 15m writer's exact post-fix statement shape
        cur.execute(
            """
            INSERT INTO momentum_cache (token, slope_15m, regime_15m, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (token) DO UPDATE SET
                slope_15m = EXCLUDED.slope_15m,
                regime_15m = EXCLUDED.regime_15m,
                updated_at = EXCLUDED.updated_at
            """, (scratch, -0.2, 'SHORT_BIAS'))
        cur.execute(
            "SELECT trend, regime_4h, regime_15m FROM momentum_cache WHERE token=%s", (scratch,))
        trend, r4, r15 = cur.fetchone()
        assert trend == 'uptrend', f'4h trend was clobbered: {trend!r}'
        assert r4 == 'LONG_BIAS', f'4h regime clobbered: {r4!r}'
        assert r15 == 'SHORT_BIAS', f'15m regime not written: {r15!r}'
        # and the 4h writer still updates trend
        cur.execute(
            """
            INSERT INTO momentum_cache (token, slope_4h, regime_4h, trend, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (token) DO UPDATE SET
                slope_4h = EXCLUDED.slope_4h,
                regime_4h = EXCLUDED.regime_4h,
                trend = EXCLUDED.trend,
                updated_at = EXCLUDED.updated_at
            """, (scratch, -0.9, 'SHORT_BIAS', 'downtrend'))
        cur.execute("SELECT trend, regime_4h FROM momentum_cache WHERE token=%s", (scratch,))
        trend2, r4b = cur.fetchone()
        assert trend2 == 'downtrend' and r4b == 'SHORT_BIAS', (trend2, r4b)
        conn.commit()
    finally:
        cur.execute("DELETE FROM momentum_cache WHERE token=%s", (scratch,))
        conn.commit()
        cur.close()
        conn.close()


def selfcheck():
    hits = writers_of_trend()
    assert hits['15m_regime_scanner.py'] == 0, \
        f"15m scanner still writes momentum_cache.trend: {hits}"
    assert hits['4h_regime_scanner.py'] >= 1, \
        f"4h scanner no longer owns momentum_cache.trend: {hits}"
    live_roundtrip()
    print(f"SELFCHECK PASS — writers={hits}; live round-trip: 15m write preserves 4h trend")
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck())
