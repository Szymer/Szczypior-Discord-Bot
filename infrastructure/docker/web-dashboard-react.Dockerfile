# syntax=docker/dockerfile:1
FROM node:20-slim AS builder

WORKDIR /app

# Skopiuj tylko pliki wymagane do instalacji
COPY services/web-dashboard/react/package*.json ./

RUN npm ci

# Skopiuj całość frontendu
COPY services/web-dashboard/react /app

# Zbuduj frontend
RUN npm run build

# Stage drugi – serwer statycznych plików (nginx)
FROM nginx:stable-alpine AS production

# Domyslna konfiguracja nginx dla SPA
COPY infrastructure/docker/nginx/spa.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
