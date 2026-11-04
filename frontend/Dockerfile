FROM node:22-alpine

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm@11.17.0 \
    && pnpm install --frozen-lockfile --ignore-scripts && pnpm exec nuxt prepare

COPY . .

RUN chown -R node:node /app
USER node

EXPOSE 3000

# pnpm's default "verify deps before run" behavior spawns an internal
# `pnpm install` subprocess whenever it suspects node_modules might be
# stale relative to the lockfile — which it always does on a fresh
# container, since the build-time install happens in a different
# environment than the runtime one. That subprocess crashes under this
# non-root Alpine setup ("attempt to write a readonly database" opening
# its SQLite store index, even though file permissions are correct).
# `--config.verify-deps-before-run=warn` keeps the (harmless) check but
# only logs instead of re-installing. A project .npmrc with the same
# setting was tried first but isn't picked up in this run context, so
# it's passed as an explicit CLI flag instead.
CMD ["pnpm", "--config.verify-deps-before-run=warn", "dev"]
