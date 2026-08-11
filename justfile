github_repo := "applewebbo/school_menu"

# List all available commands.
@_:
    just --list

##########################################################################
# Setup
##########################################################################


# Ensure project virtualenv is up to date
[group('setup')]
@install:
    uv sync

# Update dependencies and pre-commit hooks
[group('setup')]
@update_all: lock
    uv sync --all-extras --upgrade
    uvx --with pre-commit-uv prek auto-update

# Update a specific package
[group('setup')]
@update *args:
    uv sync --upgrade-package {{ args }}

# Rebuild lock file from scratch
[group('setup')]
@lock:
    echo "Rebuilding lock file..."
    uv lock --upgrade
    echo "Done!"

# Remove temporary files
[group('setup')]
clean:
    rm -rf .venv .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
    find . -type d -name "__pycache__" -exec rm -r {} +

# Recreate project virtualenv from nothing
[group('setup')]
fresh: clean install

##########################################################################
# Development
##########################################################################

# Run the local development server
[group('development')]
@local:
    uv run python manage.py tailwind runserver

# Run the development server + workers
[group('development')]
@serve:
    rm -f ./.overmind.sock
    uv run overmind start -r all -f ./Procfile.dev

# Crawl the site for broken links / runtime errors (needs a populated dev DB)
[group('development')]
crawl *args:
    ENVIRONMENT=dev uv run python manage.py crawl -v 2 {{ args }}

# Create database migrations
[group('development')]
makemigrations:
    uv run python manage.py makemigrations

# Run database migrations
[group('development')]
migrate:
    uv run python manage.py migrate

# Compile Translation Files
[group('development')]
compilemessages:
    uv run python manage.py compilemessages

# Update Translation Files
[group('development')]
makemessages:
    uv run python manage.py makemessages -a

# Run Tasks Worker
[group('development')]
@tasks:
    uv run python manage.py qcluster

##########################################################################
# Utility
##########################################################################

# Run tests
[group('utility')]
test *args:
    ENVIRONMENT=test uv run -m pytest --reuse-db -s -x {{ args }}


# Run fast tests (unit tests only, excludes performance)
# TEST_WORKERS controls parallelism (default 4; raise it for faster CI runs).
# taskpolicy -b routes the xdist workers to the efficiency cores (background QoS) so the
# performance cores stay free and the Mac remains responsive during the run.
[group('utility')]
ftest *args:
    taskpolicy -b nice -n 10 env ENVIRONMENT=test uv run pytest -n ${TEST_WORKERS:-4} --reuse-db --dist loadscope --exitfirst -m "not performance" -p no:benchmark {{ args }}


# Run fast tests with coverage report (must reach 100%)
[group('utility')]
cov *args:
    taskpolicy -b nice -n 10 env ENVIRONMENT=test uv run pytest -n ${TEST_WORKERS:-4} --reuse-db --dist loadscope --exitfirst -m "not performance" -p no:benchmark --cov=. --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100 {{ args }}


# Run performance tests only
[group('utility')]
perftest *args:
    ENVIRONMENT=test uv run -m pytest --reuse-db --no-cov -m performance {{ args }}


# Run complete performance baseline suite with report generation
[group('utility')]
perfbaseline:
    bash tests/performance/run_all_baselines.sh


# Run Ruff linting and formatting; niced to keep the machine responsive
[group('utility')]
lint:
    nice -n 10 uv run ruff check --fix --unsafe-fixes .
    nice -n 10 uv run ruff format .
    @nice -n 10 just _pre-commit run --all-files

# Run type checking with mypy
[group('utility')]
typecheck:
    uv run mypy .

_pre-commit *args:
    uvx prek {{ args }}

# Check for unsecured dependencies
[group('utility')]
secure:
    uv-secure

##########################################################################
# GitHub Issues
##########################################################################

# List issues (state: open|closed|all)
[group('github')]
issues state="open":
    gh issue list -R {{github_repo}} --state {{state}}

# Show issue details
[group('github')]
issue number:
    gh issue view -R {{github_repo}} {{number}}

# Add comment to issue
[group('github')]
issue-comment number text:
    gh issue comment -R {{github_repo}} {{number}} --body {{ quote(text) }}

# Close issue
[group('github')]
issue-close number:
    gh issue close -R {{github_repo}} {{number}}

# Reopen issue
[group('github')]
issue-reopen number:
    gh issue reopen -R {{github_repo}} {{number}}

# Add labels to issue (space-separated, labels must already exist)
[group('github')]
issue-label number *labels:
    gh issue edit -R {{github_repo}} {{number}} --add-label "{{labels}}"

# Create a label if it doesn't exist (color optional, default blue)
[group('github')]
label-create name color="0075ca":
    gh label create -R {{github_repo}} "{{name}}" --color "{{color}}" --force

# Create a label if missing, then assign it to an issue: just issue-label-create <issue> <label> [color]
[group('github')]
issue-label-create number name color="0075ca":
    #!/usr/bin/env bash
    set -euo pipefail
    just label-create "{{name}}" "{{color}}"
    gh issue edit -R {{github_repo}} {{number}} --add-label "{{name}}"

# Create new issue
[group('github')]
issue-create title body="":
    gh issue create -R {{github_repo}} --title {{ quote(title) }} --body {{ quote(body) }}

##########################################################################
# GitHub Releases
##########################################################################

# List all releases
[group('github')]
release-list:
    gh release list -R {{github_repo}}

# Show release details
[group('github')]
release-show tag:
    gh release view -R {{github_repo}} {{tag}}

# Create a new release (creates + pushes tag, auto-generates notes from commits)
[group('github')]
release-create tag previous_tag="" prerelease="false":
    #!/usr/bin/env bash
    set -euo pipefail

    if git rev-parse "{{tag}}" >/dev/null 2>&1; then
        echo "✓ Tag {{tag}} already exists locally"
    else
        echo "📝 Creating tag {{tag}} on current commit..."
        git tag "{{tag}}"
    fi

    echo "📤 Pushing tag {{tag}} to origin..."
    git push origin "{{tag}}" || echo "✓ Tag {{tag}} already on remote"

    PRERELEASE_FLAG=""
    if [ "{{prerelease}}" = "true" ]; then PRERELEASE_FLAG="--prerelease"; fi

    NOTES_FLAG="--generate-notes"
    if [ "{{previous_tag}}" != "" ]; then NOTES_FLAG="--notes-start-tag {{previous_tag}} --generate-notes"; fi

    echo "🚀 Creating release on GitHub..."
    gh release create -R {{github_repo}} "{{tag}}" --title "{{tag}}" $NOTES_FLAG $PRERELEASE_FLAG

# Delete a release (use with caution!)
[group('github')]
release-delete tag:
    gh release delete -R {{github_repo}} "{{tag}}" --yes

##########################################################################
# Deployment
##########################################################################

# Deploy to production via Coolify webhook
[group('deployment')]
deploy:
    #!/usr/bin/env bash
    set -euo pipefail
    WEBHOOK_URL=$(grep "^COOLIFY_WEBHOOK_URL=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    WEBHOOK_TOKEN=$(grep "^COOLIFY_WEBHOOK_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    echo "🚀 Deploying to production..."
    curl -s -X GET "${WEBHOOK_URL}?token=${WEBHOOK_TOKEN}" | jq .
    echo "✓ Deploy triggered"

##########################################################################
# Tasks
##########################################################################

# List all ready/in-progress tasks
[group('tasks')]
tasks-list:
    taskdb list

# List completed tasks
[group('tasks')]
tasks-done:
    taskdb list --status done
