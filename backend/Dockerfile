FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifest and lock file first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev extras)
RUN uv sync --no-dev --frozen

# Copy source
COPY src/ ./src/
# Game data is baked in at build time via make fetch-game-data + make build
COPY data/game/ ./data/game/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "ficsolver.main:app", "--host", "0.0.0.0", "--port", "8000"]
