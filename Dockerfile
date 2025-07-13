# pull official base image
FROM python:3.13-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1

# install libraries and postgresql client
RUN apt update && \
    apt install --no-install-recommends -y libpq-dev curl unzip gnupg2 lsb-release apt-transport-https ca-certificates tmux wget
# Add the PGDG apt repo
RUN echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
# Trust the PGDG gpg key
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc| gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
RUN apt update \
    && apt -y install postgresql-16 \
    && rm -rf /var/lib/apt/lists/*

# Install Overmind 2.5.1
RUN wget https://github.com/DarthSim/overmind/releases/download/v2.5.1/overmind-v2.5.1-linux-amd64.gz \
    && gunzip overmind-v2.5.1-linux-amd64.gz \
    && chmod +x overmind-v2.5.1-linux-amd64 \
    && mv overmind-v2.5.1-linux-amd64 /usr/local/bin/overmind

# Install uv using the official script
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# copy project
WORKDIR /app
COPY . /app

# activate virtual env
ARG VIRTUAL_ENV=/app/.venv
ENV PATH=/app/.venv/bin:$PATH

# install dependencies
COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# copy project
WORKDIR /app
COPY . /app

# create logs directory
RUN mkdir -p /app/logs

# expose port for gunicorn
EXPOSE 80

# run entrypoint.sh
CMD ["sh", "./entrypoint.sh"]
