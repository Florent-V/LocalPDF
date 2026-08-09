COMPOSE := docker compose

.PHONY: install up up-build down restart logs logs-front logs-back clean build test test-back test-front lint lint-back lint-front fmt

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && pnpm install

up:
	$(COMPOSE) up -d

up-build:
	$(COMPOSE) up --build -d

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
