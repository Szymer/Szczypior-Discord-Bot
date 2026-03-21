# syntax=docker/dockerfile:1
FROM node:20-slim AS builder

WORKDIR /app

# Skopiuj tylko pliki wymagane do instalacji
COPY services/web-dashboard/react/package*.json ./
ENV NODE_ENV=development
ENV VITE_APP_ENV=production
ENV NODE_OPTIONS=--max-old-space-size=1024

RUN npm ci --include=dev

COPY services/web-dashboard/react /app

RUN npm run build

# Fail fast if build output is missing.
RUN test -d /app/dist

# Stage drugi – serwer statycznych plików (nginx)
FROM nginx:stable-alpine AS production

# Domyslna konfiguracja nginx dla SPA
COPY infrastructure/docker/nginx/spa.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
