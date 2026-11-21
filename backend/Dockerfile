FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.10.5 /uv /usr/local/bin/uv

# System libraries: the only app-specific block of this file.
# `apt-get upgrade` picks up Debian security fixes newer than the pinned base image.
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libmagic1 \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    libreoffice-common \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (cached layer), exact versions from uv.lock
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY app ./app

# /data holds the sessions database (volume), owned by the unprivileged user
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir /data /tmp/localpdf && chown app /data /tmp/localpdf
USER app

EXPOSE 8000
VOLUME /data

# Workers: WEB_CONCURRENCY. Client scheme/address come from the proxy in front
# (--proxy-headers, trusted through FORWARDED_ALLOW_IPS: see docker-compose.yml).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "30", "--proxy-headers"]
