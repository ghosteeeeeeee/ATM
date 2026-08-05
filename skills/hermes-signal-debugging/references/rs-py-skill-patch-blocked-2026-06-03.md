# hermes-signal-debugging skill update — 2026-06-03

## Changes made

Added reference document: `references/rs-py-short-bias-2026-06-03.md`
Contains full investigation notes on the rs.py SHORT bias question.

## Planned trigger patch (blocked — YAML structure issue)

The SKILL.md has a YAML frontmatter problem: the description field appears to span multiple lines (no pipe `|` or indentation) causing subsequent list items to be parsed as part of the description. This prevents patching the triggers section.

**To fix later**: The SKILL.md frontmatter needs YAML multiline formatting for the description, OR the description needs to be on a single line. After fixing, add these triggers:

```yaml
  - "why are we only firing SHORTs"   # refs: rs-py-short-bias-2026-06-03.md
  - "LONGs not doing well"            # refs: rs-py-short-bias-2026-06-03.md
```

## Key findings captured in reference doc

1. Directional accuracy: SHORTs 57% WR, LONGs 50% WR — no code bug in signal direction
2. SHORT skew comes from market regime (65/69 NEUTRAL tokens negative slope = downtrend)
3. Structural asymmetry: rs-r-broken fallthrough to SHORT path (line 625 → 660) — minor, not the root cause
4. Real root cause: ATR stops too tight (~1%) relative to candle noise — 30/31 losers hit atr_sl_hit
5. Improvement: regime alignment check before confluence gate to suppress anti-regime LONGs

## Action items
- [ ] Fix YAML frontmatter in hermes-signal-debugging SKILL.md (description multiline issue)
- [ ] Patch triggers section once YAML is fixed