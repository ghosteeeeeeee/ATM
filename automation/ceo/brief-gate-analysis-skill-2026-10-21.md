# CEO Brief: Gate/Filter Analysis + Shadow Skill + T's Directive

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-21 00:10 UTC
**Priority:** HIGH — Gate analysis findings + T's new directive

## TLDR

1. **Gate analysis complete**: CONFLUENCE-EXPIRY is the ONLY gate that's HELPING (blocked 7711 signals that would have lost -903%). All other gates are neutral or unmeasurable.
2. **Shadow-analysis skill created**: `skills/shared/shadow-mode-analysis/SKILL.md` with 11 analysis frameworks.
3. **T's new directive**: "I also want to turn on all our old signals in shadow-mode."

## Gate/Filter Analysis Results

### Which gates are HELPING vs HURTING?

| Gate | Blocked | Would Win | Total PnL | Verdict |
|------|---------|-----------|-----------|---------|
| CONFLUENCE-EXPIRY | 7,711 | 48.5% | **-903.1%** | **HELPING** |
| CTX-GATE | 120 | 39.2% | -27.2% | NEUTRAL |
| UNKNOWN | 38 | 52.6% | -5.6% | NEUTRAL |

**CONFLUENCE-EXPIRY is HELPING** — it blocked 7711 signals that would have lost -903%. The confluence gate is doing its job.

### Single vs Multi-Source

| Source Type | n | WR | Total | Avg |
|-------------|---|-----|-------|-----|
| Single-source | 7,555 | 49.1% | **-922.7%** | -0.122% |
| Multi-source | 531 | 33.9% | -76.2% | -0.144% |

Single-source signals account for most of the losses (-922.7% vs -76.2%).

### Confidence Threshold Doesn't Help

| Threshold | n | WR | Total | Avg |
|-----------|---|-----|-------|-----|
| conf>=60 | 8,086 | 48.1% | -998.9% | -0.124% |
| conf>=70 | 7,822 | 48.6% | -972.7% | -0.124% |
| conf>=80 | 4,213 | 42.5% | -477.5% | -0.113% |
| conf>=85 | 3,308 | 40.1% | -378.2% | -0.114% |

Higher confidence doesn't correlate with better performance.

### RSI Bands

| RSI Band | n | WR | Total | Avg |
|----------|---|-----|-------|-----|
| 30-40 | 1,181 | **49.4%** | -99.6% | **-0.084%** |
| 50-60 | 1,398 | **51.7%** | -159.1% | -0.114% |
| 60-70 | 1,091 | 46.9% | -203.5% | **-0.186%** |

RSI 30-40 is the best band but still negative.

### Direction x Regime

| Direction | Regime | n | WR | Total | Avg |
|-----------|--------|---|-----|-------|-----|
| SHORT | HIGH | 1,869 | **53.8%** | -126.7% | **-0.068%** |
| SHORT | NORMAL | 779 | 52.1% | -77.4% | -0.099% |
| LONG | HIGH | 1,087 | 45.4% | -209.2% | **-0.192%** |

SHORT HIGH is the best combo (WR=53.8%) but still negative.

## Shadow-Analysis Skill Created

**`skills/shared/shadow-mode-analysis/SKILL.md`** — 11 analysis frameworks:
1. Overall health check
2. Direction analysis
3. Exit engine analysis
4. Hold time analysis
5. Gate/filter analysis
6. Confidence threshold analysis
7. RSI filter analysis
8. Direction x Regime cross-analysis
9. Token analysis
10. Flip test
11. Parameter sweeps

**`scripts/shadow_mode_analysis.py`** — standalone script with `--full`, `--gates`, `--summary` modes.

Usage:
```bash
python3 scripts/shadow_mode_analysis.py          # Full analysis
python3 scripts/shadow_mode_analysis.py --gates  # Gate analysis only
python3 scripts/shadow_mode_analysis.py --summary # One-line summary
```

## T's New Directive

> "I also want to turn on all our old signals in shadow-mode."

T wants to enable ALL old/disabled signals in shadow mode to collect data on them. This would include:
- Signals that were disabled for poor performance
- Signals that are currently blocked by gates
- Signals that are in the STANDALONE_BYPASS list but not firing

**Goal**: Collect shadow data on ALL signals to see which ones might be profitable with different filters/exits.

## CEO Decision Needed

1. **Should we turn on all old signals in shadow mode?** (T directive)
2. **How do we handle signals that are in CEO_PROTECTED_FLAGS?**
3. **Should we add a shadow-only bypass list** for signals that are currently blocked?

## What T Wants

T wants comprehensive shadow data on ALL signals, not just the ones currently firing. This would give us the data to make informed decisions about which signals to re-enable.

## Protected Flags

13/13 INTACT. No config changed in this brief.
