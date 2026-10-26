#!/usr/bin/env python3
"""cluster_t — cluster-robust t-statistic for event-level shadow instruments.

WHY (brain_auditor run #160, 2026-10-26):
expiry_shadow / gate_shadow emit one ROW PER SIGNAL EVENT, but events repeat
over the SAME tokens (79-102 distinct tokens per 14-30d cohort). Treating rows
as independent inflates t by ~sqrt(events/tokens) — pseudo-replication.

Measured this run (excess_4h, events / CR1 t / naive t):
  SKIPPED SHORT 14d  n=1517  G=79   +0.3223   t=+2.13  naive=+6.64
  SKIPPED SHORT 30d  n=1901  G=80   +0.2269   t=+1.72  naive=+4.81
  SKIPPED LONG  14d  n=2013  G=76   -0.1877   t=-1.40  naive=-4.16
  EXPIRED LONG  14d  n=4312  G=101  -0.0994   t=-1.37  naive=-3.24
Every prior "gates save money (t=-3.00)" and "short-supply edge (t=+4.22)"
claim in runs #76/#153 used the naive column. Under CR1, no cohort in the
instrument reaches |t|>=2 at BOTH 14d and 30d.

Formula (CR1 sandwich, intercept-only): beta = mean(y);
  S_g = sum_{i in g} (y_i - beta);  SE = sqrt(G/(G-1) * sum_g S_g^2) / N;
  t = beta / SE.  Keeps the event-weighted estimand, corrects only the SE —
  unlike taking token-means, which silently re-weights one-off tokens equal
  to the most active one.

Usage:
    from cluster_t import cluster_t
    t, beta, G = cluster_t(values, clusters)
    python3 brain/analysis/cluster_t.py --selfcheck
"""
import math
import sys
from collections import defaultdict


def cluster_t(values, clusters):
    """CR1 cluster-robust t for the mean of `values`, clustered on `clusters`.

    Returns (t, beta, n_clusters). Raises ValueError on <2 clusters.
    """
    if len(values) != len(clusters):
        raise ValueError("values and clusters must be the same length")
    n = len(values)
    if n < 2:
        raise ValueError("need at least 2 observations")
    beta = sum(values) / n
    grouped = defaultdict(float)
    for v, g in zip(values, clusters):
        grouped[g] += v - beta
    g = len(grouped)
    if g < 2:
        raise ValueError("need at least 2 clusters")
    se = math.sqrt((g / (g - 1)) * sum(s * s for s in grouped.values())) / n
    if se == 0:
        return (0.0 if beta == 0 else math.copysign(float("inf"), beta)), beta, g
    return beta / se, beta, g


def naive_t(values):
    n = len(values)
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    return 0.0 if sd == 0 else m / (sd / math.sqrt(n))


def _selfcheck():
    import random
    rng = random.Random(20261026)

    # 1. Pseudo-replication: 20 clusters x 50 near-identical draws, cluster
    #    means ~0. Naive t must look huge, CR t must NOT.
    vals, cl = [], []
    for c in range(20):
        cm = rng.uniform(-0.05, 0.05)          # true cluster effect ~ 0
        for _ in range(50):
            vals.append(cm + rng.gauss(0, 0.01))
            cl.append(c)
    tn, tc_null = naive_t(vals), cluster_t(vals, cl)[0]
    assert abs(tn) > 3, f"naive t should be inflated, got {tn:.2f}"
    assert abs(tc_null) < 2.5, f"cluster t should deflate, got {tc_null:.2f}"
    assert abs(tc_null) < abs(tn), "cluster t must be <= naive t in magnitude"

    # 2. Real common effect: 40 clusters, all shifted -0.10, tiny noise.
    #    CR t must stay strongly significant (deflation must not eat truth).
    vals, cl = [], []
    for c in range(40):
        for _ in range(30):
            vals.append(-0.10 + rng.gauss(0, 0.02))
            cl.append(c)
    tc_eff = cluster_t(vals, cl)[0]
    assert tc_eff < -5, f"cluster t missed a real common effect: {tc_eff:.2f}"

    # 3. Degenerate input rejected.
    for bad in ([1.0], [1.0, 2.0]):
        try:
            cluster_t(bad, ["a"] * len(bad))
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad}")

    # 4. Exact hand-computed CR1 value: beta=3, S=[-3,3], G=2, N=4 ->
    #    SE = sqrt(2*18)/4 = 1.5, t = 2.0 exactly. Catches any formula
    #    drift (e.g. dropping G/(G-1) gives 2.83, an SE off by /N gives
    #    something else entirely) that the loose statistical asserts above
    #    would let through.
    t4 = cluster_t([1.0, 2.0, 3.0, 6.0], ["a", "a", "b", "b"])[0]
    assert abs(t4 - 2.0) < 1e-12, f"CR1 formula drift: expected 2.0, got {t4}"

    print("cluster_t --selfcheck PASS "
          f"(pseudo-rep naive={tn:+.2f} -> CR={tc_null:+.2f}; "
          f"common-effect CR={tc_eff:+.2f}; degenerate inputs rejected)")
    return True


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(0 if _selfcheck() else 1)
    print(__doc__)
