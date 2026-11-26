# ==============================================================================
# InfraScan Frontend Production Dockerfile
# Stage 1: Build React/Vite SPA bundle
# Stage 2: Serve via lightweight Nginx web server with API reverse proxy
# ==============================================================================

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications
COPY package.json package-lock.json* ./

# Install npm dependencies
RUN npm ci --prefer-offline --no-audit

# Copy frontend source code
COPY . .

# Build production bundle into /app/dist
RUN npm run build

# Stage 2: Production Web Server
FROM nginx:alpine

# Remove default nginx html files
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose web server port
EXPOSE 80

# Nginx healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
