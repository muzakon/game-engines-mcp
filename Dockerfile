FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md docsets.json config.yaml engines.local.yaml ./
COPY src/__init__.py src/__init__.py
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY scripts/ scripts/

# data/ is NOT copied — databases are downloaded from GitHub Releases at startup.
# If you need to include local DBs, uncomment the next line:
# COPY data/ data/

EXPOSE ${UNITY_MCP_PORT:-8080}

CMD ["uv", "run", "python", "scripts/run_server.py"]
