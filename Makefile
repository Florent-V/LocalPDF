# Same Makefile in ImageConverter and pdf-tools: only the two defaults below differ.
DEFAULT_FRONTEND_PORT := 3010
DEFAULT_REMOTE_PORT   := 3010

BACKEND_DIR := backend
BACKUP_DIR  ?= ./backups
DEV_COMP    := docker compose
PROD_COMP   := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# Variables that must be set in .env (see .env.example)
REQUIRED_ENV      := OAUTH_ISSUER OAUTH_CLIENT_ID OAUTH_CLIENT_SECRET
REQUIRED_PROD_ENV := $(REQUIRED_ENV) PUBLIC_ORIGIN

.DEFAULT_GOAL := help
.PHONY: help env-check dev up down restart logs ps build rebuild urls install test test-back test-front \
        lint lint-back lint-front fmt audit clean \
        prod-check prod-build prod-up prod-backup prod-deploy prod-down prod-restart prod-logs prod-ps prod-health

## —— Help ——————————————————————————————————————————————————————————————
help: ## List the commands
	@grep -E '(^[a-zA-Z_-]+:.*?## .*$$)|(^## )' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-14s\033[0m %s\n", $$1, $$2}' | sed -e 's/\[32m## /\n[33m/'

env-check: ## Check that .env exists and holds every OAuth variable
	@test -f .env || (echo "Missing .env: cp .env.example .env, then fill it (docs/deploiement.md)." && exit 1)
	@set -a; . ./.env; set +a; missing=""; \
	for v in $(REQUIRED_ENV); do eval "val=\$${$$v:-}"; [ -n "$$val" ] || missing="$$missing $$v"; done; \
	if [ -n "$$missing" ]; then echo "Empty in .env:$$missing" && exit 1; fi

## —— Dev (hot reload, http://localhost:FRONTEND_PORT) ———————————————————
dev: env-check ## Start the dev stack in the foreground (Ctrl+C to stop)
	@$(DEV_COMP) up --build

up: env-check ## Start the dev stack in the background
	@$(DEV_COMP) up -d --build
	@$(MAKE) --no-print-directory urls

down: ## Stop the dev stack
	@$(DEV_COMP) down

restart: down up ## Restart the dev stack

logs: ## Follow the dev stack logs
	@$(DEV_COMP) logs -f

ps: ## Dev containers status
	@$(DEV_COMP) ps

build: ## Build the dev images
	@$(DEV_COMP) build

rebuild: ## Rebuild the dev images from scratch, then start
	@$(DEV_COMP) build --no-cache
	@$(DEV_COMP) up -d

urls: ## Show the dev URLs and the settings to declare on the OAuth server
	@set -a; . ./.env 2>/dev/null; set +a; port=$${FRONTEND_PORT:-$(DEFAULT_FRONTEND_PORT)}; \
	echo "Application   : http://localhost:$$port   (Nuxt proxies /api and /auth to the API)"; \
	echo "Redirect URI  : http://localhost:$$port/auth/callback"; \
	echo "Back-channel  : http://host.docker.internal:$$port/auth/backchannel-logout  (OAuth server in Docker)"; \
	echo "API (host net): http://localhost:$${BACKEND_PORT:-8000}"

## —— Code ——————————————————————————————————————————————————————————————
install: ## uv sync + pnpm install
	cd $(BACKEND_DIR) && uv sync
	cd frontend && pnpm install

test: test-back test-front ## Run every test

test-back: ## Backend tests
	cd $(BACKEND_DIR) && uv run pytest

test-front: ## Frontend tests (if the app has any)
	cd frontend && pnpm run --if-present test

lint: lint-back lint-front ## Lint everything

lint-back:
	cd $(BACKEND_DIR) && uv run ruff check .

lint-front:
	cd frontend && pnpm lint

fmt: ## Auto-format / fix lint
	cd $(BACKEND_DIR) && uv run ruff format .
	cd frontend && pnpm lint --fix

audit: ## pnpm audit (high+ severity) in frontend/
	cd frontend && pnpm audit --audit-level=high

clean: ## Remove caches and the dev volumes
	$(DEV_COMP) down -v
	rm -rf $(BACKEND_DIR)/.venv $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache

## —— Production (web on 127.0.0.1:REMOTE_FRONTEND_PORT, behind the host's Caddy) ——
prod-check: env-check ## Check .env for production (no dev-only values)
	@set -a; . ./.env; set +a; \
	[ -n "$${PUBLIC_ORIGIN:-}" ] || (echo "Empty in .env: PUBLIC_ORIGIN" && exit 1); \
	case "$$PUBLIC_ORIGIN" in https://*) ;; *) echo "PUBLIC_ORIGIN must be https:// in production" && exit 1;; esac; \
	case "$$OAUTH_ISSUER" in https://*) ;; *) echo "OAUTH_ISSUER must be https:// in production" && exit 1;; esac; \
	[ "$${APP_ENV:-prod}" = prod ] || (echo "APP_ENV must be prod in production" && exit 1)

prod-build: prod-check ## Build the production images
	@$(PROD_COMP) build --pull

prod-up: prod-check ## Start (or update) production
	@$(PROD_COMP) up -d --wait

prod-backup: prod-check ## Back up the sessions database and .env into BACKUP_DIR (keeps 30 days)
	@umask 077; mkdir -p "$(BACKUP_DIR)"; stamp=$$(date +%F-%H%M%S); \
	cp .env "$(BACKUP_DIR)/env-$$stamp"; \
	if $(PROD_COMP) ps --status running --services | grep -qx api; then \
	  $(PROD_COMP) exec -T api python -c "import sqlite3; s=sqlite3.connect('/data/sessions.db'); d=sqlite3.connect('/tmp/sessions-backup.db'); s.backup(d)" \
	  && $(PROD_COMP) cp api:/tmp/sessions-backup.db "$(BACKUP_DIR)/sessions-$$stamp.db"; \
	fi; \
	find "$(BACKUP_DIR)" -type f -mtime +30 -delete; \
	echo "Backup in $(BACKUP_DIR) ($$stamp)"

prod-deploy: prod-check ## Update: git pull, backup, build, restart, health check (fails if unhealthy)
	git pull --ff-only
	$(MAKE) --no-print-directory prod-backup prod-build prod-up prod-health
	$(PROD_COMP) ps
	@docker image prune -f >/dev/null

prod-down: ## Stop production
	@$(PROD_COMP) down

prod-restart: ## Restart production (no rebuild)
	@$(PROD_COMP) restart

prod-logs: ## Follow production logs
	@$(PROD_COMP) logs --tail=200 -f

prod-ps: ## Production containers status
	@$(PROD_COMP) ps

prod-health: prod-check ## 302 to the OAuth login when logged out, and the API ready; non-zero exit otherwise
	@set -a; . ./.env; set +a; code=$$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$${REMOTE_FRONTEND_PORT:-$(DEFAULT_REMOTE_PORT)}/auth/login); \
	echo "app /auth/login : HTTP $$code (302 expected)"; test "$$code" = "302"
	@$(PROD_COMP) exec -T api python -c "import urllib.request as u; print('api /api/health :', u.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status)"
