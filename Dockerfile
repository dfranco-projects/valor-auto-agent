FROM python:3.12-slim

# uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    VALOR_API_BASE=http://localhost:8000 \
    VALOR_HEADLESS=true

WORKDIR /app

# 1. deps only — cached unless pyproject/uv.lock change
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. patched chromium + its system libs (both targets sit behind cloudflare)
#    --no-sync: use the deps from step 1; the project itself isn't needed yet
RUN uv run --no-sync patchright install --with-deps chromium

# 3. app source, then install the project itself
COPY src ./src
RUN uv sync --frozen --no-dev

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000 8501

ENTRYPOINT ["docker-entrypoint.sh"]
