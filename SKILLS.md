# Claude Code Skills

Custom skills available for common Django workflows. Use these for automated quality checks and safe operations.

## Available Skills

### `/makemigrations` - Safe Migration Creation
**Use when:** Modifying Django models

**What it does:**
1. Runs `just ftest` to ensure tests pass before creating migrations
2. Shows preview with `--dry-run` to review changes
3. Detects dangerous operations (RenameField, RemoveField, AddField without default)
4. Asks for confirmation before creating
5. Creates migrations and re-runs tests to verify
6. Reminds to commit migrations and update related tasks

### `/check-all` - Comprehensive Health Check
**Use when:** Before commits, before deployments, during code reviews

**What it does:**
1. Django system checks (dev + deploy mode)
2. Migration status verification
3. Code quality check (`just lint`)
4. Security audit (`just secure`)
5. Full test suite with 100% coverage (`just ftest`)
6. Counts TODO/FIXME comments
7. Lists open tasks

**Output:** Health report with overall status (HEALTHY / NEEDS ATTENTION / FAILING)

### `/pre-deploy` - Pre-Deployment Checklist
**Use when:** Before production deployments

**What it does:**
1. Runs full `/check-all` health check
2. Verifies production settings (DEBUG=False, SECRET_KEY, ALLOWED_HOSTS, CSRF/Session security)
3. Tests static files collection (`collectstatic --dry-run`)
4. Verifies git status (clean, correct branch, synced with remote)
5. Presents interactive deployment checklist

### `/db-backup` - Database Backup
**Use when:** Before risky operations, before deployments, periodic backups

**What it does:**
1. Checks disk space and database status
2. Creates timestamped JSON backup with `dumpdata` (portable format)
3. Creates timestamped SQLite backup (fast restore)
4. Verifies backup integrity and compresses with gzip
5. Shows restore commands

**Output:**
- `backups/db_backup_YYYYMMDD_HHMMSS.json.gz`
- `backups/db_sqlite3_YYYYMMDD_HHMMSS.db.gz`

### `/review` - Automated Code Review
**Use when:** Before merging a branch, during PR review, before release

**What it does:**
1. Analyzes `git diff main...HEAD` (all branch changes)
2. Checks for bugs, logic errors, N+1 queries
3. Security review (OWASP Top 10, Django-specific)
4. Verifies project pattern compliance (FBV, HTMX, Crispy Forms, Tailwind/DaisyUI)
5. Checks test coverage for changed code
6. Generates report with severity levels (CRITICAL/WARNING/SUGGESTION)

**Output:** Review report with verdict (APPROVED / NEEDS CHANGES / BLOCKED)

### `/release` - Complete Release Workflow
**Use when:** Ready to ship a release branch to production

**What it does:**
1. Validates release branch and runs all checks
2. Generates categorized release notes from commits
3. Fetches issue details to enrich release descriptions
4. Merges to main with `--ff-only` (linear history)
5. Creates tag and pushes to origin
6. Creates GitHub release with detailed, human-readable release notes
7. Labels closed issues with release version
8. Optionally creates next release branch

### `/deploy` - Deploy to Production (Coolify)
**Use when:** Ready to deploy to production after a release or hotfix

**What it does:**
1. Validates branch (warns if not on `main`), clean working tree and remote sync
2. Runs quick health check (tests, lint, Django check, migrations)
3. Shows confirmation summary before deploying
4. Triggers deployment via Coolify webhook (HTTP POST)
5. Verifies the app is up with an HTTP health check

**App:** `school_menu` on Coolify (deploys via Dockerfile automatically on push to `main`)

### `/deps-update` - Safe Dependency Updates
**Use when:** Weekly maintenance, security patches, package upgrades

**What it does:**
1. Backs up current `uv.lock` before updating
2. Runs baseline tests to verify starting state
3. Updates dependencies (all or specific package)
4. Runs full test suite + security audit after update
5. Shows version diff (old → new) with major bump warnings
6. **Automatic rollback** if tests fail after update

### `/cleanup` - Project Maintenance
**Use when:** Monthly maintenance, before releases, when disk space is low

**What it does:**
1. Cleans Python caches (`__pycache__`, `.pyc`, `.pyo`)
2. Clears expired Django sessions
3. Cleans test artifacts (`htmlcov/`, `.pytest_cache/`, `.ruff_cache/`)
4. Run tailwind-cleanup command to erase old tailwindcss files

## GitHub Issue Management

Use `just` recipes to manage GitHub issues without leaving the terminal (backed by the `gh` CLI):

```bash
just issues              # List open issues
just issues closed       # List closed issues
just issue 42            # Show issue details + comments
just issue-create "Title" "Body"   # Create new issue
just issue-comment 42 "text"       # Add comment
just issue-close 42                # Close issue
just issue-reopen 42               # Reopen issue
just issue-label 42 bug            # Add a label
```

## Release Management

```bash
just release-list                          # List all releases
just release-show v2026.1                  # Show release details
just release-create v2026.1               # Create release from current tag
just release-create v2026.1 v2025.4       # With explicit previous tag
just release-create v2026.1 "" true       # Pre-release
just release-delete v2026.1               # Delete a release (caution!)
```

## Task Tracking (taskdb)

```bash
just tasks-list        # List ready/in-progress tasks
just tasks-done        # List completed tasks
```

## Recommended Workflows

### Normal Development
```bash
/check-all   # Verify everything is OK
/commit      # Commit if all checks pass
```

### Before Merging
```bash
/review      # Review all branch changes
/commit      # Fix any issues and commit
```

### Release Cycle
```bash
/review      # Review branch changes
/release     # Complete release workflow (merge, tag, GitHub release)
/deploy      # Deploy to production
```

### Pre-Deployment (manual checklist)
```bash
/db-backup   # Backup database first
/pre-deploy  # Run comprehensive pre-deployment checks
/deploy      # Deploy to production
```

### Weekly Maintenance
```bash
/deps-update  # Update dependencies safely
/cleanup      # Clean caches and optimize DB
/commit       # Commit dependency updates
```

## Setup

1. Install and authenticate the GitHub CLI: `gh auth login` (needs `repo`, `workflow` scopes)
2. Recipes target the repo explicitly via the `github_repo` justfile variable
