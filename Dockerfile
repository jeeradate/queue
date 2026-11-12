FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    MEDIQUEUE_HOST=0.0.0.0 \
    MEDIQUEUE_PORT=8080 \
    MEDIQUEUE_DATABASE_URL=sqlite:////data/mediqueue.db \
    NICEGUI_STORAGE_PATH=/data/.nicegui

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY static ./static
RUN uv sync --frozen --no-dev

VOLUME ["/data"]
EXPOSE 8080

CMD ["uv", "run", "--frozen", "--no-dev", "mediqueue"]
