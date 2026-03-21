# syntax=docker/dockerfile:1
FROM node:20-slim AS builder

WORKDIR /app

ARG VITE_DJANGO_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY

# Skopiuj tylko pliki wymagane do instalacji
COPY services/web-dashboard/react/package*.json ./
ENV NODE_ENV=development
ENV VITE_APP_ENV=production
ENV NODE_OPTIONS=--max-old-space-size=1024
ENV VITE_DJANGO_API_URL=${VITE_DJANGO_API_URL}
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY=${VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY}

RUN npm ci --include=dev

COPY services/web-dashboard/react /app

RUN test -n "$VITE_DJANGO_API_URL"
RUN test -n "$VITE_SUPABASE_URL"
RUN test -n "$VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY"

RUN npm run build

# Fail fast if build output is missing.
RUN test -d /app/dist

# Stage drugi – serwer statycznych plików (nginx)
FROM nginx:stable-alpine AS production

# Domyslna konfiguracja nginx dla SPA
COPY infrastructure/docker/nginx/spa.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

# Generate runtime env.js so frontend can read Railway variables at container start.
RUN cat > /docker-entrypoint.d/30-generate-env.sh <<'EOF'
#!/bin/sh
set -eu

escape_js() {
	printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

cat > /usr/share/nginx/html/env.js <<EOC
window.__APP_CONFIG__ = {
	VITE_DJANGO_API_URL: "$(escape_js "${VITE_DJANGO_API_URL:-}")",
	VITE_SUPABASE_URL: "$(escape_js "${VITE_SUPABASE_URL:-}")",
	VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY: "$(escape_js "${VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY:-}")"
};
EOC
EOF

RUN chmod +x /docker-entrypoint.d/30-generate-env.sh

EXPOSE 80
