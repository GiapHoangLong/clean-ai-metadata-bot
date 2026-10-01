# Dockerfile for CleanAI Metadata Stripper Telegram Bot
FROM python:3.11-slim

# Install system dependencies including ffmpeg for video stripping
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using uv sync (frozen lockfile)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY src/ ./src/
COPY main.py ./

# Create data and scratch directories and grant ownership to non-root user
RUN mkdir -p data scratch/temp_uploads && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Run the Telegram Bot
CMD ["python", "main.py"]
