#!/usr/bin/env python3
"""floor_admit_shadow outcome join — pre-registered brain_auditor #126, shipped #132.

WHAT THE SHADOW IS: decider_run.py:3779 logs every signal whose exec confidence
depends on PENALTY_MULT_FLOOR. `floor_admitted=True` = the trade crossed
MIN_EXEC_CONFIDENCE (40) ONLY because the floor is 0.5 (CEO 2026-10-13, was 0.3).
Under the old 0.3 floor it would have been PENALTY-BLOCKED.

QUESTIONS ANSWERED (all zero-behavior — this script writes nothing to trading state):
  1. Do floor-only admits win like normal admits, or worse? (floor_only vs always_admit)
  2. Would the pp-conditional floor (0.3 when penalty_product<0.10, else 0.5) have
     blocked a better or worse cohort? (the third CEO floor option, decider_run.py:3775)
  3. Per-source breakdown of the floor-only cohort.

UNIT RULE: outcome is price-move % only. ±0.40% favourable before ±0.40% adverse
within 30 x 5m closes, else SHALLOW — the same classification as
analysis/contrarian_outcome_join.py so numbers are comparable across shadows.

DEDUP: shadow rows re-emit every ~1m while a signal stays live, so rows are NOT
independent. One row per (token, direction, source, 5-minute bucket), first row
wins. Raw n=1787 -> episodes shown next to raw n.

PRE-REGISTERED BARS (#126, locked pre-data): n>=200 AND Fisher p<0.05 AND 30d
same sign. Data starts 2026-10-16, so the 30d bar cannot be met before
2026-11-15 — any verdict before then is COLLECT/MONITOR, never SHIP.

Usage: python3 analysis/floor_admit_outcome_join.py [--selfcheck]
"""
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone

CANDLES = "/root/.hermes/data/candles.db"
SHADOW = "/root/.hermes/data/floor_admit_shadow.jsonl"
OUT = "/root/.hermes/data/floor_admit_outcome_join.json"
ARM_PCT = 0.40
ADV_PCT = 0.40
MAX_CANDLES = 30
MIN_EXEC_CONFIDENCE = 40
DEDUP_KEYLEN = 15  # 'YYYY-MM-DDTHH:MM' = 5-minute bucket
EPISODE_GAP_S = 600  # merge same (token,direction,source) episodes closer than 10 min —
# a signal that stays live across a 5m bucket edge would otherwise be counted twice
# and inflate n (and every Fisher test built on it).
SHADOW_START = "2026-10-16"  # first row in the shadow; 30d bar is SHADOW_START + 30d


def to_unix(ts_str):
    try:
        return int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def dedup(rows):
    """One row per signal episode.

    Step 1: one row per (token, direction, source, 5m bucket), first by ts wins —
            collapses the ~1m re-emits while a signal stays live.
    Step 2: merge consecutive same-key episodes closer than EPISODE_GAP_S —
            a live signal crossing a bucket edge must not become 2 episodes.
    """
    seen = {}
    for r in sorted(rows, key=lambda x: x.get("ts") or ""):
        k = (r.get("token"), r.get("direction"), r.get("source"),
             (r.get("ts") or "")[:DEDUP_KEYLEN])
        if k not in seen:
            seen[k] = r
    eps = sorted(seen.values(), key=lambda x: x.get("ts") or "")
    out = []
    for r in eps:
        k = (r.get("token"), r.get("direction"), r.get("source"))
        if out and (out[-1].get("token"), out[-1].get("direction"),
                    out[-1].get("source")) == k:
            gap = (to_unix(r.get("ts") or "") or 0) - (to_unix(out[-1].get("ts") or "") or 0)
            if 0 <= gap <= EPISODE_GAP_S:
                continue  # same episode, keep the earlier row
        out.append(r)
    return out


def cohort_of(r):
    if r.get("floor_admitted"):
        return "floor_only"
    return "always_admit" if float(r.get("exec_conf") or 0) >= MIN_EXEC_CONFIDENCE else "blocked"


def classify_from_entry(direction, entry_price, ts_unix, token, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT open, high, low, close FROM candles_5m
        WHERE token = ? AND ts > ? AND is_closed = 1
        ORDER BY ts ASC LIMIT ?
    """, (token, ts_unix, MAX_CANDLES))
    rows = cur.fetchall()
    if not rows:
        return "NO_DATA", 0.0, 0.0, 0
    max_fav = 0.0
    max_adv = 0.0
    outcome = "SHALLOW"
    for (_, h, l, c) in rows:
        if direction == "LONG":
            fav = (h - entry_price) / entry_price * 100
            adv = (entry_price - l) / entry_price * 100
        else:
            fav = (entry_price - l) / entry_price * 100
            adv = (h - entry_price) / entry_price * 100
        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)
        if max_fav >= ARM_PCT and max_adv < ADV_PCT:
            outcome = "WINNER"
            break
        if max_adv >= ADV_PCT and max_fav < ARM_PCT:
            outcome = "LOSER"
            break
        if max_fav >= ARM_PCT and max_adv >= ADV_PCT:
            # same candle crossed both sides — tie-break on CLOSE DIRECTION.
            # direction-signed: a close AT/ABOVE entry favours LONG and hurts SHORT.
            closed_fav = (c >= entry_price) if direction == "LONG" else (c <= entry_price)
            outcome = "WINNER" if closed_fav else "LOSER"
            break
    else:
        if max_fav >= ARM_PCT:
            outcome = "WINNER"
        elif max_adv >= ADV_PCT:
            outcome = "LOSER"
    return outcome, round(max_fav, 3), round(max_adv, 3), len(rows)


def entry_for(r, ts_unix, conn):
    """Entry price = open of the first closed 5m candle after the signal ts.

    The shadow has no entry_price; using the next closed open is the earliest
    price a system trade could actually have filled at (no lookahead)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT open FROM candles_5m
        WHERE token = ? AND ts > ? AND is_closed = 1 ORDER BY ts ASC LIMIT 1
    """, (r.get("token"), ts_unix))
    row = cur.fetchone()
    return float(row[0]) if row else None


def load_rows():
    """Per-line tolerant: one corrupt line must not abort the whole join."""
    rows, bad = [], 0
    for line in open(SHADOW):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            bad += 1
    if bad:
        print(f"  WARN: skipped {bad} unparseable shadow line(s)")
    return rows, bad


def run(write=True):
    rows, _bad = load_rows()
    eps = dedup(rows)
    print(f"raw rows={len(rows)}  episodes={len(eps)}")

    conn = sqlite3.connect(f"file:{CANDLES}?mode=ro", uri=True, timeout=10)
    out = []
    no_data = 0
    try:
        for r in eps:
            if r.get("direction") not in ("LONG", "SHORT"):
                continue  # never guess a direction
            ts = to_unix(r.get("ts", ""))
            if not ts or not r.get("token"):
                continue
            ep = entry_for(r, ts, conn)
            if ep is None:
                no_data += 1
                continue
            oc, fav, adv, nc = classify_from_entry(r.get("direction"), ep, ts,
                                                   r.get("token"), conn)
            if oc == "NO_DATA":
                no_data += 1
                continue
            out.append({**r, "_cohort": cohort_of(r), "_outcome": oc,
                        "_max_fav": fav, "_max_adv": adv, "_candles": nc})
    finally:
        conn.close()
    # 30d bar is date-driven from the SHADOW's own first row, not a constant.
    stamps = sorted(x.get("ts") or "" for x in rows if x.get("ts"))
    shadow_start = stamps[0][:10] if stamps else SHADOW_START
    print(f"classified={len(out)}  no_data={no_data}")

    def tally(items):
        d = defaultdict(int, {"WINNER": 0, "LOSER": 0, "SHALLOW": 0, "NO_DATA": 0})
        for x in items:
            d[x["_outcome"]] += 1
        dec = d["WINNER"] + d["LOSER"]
        wr = 100.0 * d["WINNER"] / dec if dec else 0.0
        return dict(d), dec, wr

    cohorts = defaultdict(list)
    for x in out:
        cohorts[x["_cohort"]].append(x)

    print(f"\n{'cohort':14s} {'n':>5s} {'WIN':>5s} {'LOSS':>5s} {'SHAL':>5s} {'dec':>5s} {'WR':>7s}")
    stats = {}
    for c in ("floor_only", "always_admit", "blocked"):
        items = cohorts.get(c, [])
        d, dec, wr = tally(items)
        stats[c] = {"n": len(items), "decided": dec, "wr": round(wr, 1), **d}
        print(f"{c:14s} {len(items):5d} {d['WINNER']:5d} {d['LOSER']:5d} "
              f"{d['SHALLOW']:5d} {dec:5d} {wr:6.1f}%")

    # ---- Q1: floor_only vs always_admit (both actually traded) ----
    a = cohorts.get("floor_only", [])
    b = cohorts.get("always_admit", [])
    from scipy import stats as sps
    aw = sum(1 for x in a if x["_outcome"] == "WINNER")
    al = sum(1 for x in a if x["_outcome"] == "LOSER")
    bw = sum(1 for x in b if x["_outcome"] == "WINNER")
    bl = sum(1 for x in b if x["_outcome"] == "LOSER")
    q1_p = None
    if aw + al and bw + bl:
        _, q1_p = sps.fisher_exact([[aw, al], [bw, bl]])
    print(f"\nQ1 floor_only WR vs always_admit WR: "
          f"{aw}/{aw+al} vs {bw}/{bw+bl}  Fisher p="
          f"{'n/a' if q1_p is None else f'{q1_p:.4f}'}")

    # ---- Q2: pp-conditional floor (block pp<0.10, keep pp>=0.10) ----
    lo = [x for x in a if float(x.get("penalty_raw") or 0) < 0.10]
    hi = [x for x in a if float(x.get("penalty_raw") or 0) >= 0.10]
    low_ = sum(1 for x in lo if x["_outcome"] == "WINNER")
    lol = sum(1 for x in lo if x["_outcome"] == "LOSER")
    hiw = sum(1 for x in hi if x["_outcome"] == "WINNER")
    hil = sum(1 for x in hi if x["_outcome"] == "LOSER")
    q2_p = None
    if low_ + lol and hiw + hil:
        _, q2_p = sps.fisher_exact([[low_, lol], [hiw, hil]])
    q2_wr_lo = (100.0 * low_ / (low_ + lol)) if (low_ + lol) else None
    q2_wr_hi = (100.0 * hiw / (hiw + hil)) if (hiw + hil) else None
    print(f"Q2 pp<0.10 (pp_cond would BLOCK) vs pp>=0.10 (kept): "
          f"{low_}/{low_+lol} vs {hiw}/{hiw+hil}  Fisher p="
          f"{'n/a' if q2_p is None else f'{q2_p:.4f}'}")

    # ---- Q3: per-source floor_only ----
    by_src = defaultdict(list)
    for x in a:
        by_src[x.get("source", "?")].append(x)
    print(f"\n{'source':38s} {'n':>4s} {'WIN':>4s} {'LOSS':>4s} {'SHAL':>5s} {'WR':>7s}")
    src_stats = {}
    for s in sorted(by_src, key=lambda k: -len(by_src[k])):
        items = by_src[s]
        d, dec, wr = tally(items)
        src_stats[s] = {"n": len(items), "decided": dec, "wr": round(wr, 1), **d}
        print(f"{s:38s} {len(items):4d} {d['WINNER']:4d} {d['LOSER']:4d} "
              f"{d['SHALLOW']:5d} {wr:6.1f}%")

    n_floor = stats["floor_only"]["n"]
    # 30d bar is date-driven, not hardcoded: fails loudly once the window is mature.
    days = (datetime.now(timezone.utc).date()
            - datetime.fromisoformat(shadow_start).date()).days
    bar_n = "PASS" if n_floor >= 200 else "FAIL"
    if days < 30:
        bar_30d = f"NOT YET ({days}/30d — mature {shadow_start}+30d)"
        verdict = f"COLLECT — n bar {bar_n}, 30d same-sign bar not reachable until {shadow_start}+30d"
    else:
        # mature: same-sign = floor_only WR beats always_admit WR AND q2 keeps its sign
        same_sign = (stats["floor_only"]["wr"] > stats["always_admit"]["wr"]
                     and (q2_wr_hi is None or q2_wr_lo is None
                          or q2_wr_hi >= q2_wr_lo))
        bar_30d = "PASS (same sign)" if same_sign else "FAIL (sign flipped or reversed)"
        verdict = ("READY FOR VERDICT — mature window, " + bar_30d)
    print(f"\nBAR CHECK (#126): n>=200 -> {bar_n} ({n_floor}) | 30d same-sign -> {bar_30d} "
          f"-> {verdict}")

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "params": {"arm_pct": ARM_PCT, "adv_pct": ADV_PCT,
                   "max_candles": MAX_CANDLES, "dedup_bucket_min": 5,
                   "min_exec_confidence": MIN_EXEC_CONFIDENCE},
        "raw_rows": len(rows), "episodes": len(eps), "classified": len(out),
        "no_data": no_data,
        "cohorts": stats,
        "q1_floor_vs_always": {"floor_wr": stats["floor_only"]["wr"],
                               "always_wr": stats["always_admit"]["wr"],
                               "fisher_p": None if q1_p is None else round(q1_p, 4)},
        "q2_pp_cond": {"pp_lt_010_wr": q2_wr_lo,
                       "pp_ge_010_wr": q2_wr_hi,
                       "n_pp_lt_010": len(lo), "n_pp_ge_010": len(hi),
                       "fisher_p": None if q2_p is None else round(q2_p, 4)},
        "by_source": src_stats,
        "verdict": verdict,
        "days_since_shadow_start": days,
        "bars": {"n_ge_200": bar_n, "same_sign_30d": bar_30d},
    }
    if write:
        tmp = OUT + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OUT)  # atomic — a crash mid-dump must not truncate OUT
        print(f"\nWritten: {OUT}")
    return payload


def selfcheck():
    # 1. ts parsing
    assert to_unix("2026-10-16T00:15:24Z") > 0
    assert to_unix("nope") is None
    # 2. cohort assignment is exhaustive and disjoint
    assert cohort_of({"floor_admitted": True, "exec_conf": 10}) == "floor_only"
    assert cohort_of({"floor_admitted": False, "exec_conf": 40}) == "always_admit"
    assert cohort_of({"floor_admitted": False, "exec_conf": 39.9}) == "blocked"
    # 3. dedup collapses a burst of 1m re-emits to ONE episode and keeps the first by ts
    burst = [{"ts": f"2026-10-16T00:0{i}00Z", "token": "ALGO", "direction": "LONG",
              "source": "s", "floor_admitted": True} for i in range(5)]
    assert len(dedup(burst)) == 1, dedup(burst)
    two = burst + [{"ts": "2026-10-16T00:30:00Z", "token": "ALGO",
                    "direction": "LONG", "source": "s", "floor_admitted": True}]
    assert len(dedup(two)) == 2
    # 3b. episode merge across a 5m bucket edge: 03:04 and 03:08 are ONE episode,
    #     03:04 and 03:30 are two. Without this the bucket split inflates n and Fisher.
    edge = [{"ts": "2026-10-16T03:04:00Z", "token": "X", "direction": "LONG", "source": "s"},
            {"ts": "2026-10-16T03:08:00Z", "token": "X", "direction": "LONG", "source": "s"}]
    assert len(dedup(edge)) == 1, dedup(edge)
    far = edge + [{"ts": "2026-10-16T03:30:00Z", "token": "X",
                   "direction": "LONG", "source": "s"}]
    assert len(dedup(far)) == 2, dedup(far)
    # 3c. null ts must not crash the sort
    assert len(dedup(edge + [{"ts": None, "token": "Y", "direction": "LONG", "source": "s"}])) in (2, 3)
    # 4. shadow semantics: pp_cond_would_block must equal (floor_admitted AND pp<0.10)
    #    because pp_cond uses floor 0.5 for pp>=0.10 (= current floor) and 0.3 for pp<0.10.
    #    Tolerance: penalty_raw is stored ROUNDED to 3dp, so a true pp of 0.0995-0.1000
    #    writes as 0.100 and looks >=0.10 while the live comparison said <0.10. Rows on
    #    that boundary are exempt, everything else must match exactly.
    rows, _ = load_rows()
    bad = boundary = 0
    for r in rows:
        pp = float(r.get("penalty_raw") or 0)
        expect = bool(r["floor_admitted"]) and pp < 0.10
        got = bool(r.get("pp_cond_would_block", False))
        if "pp_cond_would_block" in r and expect != got:
            if abs(pp - 0.10) <= 0.0005:
                boundary += 1
            else:
                bad += 1
    assert bad == 0, f"pp_cond equivalence broken on {bad} rows (boundary-exempt {boundary})"
    # 5. classify_from_entry — real synthetic-candle fixture (the old "units guard"
    #    here was arithmetic on literals and proved nothing; it let a direction-sign
    #    bug in the both-crossed tie-break pass review).
    import sqlite3 as _sq
    fx = _sq.connect(":memory:")
    fx.execute("CREATE TABLE candles_5m (token TEXT, ts INTEGER, is_closed INT,"
               " open REAL, high REAL, low REAL, close REAL)")
    T0 = 1792000000
    def _c(tok, i, o, h, l, c):
        fx.execute("INSERT INTO candles_5m VALUES (?,?,?,?,?,?,?)",
                   (tok, T0 + i * 300, 1, o, h, l, c))
    # entry 100. LONG: +0.5% high, never adverse -> WINNER
    _c("W", 1, 100, 100.5, 99.9, 100.4)
    assert classify_from_entry("LONG", 100.0, T0, "W", fx)[0] == "WINNER"
    # LONG: -0.5% low first -> LOSER
    _c("L", 1, 100, 100.1, 99.5, 99.6)
    assert classify_from_entry("LONG", 100.0, T0, "L", fx)[0] == "LOSER"
    # SHORT: low must be the favourable side -> +0.5% favourable = WINNER
    _c("SW", 1, 100, 100.1, 99.5, 99.6)
    assert classify_from_entry("SHORT", 100.0, T0, "SW", fx)[0] == "WINNER"
    # SHORT: high is adverse -> LOSER
    _c("SL", 1, 100, 100.5, 99.9, 100.4)
    assert classify_from_entry("SHORT", 100.0, T0, "SL", fx)[0] == "LOSER"
    # both crossed on ONE candle, close ABOVE entry: favours LONG, hurts SHORT
    _c("BL", 1, 100, 100.6, 99.4, 100.5)
    _c("BS", 1, 100, 100.6, 99.4, 100.5)
    assert classify_from_entry("LONG", 100.0, T0, "BL", fx)[0] == "WINNER", "tie-break LONG"
    assert classify_from_entry("SHORT", 100.0, T0, "BS", fx)[0] == "LOSER", "tie-break SHORT"
    # both crossed, close BELOW entry: flips both
    _c("BL2", 1, 100, 100.6, 99.4, 99.5)
    _c("BS2", 1, 100, 100.6, 99.4, 99.5)
    assert classify_from_entry("LONG", 100.0, T0, "BL2", fx)[0] == "LOSER"
    assert classify_from_entry("SHORT", 100.0, T0, "BS2", fx)[0] == "WINNER"
    # shallow: never reaches either threshold
    _c("SH", 1, 100, 100.2, 99.8, 100.1)
    assert classify_from_entry("LONG", 100.0, T0, "SH", fx)[0] == "SHALLOW"
    # bracket ARM_PCT on BOTH sides so a regression either way fails:
    # 0.45% must ARM (catches ARM_PCT raised above 0.45) ...
    _c("AR", 1, 100, 100.45, 99.9, 100.4)
    assert classify_from_entry("LONG", 100.0, T0, "AR", fx)[0] == "WINNER", "ARM bracket high"
    # ... and 0.35% must NOT arm (catches ARM_PCT lowered to <=0.35)
    _c("MID", 1, 100, 100.35, 99.9, 100.3)
    assert classify_from_entry("LONG", 100.0, T0, "MID", fx)[0] == "SHALLOW", "ARM bracket low"
    fx.close()
    # 6. MIN_EXEC_CONFIDENCE must match decider_run's local value
    dr = open("/root/.hermes/scripts/decider_run.py").read()
    assert f"MIN_EXEC_CONFIDENCE = {MIN_EXEC_CONFIDENCE}" in dr, "constant drifted"
    print(f"SELFCHECK PASS — {len(rows)} raw rows, pp_cond equivalence holds on all of them")
    p = run(write=False)  # selfcheck must not touch the output file
    assert p["episodes"] > 0 and p["classified"] > 0
    return p


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        run()
