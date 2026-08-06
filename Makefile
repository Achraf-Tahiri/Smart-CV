# New Smart CV — raccourcis de développement.
# Usage : make <cible>. « make » seul (ou « make help ») liste les cibles.
# Note : certaines cibles sont câblées aux incréments indiqués [0.x].

COMPOSE := docker compose
API := apps/api
WEB := apps/web

.DEFAULT_GOAL := help

.PHONY: help
help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## Démarre la stack Docker (Postgres, API, ...) [0.3]
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Arrête la stack Docker
	$(COMPOSE) down

.PHONY: logs
logs: ## Suit les logs de la stack
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Liste les conteneurs
	$(COMPOSE) ps

.PHONY: test
test: ## Lance les tests de l'API (pytest) [0.2]
	cd $(API) && uv run pytest

.PHONY: lint
lint: ## Vérifie le style Python (ruff) [0.2]
	cd $(API) && uv run ruff check .

.PHONY: format
format: ## Formate le code Python (black + ruff --fix) [0.2]
	cd $(API) && uv run black . && uv run ruff check --fix .

.PHONY: migrate
migrate: ## Applique les migrations (alembic upgrade head) [0.4]
	cd $(API) && uv run alembic upgrade head

.PHONY: migration
migration: ## Crée une migration ; usage : make migration m="message" [0.4]
	cd $(API) && uv run alembic revision --autogenerate -m "$(m)"

.PHONY: web-dev
web-dev: ## Démarre le front Next.js en mode dev [0.5]
	cd $(WEB) && pnpm dev
