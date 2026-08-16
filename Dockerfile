# pull official base image
FROM python:3.14-slim-bookworm

# set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1

# Install system dependencies in a single layer to reduce image size
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    # Install prerequisites for adding new repos
    curl gnupg2 lsb-release apt-transport-https ca-certificates && \
    # Add the PGDG apt repo
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    # Trust the PGDG gpg key
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg && \
    # Update apt list again to fetch packages from the new repo
    apt-get update && \
    # Install the rest of the packages
    apt-get install --no-install-recommends -y \
    supervisor \
    postgresql-client-16 \
    libpq-dev \
    unzip && \
    # Clean up to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Set work directory
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install python dependencies
# Using a virtual environment is a good practice
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen --no-dev --no-install-project

# Activate virtual env for subsequent commands
ENV PATH="/app/.venv/bin:$PATH"

# Pre-download the Tailwind CSS CLI to avoid the ~120MB runtime download on every start
# (entrypoint.sh runs `tailwind build --force`).
# IMPORTANT: keep TAILWIND_VERSION aligned with the version django-tailwind-cli expects
# (the release skill verifies this on every release). The filename must match what
# django-tailwind-cli resolves, otherwise it silently downloads the binary again.
ARG TAILWIND_VERSION=2.10.11
# Pin the runtime to the version baked above: left on the default `latest`, the app would
# ask GitHub which version to look for and miss the file as soon as upstream moves on.
ENV TAILWIND_CLI_VERSION=${TAILWIND_VERSION}
RUN mkdir -p /app/.django_tailwind_cli \
  && ARCH="$(dpkg --print-architecture)" \
  && case "$ARCH" in \
       amd64)  TW_ARCH="x64" ;; \
       arm64)  TW_ARCH="arm64" ;; \
       *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
     esac \
  && curl -fsSL "https://github.com/dobicinaitis/tailwind-cli-extra/releases/download/v${TAILWIND_VERSION}/tailwindcss-extra-linux-${TW_ARCH}" \
     -o "/app/.django_tailwind_cli/tailwindcss-extra-linux-${TW_ARCH}-${TAILWIND_VERSION}" \
  && chmod +x "/app/.django_tailwind_cli/tailwindcss-extra-linux-${TW_ARCH}-${TAILWIND_VERSION}"

# Copy the rest of the application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port for gunicorn
EXPOSE 80

# Run entrypoint.sh
CMD ["sh", "./entrypoint.sh"]
