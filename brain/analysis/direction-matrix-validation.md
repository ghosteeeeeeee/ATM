# Direction Matrix v1 — validation gate (spec §2.5)

Generated: 2026-11-23T01:41:35Z · mode=validate · reproduce: `python3 scripts/dir_matrix.py validate`
Spec: brain/plans/direction-matrix-spec.md (v1.0, 2026-11-22) · data: local `/root/.hermes/data/candles.db` ONLY (SELECT-only, mode=ro, is_closed=1, token=BTC, cursors closed in finally) · NO external API · model: StandardScaler→LogisticRegression(C=1.0, L2, random_state=42), per horizon, 30d rolling window.
ε fixed: 15m=5bps 1h=10bps 4h=20bps (ε = 5bps·√(H_min/15); spec-fixed table) (printed every run)

## Data pin (§15.6) — window bounds + row count + sha of candle slice

| horizon tier | window [first_close .. last_close] UTC | rows | sha256 |
|---|---|---|---|
| candles_15m (H=15m) | [2026-10-24 01:15 .. 2026-11-23 01:15] | 2881 | `cc2e388c6db5cac3c40d53f0baa08cb3e16f95e5041221556c198418fc1f1e69` |
| candles_1h (H=1h) | [2026-10-24 00:00 .. 2026-11-23 00:00] | 721 | `b3043d6b072e9cab8f588664459cdebad0cdbd8e5cf74380f90651e6805c305c` |
| candles_4h (H=4h) | [2026-10-24 00:00 .. 2026-11-23 00:00] | 181 | `420d1309262bc85784059702f144605783d74edef6b4a6c523ae9e9e90b31f21` |

## Gate definitions (pre-registered §2.5, judged per horizon, never pooled)

- Walk-forward inside the 30d window: train first 80% → test last 20% (k = 20% of window).
- **(a)** Brier(p) < Brier(base-rate predictor = TRAIN class frequencies), day-cluster-robust 95% t-CI of per-row difference excludes 0 (upper bound < 0).
- **(b)** calibration-in-the-large: max_c |mean p_c − freq_c(test)| ≤ 0.05; top decile by claimed p_up: day-cluster 95% CI of empirical up-frequency contains the claimed mean p_up.
- **(c)** n disclosed per horizon; 4h judged alone. UNSTABLE-LOW-N flag if window n < 300.
- Brier = mean_i Σ_c (p_ic − y_ic)² (3 classes, range 0..2).

## Results per horizon

### 15m — UNVALIDATED

- n: window n=2880 (30d, window=[2026-10-24 01:15 .. 2026-11-23 01:15]), train n=2304, test n=576 over 7 days
- (a) Brier_model=0.6748 vs Brier_base=0.6533, diff=0.0215, day-cluster 95% CI [-0.0047, 0.0517] p=0.08745 → FAIL
- (b) calibration-in-the-large: up |0.060|, side |0.076|, down |0.136| → max=0.1357 > 0.05 → FAIL; top decile p_up≥0.440: n=58, claimed mean p=0.482, empirical up freq=0.431, day-cluster 95% CI [0.303, 0.809] → PASS → (b) FAIL
- (c) n disclosed: window n=2880, train n=2304, test n=576; 4h judged alone (no pooling) → PASS
- train class freq (up/side/down) = 0.330/0.303/0.367 (n=2304) · test freq = 0.377/0.188/0.436 (n=576) · mean p = 0.317/0.112/0.571

### 1h — UNVALIDATED

- n: window n=720 (30d, window=[2026-10-24 00:00 .. 2026-11-23 00:00]), train n=576, test n=144 over 6 days
- (a) Brier_model=0.6755 vs Brier_base=0.6476, diff=0.0279, day-cluster 95% CI [-0.0690, 0.1249] p=0.4923 → FAIL
- (b) calibration-in-the-large: up |0.076|, side |0.008|, down |0.084| → max=0.0839 > 0.05 → FAIL; top decile p_up≥0.457: n=15, claimed mean p=0.550, empirical up freq=0.333, day-cluster 95% CI [-0.189, 0.606] → PASS → (b) FAIL
- (c) n disclosed: window n=720, train n=576, test n=144; 4h judged alone (no pooling) → PASS
- train class freq (up/side/down) = 0.321/0.300/0.378 (n=576) · test freq = 0.375/0.160/0.465 (n=144) · mean p = 0.299/0.152/0.549

### 4h — UNVALIDATED **UNSTABLE-LOW-N**

- n: window n=180 (30d, window=[2026-10-24 00:00 .. 2026-11-23 00:00]), train n=144, test n=36 over 6 days
- (a) Brier_model=0.9630 vs Brier_base=0.6390, diff=0.3240, day-cluster 95% CI [0.0998, 0.5483] p=0.0138 → FAIL
- (b) calibration-in-the-large: up |0.036|, side |0.101|, down |0.065| → max=0.1012 > 0.05 → FAIL; top decile p_up≥0.960: n=4, claimed mean p=0.987, empirical up freq=0.500, day-cluster 95% CI [-0.742, 1.742] → PASS → (b) FAIL
- (c) n disclosed: window n=180, train n=144, test n=36; 4h judged alone (no pooling) → PASS · **UNSTABLE-LOW-N (n < 300)**
- train class freq (up/side/down) = 0.312/0.306/0.382 (n=144) · test freq = 0.444/0.028/0.528 (n=36) · mean p = 0.408/0.129/0.463

## Verdicts

| horizon | (a) Brier vs base | (b) calibration | (c) n | flag | VERDICT |
|---|---|---|---|---|---|
| 15m | FAIL (Δ=0.0215, CI [-0.0047, 0.0517]) | FAIL (CITL max 0.1357, topdec PASS) | n_window=2880 n_test=576 | — | **UNVALIDATED** |
| 1h | FAIL (Δ=0.0279, CI [-0.0690, 0.1249]) | FAIL (CITL max 0.0839, topdec PASS) | n_window=720 n_test=144 | — | **UNVALIDATED** |
| 4h | FAIL (Δ=0.3240, CI [0.0998, 0.5483]) | FAIL (CITL max 0.1012, topdec PASS) | n_window=180 n_test=36 | UNSTABLE-LOW-N | **UNVALIDATED** |

Status written to `data/dir_matrix_state.json`. Consumers v1: informational only — any trading-path consumer requires validated status + shadow wiring (automatic-implementation) + CEO approval (spec §2.5).

Reproduce: `python3 scripts/dir_matrix.py validate` · selfcheck: `python3 scripts/dir_matrix.py --selfcheck`
