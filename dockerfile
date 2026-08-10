# --------------------------------------------------------
# Stage 1: Build dependencies and compile wheels
# --------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Leverage cache mounts and bind mounts for fast layer caching
# Installs dependencies into a virtual environment (.venv) without copying project code yet
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --compile-bytecode

# --------------------------------------------------------
# Stage 2: Final lightweight runtime environment
# --------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-privileged user for security compliance
RUN useradd -u 10001 -m django-user

# Copy the built virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Pre-pend the virtual environment's binaries to the system PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the remaining Django source code and fix ownership permissions
COPY --chown=django-user:django-user . /app

# Switch to the non-root user
USER django-user

# Expose Django's standard port
EXPOSE 8000

# Collect static files during image building if needed (or do it in your deployment pipeline)
RUN python manage.py collectstatic --noinput --clear

# Run Gunicorn or your preferred WSGI server (Ensure gunicorn is listed in your pyproject.toml)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
