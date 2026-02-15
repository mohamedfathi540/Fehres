
FROM ghcr.io/astral-sh/uv:0.9.26-python3.11-trixie

WORKDIR /app
#Install Additional system dependences for lxml and other packages

RUN apt-get update && apt-get install -y \
    build-essential \
    libavif-dev pkg-config \
    libjpeg-dev \
    gcc unzip zip \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxkbcommon0 \
    libxshmfence1 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libcups2 \
    libdrm2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY SRC/pyproject.toml SRC/uv.lock* ./

ENV UV_HTTP_TIMEOUT=600
ENV UV_SYSTEM_PYTHON=1

# Install dependencies and Playwright browser binaries to shared volume
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN uv sync --no-dev && ./.venv/bin/python -m playwright install chromium

COPY SRC/ .

#create directory for alembic
RUN mkdir -p Models/DB_Schemes/minirag

COPY Docker/minirag/alembic.ini /app/Models/DB_Schemes/minirag/alembic.ini

COPY Docker/minirag/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
