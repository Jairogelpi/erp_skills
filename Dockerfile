# syntax=docker/dockerfile:1
# Python 3.12-slim digest retrieved 2026-08-05; verify with:
# docker buildx imagetools inspect python:3.12-slim
FROM python:3.12-slim@sha256:9e869b0816f5537709825b49e62dc86d1c2691eff19b05c1d4dc3a07992cc052

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.11.19 \
    && useradd --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --chown=app:app pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --group dev --no-install-project
COPY --chown=app:app src ./src

USER app
CMD ["uv", "run", "python", "-c", "print('ERP Agent OS development container is ready; no application runtime is implemented.')"]
