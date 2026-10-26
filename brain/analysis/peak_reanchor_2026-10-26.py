#!/usr/bin/env python3
"""Peak re-anchor selfcheck — run #165 (2026-10-26).

Bug class: brain.py seeds highest_price/lowest_price from creation-time
hl_entry_price; position_manager then rewrites entry_price to HL's entry_px when
they disagree, leaving the seed behind. The two-entry delta then reads as a
phantom favorable peak, so peak-based exits fire on entry disagreement alone.

Evidence: ETH #16421 — creation entry/seed 2301.98 (log: "confirmed on HL @
$2301.982300"), HL truth 2312.60 (log: "[PERSIST] ... entry=2312.6"),
fav = 1 - 2301.98/2312.60 = +0.459% >= PM_TRAIL_ACTIVATE 0.40 -> UGB-PT exit
1.45s after open. Same phantom explains mfe_pct 0.545 on BTC #16384 (entry
80095 / seed 80532) and 14.646 on IMX #16165 — both contaminate the
mfe_pct>=0.40 arm-rate KPI.

Usage:
  python3 brain/analysis/peak_reanchor_2026-10-26.py --selfcheck
"""
import sys

sys.path.insert(0, "/root/.hermes/scripts")

PM = "/root/.hermes/scripts/position_manager.py"


def main():
    import position_manager as pm

    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    # 1. the reported incident re-anchors
    check("ETH16421 short re-anchors",
          pm._reanchor_seed_peak(2301.98, 2312.60, 2301.98) == 2312.60)
    # 2. LONG mirror (BTC 16384 class): creation entry/seed 80532, HL truth 80095
    check("BTC16384 long re-anchors",
          pm._reanchor_seed_peak(80532.0, 80095.0, 80532.0) == 80095.0)
    check("BTC16384 phantom high removed",
          (pm._reanchor_seed_peak(80532.0, 80095.0, 80532.0) or 0) >= 80095.0 - 1e-9)
    # 3. real post-open favorable move is never erased
    check("moved seed preserved",
          pm._reanchor_seed_peak(2301.98, 2312.60, 2295.0) is None)
    # 4. no material entry correction -> no touch
    check("entry==ep untouched",
          pm._reanchor_seed_peak(2312.60, 2312.60, 2312.60) is None)
    check("sub-0.1% delta untouched",
          pm._reanchor_seed_peak(100.0, 100.05, 100.0) is None)
    # 5. degenerate inputs
    check("seed 0 untouched", pm._reanchor_seed_peak(100.0, 105.0, 0.0) is None)
    check("entry 0 untouched", pm._reanchor_seed_peak(0.0, 105.0, 0.0) is None)
    check("negative ep untouched", pm._reanchor_seed_peak(100.0, -1.0, 100.0) is None)
    check("None input untouched", pm._reanchor_seed_peak(100.0, None, 100.0) is None)
    # 6. genuine favorable move with no entry correction -> no touch
    check("real MFE no correction",
          pm._reanchor_seed_peak(2312.60, 2312.60, 2300.0) is None)
    # 7. the corrected fav cannot arm UGB-PT any more
    entry_before, entry_after = 2301.98, 2312.60
    seed_after = pm._reanchor_seed_peak(entry_before, entry_after, entry_before)
    fav_after = (1.0 - seed_after / entry_after) * 100
    check("post-fix fav below 0.40 arm", fav_after < 0.40)

    # 8. wiring: helper is actually called on the rewrite path, and persisted
    src = open(PM).read()
    check("helper defined", "def _reanchor_seed_peak(" in src)
    check("helper called on _ep rewrite",
          "_reanchor_seed_peak(entry, _ep, pos.get(_seed_pk))" in src)
    check("seed persisted in SAME stmt as entry",
          '_set_cols += ", " + _seed_pk + " = %s"' in src)
    check("single UPDATE statement built",
          '"UPDATE trades SET " + _set_cols + ", updated_at = NOW() "' in src)

    # 8b. the second entry-rewrite path (hl-sync-guardian) carries the same guard
    gsrc = open("/root/.hermes/scripts/hl-sync-guardian.py").read()
    check("guardian imports the shared guard",
          "from position_manager import _reanchor_seed_peak" in gsrc)
    check("guardian re-anchors on entry correction",
          "_reanchor_seed_peak(paper_entry, entry_px, _seed)" in gsrc)
    # both guardian call sites (reconcile + mirror-fill writeback, bug_hunter MED#1)
    check("guardian mirror path re-anchors too",
          gsrc.count("_reanchor_seed_peak(") >= 2)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'ok ' if ok else 'FAIL'} {n}")
    if failed:
        print(f"SELF-CHECK FAIL ({len(failed)}/{len(checks)})")
        return 1
    print(f"SELF-CHECK PASS ({len(checks)} assertions)")
    return 0


if __name__ == "__main__":
    if "--selfcheck" not in sys.argv:
        print(__doc__)
        sys.exit(main() if "--run" in sys.argv else 0)
    sys.exit(main())
