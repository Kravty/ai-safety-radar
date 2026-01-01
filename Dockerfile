FROM python:3.11-slim as builder

# Install uv provided by astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Copy source code and README for package installation
COPY src /app/src
COPY README.md ./

# Sync dependencies and install the project package
RUN uv sync --frozen && uv pip install -e .

# ============================================
# Final Runtime Stage
# ============================================
FROM python:3.11-slim-bookworm

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set path to use venv by default
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy application source code
COPY src /app/src

# Copy tests directory for validation
COPY tests /app/tests

# Copy project metadata
COPY README.md pyproject.toml ./

# Default command
CMD ["python", "-m", "ai_safety_radar"]
