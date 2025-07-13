# pull official base image
FROM python:3.13-slim-bookworm

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
    tmux \
    postgresql-client-16 \
    libpq-dev \
    unzip && \
    # Clean up to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Overmind
RUN curl -L https://github.com/DarthSim/overmind/releases/download/v2.5.1/overmind-v2.5.1-linux-amd64.gz | gunzip > /usr/local/bin/overmind && \
    chmod +x /usr/local/bin/overmind

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

# Copy the rest of the application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port for gunicorn
EXPOSE 80

# Run entrypoint.sh
CMD ["sh", "./entrypoint.sh"]
