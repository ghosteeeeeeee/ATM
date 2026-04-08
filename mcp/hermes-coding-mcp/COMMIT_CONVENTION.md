# Better Coder - Git Commit Convention

**Branch:** `feat/better-coder`  
**Strategy:** Trunk-based with short-lived feature branches  
**All work happens on `feat/better-coder` until merged to `main`

---

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only changes |
| `style` | Formatting, whitespace (no code change) |
| `refactor` | Code change that neither fixes bug nor adds feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Build process, tooling, dependencies |
| `build` | Changes that affect build system |
| `ci` | Changes to CI configuration |
| `revert` | Revert a previous commit |

### Scope

The `scope` is the affected component:

- `router` - Tool router, embeddings
- `react` - ReAct state machine
- `server` - MCP server implementation
- `tools` - Individual tool implementations
- `mcp` - MCP integration
- `docs` - Documentation

### Examples

```bash
feat(router): add embeddings-based tool routing

Implements route_task() using sentence-transformers/all-MiniLM-L6-v2
with cosine similarity, name boost, and pattern boost. Falls back to
search_code when confidence < 0.3.

Closes #1

fix(server): handle empty command gracefully

Returns proper error JSON instead of crashing on empty command string.

docs(readme): add installation instructions

chore: add sentence-transformers to requirements.txt
```

---

## Branch Strategy

### Active Development

```bash
# All work on feat/better-coder
git checkout feat/better-coder

# Make atomic commits
git add <changed files>
git commit -m "feat(router): add cosine similarity scoring"

# Push changes
git push origin feat/better-coder
```

### Merging to Main

When ready to merge:
1. Rebase on latest `main`
2. Squash commits into logical units if needed
3. Create PR or merge directly
4. Delete `feat/better-coder` after merge

```bash
# Rebase on main before merge
git fetch origin
git rebase origin/main

# Force push (safe for feature branch)
git push --force-with-lease origin feat/better-coder
```

---

## File Change Guidelines

### Atomic Commits

Each commit should:
- Do ONE thing (fix one bug, add one feature)
- Be self-contained (can be reverted independently)
- Include tests for new behavior
- Update docs if behavior changes

### Good Commit Messages

- Subject line ≤ 72 characters
- Use imperative mood: "add" not "added" or "adds"
- Don't end subject line with period
- Body explains **what** and **why**, not how

### Commit Frequency

- Commit early and often during development
- Rebase/squash before merging to main
- Each commit on `feat/better-coder` should be meaningful
