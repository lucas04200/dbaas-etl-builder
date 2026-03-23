# ── Stage 1 : Build frontend ───────────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /build
COPY web/frontend/package*.json ./
RUN npm ci --silent
COPY web/frontend .
RUN npm run build

# ── Stage 2 : Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

# Ansible + Docker CLI (pour les playbooks et docker exec/logs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ansible \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY web/ ./web/
COPY ansible/ ./ansible/

# Frontend build → static files
COPY --from=frontend /build/../static ./web/static

# Expose port
EXPOSE 8080

# Point d'entrée
CMD ["python", "web/main.py"]
