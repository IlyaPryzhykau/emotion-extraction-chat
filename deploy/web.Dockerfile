# Build the frontend, then bake the static assets into a Caddy image that also
# reverse-proxies /api to the backend. Build context is the repo root (needs both
# frontend/ and deploy/Caddyfile).
FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
