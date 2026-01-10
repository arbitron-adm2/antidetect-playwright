# Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for cache
COPY pyproject.toml ./
COPY src ./src

# Install package
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r <(echo "playwright redis aiohttp click")


# Runtime stage
FROM python:3.12-slim

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Install runtime dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /wheels /wheels
COPY --from=builder /build/dist/*.whl /wheels/
RUN pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels

# Install Playwright browsers
RUN playwright install chromium && \
    playwright install-deps chromium

# Create data directories
RUN mkdir -p /data/profiles /data/scripts /data/results /data/logs /data/screenshots /data/proxies && \
    chown -R appuser:appgroup /data

# Copy config
COPY .config /app/.config
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Environment
ENV PYTHONUNBUFFERED=1
ENV APP_BROWSER_HEADLESS=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from antidetect_playwright.infrastructure.redis_client import RedisClient; asyncio.run(RedisClient('localhost', 6379, None, 0, 1, 'test', 60, 5).connect())" || exit 1

# Volumes
VOLUME ["/data", "/app/.config"]

# Entry point
ENTRYPOINT ["python", "-m", "antidetect_playwright"]
CMD ["run"]
