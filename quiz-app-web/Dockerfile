# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the static bundle. Create React App inlines REACT_APP_* at
# build time, so the API base URL is a build argument, not a runtime env var.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

ARG REACT_APP_API_BASEURL=http://localhost:8221/
ENV REACT_APP_API_BASEURL=${REACT_APP_API_BASEURL} \
    CI=true \
    GENERATE_SOURCEMAP=false

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — serve. Only the built assets and an nginx config ship.
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/build /usr/share/nginx/html

# nginx:alpine already defines the `nginx` user; give it the directories it
# needs so the server never runs as root.
RUN mkdir -p /tmp/client_temp \
    && chown -R nginx:nginx /usr/share/nginx/html /tmp/client_temp

USER nginx
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
