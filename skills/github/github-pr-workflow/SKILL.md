---
name: github-pr-workflow
title: GitHub Workflow
description: "Full GitHub workflow: auth, repos, PRs, code review, issues. Branch, commit, push, open PR, monitor CI, review, merge, and manage issues — via `gh` CLI when available or `git` + `curl` fallback."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge, Auth, Issues, Code-Review, Repositories, Releases, Secrets]
    related_skills: [hermes-agent]
---

# GitHub Workflow

End-to-end GitHub operations for an autonomous agent. Covers the full lifecycle:

1. **Section 1 — Authentication** (setup once, reuse everywhere)
2. **Section 2 — Repositories** (clone, create, fork, releases, secrets, Actions)
3. **Section 3 — Pull Requests** (branch, commit, push, open, monitor CI, merge)
4. **Section 4 — Code Review** (review local diffs, review PRs, post inline comments)
5. **Section 5 — Issues** (create, triage, label, assign, close)

All sections use `gh` first, then `git` + `curl` fallback for machines without `gh`. The setup block at the top of every section resolves `AUTH` (gh or curl), `OWNER`, `REPO`, and `GH_USER` once per command.

## When to Use

- Working in any git repo with a GitHub remote
- Creating/reviewing PRs, issues, releases
- Setting up CI/CD, secrets, branch protection
- Code review (local diffs or remote PRs)
- Repository management (clone, create, fork, sync)

## Quick Auth Detection (use at start of every section)

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

# Extract owner/repo from git remote (works with HTTPS and SSH)
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)

# Username (needed for repo management)
if [ "$AUTH" = "gh" ]; then
  GH_USER=$(gh api user --jq '.login')
else
  GH_USER=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin)['login'])")
fi
```

A reusable version of this setup is at `scripts/gh-env.sh` — `source` it instead of inlining.

---

# Section 1 — Authentication

Two paths: **`git`-only** (no `gh` needed, no sudo) and **`gh` CLI** (richer API, simpler auth).

## Detection Flow

```bash
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"
```

**Decision tree:**
1. `gh auth status` authenticated → use `gh` for everything
2. `gh` installed but not authenticated → use "gh auth login" method
3. No `gh` → use git-only method (HTTPS token or SSH)

## Method 1: Git-Only (No gh, No sudo)

### HTTPS with Personal Access Token (recommended)

1. User goes to **https://github.com/settings/tokens** → "Generate new token (classic)"
2. Scopes: `repo`, `workflow`, `read:org` (if org repos)
3. Configure git:

```bash
git config --global credential.helper store
git ls-remote https://github.com/<user>/<any-repo>.git   # prompted for creds — paste token as password
```

**Cache helper (in-memory, 8h):**

```bash
git config --global credential.helper 'cache --timeout=28800'
```

**Per-repo embedded token (no prompts):**

```bash
git remote set-url origin https://<user>:<token>@github.com/<owner>/<repo>.git
```

**Set git identity (required for commits):**

```bash
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```

### SSH Keys

```bash
# Generate if missing
[ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub   # add to https://github.com/settings/keys

# Test
ssh -T git@github.com

# Auto-rewrite HTTPS → SSH
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

## Method 2: gh CLI

```bash
# Browser (desktop)
gh auth login
# Headless
echo "$TOKEN" | gh auth login --with-token
gh auth setup-git
# Verify
gh auth status
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `git push` asks for password | Passwords disabled. Use PAT as password or switch to SSH |
| `Permission to X denied` | Token missing `repo` scope — regenerate |
| `Authentication failed` | Stale creds — `git credential reject` then re-auth |
| SSH `Connection refused` port 22 | Use port 443 — `Host github.com` with `Port 443` and `Hostname ssh.github.com` in `~/.ssh/config` |
| Creds not persisting | `git config --global credential.helper` must be `store` or `cache` |
| Multiple GitHub accounts | SSH with per-host keys in `~/.ssh/config`, or per-repo credential URLs |
| `gh: command not found` + no sudo | Use Method 1 — no installation needed |

---

# Section 2 — Repositories

## Cloning

```bash
# HTTPS
git clone https://github.com/owner/repo.git
git clone --depth 1 https://github.com/owner/repo.git
git clone --branch develop https://github.com/owner/repo.git

# gh shorthand
gh repo clone owner/repo
```

## Creating

```bash
# gh
gh repo create my-new-project --public --clone
gh repo create my-new-project --private --description "A tool" --license MIT --clone
gh repo create my-org/my-new-project --public --clone
gh repo create my-project --source . --public --push   # from local dir

# curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user/repos \
  -d '{"name":"my-new-project","description":"A tool","private":false,"auto_init":true,"license_template":"mit"}'
```

## Forking

```bash
gh repo fork owner/repo --clone
# curl + git
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/repos/owner/repo/forks
sleep 3
git clone https://github.com/$GH_USER/repo.git
cd repo && git remote add upstream https://github.com/owner/repo.git
```

### Keeping a Fork in Sync

```bash
git fetch upstream
git checkout main && git merge upstream/main && git push origin main
# or
gh repo sync $GH_USER/repo-name
```

## Repository Info

```bash
gh repo view owner/repo
gh repo list --limit 20
gh search repos "machine learning" --language python --sort stars
```

## Settings

```bash
gh repo edit --description "..." --visibility public
gh repo edit --enable-wiki=false --enable-issues=true
gh repo edit --default-branch main
gh repo edit --add-topic "ml,python"
gh repo edit --enable-auto-merge
```

## Branch Protection

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{
    "required_status_checks":{"strict":true,"contexts":["ci/test","ci/lint"]},
    "enforce_admins":false,
    "required_pull_request_reviews":{"required_approving_review_count":1},
    "restrictions":null
  }'
```

## Secrets (GitHub Actions)

`gh` is dramatically simpler — use it whenever possible:

```bash
gh secret set API_KEY --body "your-secret-value"
gh secret set SSH_KEY < ~/.ssh/id_rsa
gh secret list
```

For curl (requires PyNaCl for encryption), see `references/github-api-cheatsheet.md`.

## Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release create v2.0.0-rc1 --draft --prerelease --generate-notes
gh release create v1.0.0 ./dist/binary --title "v1.0.0" --notes "Notes"
gh release list
gh release download v1.0.0 --dir ./downloads
```

## GitHub Actions Workflows

```bash
gh workflow list
gh run list --limit 10
gh run view <RUN_ID>
gh run view <RUN_ID> --log-failed
gh run rerun <RUN_ID>
gh run rerun <RUN_ID> --failed
gh workflow run ci.yml --ref main
gh workflow run deploy.yml -f environment=staging
```

See `references/ci-troubleshooting.md` for diagnosing common CI failures.

## Gists

```bash
gh gist create script.py --public --desc "Useful script"
gh gist list
```

---

# Section 3 — Pull Requests

## Branch Creation

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
```

**Branch naming:** `feat/`, `fix/`, `refactor/`, `docs/`, `ci/`, `chore/`, `perf/`

## Making Commits

```bash
git add src/auth.py src/models/user.py tests/test_auth.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add auth middleware for protected routes
- Add unit tests"
```

See `references/conventional-commits.md` for the full Conventional Commits spec.

## Pushing and Creating a PR

```bash
git push -u origin HEAD
```

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

**With curl:**

```bash
BRANCH=$(git branch --show-current)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

Templates: `templates/pr-body-feature.md`, `templates/pr-body-bugfix.md`.

## Monitoring CI

```bash
# One-shot
gh pr checks
# Watch
gh pr checks --watch
```

**Poll status with curl:**

```bash
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  case "$STATUS" in success|failure|error) break;; esac
  sleep 30
done
```

See `references/ci-troubleshooting.md` for diagnosing failures.

## Auto-Fixing CI Failures

1. Get failure details: `gh run view <RUN_ID> --log-failed` (or download with curl)
2. Use `read_file` + `patch`/`write_file` to fix
3. `git add . && git commit -m "fix: ..." && git push`
4. Wait for CI → re-check
5. Repeat up to 3 attempts, then ask the user

## Merging

```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch
```

**With curl:**

```bash
PR_NUMBER=<n>
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{\"merge_method\": \"squash\"}"

BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH
git checkout main && git pull origin main && git branch -d $BRANCH
```

**Auto-merge via GraphQL:**

```bash
PR_NODE_ID=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/graphql \
  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
```

## End-to-End Workflow

```bash
git checkout main && git pull origin main
git checkout -b fix/login-redirect-bug
# (agent makes code changes with file tools)
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login"
git push -u origin HEAD
# (then create PR per Section 3)
# (then monitor CI per Section 3)
# (then merge per Section 3)
```

## PR Command Reference

| Action | gh | git + curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `curl /pulls?state=open` |
| View PR diff | `gh pr diff` | `git diff main...HEAD` |
| Add comment | `gh pr comment N --body "..."` | `curl POST /issues/N/comments` |
| Request review | `gh pr edit N --add-reviewer user` | `curl POST /pulls/N/requested_reviewers` |
| Close PR | `gh pr close N` | `curl PATCH /pulls/N -d '{"state":"closed"}'` |
| Check out PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |

---

# Section 4 — Code Review

## Reviewing Local Changes (Pre-Push)

```bash
git diff --staged
git diff main...HEAD
git diff main...HEAD --name-only
git diff main...HEAD --stat
```

**Strategy:**
1. `git diff main...HEAD --stat` and `git log main..HEAD --oneline` for the big picture
2. File-by-file: read the file with `read_file` for context
3. Hunt common issues:

```bash
# Debug statements, TODOs left behind
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"
# Large files accidentally staged
git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10
# Secrets
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
# Merge conflict markers
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
```

**Output format:**

```
## Code Review Summary

### Critical
- **src/auth.py:45** — SQL injection: user input passed directly to query.
  Suggestion: Use parameterized queries.

### Warnings
- **src/models/user.py:23** — Password stored in plaintext. Use bcrypt or argon2.

### Suggestions
- **src/utils/helpers.py:8** — Duplicates logic in src/core/utils.py:34. Consolidate.

### Looks Good
- Clean separation of concerns
- Good test coverage for the happy path
```

See `references/review-output-template.md` for the full template.

## Reviewing a Pull Request on GitHub

```bash
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only
```

**Check out PR locally for full review:**

```bash
git fetch origin pull/123/head:pr-123
git checkout pr-123
# Now use read_file, search_files, run tests, etc.
```

**With gh:** `gh pr checkout 123`

## Posting Comments

```bash
# General PR comment
gh pr comment 123 --body "Overall looks good."
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

**Inline comments with gh:**

```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="Simplify with a list comprehension." \
  -f path="src/auth/login.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45 \
  -f side="RIGHT"
```

**Atomic multi-comment review with curl:**

```bash
HEAD_SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123/reviews \
  -d "{
    \"commit_id\": \"$HEAD_SHA\",
    \"event\": \"REQUEST_CHANGES\",
    \"body\": \"## Hermes Review\n\n2 issues, 1 suggestion.\",
    \"comments\": [
      {\"path\": \"src/auth.py\", \"line\": 45, \"body\": \"🔴 SQL injection.\"},
      {\"path\": \"src/models.py\", \"line\": 23, \"body\": \"⚠️ Plaintext password.\"},
      {\"path\": \"src/utils.py\", \"line\": 8, \"body\": \"💡 Duplicates logic.\"}
    ]
  }"
```

Event values: `APPROVE`, `REQUEST_CHANGES`, `COMMENT`. For deleted lines, use `"side": "LEFT"`.

## Review Checklist

**Correctness:** edge cases (empty, null, large, concurrent), error paths
**Security:** no hardcoded secrets, input validation, no SQLi/XSS/path traversal, auth checks
**Quality:** clear naming, no premature abstraction, DRY, single responsibility
**Testing:** new paths tested, happy + error cases, readable
**Performance:** no N+1, appropriate caching, no blocking in async
**Docs:** public APIs documented, non-obvious logic commented, README updated

## Pre-Push Workflow

1. `git diff main...HEAD --stat` — scope
2. `git diff main...HEAD` — full diff
3. `read_file` changed files for context
4. Apply checklist
5. Present findings in Critical / Warnings / Suggestions / Looks Good
6. Offer to fix critical issues before push

## End-to-End PR Review

1. `source scripts/gh-env.sh` (or run setup block)
2. Get context: `gh pr view 123` / `gh pr diff 123 --name-only` / `gh pr checks 123`
3. `git fetch origin pull/123/head:pr-123 && git checkout pr-123`
4. `git diff main...HEAD` — full diff
5. Run automated checks: `python -m pytest`, linters
6. Apply checklist
7. Submit review (approve / request changes / comment)
8. Post summary comment
9. Clean up: `git checkout main && git branch -D pr-123`

---

# Section 5 — Issues

## Viewing

```bash
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42
```

## Creating

```bash
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body "## Description
After logging in, users always land on /dashboard.

## Steps to Reproduce
1. Navigate to /settings while logged out
2. Get redirected to /login?next=/settings
3. Log in
4. Actual: redirected to /dashboard

## Expected Behavior
Respect the ?next= query parameter." \
  --label "bug,backend" \
  --assignee "username"
```

Templates: `templates/bug-report.md`, `templates/feature-request.md`.

## Managing

```bash
# Labels
gh issue edit 42 --add-label "priority:high,bug"
gh issue edit 42 --remove-label "needs-triage"

# Assignment
gh issue edit 42 --add-assignee username
gh issue edit 42 --add-assignee @me

# Comments
gh issue comment 42 --body "Investigated — root cause is in auth middleware."

# Close / reopen
gh issue close 42
gh issue close 42 --reason "not planned"
gh issue reopen 42
```

## Linking Issues to PRs

Use keywords in the PR body — GitHub auto-closes on merge:

```
Closes #42
Fixes #42
Resolves #42
```

Create a branch from an issue: `gh issue develop 42 --checkout`

## Triage Workflow

1. List untriaged: `gh issue list --label "needs-triage" --state open`
2. Read & categorize each
3. Apply labels and priority
4. Assign if owner is clear
5. Comment with triage notes if needed

## Bulk Operations

```bash
# Close all "wontfix" issues
gh issue list --label "wontfix" --json number --jq '.[].number' \
  | xargs -I {} gh issue close {} --reason "not planned"
```

## Quick Reference

| Action | gh | curl |
|--------|-----|------|
| List issues | `gh issue list` | `GET /repos/{o}/{r}/issues` |
| View issue | `gh issue view N` | `GET /repos/{o}/{r}/issues/N` |
| Create issue | `gh issue create ...` | `POST /repos/{o}/{r}/issues` |
| Add labels | `gh issue edit N --add-label ...` | `POST /repos/{o}/{r}/issues/N/labels` |
| Assign | `gh issue edit N --add-assignee ...` | `POST /repos/{o}/{r}/issues/N/assignees` |
| Comment | `gh issue comment N --body ...` | `POST /repos/{o}/{r}/issues/N/comments` |
| Close | `gh issue close N` | `PATCH /repos/{o}/{r}/issues/N` |
| Search | `gh issue list --search "..."` | `GET /search/issues?q=...` |

---

## Reference Files

- `references/ci-troubleshooting.md` — diagnose common CI failures
- `references/conventional-commits.md` — full Conventional Commits spec
- `references/github-api-cheatsheet.md` — quick reference for GitHub REST API
- `references/review-output-template.md` — full code review output template
- `templates/pr-body-feature.md` — feature PR body template
- `templates/pr-body-bugfix.md` — bugfix PR body template
- `templates/bug-report.md` — issue bug report template
- `templates/feature-request.md` — issue feature request template
- `scripts/gh-env.sh` — sourceable auth + owner/repo setup block
