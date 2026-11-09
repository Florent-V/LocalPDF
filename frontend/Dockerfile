FROM node:24-slim AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.17.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run generate

# Static files only: no Node at runtime. The dev stack stops at the `build` stage.
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/.output/public /srv
# Unprivileged: port 8080, Caddy's state in /tmp
ENV XDG_DATA_HOME=/tmp XDG_CONFIG_HOME=/tmp
USER 10001:10001
EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
