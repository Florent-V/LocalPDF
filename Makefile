COMPOSE := docker compose

.PHONY: install up up-build down restart logs logs-front logs-back clean build test test-back test-front lint lint-back lint-front fmt \
        urls prod-check prod-build prod-up prod-backup prod-deploy prod-down prod-restart prod-logs prod-ps prod-health

PROD_COMPOSE := docker compose --env-file .env.prod -f docker-compose.prod.yml
BACKUP_DIR ?= ./backups

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && pnpm install

up: ## Local dev: starts the stack (see `make urls`)
	$(COMPOSE) up -d
	@$(MAKE) --no-print-directory urls

up-build: ## Local dev: rebuilds the images then starts the stack
	$(COMPOSE) up --build -d
	@$(MAKE) --no-print-directory urls

urls: ## Shows the dev URLs and the OAuth settings to declare locally
	@. ./.env 2>/dev/null; \
	echo "Application   : http://localhost:$${FRONTEND_PORT:-3010}   (Nuxt proxies /api and /auth to the API)"; \
	echo "Redirect URI  : http://localhost:$${FRONTEND_PORT:-3010}/auth/callback"; \
	echo "Back-channel  : http://host.docker.internal:$${FRONTEND_PORT:-3010}/auth/backchannel-logout  (OAuth server in Docker)"; \
	echo "API (host net): http://localhost:$${BACKEND_PORT:-8000}"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

logs-front:
	$(COMPOSE) logs -f frontend

logs-back:
	$(COMPOSE) logs -f backend

clean:
	$(COMPOSE) down -v
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +

build:
	$(COMPOSE) build

test: test-back test-front

test-back:
	cd backend && . .venv/bin/activate && pytest

test-front:
	cd frontend && pnpm test

lint: lint-back lint-front

lint-back:
	cd backend && . .venv/bin/activate && ruff check app

lint-front:
	cd frontend && pnpm lint

fmt:
	cd backend && . .venv/bin/activate && ruff format app
	cd frontend && pnpm lint --fix

## —— Production ———————————————————————————————————————————————————————
prod-check: ## Checks that .env.prod exists
	@test -f .env.prod || (echo "Create .env.prod: cp .env.prod.example .env.prod, then fill it (docs/deploiement.md)." && exit 1)

prod-build: prod-check ## Builds the production images
	$(PROD_COMPOSE) build --pull

prod-up: prod-check ## Starts (or updates) production
	$(PROD_COMPOSE) up -d --wait

prod-backup: prod-check ## Backs up the sessions database and .env.prod into BACKUP_DIR (keeps 30 days)
	@umask 077; mkdir -p "$(BACKUP_DIR)"; stamp=$$(date +%F-%H%M%S); \
	cp .env.prod "$(BACKUP_DIR)/env.prod-$$stamp"; \
	if $(PROD_COMPOSE) ps --status running --services | grep -qx api; then \
	  $(PROD_COMPOSE) exec -T api python -c "import sqlite3; s=sqlite3.connect('/data/sessions.db'); d=sqlite3.connect('/tmp/sessions-backup.db'); s.backup(d)" \
	  && docker cp localpdf-api:/tmp/sessions-backup.db "$(BACKUP_DIR)/sessions-$$stamp.db"; \
	fi; \
	find "$(BACKUP_DIR)" -type f -mtime +30 -delete; \
	echo "Backup in $(BACKUP_DIR) ($$stamp)"

prod-deploy: prod-check ## Update: git pull, backup, build, restart, health check (fails if unhealthy)
	git pull --ff-only
	$(MAKE) --no-print-directory prod-backup prod-build prod-up prod-health
	$(PROD_COMPOSE) ps
	@docker image prune -f >/dev/null

prod-down: prod-check ## Stops production
	$(PROD_COMPOSE) down

prod-restart: prod-check ## Restarts production
	$(PROD_COMPOSE) restart

prod-logs: prod-check ## Production logs
	$(PROD_COMPOSE) logs --tail=200 --follow

prod-ps: prod-check ## Containers status
	$(PROD_COMPOSE) ps

prod-health: prod-check ## Checks the app answers (302 to the OAuth login when logged out) and the API is ready; non-zero exit otherwise
	@. ./.env.prod; code=$$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$${FRONTEND_PORT:-3010}/auth/login); \
	echo "app /auth/login : HTTP $$code (302 expected)"; test "$$code" = "302"
	@$(PROD_COMPOSE) exec -T api python -c "import urllib.request as u; print('api /api/health :', u.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status)"
