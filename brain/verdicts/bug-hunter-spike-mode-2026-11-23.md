# bug_hunter verdict — cef296e2 "MTF spike state" (2026-11-23)

Scope verified: exactly the six commit files — `scripts/spike_state.py`,
`scripts/auto_trader.py`, `scripts/hermes_constants.py`,
`analysis/test_spike_state.py`, `skills/shared/full-analysis/SKILL.md`,
`skills/shared/manual-trade-override/SKILL.md` (409 insertions, 0 deletions).
Harness: `/tmp/spike_harness.py` (mocks + SELECTs only, zero production
writes). Verdict: **regressions GREEN; changes requested — 1 HIGH, 1 MEDIUM,
3 LOW**.

## Verdict table

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| A1 | `test_spike_state.py` 8/8 | **PASS** | `ALL PASS (8/8)` live run |
| A2 | window/limit arithmetic | **PASS** | `LIMIT max(win,200)` L67; `rsi[-min(win,len(rsi)):]` L89 covers exactly the last `win` closes for histories ≥ win+13 (N=200 → closes[20..199]); `closes[-min(win,len):]` L95 |
| A3 | RSI-on-reversed-list | **PASS** | single `closes.reverse()` at L75 precedes every use (L77+, L89, L95); harness §8: monotonic rally → `'up'` (a missing reverse would read it as a dump) |
| A4 | range detector `pos` edges | **PASS** | `hi==lo` → pos=0.5 (unreachable anyway: span=0 < rng); `lo==0` → span=0 L97; last close is inside the window suffix |
| A5 | tier `WWW_DATA` fallback | **PASS + LOW** | production never sets `spike_state.WWW_DATA` → hardcoded default `/var/www/hermes/data` used, file exists, returns cleanly (harness §7) → **F-5 LOW**: `globals().get('WWW_DATA')` L32 is dead code; diverges from `paths.WWW_DATA` if `WWW_DATA_DIR` env override is set |
| A6 | z-tier-first masking / direction | **PASS + LOW** | one-trip design is fine; tier vocabulary is only `STRONG_POS`/`STRONG_NEG` (continuum_engine.py:59-63, :291-300) → sign mapping correct for all values (harness §6, 6/6); direction is **cosmetic for placement** — BOTH sides override regardless of direction (auto_trader.py:1045, 1123) → **F-4 LOW**: reason string claims `(|z| >= 2)` but STRONG trips at \|z\| ≥ 1.5 (continuum_constants.py:28,31) |
| B1 | spike_state exception isolated in keeper | **PASS** | inner `try/except` auto_trader.py:859-863; harness §5: patched `spike_state` to raise → keeper still arms 2 orders (calm), rc clean |
| B2 | override after §17 clamp, no fight | **PASS** | overrides at L1045-1049 (short) / L1123-1127 (long) re-clamp the near edge as input; harness §1: **10/10 proofs** (5 prices × 2 sides) — result always in-band and within one 250-round of the edge (e.g. 61152: short→60500 of edge 60540.5, long→62000 of edge 61763.5) |
| B3 | reach guard vs fixed 1% near edge | **FAIL → F-3 LOW** | harness §4: ATR1h=150 (0.24%) → reach_lo 60702 > near short 60540, reach_hi 61602 < long 61764 → **both arms silently skipped**, no skip log, while the INFO still claims "near-edge placement mode". Arm needs ATR1h ≥ ~0.33% of price. Silent-skip class |
| B4 | long ITM guard order | **PASS** | override L1123-1127 runs **before** guard `price < trig <= reach_hi` L1130; +1% edge always passes ITM. Short mirror: override L1045-1049 before `reach_lo <= trig < price` L1050 |
| B5 | note/log reflects spike-mode? | **FAIL → F-2 MEDIUM (note-lie)** | see below |
| C | RIP-CLIMAX gates NOT bypassed | **PASS (with caveat)** | `_rip_climax_defer` still called for every `btc-auto-*` fill at trade_watchdog.py:2016; the commit does not touch trade_watchdog; keeper diff only reassigns `trig`. Keeper writes **no** `band_exempt` (read-only guard at auto_trader.py:952; writes live only in trade_watchdog:2167,2227 — untouched). No `import trade_watchdog` in auto_trader (no circularity). **Caveat:** the shape validation (trade_watchdog.py:1810-1815) runs *before* the gate → a wrong-shape spike arm never reaches the RIP gates (ties to F-1) |
| D1 | pre-pass vs spike-mode churn / double-run | **PASS** | harness §3: keeper run 2 **byte-identical**, run 3 byte-identical. Why: spike derivations go through the same `_band_clamp` → land in-band → pre-pass skips them at L955; pre-pass touches only the EXISTING nearest out-of-band rung (L936-982), spike affects only NEW derivations (L1045/1123). Production: `pending_orders.json` mtime still 17:46:09 after the live 18:39 cycle + 2 manual runs |
| D2 | `band_exempt` rungs untouched by spike-mode | **PASS** | grep: auto_trader references `band_exempt` only at 948-952 (pre-pass read-skip); spike code (852-873, 1045-1049, 1123-1127) never touches it |
| E1 | py_compile ×4 | **PASS** | spike_state, auto_trader, hermes_constants, trade_watchdog → COMPILE_OK |
| E2 | test_rip_climax 7/7 | **PASS** | `ALL PASS (7/7)` |
| E3 | test_pending_machine ALL PASS | **PASS** | `ALL PENDING-MACHINE TESTS PASS` |
| E4 | test_manual_exit_manager 20/20 | **PASS** | `20 passed, 0 failed` |
| E5 | ONE live run_cycle rc=0 | **PASS (ran ×2 — disclosed)** | `python3 scripts/auto_trader.py` rc=0 both times. Exact summary (2nd run, `/tmp/bh_runcycle.json`): `enabled:true, mode:"live", decision:"BRACKET", price:61582.75, scores long -40 / short 20, regime CHOP, shadow_armed:[], live_armed:[], armed_detail:[], hypotheticals:0`. **No SPIKE STATE line at 19:09** (state had receded to None — fail-open correct). The sanctioned production cycle **18:39:55 did log**: `ladder_keeper: SPIKE STATE down (the window range 3.1% >= 3% with the close at the bottom third) — the near-edge placement mode (1% both sides)` — state `down`, range detector. (2nd run was to capture the summary head — one run over the sanction; both idempotent, zero config writes) |
| E6 | logs since 18:00: 0 Tracebacks | **PASS** | pipeline.log: 0 Tracebacks (0 ever); trade-watchdog.log from line 436696 (18:09): 0 Tracebacks; 0 `auto_trader cycle failed`; pipeline.err.log empty (0 lines) |
| E7 | two SKILL.md intact | **PASS** | full-analysis **1501** lines (parent 1461 +40 ✓); manual-trade-override **529** (parent 503 +26 ✓) — matches diff stat, no truncation. Greps: `MTF Spike State (COMPUTED)` L1230, template `SPIKE STATE:` L1450, `SPIKE-MODE PLACEMENT` L499 — sections read in full, coherent |
| E8 | scope = six files | **PASS** | `git show --stat` = exactly the 6 files. Working tree has parallel modifications (automation/*, brain.py, decider_run, hermes_constants **hedge-append only** — spike/RIP constants untouched, position_manager, trade_watchdog, hedge_leg.py untracked) — all outside the commit; auto_trader.py + spike_state.py clean vs HEAD |

## Note-lie check (F7) — CONFIRMED MEDIUM

A spike-mode arm's note claims the **structure source** with a derivation that
never happened. Shipped-fixture arm (harness §2):

- short note: `... 1h MAJOR-floor break: trigger 60500 (sl1h−60 = 59929 →
  band-clamped 60500), SL 60199 = sl1h+0.6·ATR15 reclaim (break failed), TP
  58940 ...` — the §17 clamp of 59929 yields the **far** edge (59930), not
  60500; the actual derivation (`price×0.99` near edge) is never named; event
  tag `_ev` = `"1h-floor"` (L1083), appended detail `(1h-floor, ...)`.
- long note: `... Reclaim of the 1h major ceiling 62100: trigger 62000
  (sh+60) ...` — 62160 ≠ 62000, near-edge derivation unnamed.
- Zero occurrences of "spike" in either note (harness S3), while the
  `SPIKE STATE` INFO (L870-873) does name it — the log is honest, the
  **order note lies**. `_src1h` captured at L1037 (pre-override) feeds both
  the SL source (correct — SL really is structure) and the note text (wrong).
  Lines: auto_trader.py:1069-1090 (short), 1142-1149 (long), 1098/1109 event.

## Double-run idempotency proof

Fixture: price 61152, tier STRONG_POS, empty config (harness §3):

```
run1 -> short 60500 (sl 60199 tp 58940) + long 62000 (sl 61890 tp 63560)
run2 -> cfg byte-identical to run1  (PASS)
run3 -> cfg byte-identical to run2  (PASS)
```

Production corroboration: `data/pending_orders.json` mtime `2026-11-23
17:46:09` — unchanged through the 18:39 live spike-state cycle and both
manual runs (readiness satisfied by existing in-reach rungs; no derivation,
no write).

## Findings (severity + line refs)

**F-1 — HIGH — spike-mode short arm can be dead-on-arrival (wrong-side SL →
shape-skip → dark side).** The override moves only the trigger (near edge,
~1% below price) while the SL stays at the structure
(`sl1h+0.6·ATR15`, L1056). Whenever the 1h floor sits deeper than ~1% +
0.6·ATR15 below price — routine in the vertical-move spike that trips
detector 3 — `sl < trigger`, violating trade_watchdog's shape rule
(`target < trigger < sl`, trade_watchdog.py:1813-1814) → the fill is
**skipped every cycle** (WARN spam; precedent: `btc-auto-ladder-1795442993`
WARNed 14:39→16:39 today), the arm never reaches the RIP-CLIMAX gate, and
the keeper counts it as ready (L985-990) → **no replacement derivation = short
side dark**. The §17 pre-pass cannot heal it: spike arms are in-band by
construction (L955 skip) — the pre-pass healed today's §17 instance only
because that one was out-of-band. Proof in the shipped test's own fixture:
trigger 60500 / sl 60199 / tp 58940 → 60500 < 60199 is false. Same class on
the long side when the ceiling is ≳1.6% above price (SL above trigger,
trade_watchdog.py:1810). No money is lost (validation blocks the fill) — the
failure is the feature silently not working + self-suppressing. In a pump the
long usually survives; the **closer short — the CEO's headline ask — is the
one that dies**. Lines: auto_trader.py:1044-1063 (short), 1122-1134 (long),
985-990 (readiness), 955 (pre-pass skip), trade_watchdog.py:1810-1815.

**F-2 — MEDIUM — note-lie (F7)**: per above. The arm's note/event names a
derivation that did not happen; review-by-note reads it as a structure break.

**F-3 — LOW — silent reach-skip**: ATR1h < ~0.33% of price → the fixed 1%
near edge is outside 3·ATR1h → both guards fail, no arm, no log, while the
INFO claims the placement mode (auto_trader.py:919-920, 1050, 1130; harness §4).

**F-4 — LOW — wrong threshold in the reason string**: `(|z| >= 2)`
(spike_state.py:58, :12) vs actual STRONG at \|z\| ≥ 1.5
(continuum_constants.py:28,31). Copied from the watchdog docstring; means the
state trips more often than the log claims.

**F-5 — LOW — dead `WWW_DATA` lookup**: `globals().get('WWW_DATA')` is always
None in production (only `HERMES_DATA` is imported, spike_state.py:27) →
hardcoded default; correct today, diverges under a `WWW_DATA_DIR` override
(spike_state.py:32; paths.py:59).

**F-8 — INFO — spike short keeps `entry_style='retest'`** (L1097): even a
shape-valid near-edge short fills only on break→reclaim→re-cross, never on
first touch — softens the "reversal catch" the CEO described (calm logic
unchanged; design question, not a regression).

**INFO — RSI loop off-by-one** (spike_state.py:85-88): first iteration
re-consumes `g[13]`, duplicating RSI(14) and double-counting the last gain in
the smoothing base. Measured vs reference Wilder: max |Δ| 7.6 confined to the
first ~3 values (decays (13/14)^k); **0 verdict flips** (≥90/≤10) across every
window position in a 400-bar random walk; in-window only for histories
< ~194 closes. No action needed.

**INFO — both-conditions precedence** (spike_state.py:90-93): pump-then-dump
inside the window returns `'up'` (max checked first). Acceptable: direction
is informational (both sides override regardless) and `'up'` = the spike's
direction, which is the CEO's framing.

**INFO — revert coupling** (spike_state.py:51-52): `not (top and win and rng)`
means `SPIKE_RANGE_PCT=0` also kills the RSI+tier detectors (documented revert
is `RIP_RSI_TOP=0`, which works — test 5 ✓).

## Overall verdict

**CHANGES REQUESTED.** Every specified regression gate is green (4 suites,
py_compile, live rc=0 with a real `SPIKE STATE down` log from the sanctioned
18:39 cycle, 0 tracebacks, skills intact, scope clean, double-run stable,
gates not bypassed). But the feature's primary deliverable — the closer
shorts — is **dead-on-arrival in its primary scenario** (F-1 HIGH), and the
arm notes misreport the derivation (F-2 MEDIUM). F-1 is a placement/SL
coupling bug, not a fill-safety bug: validation blocks the bad fill, so
exposure is the silent dark side + WARN spam, not money.
