FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/__init__.py src/__init__.py
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY scripts/ scripts/
COPY data/unity_docs.db data/unity_docs.db

EXPOSE ${UNITY_MCP_PORT:-8080}

CMD ["uv", "run", "python", "scripts/run_server.py"]
