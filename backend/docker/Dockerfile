# syntax=docker/dockerfile:1
# Build context: the repository root (see docker-compose.yml)

# --- Web UI ---------------------------------------------------------------
FROM node:24-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npx vue-cli-service build --dest /web/dist

# --- Backend --------------------------------------------------------------
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY backend/ /app/
COPY --from=web /web/dist /app/application/dist
RUN chmod +x /app/docker/entrypoint.sh

ENV FLASK_APP=wsgi.py
EXPOSE 5001
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["flask", "run", "--port=5001", "--host=0.0.0.0"]
