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
    uvx --with pre-commit-uv pre-commit autoupdate

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
[group('utility')]
ftest *args:
    ENVIRONMENT=test uv run -m pytest -n 8 --reuse-db --dist loadscope --exitfirst -m "not performance" {{ args }}


# Run performance tests only
[group('utility')]
perftest *args:
    ENVIRONMENT=test uv run -m pytest --reuse-db --no-cov -m performance {{ args }}


# Run complete performance baseline suite with report generation
[group('utility')]
perfbaseline:
    bash tests/performance/run_all_baselines.sh


# Run Ruff linting and formatting
[group('utility')]
lint:
    uv run ruff check --fix --unsafe-fixes .
    uv run ruff format .
    @just _pre-commit run --all-files

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
# Codeberg Issues
##########################################################################

# List issues (state: open|closed|all)
[group('codeberg')]
issues state="open":
    ./bin/codeberg list {{state}}

# Show issue details
[group('codeberg')]
issue number:
    ./bin/codeberg show {{number}}

# Add comment to issue
[group('codeberg')]
issue-comment number text:
    ./bin/codeberg comment {{number}} {{ quote(text) }}

# Mark a checkbox step as done in issue body
[group('codeberg')]
issue-check number step:
    ./bin/codeberg check {{number}} {{ quote(step) }}

# Close issue
[group('codeberg')]
issue-close number:
    ./bin/codeberg close {{number}}

# Reopen issue
[group('codeberg')]
issue-reopen number:
    ./bin/codeberg reopen {{number}}

# Add labels to issue (space-separated)
[group('codeberg')]
issue-label number *labels:
    ./bin/codeberg label {{number}} {{labels}}

# Create new issue
[group('codeberg')]
issue-create title body="":
    ./bin/codeberg create {{ quote(title) }} {{ quote(body) }}

##########################################################################
# Codeberg Releases
##########################################################################

# List all releases
[group('codeberg')]
release-list:
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    echo -e "TAG\tNAME\tPUBLISHED\tDRAFT"
    curl -s "https://codeberg.org/api/v1/repos/webbografico/school_menu/releases" \
      -H "Authorization: token ${TOKEN}" | \
      jq -r '.[] | "\(.tag_name)\t\(.name)\t\(.published_at)\t\(.draft)"' | \
      column -t -s $'\t'

# Show release details
[group('codeberg')]
release-show tag:
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    curl -s "https://codeberg.org/api/v1/repos/webbografico/school_menu/releases/tags/{{tag}}" \
      -H "Authorization: token ${TOKEN}" | \
      jq -r '"\nTag: \(.tag_name)\nName: \(.name)\nPublished: \(.published_at)\nDraft: \(.draft)\nPrerelease: \(.prerelease)\n\nURL: \(.html_url)\n\nBody:\n\(.body)\n"'

# Create a new release (auto-creates tag, pushes it, and generates notes from commits)
[group('codeberg')]
release-create tag previous_tag="" draft="false" prerelease="false":
    #!/usr/bin/env bash
    set -euo pipefail

    if git rev-parse "{{tag}}" >/dev/null 2>&1; then
        echo "✓ Tag {{tag}} already exists locally"
    else
        echo "📝 Creating tag {{tag}} on current commit..."
        git tag "{{tag}}"
        echo "✓ Tag {{tag}} created"
    fi

    echo "📤 Pushing tag {{tag}} to origin..."
    if git push origin "{{tag}}" 2>&1 | grep -q "already exists"; then
        echo "✓ Tag {{tag}} already exists on remote"
    else
        echo "✓ Tag {{tag}} pushed to origin"
    fi

    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

    if [ "{{previous_tag}}" = "" ]; then
        PREV_TAG=$(git tag --sort=-version:refname | grep -v "{{tag}}" | head -1)
    else
        PREV_TAG="{{previous_tag}}"
    fi

    echo "🔍 Generating release notes (comparing with ${PREV_TAG:-initial commit})..."

    if [ -z "$PREV_TAG" ]; then
        COMMITS=$(git log {{tag}} --pretty=format:"- %s" --reverse 2>/dev/null || echo "- Initial release")
    else
        COMMITS=$(git log ${PREV_TAG}..{{tag}} --pretty=format:"- %s" --reverse 2>/dev/null || echo "- Initial release")
    fi

    FEATURES=$(echo "$COMMITS" | grep -E "^- (✨|feat)" || true)
    FIXES=$(echo "$COMMITS" | grep -E "^- (🐛|fix)" || true)
    CHORES=$(echo "$COMMITS" | grep -E "^- (🔧|chore|📦|build|🎨)" || true)
    TESTS=$(echo "$COMMITS" | grep -E "^- (🧪|test|✅)" || true)
    DOCS=$(echo "$COMMITS" | grep -E "^- (📚|docs)" || true)

    NL=$'\n'
    BODY="## What's New in {{tag}}${NL}${NL}"

    if [ -n "$FEATURES" ]; then
        BODY+="### 🚀 Features${NL}$FEATURES${NL}${NL}"
    fi

    if [ -n "$FIXES" ]; then
        BODY+="### 🐛 Bug Fixes${NL}$FIXES${NL}${NL}"
    fi

    if [ -n "$CHORES" ]; then
        BODY+="### 🛠️ Maintenance${NL}$CHORES${NL}${NL}"
    fi

    if [ -n "$TESTS" ]; then
        BODY+="### 🧪 Testing${NL}$TESTS${NL}${NL}"
    fi

    if [ -n "$DOCS" ]; then
        BODY+="### 📖 Documentation${NL}$DOCS${NL}${NL}"
    fi

    BODY+="### 📖 Full Changelog${NL}https://codeberg.org/webbografico/school_menu/compare/${PREV_TAG}...{{tag}}"

    echo "🚀 Creating release on Codeberg..."
    curl -s -X POST "https://codeberg.org/api/v1/repos/webbografico/school_menu/releases" \
      -H "Authorization: token ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg tag "{{tag}}" \
        --arg body "$BODY" \
        --argjson draft {{draft}} \
        --argjson prerelease {{prerelease}} \
        '{tag_name: $tag, name: $tag, body: $body, draft: $draft, prerelease: $prerelease}'
      )" | jq -r '"\n✓ Release created successfully!\nURL: \(.html_url)\n"'

# Delete a release (use with caution!)
[group('codeberg')]
release-delete tag:
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    echo "⚠️  Deleting release {{tag}}..."
    curl -X DELETE "https://codeberg.org/api/v1/repos/webbografico/school_menu/releases/tags/{{tag}}" \
      -H "Authorization: token ${TOKEN}"
    echo "✓ Release {{tag}} deleted"

##########################################################################
# Beans
##########################################################################

# List active beans (excludes completed and scrapped)
[group('beans')]
beans:
    beans list --ready

# List completed beans
[group('beans')]
beans_completed:
    beans list -s completed
