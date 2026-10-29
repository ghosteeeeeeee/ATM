#!/usr/bin/env python3
"""Self-check for the brain_auditor #196 ship: brain.py close now stamps
mfe_pct/mae_pct at close time (was: NULL until the nightly
cell_stats.backfill_mfe_mae, up to a 24h window that made arm-rate KPIs count
trail winners as unarmed).

Three assertions:
  1. Formula identity — the mfe/mae expressions in brain.py's close UPDATE are
     byte-equivalent to cell_stats.backfill_mfe_mae's (same peak source, same
     rounding, same guards) after whitespace normalization.
  2. Round-trip — run brain.py's UPDATE body against a temp table of fixtures:
     LONG and SHORT produce the hand-computable values; a row with a zero peak
     stays NULL; a row that already carries mfe_pct keeps it (COALESCE).
  3. Source guard — brain.py really writes these columns in the same UPDATE
     that sets status='closed' (i.e. one statement, not a second window).

Run: python3 brain/analysis/mfe_write_at_close_2026-10-29.py --selfcheck
"""
import os
import re
import sys

BRAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                     'scripts', 'brain.py')
CELL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                    'scripts', 'cell_stats.py')


def _norm(sql):
    return re.sub(r'\s+', ' ', sql).strip()


def extract_close_update(path):
    src = open(path).read()
    # first cur.execute(""" UPDATE trades SET ... """) inside _close_trade_impl
    m = re.search(r'UPDATE trades SET\s+exit_price.*?WHERE id = %s AND status = \'open\'',
                  src, re.S)
    assert m, 'could not locate the close UPDATE in brain.py'
    return m.group(0)


def extract_backfill_update(path):
    src = open(path).read()
    m = re.search(r'UPDATE trades SET\s+mfe_pct = CASE direction.*?'
                  r"\(\(direction='LONG' AND highest_price > 0 AND lowest_price > 0\)\s*"
                  r"OR \(direction='SHORT' AND highest_price > 0 AND lowest_price > 0\)\)",
                  src, re.S)
    assert m, 'could not locate the backfill UPDATE in cell_stats.py'
    return m.group(0)


def field_expr(update_sql, col):
    m = re.search(re.escape(col) + r'\s*=\s*(COALESCE\([^;]*?\))\s*,', update_sql, re.S)
    if not m:
        m = re.search(re.escape(col) + r'\s*=\s*(COALESCE\([^;]*?\))\s*(?:,|\n\s*WHERE)',
                      update_sql, re.S)
    assert m, f'{col} assignment not found'
    return _norm(m.group(1))


def test_formula_identity():
    close_sql = extract_close_update(BRAIN)
    backfill_sql = extract_backfill_update(CELL)

    for col, backfill_col in (('mfe_pct', 'mfe_pct'), ('mae_pct', 'mae_pct')):
        got = field_expr(close_sql, col)
        # normalize the backfill SET expression for the same column
        m = re.search(re.escape(backfill_col) + r'\s*=\s*(CASE direction.*?)(?:,\s*\n\s*(?:mfe_pct|mae_pct)\s*=|\s*WHERE)',
                      backfill_sql, re.S)
        assert m, f'{backfill_col} not found in backfill'
        want = _norm(m.group(1))
        # strip COALESCE(mfe_pct, ...) wrapper + NULL guard on the close side
        inner = re.sub(r'^COALESCE\(\s*(?:mfe_pct|mae_pct)\s*,\s*(.*)\)$', r'\1', got)
        inner = _norm(inner)
        # close side guards the whole CASE with WHEN entry/extremes > 0; backfill
        # puts those in WHERE. Compare the direction-case maths + rounding only.
        assert "direction IN ('LONG','SHORT')" in inner, 'direction guard missing on close side'
        assert "direction='LONG'" in backfill_sql and "direction='SHORT'" in backfill_sql, \
            'backfill no longer constrains direction in WHERE'
        def math(s):
            s = re.sub(r'CASE\s+WHEN entry_price > 0.*?THEN\s*', '', s)
            s = re.sub(r'\s*END$', '', s)  # drop the guard's trailing END
            return _norm(s)
        assert math(inner) == want, (
            f'{col} formula drift:\n  close   : {inner}\n  backfill: {want}')
    print('PASS 1 formula identity (close == nightly backfill, both cols)')


def test_roundtrip():
    import psycopg2
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', 'scripts'))
    from _secrets import BRAIN_DB_DICT
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    try:
        cur = conn.cursor()
        cur.execute('CREATE TEMP TABLE mfe_sc_fixture ('
                    'id int, direction text, entry_price numeric, '
                    'highest_price numeric, lowest_price numeric, '
                    'mfe_pct real, mae_pct real, status text, '
                    'exit_price numeric, pnl_usdt numeric, pnl_pct numeric, '
                    'hype_pnl_usdt numeric, hype_pnl_pct numeric, '
                    'close_time timestamp, close_reason text, exit_reason text, '
                    'exit_conditions text, notes text)')
        rows = [
            # id, dir, entry, high, low, existing mfe/mae, status
            (1, 'LONG', 100, 104, 98, None, None, 'open'),
            (2, 'SHORT', 100, 104, 97, None, None, 'open'),
            (3, 'LONG', 100, 0, 98, None, None, 'open'),      # no peak yet
            (4, 'LONG', 100, 104, 98, 0.40, 1.0, 'open'),      # already stamped
            (5, 'LONG', 100, 104, 98, None, None, 'closed'),   # WHERE clause
        ]
        cur.executemany(
            'INSERT INTO mfe_sc_fixture (id, direction, entry_price, highest_price, '
            'lowest_price, mfe_pct, mae_pct, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
            rows)

        close_sql = extract_close_update(BRAIN)
        # swap the literal/placeholder write columns for fixture-safe values and
        # re-target the temp table; the mfe/mae expressions are used verbatim.
        fixture_sql = close_sql.replace('UPDATE trades SET', 'UPDATE mfe_sc_fixture SET')
        # %s placeholders 1..10: exit_price, pnl_usdt, pnl_pct, hype_pnl_usdt,
        # hype_pnl_pct, close_reason, exit_reason, exit_conditions, notes, id
        cur.execute(fixture_sql, (99, 1, 1, 1, 1, 'r', 'r', None, '', 1))
        assert cur.rowcount == 1, 'UPDATE #1 (LONG) touched 0 rows'
        cur.execute(fixture_sql, (99, 1, 1, 1, 1, 'r', 'r', None, '', 2))
        cur.execute(fixture_sql, (99, 1, 1, 1, 1, 'r', 'r', None, '', 3))
        cur.execute(fixture_sql, (99, 1, 1, 1, 1, 'r', 'r', None, '', 4))
        cur.execute(fixture_sql, (99, 1, 1, 1, 1, 'r', 'r', None, '', 5))

        cur.execute('SELECT id, status, mfe_pct, mae_pct FROM mfe_sc_fixture ORDER BY id')
        got = {r[0]: r for r in cur.fetchall()}

        # hand-computed: LONG high 104 low 98 entry 100 -> mfe +4, mae +2
        assert got[1][2] is not None and abs(got[1][2] - 4.0) < 1e-3, got[1]
        assert got[1][3] is not None and abs(got[1][3] - 2.0) < 1e-3, got[1]
        # SHORT: mfe = entry-low = 3, mae = high-entry = 4
        assert got[2][2] is not None and abs(got[2][2] - 3.0) < 1e-3, got[2]
        assert got[2][3] is not None and abs(got[2][3] - 4.0) < 1e-3, got[2]
        # zero peak -> untouched NULL (nightly backfill skips it too)
        assert got[3][2] is None and got[3][3] is None, got[3]
        # COALESCE preserves an existing stamp
        assert abs(got[4][2] - 0.40) < 1e-4 and abs(got[4][3] - 1.0) < 1e-4, got[4]
        # WHERE status='open' guard still holds
        assert got[5][1] == 'closed' and got[5][2] is None, got[5]
        cur.close()
        print('PASS 2 round-trip (LONG/SHORT math, zero-peak NULL, COALESCE, status guard)')
    finally:
        conn.close()


def test_single_statement():
    src = open(BRAIN).read()
    block = extract_close_update(BRAIN)
    assert 'status        = \'closed\'' in block or "status        = 'closed'" in block
    assert 'mfe_pct' in block and 'mae_pct' in block
    # the close path must not issue a second trades UPDATE for mfe
    n_updates = len(re.findall(r'UPDATE trades SET', src))
    mfe_updates = len(re.findall(r'UPDATE trades SET[^;]{0,2000}mfe_pct', src, re.S))
    assert n_updates == 1, f'expected 1 trades UPDATE in brain.py, found {n_updates}'
    assert mfe_updates == 1, 'mfe write is not inside the single close UPDATE'
    print(f'PASS 3 single-statement close (trades UPDATE count={n_updates}, mfe in it)')


def main():
    test_formula_identity()
    test_roundtrip()
    test_single_statement()
    print('ALL PASS')


if __name__ == '__main__':
    if '--selfcheck' not in sys.argv:
        print('run with --selfcheck')
        sys.exit(1)
    main()
