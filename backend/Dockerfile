FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install deps first (better layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY src/ ./src/

EXPOSE 8000

ENV IDE_WORKSPACE_DIR=/app/projects \
    IDE_PROMPTS_DIR=/app/prompts \
    IDE_DB_PATH=/app/data/tessera.db

CMD ["uv", "run", "uvicorn", "tessera.main:app", "--host", "0.0.0.0", "--port", "8000"]
