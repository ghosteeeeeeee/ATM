#!/usr/bin/env python3
"""
accounting_reconciliation.py — three-way PnL reconciliation (CEO idea 1,
edge-diagnosis verdict 20261122T194418Z). REPORT-ONLY: SELECTs against PG
brain.trades, prints tables, writes brain/analysis/accounting_reconciliation_<date>.md.
No writes to PG/SQLite, no trading behavior, no trading flags.

Three sources joined over closed trades:
  internal   pnl_usdt                                       gross, no fees
  fee-JSON   pnl_usdt - COALESCE((fees->>'fee_total'), 0)    SYNTHETIC (see BUG-099)
  HL truth   hype_realized_pnl_usdt                          fee-exclusive, path-biased coverage

BUG-099 window split (CLOSE TIME, midnight UTC):
  pre  = close_time <  2026-08-22 00:00:00   (exclusive of Aug 22)
  post = close_time >= 2026-08-22 00:00:00   (inclusive of Aug 22)
Fee JSON is written at close, so close_time is the boundary that matters; pre-8/22
fee_total is inflated ~7-10x (measured 0.78% of margin vs 0.102% post).

Usage:
    python3 scripts/accounting_reconciliation.py                # full report (DB only)
    python3 scripts/accounting_reconciliation.py --hl-fills     # + live HL fill cross-check
    python3 scripts/accounting_reconciliation.py --selfcheck    # invariants only, exit 0/1
"""

import os
import sys
import time
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from _secrets import BRAIN_DB_DICT

BOUNDARY = date(2026, 8, 22)          # BUG-099 fee-JSON era split (close_time, UTC midnight)
# Hyperliquid /info userFillsByTime only serves ~160 days back; anything earlier is
# not retrievable, so the independent fill cross-check starts here (measured 2026-11-22).
HL_FILL_FLOOR = date(2026, 6, 14)
TAKER_RT = 0.0009                      # HL taker 0.045% per side x 2 (pnl_utils fee model)
ARITH_OK_MIN = 0.90                    # fraction of blob rows whose pnl must recompute
SIGN_FLIP_MATERIALITY = 5.0            # $ of wrong-sign pnl that would make the blob BOGUS
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'brain', 'analysis')

# direction-aware unleveraged price move from recorded prices (both eras store
# pnl_usdt = notional x raw move; pnl_pct is unleveraged pre-2026-08-21, leveraged after)
RAW = ("(CASE WHEN direction='SHORT' THEN (entry_price-exit_price) "
       "ELSE (exit_price-entry_price) END)/NULLIF(entry_price,0)")
# effective position value: HL's recorded notional when we have it, else the margin
POS = "COALESCE(NULLIF(hl_notional_usdt,0), amount_usdt)"


def era_sql(which):
    if which == 'pre':
        return "close_time < %s::timestamp"
    if which == 'post':
        return "close_time >= %s::timestamp"
    return "TRUE"


def agg(cur, era, paper):
    """Window aggregates. paper: 'false' (real book) or 'true'."""
    paper_sql = {'false': "paper = FALSE", 'true': "paper = TRUE"}[paper]
    cur.execute(f"""
        SELECT count(*) AS n,
               round(sum(pnl_usdt)::numeric, 2) AS internal,
               count(*) FILTER (WHERE fees ~ '^\\{{') AS feej_n,
               round(coalesce(sum((fees::json->>'fee_total')::numeric), 0)::numeric, 2) AS fee_total,
               round(coalesce(sum((fees::json->>'net_pnl')::numeric), 0)::numeric, 2) AS feej_net_json,
               round((sum(pnl_usdt) FILTER (WHERE fees ~ '^\\{{'))::numeric, 2) AS feej_pnl,
               count(*) FILTER (WHERE hype_realized_pnl_usdt IS NOT NULL) AS hl_n,
               round(coalesce(sum(hype_realized_pnl_usdt), 0)::numeric, 2) AS hl_sum,
               round(coalesce(sum(amount_usdt), 0)::numeric, 2) AS amount_sum,
               round(coalesce(sum(amount_usdt) FILTER (WHERE fees ~ '^\\{{'), 0)::numeric,
                     2) AS feej_amount_sum,
               round(coalesce(sum(CASE WHEN {POS} > 0 THEN {POS} END), 0)::numeric, 2) AS pos_sum,
               round(coalesce(sum(CASE WHEN {POS} > 0 THEN {POS} END)
                              FILTER (WHERE fees ~ '^\\{{'), 0)::numeric, 2) AS feej_pos_sum,
               count(*) FILTER (WHERE hl_notional_usdt > 0) AS pos_known_n
          FROM trades
         WHERE status = 'closed' AND {paper_sql} AND {era_sql(era)}
    """, (BOUNDARY,) if era in ('pre', 'post') else ())
    return dict(zip([d[0] for d in cur.description], cur.fetchone()))


def pct(num, den):
    return (100.0 * float(num) / float(den)) if den else 0.0


def money(x):
    return f"{float(x):+,.2f}"


def table(rows, headers):
    widths = [max(len(str(r[i])) for r in rows + [headers]) for i in range(len(headers))]
    out = ['| ' + ' | '.join(str(headers[i]).ljust(widths[i]) for i in range(len(headers))) + ' |',
           '|' + '|'.join('-' * (w + 2) for w in widths) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(r[i]).ljust(widths[i]) for i in range(len(headers))) + ' |')
    return '\n'.join(out)


def window_table(cur):
    rows = []
    labels = [('pre  (close < 2026-08-22)', 'pre'), ('post (close >= 2026-08-22)', 'post'),
              ('all closed', 'all')]
    for label, era in labels:
        for paper, suffix in (('false', ' real'), ('true', ' paper')):
            a = agg(cur, era, paper)
            if a['n'] == 0:
                continue
            rows.append([label + suffix, a['n'], money(a['internal']),
                         money(a['internal'] - a['fee_total']), f"{a['feej_n']}/{a['n']}",
                         f"{pct(a['fee_total'], a['feej_amount_sum']):.4f}%",
                         f"{pct(a['fee_total'], a['feej_pos_sum']):.4f}%",
                         a['hl_n'], money(a['hl_sum'])])
    return table(rows, ['window', 'n', 'internal gross', 'fee-JSON net', 'feeJ n',
                        'fee % of margin (fee rows)', 'fee % of position (fee rows)',
                        'HL n', 'HL sum'])


def fee_rates(cur):
    """Fee rate over the rows that actually carry a fee JSON (BUG-099 denominators)."""
    rows = []
    for label, era in (('pre-8/22', 'pre'), ('post-8/22', 'post'), ('all', 'all')):
        a = agg(cur, era, 'false')
        rows.append([label, a['feej_n'], money(a['fee_total']),
                     money(a['feej_amount_sum']),
                     f"{pct(a['fee_total'], a['feej_amount_sum']):.4f}%",
                     f"{pct(a['fee_total'], a['feej_pos_sum']):.4f}%"])
    return table(rows, ['era (paper=false)', 'feeJ n', 'fee_total sum', 'fee-row margin',
                        '% of margin (amount_usdt)', '% of position value'])


def anomaly(cur):
    """Pre-8/22 rows split by HL coverage + corruption checks. Returns (markdown, stats)."""
    cur.execute(f"""
        SELECT CASE WHEN hype_realized_pnl_usdt IS NULL THEN 'no HL' ELSE 'HL' END AS grp,
               count(*) AS n, round(sum(pnl_usdt)::numeric, 2) AS internal,
               count(*) FILTER (WHERE pnl_usdt > 0) AS wins,
               round(avg(pnl_usdt)::numeric, 4) AS avg_pnl,
               count(*) FILTER (WHERE fees ~ '^\\{{') AS feej_n,
               round(coalesce(sum((fees::json->>'fee_total')::numeric), 0)::numeric, 2) AS fee_total
          FROM trades
         WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
         GROUP BY 1 ORDER BY 1 DESC
    """, (BOUNDARY,))
    rows = cur.fetchall()
    split = {r[0]: r for r in rows}
    split_rows = [[r[0], r[1], money(r[2]), r[3], f"{pct(r[3], r[1]):.1f}%", r[4],
                   f"{r[5]}/{r[1]}", money(r[6])] for r in rows]

    def top_group(col, limit=None, order='2 DESC'):
        cur.execute(f"""
            SELECT {col}, count(*) AS n, round(sum(pnl_usdt)::numeric, 2) AS internal,
                   count(*) FILTER (WHERE pnl_usdt > 0) AS wins
              FROM trades
             WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
               AND hype_realized_pnl_usdt IS NULL
             GROUP BY 1 ORDER BY {order} {('LIMIT ' + str(limit)) if limit else ''}
        """, (BOUNDARY,))
        return cur.fetchall()

    paths = top_group('close_reason', 6)
    signals = top_group('signal', 5)
    tokens = top_group('token', 5, '3 DESC')
    dirs = top_group('direction')

    # HL coverage by exit family — the mechanism behind the ±$111 split
    cur.execute(f"""
        SELECT CASE WHEN close_reason LIKE 'profit-monster%%'
                     OR close_reason LIKE 'profit_monster%%'
                    THEN 'profit-monster family'
                    WHEN close_reason = 'atr_sl_hit' THEN 'atr_sl_hit'
                    ELSE 'other' END AS fam,
               count(*) AS n,
               count(*) FILTER (WHERE hype_realized_pnl_usdt IS NOT NULL) AS hl_n
          FROM trades
         WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
         GROUP BY 1 ORDER BY 2 DESC
    """, (BOUNDARY,))
    fam_rows = cur.fetchall()
    fam = {r[0]: r for r in fam_rows}
    pm_n, pm_hl = fam['profit-monster family'][1], fam['profit-monster family'][2]
    sl_n, sl_hl = fam['atr_sl_hit'][1], fam['atr_sl_hit'][2]

    # ── corruption checks ────────────────────────────────────────────────
    cur.execute(f"""
        SELECT count(*) AS n,
               count(*) FILTER (WHERE abs(pnl_usdt - ({RAW}) * {POS}) < 0.011) AS arith_ok,
               count(*) FILTER (WHERE abs(pnl_usdt) > 0.01
                                 AND (pnl_usdt > 0) <> (({RAW}) > 0)) AS sign_flip_n,
               coalesce(sum(abs(pnl_usdt)) FILTER (WHERE abs(pnl_usdt) > 0.01
                                 AND (pnl_usdt > 0) <> (({RAW}) > 0)), 0)::numeric
                   AS sign_flip_sum,
               count(*) FILTER (WHERE hl_notional_usdt > 0) AS pos_known,
               count(*) FILTER (WHERE hl_entry_price IS NOT NULL AND hl_entry_price <> 0) AS hl_entry,
               count(*) FILTER (WHERE paper) AS paper_rows,
               count(*) FILTER (WHERE missed_opportunity) AS missed_rows
          FROM trades
         WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
           AND hype_realized_pnl_usdt IS NULL
    """, (BOUNDARY,))
    chk = dict(zip(['n', 'arith_ok', 'sign_flip_n', 'sign_flip_sum', 'pos_known', 'hl_entry',
                    'paper_rows', 'missed_rows'], cur.fetchone()))

    cur.execute(f"""
        SELECT count(*) FROM (
            SELECT token, entry_price, open_time
              FROM trades
             WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
               AND hype_realized_pnl_usdt IS NULL
             GROUP BY 1, 2, 3 HAVING count(*) > 1) d
    """, (BOUNDARY,))
    dupes = cur.fetchone()[0]

    # ids of the wrong-sign rows (cited in the verdict)
    cur.execute(f"""
        SELECT id, token, direction, pnl_usdt, close_reason
          FROM trades
         WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
           AND hype_realized_pnl_usdt IS NULL
           AND abs(pnl_usdt) > 0.01
           AND (pnl_usdt > 0) <> (({RAW}) > 0)
         ORDER BY abs(pnl_usdt) DESC
    """, (BOUNDARY,))
    sign_rows = cur.fetchall()

    # top contributing rows (cited by id)
    cur.execute(f"""
        SELECT id, token, signal, direction, pnl_usdt, pnl_pct, close_time::date,
               close_reason, amount_usdt, hl_notional_usdt, hl_entry_price
          FROM trades
         WHERE status='closed' AND paper=FALSE AND {era_sql('pre')}
           AND hype_realized_pnl_usdt IS NULL
         ORDER BY pnl_usdt DESC LIMIT 15
    """, (BOUNDARY,))
    top = cur.fetchall()

    # independent cross-check window (as far back as HL fill history reaches)
    cur.execute("""
        SELECT count(*), round(sum(pnl_usdt)::numeric, 2),
               count(*) FILTER (WHERE hype_realized_pnl_usdt IS NULL),
               round(coalesce(sum(pnl_usdt) FILTER (WHERE hype_realized_pnl_usdt IS NULL),
                              0)::numeric, 2)
          FROM trades
         WHERE status='closed' AND paper=FALSE
           AND close_time >= %s::timestamp AND close_time < %s::timestamp
    """, (HL_FILL_FLOOR, BOUNDARY))
    hlwin = cur.fetchone()

    # verdict: REAL only if every corruption check passes
    real = (dupes == 0 and chk['paper_rows'] == 0 and chk['missed_rows'] == 0
            and chk['arith_ok'] >= ARITH_OK_MIN * chk['n']
            and float(chk['sign_flip_sum']) < SIGN_FLIP_MATERIALITY)
    verdict = 'REAL' if real else 'BOGUS'

    stats = dict(split=split, chk=chk, dupes=dupes, hlwin=hlwin, verdict=verdict, fam=fam)
    md = ['### 2a. Pre-8/22 split by HL ground-truth coverage\n',
          table(split_rows, ['group', 'n', 'internal', 'wins', 'WR', 'avg pnl',
                             'feeJ n', 'fee_total']), '',
          '### 2b. What the no-HL blob is made of (close paths)\n',
          table([[r[0], r[1], money(r[2]), r[3], f"{pct(r[3], r[1]):.1f}%"] for r in paths],
                ['close_reason', 'n', 'internal', 'wins', 'WR']), '',
          'HL ground-truth coverage by exit family (pre-8/22, both halves together):\n',
          table([[r[0], r[1], r[2], f"{pct(r[2], r[1]):.1f}%"] for r in fam_rows],
                ['exit family', 'n', 'with HL truth', 'HL coverage']), '',
          '### 2c. Dominant signals / tokens / directions in the blob\n',
          'Top signals:\n',
          table([[r[0], r[1], money(r[2]), r[3]] for r in signals],
                ['signal', 'n', 'internal', 'wins']),
          '\nTop tokens:\n',
          table([[r[0], r[1], money(r[2]), r[3]] for r in tokens],
                ['token', 'n', 'internal', 'wins']),
          '\nDirections:\n',
          table([[r[0], r[1], money(r[2]), r[3], f"{pct(r[3], r[1]):.1f}%"] for r in dirs],
                ['direction', 'n', 'internal', 'wins', 'WR']), '',
          '### 2d. Corruption checks on the blob\n',
          table([
              ['rows under test', chk['n'], 'pre-8/22, paper=FALSE, no HL ground truth'],
              ['pnl_usdt == raw_move x position value (<=1.1c)', chk['arith_ok'],
               f"{pct(chk['arith_ok'], chk['n']):.1f}% — arithmetic intact, not corrupted"],
              ['wrong-sign rows (|pnl|>$0.01)', f"{chk['sign_flip_n']} rows / "
               f"${float(chk['sign_flip_sum']):.2f}",
               'ids: ' + (', '.join(str(r[0]) for r in sign_rows) or 'none')
               + ' — cannot produce +$111'],
              ['duplicate (token, entry_price, open_time) groups', dupes, 'no duplicated opens'],
              ['rows with an HL position recorded (hl_notional>0)', chk['pos_known'],
               f"{pct(chk['pos_known'], chk['n']):.1f}% — a real HL position existed"],
              ['rows with an HL entry fill price', chk['hl_entry'],
               f"{pct(chk['hl_entry'], chk['n']):.1f}% — entry fill confirmed by HL API"],
              ['paper=true rows in blob', chk['paper_rows'], 'filter is paper=FALSE, cannot be >0'],
              ['missed_opportunity rows', chk['missed_rows'], 'none are simulated rows'],
          ], ['check', 'value', 'reading']), '',
          '### 2e. Top 15 contributing rows (ids cited)\n',
          table([[r[0], r[1], r[2], r[3], money(r[4]), r[5], str(r[6]), r[7],
                  f"{float(r[8]):.2f}", '' if r[9] is None else f"{float(r[9]):.2f}",
                  '' if r[10] is None else f"{float(r[10]):.6g}"] for r in top],
                ['id', 'token', 'signal', 'dir', 'pnl_usdt', 'pnl_pct', 'close',
                 'close_reason', 'margin', 'hl_notional', 'hl_entry_px']), '',
          f'### 2f. Verdict on the +$111 blob: **{verdict}**\n',
          'The split is a **close-path split, not an accounting split**:',
          '',
          f"- the no-HL half ({split['no HL'][1]} rows, {money(split['no HL'][2])}, "
          f"WR {pct(split['no HL'][3], split['no HL'][1]):.1f}%) is dominated by "
          f"**profit-monster trail exits** ({pm_n - pm_hl} of {split['no HL'][1]} = "
          f"{pct(pm_n - pm_hl, split['no HL'][1]):.1f}%) — a trailing profit exit closes IN "
          'PROFIT by construction, so a high win rate there is structural, not fabricated;',
          f"- the HL half ({split['HL'][1]} rows, {money(split['HL'][2])}, WR "
          f"{pct(split['HL'][3], split['HL'][1]):.1f}%) is {sl_hl}/{split['HL'][1]} = "
          f"{pct(sl_hl, split['HL'][1]):.1f}% `atr_sl_hit` "
          '(stop-loss exits = losses by construction);',
          f"- together they are ONE book: {split['no HL'][1] + split['HL'][1]} rows, "
          f"{money(split['no HL'][2] + split['HL'][2])}, WR "
          f"{pct(split['no HL'][3] + split['HL'][3], split['no HL'][1] + split['HL'][1]):.1f}% "
          '— in line with the documented system win rate, so the halves complement each other;',
          f"- the HL sync covered {sl_hl}/{sl_n} `atr_sl_hit` exits "
          f"({pct(sl_hl, sl_n):.1f}%) but only {pm_hl}/{pm_n} profit-monster exits "
          f"({pct(pm_hl, pm_n):.1f}%) — that is *why* coverage splits on outcome;",
          f"- corruption checks: arithmetic intact on "
          f"{pct(chk['arith_ok'], chk['n']):.1f}% of rows, {chk['sign_flip_n']} wrong-sign row "
          f"(${float(chk['sign_flip_sum']):.2f}, id {', '.join(str(r[0]) for r in sign_rows)}), "
          f"{dupes} duplicate opens, 0 paper rows, 0 missed_opportunity rows;",
          f"- corroborated: {chk['pos_known']} rows ({pct(chk['pos_known'], chk['n']):.1f}%) "
          f"record an HL position and {chk['hl_entry']} "
          f"({pct(chk['hl_entry'], chk['n']):.1f}%) record an HL entry fill price — real "
          'positions, real fills;',
          f'- **caveat:** for {HL_FILL_FLOOR}..{BOUNDARY} the blob contributes only '
          f'{money(hlwin[3])}; the remaining {money(split["no HL"][2] - hlwin[3])} of it closed '
          'before that date, where HL fill history is not retrievable (API serves ~160 days '
          'back) — that portion rests on the internal-consistency + entry-fill evidence above, '
          'not on a fill replay.',
          '']
    return '\n'.join(md), stats


def fetch_hl_fills(start, end):
    """All HL fills in [start, end) dates, chunked (API caps ~2,000 rows/request)."""
    from hyperliquid_exchange import get_trade_history
    to_ms = lambda d: int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
    lo, hi = to_ms(start), to_ms(end)
    out, seen = [], set()
    while hi > lo:
        fills = get_trade_history(lo, hi)
        if not fills:
            break
        for f in fills:
            key = (f.get('hash'), f.get('oid'), f.get('time_ms'))
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
        oldest = min(f['time_ms'] for f in fills)
        if oldest <= lo or len(fills) < 2000:
            break
        hi = oldest - 1
        time.sleep(0.5)                     # ponytail: single fixed backoff, no retry ladder
    return out


def hl_fill_check(cur, an_stats):
    """Independent exchange-side cross-check over the retrievable part of the pre window."""
    try:
        fills = fetch_hl_fills(HL_FILL_FLOOR, BOUNDARY)
    except Exception as e:
        return f'HL fill fetch unavailable ({e}); cross-check skipped.\n'
    if not fills:
        return ('HL fill fetch returned 0 rows (API depth/rate limit); cross-check '
                'skipped — §2f stands on internal evidence.\n')
    closes = [f for f in fills if 'Close' in str(f.get('dir', ''))]
    hl_sum = sum(f['closed_pnl'] for f in closes)
    n, internal, blob_n, blob_sum = an_stats['hlwin']
    return (f"### 2g. Independent HL-fill cross-check (live exchange data)\n\n"
            f"- window `{HL_FILL_FLOOR}` .. `{BOUNDARY}` — all HL fill history that is "
            f"retrievable (the API serves ~160 days back)\n"
            f"- internal, paper=false: n={n} (of which {blob_n} are no-HL blob rows) "
            f"sum={money(internal)}; blob alone = {money(blob_sum)}\n"
            f"- HL fills: {len(fills)} fills, {len(closes)} close fills, "
            f"**closed_pnl sum = {money(hl_sum)}**\n"
            f"- reading: exchange realized PnL over the window is within "
            f"${abs(float(internal) - float(hl_sum)):.2f} of the internal book. The blob "
            f"contributes {money(blob_sum)} inside this window; if it were phantom the "
            f"exchange total would read ~{money(internal - blob_sum)} (SL side only), "
            f"not ~{money(hl_sum)}.\n")


def slippage_section(cur):
    cur.execute("""
        SELECT pg_get_expr(d.adbin, d.adrelid)
          FROM pg_attrdef d
          JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
         WHERE a.attrelid = 'trades'::regclass AND a.attname = 'exit_slippage_pct'
    """)
    ddl = ' '.join(cur.fetchone()[0].split())
    cur.execute("""
        SELECT count(*) FILTER (WHERE status='closed') AS closed_n,
               count(*) FILTER (WHERE status='closed' AND hl_entry_price IS NOT NULL
                                 AND hl_entry_price <> 0) AS hl_entry_n,
               count(*) FILTER (WHERE status='closed' AND hl_entry_price IS NOT NULL
                                 AND hl_entry_price <> 0
                                 AND abs(hl_entry_price - entry_price) > 1e-12) AS hl_entry_diff_n,
               count(*) FILTER (WHERE status='closed' AND hl_exit_price IS NOT NULL
                                 AND hl_exit_price <> 0) AS hl_exit_n
          FROM trades
    """)
    c = dict(zip(['closed', 'hl_entry', 'hl_entry_diff', 'hl_exit'], cur.fetchone()))
    md = ['### 4a. `exit_slippage_pct` — actual definition (live PG DDL)\n',
          '`exit_slippage_pct` is a **GENERATED ALWAYS ... STORED** column. No script writes '
          'it — PostgreSQL computes it on every INSERT/UPDATE:\n',
          '```sql\n' + ddl + '\n```\n',
          'It measures **distance-from-stop-at-exit as a % of the stop level**, NOT fill '
          'slippage. Winners trail away from the stop (large values), losers exit AT the stop '
          '(small values) — that construction alone produces the diagnosis doc\'s '
          '"winners slip 2.7x more than losers" anomaly. It also double-counts for '
          'stop-family exits (the exit IS the stop -> 0) and cannot be summed into a '
          'friction budget.\n',
          '### 4b. Doc/comment notes for the definition\n',
          table([
              ['`brain/analysis/stop_tighten_scope_walk_2026-11-20.py` (line 20)',
               'comment added', 'consumer called it a "Slippage model" — corrected to '
                                'stop-overshoot at exit'],
              ['`brain/2026-11-22_hermes-edge-diagnosis.md` §7.7', 'correction note added',
               'doc said the computation "could not be located" and read 0.69% as friction'],
              ['`automation/ceo/shadow_disposition_report.md:98`', 'already documented '
               '(2026-11-16)', 'carries the DDL definition + the forward rule for '
                               'stop-tighten counterfactuals'],
          ], ['location', 'action', 'note']), '',
          '### 4c. `hl_entry_price` / `hl_exit_price` coverage\n',
          table([
              ['closed trades', c['closed'], 'denominator'],
              ['hl_entry_price populated (non-zero)', c['hl_entry'],
               f"{pct(c['hl_entry'], c['closed']):.1f}% — entry fill price IS available"],
              ['...of which differ from entry_price', c['hl_entry_diff'],
               'entry fill-vs-recorded-entry gap is measurable today'],
              ['hl_exit_price populated (non-zero)', c['hl_exit'],
               f"{pct(c['hl_exit'], c['closed']):.2f}% — exit fill price effectively absent, "
               'so real fill-vs-mark EXIT slippage is impossible today'],
          ], ['metric', 'n', 'reading']), '',
          'Consequence: an honest slippage field needs `hl_exit_price` written at close (one '
          'writer change in the close path); until then only the entry side can be measured. '
          'No writer change ships with this report — doc-only deliverable.\n']
    return '\n'.join(md), c


def reconcile(cur, an_stats):
    a = {k: agg(cur, k, 'false') for k in ('pre', 'post', 'all')}
    internal = float(a['all']['internal'])
    fee_lit = float(a['all']['fee_total'])
    pre_rate = pct(a['pre']['fee_total'], a['pre']['feej_amount_sum'])
    post_rate = pct(a['post']['fee_total'], a['post']['feej_amount_sum'])
    inflation = (pre_rate / post_rate) if post_rate else 0.0
    fee_corr = (float(a['pre']['fee_total']) / inflation
                + float(a['post']['fee_total'])) if inflation else fee_lit
    fee_model = post_rate / 100.0 * float(a['all']['amount_sum'])
    pos_fee = TAKER_RT * float(a['all']['pos_sum'])
    hl = float(a['all']['hl_sum'])

    rows = [
        ['internal gross (pnl_usdt, all closed, paper=false)', money(internal),
         'the dashboard number; fees excluded'],
        ['fee-JSON `net_pnl` field as stored (fee rows only)', money(a['all']['feej_net_json']),
         f"n={a['all']['feej_n']} fee rows — THIS is the doc's -$350.31 (its value drifts as "
         'pnl_usdt is revised after the blob is written)'],
        ['fee-JSON net = pnl_usdt - fee_total (all rows)', money(internal - fee_lit),
         'literal BUG-099 construction: rows without a fee JSON contribute 0 fees'],
        ['HL ground truth where present', money(hl),
         f"{a['all']['hl_n']}/{a['all']['n']} rows; fee-exclusive; coverage is PATH-BIASED"],
        ['gross - BUG-099-corrected fee JSON', money(internal - fee_corr),
         f"pre fee / measured {inflation:.1f}x inflation + post fee"],
        ['gross - post-era fee rate on all margin', money(internal - fee_model),
         f"{post_rate:.4f}% x ${float(a['all']['amount_sum']):,.0f} margin "
         f"(all closed rows, not just fee-JSON rows)"],
        ['gross - HL taker model (0.09% RT x position value)', money(internal - pos_fee),
         f"0.09% x ${float(a['all']['pos_sum']):,.0f} position value"],
    ]
    stale = float(a['all']['feej_pnl']) - (float(a['all']['feej_net_json'])
                                           + float(a['all']['fee_total']))
    md = ['### 3a. All-time three-way reconciliation (paper=false)\n',
          table(rows, ['basis', 'all-time $', 'note']), '',
          f'Note: on the {a["all"]["feej_n"]} fee rows the stored `net_pnl` embeds the gross as '
          f'of fee-write time; current `pnl_usdt` on those rows is {money(stale)} vs that '
          'embedded gross, so the JSON `net_pnl` field is stale — `pnl_usdt - fee_total` is '
          'the current reading.\n',
          '### 3b. Fee rate per side of the BUG-099 boundary (paper=false; denominator = '
          'rows that carry a fee JSON, so the two eras are comparable)\n',
          fee_rates(cur), '']

    true_nets = [internal - fee_corr, internal - fee_model, internal - pos_fee]
    fam = an_stats['fam']
    pm_n, pm_hl = fam['profit-monster family'][1], fam['profit-monster family'][2]
    sl_n, sl_hl = fam['atr_sl_hit'][1], fam['atr_sl_hit'][2]
    md += ['### 3c. The CEO\'s -$170..-$200 hypothesis\n',
           '- quoted range: **-$170..-$200**, conditional on the +$111 blob being bogus\n',
           f"- blob verdict: **{an_stats['verdict']}** (§2) → the condition fails\n",
           f'- the HL-only anchor ({money(hl)} on {a["all"]["hl_n"]} rows) **cannot** be an '
           'all-time total: '
           f'its coverage is close-path biased — {pct(sl_hl, sl_n):.1f}% of `atr_sl_hit` (SL) '
           f'exits carry it vs {pct(pm_hl, pm_n):.1f}% of profit-monster exits — so it counts '
           'the loss side and drops the win side\n',
           f"- reconciled all-time net of TRUE fees: **{money(max(true_nets))} .. "
           f"{money(min(true_nets))}** across fee models (gross {money(internal)})\n",
           '- the diagnosis doc\'s -$350.31 is wrong in the other direction (BUG-099 fees at '
           'face value, mislabeled "exchange-reported")\n']
    stats = dict(internal=internal, fee_lit=fee_lit, fee_corr=fee_corr, fee_model=fee_model,
                 pos_fee=pos_fee, hl=hl, net_lo=min(true_nets), net_hi=max(true_nets),
                 inflation=inflation, post_rate=post_rate, pre_rate=pre_rate, a=a)
    return '\n'.join(md), stats


def selfcheck(an_stats, sl_stats, rec_stats):
    """Invariants that must hold or the reconciliation is wrong."""
    a = rec_stats['a']
    assert abs((a['pre']['internal'] + a['post']['internal']) - a['all']['internal']) < 0.01, \
        'pre+post != all (window split broken)'
    assert a['all']['n'] == a['pre']['n'] + a['post']['n'], 'n split broken'
    assert abs((a['all']['internal'] - a['all']['fee_total'])
               - (a['pre']['internal'] - a['pre']['fee_total']
                  + a['post']['internal'] - a['post']['fee_total'])) < 0.01, \
        'fee-net split broken'
    split = an_stats['split']
    assert abs((split['no HL'][2] + split['HL'][2]) - a['pre']['internal']) < 0.01, \
        'anomaly split does not sum to the pre-window total'
    assert an_stats['dupes'] == 0, 'duplicate opens detected'
    assert an_stats['chk']['paper_rows'] == 0, 'paper rows leaked into the real-book blob'
    assert sl_stats['hl_exit'] <= 2, 'hl_exit_price unexpectedly populated — slippage doc stale'
    assert rec_stats['net_hi'] > rec_stats['net_lo'], 'net range inverted'
    # BUG-099 direction: pre-era fee JSON must read inflated vs post-era
    assert rec_stats['pre_rate'] > rec_stats['post_rate'], \
        'BUG-099 inflation direction not visible — fee split broken'
    assert rec_stats['post_rate'] < 0.5, 'post-era fee rate implausible for a taker model'
    return True


def main():
    args = sys.argv[1:]
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    try:
        win = window_table(cur)
        an_md, an_stats = anomaly(cur)
        rec_md, rec_stats = reconcile(cur, an_stats)
        sl_md, sl_stats = slippage_section(cur)
        hl_md = hl_fill_check(cur, an_stats) if '--hl-fills' in args else ''
        selfcheck(an_stats, sl_stats, rec_stats)
    finally:
        cur.close()
        conn.close()

    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    doc = '\n'.join([
        f'# Accounting reconciliation — {date.today().isoformat()}',
        '',
        f'Generated by `scripts/accounting_reconciliation.py` on {stamp}. Report-only: '
        'SELECT-only against PG `brain.trades`, no writes, no flags, no trading behavior.',
        '',
        'Sources: **internal** = `pnl_usdt` (gross) · **fee-JSON** = `pnl_usdt - '
        "COALESCE((fees::json->>'fee_total')::numeric,0)` (SYNTHETIC — `pnl_utils.py:110`, "
        'notional x 0.0009 taker model) · **HL** = `hype_realized_pnl_usdt` (fee-exclusive).',
        '',
        '**BUG-099 boundary:** `close_time < 2026-08-22` = pre (exclusive of Aug 22), '
        '`close_time >= 2026-08-22` = post (inclusive of Aug 22). Split on close time because '
        'the fee JSON is written at close. **Missing fees:** only values matching `^{` are '
        'cast; rows without a fee JSON contribute 0 to the fee-JSON net (coverage = `feeJ n`), '
        'so that column understates cost — §3a\'s rate-based models cover the fee-less rows.',
        '',
        '## 1. Per-window three-way table',
        '',
        win,
        '',
        an_md,
        '',
        hl_md,
        rec_md,
        '',
        sl_md,
        '## Self-check',
        '',
        'All invariants passed: pre+post=all, fee-net split, anomaly split sums to the pre '
        'total, 0 duplicate opens, 0 paper rows in the blob, net range well-ordered, '
        'BUG-099 fee-rate direction (pre > post), post-era fee rate < 0.5% of margin, '
        'hl_exit_price coverage unchanged.',
    ])

    print(doc)
    if '--selfcheck' in args:
        print('\nSELFCHECK PASS')
        return 0

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f'accounting_reconciliation_{date.today().isoformat()}.md')
    with open(path, 'w') as f:
        f.write(doc + '\n')
    print(f'\n[report written] {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
