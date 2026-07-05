# ---- stage 1: build the next.js frontend into a standalone server bundle ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend-web/package.json frontend-web/package-lock.json ./
RUN npm ci
COPY frontend-web ./
RUN npm run build

# ---- stage 2: runtime — node (for the next server) + uv-managed python (backend) ----
FROM node:22-slim

# uv for python dependency management; it installs its own python below
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_INSTALL_DIR=/python \
    VALOR_HEADLESS=true \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app

# 1. python deps only — cached unless pyproject/uv.lock change
COPY pyproject.toml uv.lock README.md ./
RUN uv python install 3.12 && uv sync --frozen --no-dev --no-install-project

# 2. patched chromium + its system libs (both targets sit behind cloudflare)
RUN uv run --no-sync patchright install --with-deps chromium

# 3. backend source, then install the project itself
COPY src ./src
RUN uv sync --frozen --no-dev

# 4. the built next.js standalone server + its static assets
COPY --from=web /web/.next/standalone ./frontend-web
COPY --from=web /web/.next/static ./frontend-web/.next/static
COPY --from=web /web/public ./frontend-web/public

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000 3000

ENTRYPOINT ["docker-entrypoint.sh"]
