---
name: skill-authoring-thin-wrapper
description: How to author Hermes skills that delegate to subagent persona files — keep SKILL.md minimal, one source file, nothing else.
triggers:
  - create a skill
  - skill file structure
  - subagent wrapper skill
---

# Skill Authoring: Thin Wrapper Pattern

When creating a skill that delegates to a subagent persona file (`.md` in `subagents/`):

## Rule: One source file, nothing else in SKILL.md

```markdown
---
name: my-persona
description: Delegates to the subagent persona at subagents/specialized/my-persona.md
---

# My Persona

Delegates to: `.hermes/subagents/specialized/my-persona.md`
```

That is the entire SKILL.md. Nothing more.

## Why

- The subagent markdown file IS the authoritative definition — duplicating it into SKILL.md creates divergence risk
- Skills are metadata + routing, not content storage
- Keep SKILL.md under 20 lines

## Anti-pattern (don't do this)

A SKILL.md that contains:
- The full persona prompt duplicated from the subagent file
- Multiple file references
- Detailed instructions that belong in the subagent

## Correct structure

```
SKILL.md              ← thin wrapper, 10-15 lines
subagents/X/          ← actual persona content lives here
```

## Loading

When `skill_view(name)` is called, the skill system reads SKILL.md and makes the subagent file available via `file_path` parameter.
