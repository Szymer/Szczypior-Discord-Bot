# syntax=docker/dockerfile:1
FROM node:20-slim

WORKDIR /app

COPY services/web-dashboard/react/package*.json ./
RUN npm ci

COPY services/web-dashboard/react /app

ENV VITE_DJANGO_API_URL=http://web-dashboard:8001
EXPOSE 8080

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8080"]
