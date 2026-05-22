.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Couleurs ──────────────────────────────────────────────────────────────────
BOLD  := \033[1m
GREEN := \033[32m
CYAN  := \033[36m
RESET := \033[0m

# ─────────────────────────────────────────────────────────────────────────────
# AIDE
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Affiche cette aide
	@echo ""
	@echo "$(BOLD)Plateforme RAG d'Entreprise$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: install
install: ## Installe toutes les dépendances (backend + frontend)
	@echo "$(GREEN)→ Installation backend$(RESET)"
	cd backend && pip install -r requirements.txt
	@echo "$(GREEN)→ Installation frontend$(RESET)"
	cd frontend && npm install
	@echo "$(GREEN)→ Installation pre-commit$(RESET)"
	pip install pre-commit && pre-commit install

.PHONY: install-backend
install-backend: ## Installe uniquement les dépendances Python
	cd backend && pip install -r requirements.txt

.PHONY: install-frontend
install-frontend: ## Installe les dépendances Node et génère package-lock.json
	cd frontend && npm install

.PHONY: setup
setup: ## Setup complet du projet (install + .env + pre-commit + db)
	@[ -f .env ] || (cp .env.example .env && echo "$(GREEN)→ .env créé depuis .env.example — remplir OPENROUTER_API_KEY$(RESET)")
	$(MAKE) install
	$(MAKE) db-up
	@echo "$(GREEN)✓ Projet prêt. Lancer: make dev$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# DÉVELOPPEMENT
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: dev
dev: ## Lance backend + frontend en mode développement
	@echo "$(GREEN)→ Démarrage des services (postgres, redis)$(RESET)"
	docker compose up -d postgres redis
	@echo "$(GREEN)→ Démarrage backend sur :8000 et frontend sur :3000$(RESET)"
	@trap 'kill %1 %2' INT; \
		(cd backend && uvicorn app.main:app --reload --port 8000) & \
		(cd frontend && npm run dev) & \
		wait

.PHONY: dev-backend
dev-backend: ## Lance uniquement le backend (FastAPI reload)
	docker compose up -d postgres redis
	cd backend && uvicorn app.main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend: ## Lance uniquement le frontend (Next.js)
	cd frontend && npm run dev

.PHONY: worker
worker: ## Lance le worker Celery
	cd backend && celery -A app.workers.tasks worker --loglevel=info --concurrency=2

# ─────────────────────────────────────────────────────────────────────────────
# DOCKER
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: up
up: ## Lance la stack Docker complète
	docker compose up -d

.PHONY: down
down: ## Arrête les conteneurs
	docker compose down

.PHONY: restart
restart: ## Redémarre les conteneurs
	docker compose restart

.PHONY: logs
logs: ## Affiche les logs en temps réel
	docker compose logs -f

.PHONY: logs-backend
logs-backend: ## Logs du backend uniquement
	docker compose logs -f backend

.PHONY: build
build: ## Rebuild les images Docker
	docker compose build --no-cache

.PHONY: db-up
db-up: ## Lance uniquement PostgreSQL et Redis
	docker compose up -d postgres redis
	@echo "$(GREEN)→ Attente postgres...$(RESET)"
	@until docker compose exec postgres pg_isready -U rag -d ragdb 2>/dev/null; do sleep 1; done
	@echo "$(GREEN)✓ PostgreSQL prêt$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: test
test: ## Lance tous les tests
	cd backend && pytest tests/ -v --tb=short

.PHONY: test-watch
test-watch: ## Lance les tests en mode watch
	cd backend && pytest tests/ -v --tb=short -f

.PHONY: test-cov
test-cov: ## Tests avec rapport de couverture
	cd backend && pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)→ Rapport HTML: backend/htmlcov/index.html$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# QUALITÉ DE CODE
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: lint
lint: ## Lint Python (ruff) + TypeScript (eslint)
	@echo "$(GREEN)→ Ruff lint$(RESET)"
	cd backend && ruff check app/
	@echo "$(GREEN)→ ESLint$(RESET)"
	cd frontend && npm run lint

.PHONY: format
format: ## Formate Python (ruff) + TypeScript (prettier)
	@echo "$(GREEN)→ Ruff format$(RESET)"
	cd backend && ruff format app/ && ruff check --fix app/
	@echo "$(GREEN)→ Prettier$(RESET)"
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"

.PHONY: typecheck
typecheck: ## Vérifie les types Python (mypy) + TypeScript (tsc)
	@echo "$(GREEN)→ Mypy$(RESET)"
	cd backend && mypy app/ --ignore-missing-imports
	@echo "$(GREEN)→ TypeScript$(RESET)"
	cd frontend && npx tsc --noEmit

.PHONY: check
check: lint typecheck ## Lint + typecheck (sans tests)

.PHONY: pc
pc: ## Lance pre-commit sur tous les fichiers
	pre-commit run --all-files

# ─────────────────────────────────────────────────────────────────────────────
# INGESTION
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: ingest-pdf
ingest-pdf: ## Ingère un PDF (usage: make ingest-pdf FILE=doc.pdf COLLECTION=general)
	@[ -n "$(FILE)" ] || (echo "Usage: make ingest-pdf FILE=mon_doc.pdf" && exit 1)
	curl -s -X POST http://localhost:8000/api/ingest/pdf \
		-F "file=@$(FILE)" \
		-F "collection=$(or $(COLLECTION),general)" | python3 -m json.tool

.PHONY: ingest-confluence
ingest-confluence: ## Ingère un espace Confluence (usage: make ingest-confluence SPACE=ENG)
	@[ -n "$(SPACE)" ] || (echo "Usage: make ingest-confluence SPACE=ENG" && exit 1)
	curl -s -X POST "http://localhost:8000/api/ingest/confluence?space_key=$(SPACE)&collection=$(or $(COLLECTION),general)" \
		| python3 -m json.tool

# ─────────────────────────────────────────────────────────────────────────────
# REQUÊTES DE TEST
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: query
query: ## Test une requête RAG (usage: make query Q="Quelle est la politique de congés ?")
	@[ -n "$(Q)" ] || (echo 'Usage: make query Q="votre question"' && exit 1)
	curl -s -X POST http://localhost:8000/api/query \
		-H "Content-Type: application/json" \
		-d '{"question": "$(Q)", "stream": false}' | python3 -m json.tool

.PHONY: query-stream
query-stream: ## Test une requête en streaming (usage: make query-stream Q="...")
	@[ -n "$(Q)" ] || (echo 'Usage: make query-stream Q="votre question"' && exit 1)
	curl -sN -X POST http://localhost:8000/api/query \
		-H "Content-Type: application/json" \
		-d '{"question": "$(Q)", "stream": true}'

.PHONY: health
health: ## Vérifie la santé de l'API
	curl -s http://localhost:8000/api/health | python3 -m json.tool

# ─────────────────────────────────────────────────────────────────────────────
# NETTOYAGE
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Supprime les fichiers temporaires
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	cd frontend && rm -rf .next/ 2>/dev/null || true

.PHONY: clean-all
clean-all: down clean ## Supprime conteneurs, volumes et fichiers temporaires
	docker compose down -v
	cd frontend && rm -rf node_modules/ 2>/dev/null || true

.PHONY: reset-db
reset-db: ## Recrée la base de données from scratch (DESTRUCTIF)
	@echo "$(BOLD)⚠️  Ceci supprime toutes les données. Confirmer avec CONFIRM=yes$(RESET)"
	@[ "$(CONFIRM)" = "yes" ] || (echo "Annulé." && exit 1)
	docker compose down -v postgres
	docker compose up -d postgres
	@until docker compose exec postgres pg_isready -U rag -d ragdb 2>/dev/null; do sleep 1; done
	@echo "$(GREEN)✓ Base recréée$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS (dev only)
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: gen-secret
gen-secret: ## Génère un SECRET_KEY sécurisé
	@openssl rand -hex 32

.PHONY: secrets-baseline
secrets-baseline: ## Crée le baseline detect-secrets
	detect-secrets scan --exclude-files ".env" > .secrets.baseline
	@echo "$(GREEN)✓ .secrets.baseline créé$(RESET)"
