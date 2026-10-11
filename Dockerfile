# ========================================================
# Stage 1: Build Next.js Control Room Frontend
# ========================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/ict-scanner-dashboard

COPY ict-scanner-dashboard/package*.json ./
RUN npm install --legacy-peer-deps

COPY ict-scanner-dashboard/ ./
RUN npm run build

# ========================================================
# Stage 2: Production Multi-Service Container (FastAPI + Next.js)
# ========================================================
FROM python:3.11-slim

WORKDIR /app

# Environment defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC \
    PYTHONPATH=/app/src \
    MPLBACKEND=Agg \
    HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    FRONTEND_PORT=3000 \
    BACKEND_INTERNAL_URL=http://127.0.0.1:8000

# Install system dependencies (healthcheck, font rendering for charts, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    fonts-dejavu-core \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js runtime from matching Debian Bookworm image
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:20-bookworm-slim /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node:20-bookworm-slim /usr/local/bin/npx /usr/local/bin/npx
COPY --from=node:20-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules

# Install Python backend dependencies
COPY pyproject.toml requirements.txt* ./
RUN pip install --no-cache-dir -e .

# Copy backend source, migrations, and database configs
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

# Copy compiled Next.js frontend and node_modules from builder
COPY --from=frontend-builder /app/ict-scanner-dashboard ./ict-scanner-dashboard

# Create persistent storage directories
RUN mkdir -p /app/data /app/data/charts

# Copy and prepare startup script
COPY start.sh ./start.sh
RUN chmod +x /app/start.sh

# Expose backend (8000) and frontend (3000)
EXPOSE 8000 3000

# Health check checking the FastAPI backend status
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production concurrent entrypoint
CMD ["/app/start.sh"]
