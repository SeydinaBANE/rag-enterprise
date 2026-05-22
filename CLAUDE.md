# Plateforme RAG d'Entreprise — Instructions Claude Code

## Contexte projet
Système RAG (Retrieval-Augmented Generation) d'entreprise. Les utilisateurs posent des questions en langage naturel sur des documents internes (PDF, Confluence, Slack). Le backend répond en streaming avec citations de sources.

## Architecture
- **Backend** : Python 3.11 + FastAPI, dans `backend/`
- **Frontend** : Next.js 15 + Tailwind CSS + Zustand, dans `frontend/` (pas de shadcn — styles Tailwind maison)
- **Vector DB** : pgvector (PostgreSQL 16), config dans `docker-compose.yml`
- **Cache** : Redis 7
- **Workers** : Celery pour l'ingestion asynchrone
- **Auth** : JWT (python-jose) + RBAC par collection — `backend/app/api/deps.py`
- **Monitoring** : Prometheus `:9090` + Grafana `:3001` — `monitoring/`

## Commandes essentielles

```bash
# Dev local complet
docker compose up -d

# Backend seul (dev)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend seul (dev)
cd frontend && npm run dev

# Tests backend
cd backend && pytest tests/ -v

# Linter (doit passer à 0 erreur)
cd backend && ruff check app/

# Créer un admin
make create-admin-script EMAIL=admin@example.com PASSWORD=secret

# Ingestion manuelle d'un PDF (token admin requis)
curl -X POST http://localhost:8000/api/ingest/pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@doc.pdf" \
  -F "collection=general"

# Query test (guest, pas de token)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Quelle est la politique de congés ?"}'
```

## Conventions de code

### Python (backend)
- Pydantic v2 pour tous les schémas de données
- SQLAlchemy 2.0 async (`async_session`, `select()` style)
- Typage strict partout (`-> str`, `-> list[Document]`)
- Pas de `print()` — utiliser `logging` ou `structlog`
- Async/await partout dans les routes FastAPI
- Imports triés (isort via ruff) — ruff pinner à `0.15.14` dans la CI

### TypeScript (frontend)
- `'use client'` seulement quand nécessaire (hooks, events)
- Fetches via `src/lib/api.ts` uniquement — auth headers inclus automatiquement via `authHeaders()`
- SSE (Server-Sent Events) pour le streaming des réponses
- État global via Zustand (`src/store/useStore.ts`) — `user`, `collection`, `messages`, `ingestionJobs`
- Layout deux colonnes : `DocumentPanel` (sidebar gauche) + `Chat` (zone principale)

## Variables d'environnement
Voir `.env.example`. Copier en `.env` pour le dev local. Ne jamais committer `.env`.

## Points d'attention
- **RBAC** : géré dans `backend/app/api/deps.py` via `CurrentUser.can_access(collection)` — ne jamais bypasser
- **Ingest** : nécessite `require_admin` — les routes `/api/ingest/*` sont réservées aux admins
- **Embeddings** : fastembed local (no API key), `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions
- **Déduplication** : champ `checksum` dans `documents` — toujours vérifier avant d'embedder
- **Audit trail** : toutes les requêtes loggées dans `query_logs` (user_id, question, sources, latence, tokens)
- **Reranker** : Cohere optionnel (`COHERE_API_KEY`), fallback cosinus si absent
- **Métriques** : `backend/app/core/metrics.py` — 6 compteurs Prometheus, exposés sur `/metrics`
- **bcrypt** : pinner à `==3.2.2` (passlib incompatible avec bcrypt 4.x)

## Structure des migrations
- `backend/migrations/001_initial.sql` — tables documents, query_logs, ingestion_jobs + pgvector
- `backend/migrations/002_users.sql` — table users (auth JWT + RBAC)

## Skill routing
- Bugs/erreurs → `/investigate`
- Review code → `/review`
- QA → `/qa`
- Architecture → `/plan-eng-review`
