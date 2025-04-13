
# Define the default recipe
default:
    @just --list

# Bootstrap the project (UV and BUN needed)
bootstrap:
    uv venv
    source .venv/bin/activate
    uv sync
    bun add -D daisyui@latest

# Run the local development server
local:
    uv run python manage.py tailwind --settings=core.settings.dev runserver


# Run Django with DEBUG=False locally
prod_local:
    uv run python manage.py collectstatic --noinput --settings=core.settings.dev
    uv runpython manage.py runserver --settings=core.settings.dev --insecure

# Install requirements
requirements:
    uv sync

# Update all packages
update_all:
    uv sync --upgrade

# Update a specific package
update package:
    uv sync --upgrade-package {{package}}

# Run database migrations
migrate:
    uv runpython manage.py migrate --settings=core.settings.development

# Run tests
test *args:
    uv run python -m pytest --reuse-db -s -x {{ args }}

# Run fast tests
ftest *args:
    uv run pytest -n 8 --reuse-db --dist loadscope --exitfirst {{ args }}

lint:
    uv run ruff check --fix --unsafe-fixes .
    uv run ruff format .
    just _pre-commit run --all-files

_pre-commit *args:
    uvx --with pre-commit-uv pre-commit {{ args }}

docker_up:
    docker compose up -d

docker_build:
    docker compose up -d --build

docker_down:
    docker compose down -v
