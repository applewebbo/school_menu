# pull official base image
FROM python:3.12-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1

#install uv
RUN apt-get update && apt-get install -y curl unzip postgresql-client-16
RUN pip install --upgrade pip uv
RUN python -m uv venv

# copy project
WORKDIR /app
COPY . /app

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash

# # Install DaisyUI using Bun
# RUN ~/.bun/bin/bun add -D daisyui@latest
RUN ~/.bun/bin/bun install

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

# expose port for gunicorn
EXPOSE 80

# run entrypoint.sh
CMD ["sh", "./entrypoint.sh"]
