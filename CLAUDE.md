# Plateforme RAG d'Entreprise — Instructions Claude Code

## Contexte projet
Système RAG (Retrieval-Augmented Generation) d'entreprise. Les utilisateurs posent des questions en langage naturel sur des documents internes (PDF, Confluence, Slack). Le backend répond en streaming avec citations de sources.

## Architecture
- **Backend** : Python 3.11 + FastAPI + LangChain, dans `backend/`
- **Frontend** : Next.js 15 + Tailwind CSS + Zustand, dans `frontend/` (pas de shadcn — styles Tailwind maison)
- **Vector DB** : pgvector (PostgreSQL), config dans `docker-compose.yml`
- **Cache** : Redis
- **Workers** : Celery pour l'ingestion asynchrone

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

# Ingestion manuelle d'un PDF
curl -X POST http://localhost:8000/api/ingest/pdf \
  -F "file=@doc.pdf" \
  -F "collection=general"

# Query test
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

### TypeScript (frontend)
- `'use client'` seulement quand nécessaire (hooks, events)
- Fetches via `src/lib/api.ts` uniquement, jamais directement dans les composants
- SSE (Server-Sent Events) pour le streaming des réponses
- État global via Zustand (`src/store/useStore.ts`) — collection, messages, jobs d'ingestion
- Layout deux colonnes : `DocumentPanel` (sidebar gauche) + `Chat` (zone principale)

## Variables d'environnement
Voir `.env.example`. Copier en `.env` pour le dev local. Ne jamais committer `.env`.

## Points d'attention
- Les embeddings coûtent de l'argent — toujours vérifier la déduplication avant d'embedder (champ `checksum` dans `documents`)
- Le RBAC est géré dans `backend/app/api/deps.py` via `get_current_user` — ne jamais bypasser
- Toutes les requêtes utilisateur sont loggées dans la table `query_logs` (audit trail)
- Le reranker Cohere est optionnel (si `COHERE_API_KEY` absent, fallback sur score cosinus seul)

## Skill routing
- Bugs/erreurs → `/investigate`
- Review code → `/review`
- QA → `/qa`
- Architecture → `/plan-eng-review`
