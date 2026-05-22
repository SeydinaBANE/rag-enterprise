# Guide technique — RAG Enterprise Platform

> Ce document est la référence pour tout développeur qui rejoint le projet. Il couvre l'architecture réelle du code, les workflows quotidiens, les contraintes non-négociables, et les pièges connus.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Premier démarrage](#2-premier-démarrage)
3. [Workflows de développement](#3-workflows-de-développement)
4. [Architecture backend](#4-architecture-backend)
5. [Pipeline RAG — détail technique](#5-pipeline-rag--détail-technique)
6. [Auth JWT et RBAC](#6-auth-jwt-et-rbac)
7. [Ingestion de documents](#7-ingestion-de-documents)
8. [Schéma de base de données](#8-schéma-de-base-de-données)
9. [Architecture frontend](#9-architecture-frontend)
10. [Variables d'environnement](#10-variables-denvironnement)
11. [Tests et qualité de code](#11-tests-et-qualité-de-code)
12. [CI/CD GitHub Actions](#12-cicd-github-actions)
13. [Monitoring Prometheus + Grafana](#13-monitoring-prometheus--grafana)
14. [Opérations courantes](#14-opérations-courantes)
15. [Pièges connus et décisions techniques](#15-pièges-connus-et-décisions-techniques)
16. [Feuille de route Phase 2](#16-feuille-de-route-phase-2)

---

## 1. Vue d'ensemble

Le système permet aux employés de poser des questions en langage naturel sur des documents internes (PDF, Confluence, Slack) et d'obtenir des réponses sourcées en streaming.

**Stack résumée :**

| Couche | Technologie | Rôle |
|---|---|---|
| API | FastAPI 0.115 + uvicorn | Routes async, SSE, RBAC |
| Auth | JWT (python-jose) + passlib/bcrypt 3.2.2 | Access 15min + Refresh 7j |
| LLM | OpenRouter (OpenAI-compatible) | Génération de réponses |
| Embeddings | fastembed local (384d) | Sans clé API, FR/EN |
| Reranker | Cohere Rerank v3.5 | Optionnel, fallback cosinus |
| Vector DB | pgvector + PostgreSQL 16 (HNSW) | Recherche dense |
| FTS | PostgreSQL `to_tsvector('french')` | Recherche sparse BM25 |
| Cache/Queue | Redis 7 + Celery | Ingestion asynchrone |
| Frontend | Next.js 15, React 19, Zustand, Tailwind | Interface chat + upload |
| Monitoring | Prometheus 2.55 + Grafana 11 | 10 panneaux RAG |

**Ports locaux :**

| Service | URL |
|---|---|
| Interface web | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (admin / admin) |
| Prometheus | http://localhost:9090 |
| PostgreSQL | localhost:5432 (rag / rag / ragdb) |
| Redis | localhost:6379 |

---

## 2. Premier démarrage

### Prérequis

- Docker Desktop (engine + compose)
- Node.js 20+ (pour le dev frontend local)
- Python 3.11+ (pour le dev backend local)
- Une clé [OpenRouter](https://openrouter.ai) — seul champ obligatoire

### Installation complète (Docker — recommandé)

```bash
git clone https://github.com/SeydinaBANE/rag-enterprise.git
cd rag-enterprise

cp .env.example .env
# Éditer .env : renseigner OPENROUTER_API_KEY
# Générer un SECRET_KEY sécurisé :
make gen-secret

docker compose up -d
```

Attendre que tous les services soient `healthy` :

```bash
docker compose ps   # tous doivent être "healthy" ou "running"
```

Créer un compte admin pour accéder aux routes d'ingestion :

```bash
make create-admin-script EMAIL=admin@example.com PASSWORD=secret123
```

Vérifier que tout fonctionne :

```bash
make health      # {"status": "ok", "db": "ok", ...}
make metrics     # métriques Prometheus brutes
```

### Installation dev local (sans Docker pour backend/frontend)

```bash
make setup       # crée .env + installe dépendances + démarre postgres+redis Docker

make dev         # backend :8000 + frontend :3000 en parallèle
# ou séparément :
make dev-backend
make dev-frontend
```

Le worker Celery pour l'ingestion asynchrone :

```bash
make worker      # dans un terminal séparé
```

---

## 3. Workflows de développement

### Flux de travail standard

```
1. git checkout -b feat/ma-feature
2. make dev (backend + frontend)
3. Coder + tester manuellement
4. make lint        # doit passer à 0 erreur
5. make test        # tests pytest
6. git push origin feat/ma-feature
7. Ouvrir une PR → CI (lint + tests + build Docker)
8. Merge dans main
```

### Commandes Make essentielles

```bash
make help           # liste toutes les cibles disponibles

# Dev
make dev            # backend + frontend en parallèle
make dev-backend    # FastAPI seul avec rechargement auto
make dev-frontend   # Next.js seul

# Qualité
make lint           # ruff + eslint (doit passer à 0 erreur)
make format         # ruff format + prettier (auto-corrige)
make typecheck      # mypy + tsc --noEmit
make test           # pytest -v
make test-cov       # pytest avec rapport HTML (htmlcov/)

# Docker
make up / down / build / logs / logs-backend

# Opérations
make query Q="ma question"           # test rapide
make query-stream Q="ma question"    # test streaming SSE
make ingest-pdf FILE=doc.pdf COLLECTION=rh
make create-admin-script EMAIL=... PASSWORD=...
make reset-db CONFIRM=yes            # DESTRUCTIF — recrée la DB
```

### Linter Python — règles imposées

Le linter est ruff `0.15.14` (même version en local et en CI — ne pas changer).

```bash
cd backend && ruff check app/          # vérifier
cd backend && ruff check app/ --fix    # auto-corriger (la majorité des erreurs)
```

Règles qui nécessitent une correction manuelle :
- **B904** : `raise ... from exc` dans un bloc `except`
- **B905** : `zip(..., strict=False)` obligatoire
- **B007** : variable de boucle inutilisée → renommer en `_var`
- **C401** : `set(generator)` → `{x for x in ...}`

---

## 4. Architecture backend

```
backend/app/
├── main.py              # FastAPI app, CORS, routes, Prometheus instrumentator
├── api/
│   ├── deps.py          # CurrentUser, RBAC — NE PAS BYPASSER
│   └── routes/
│       ├── auth.py      # /api/auth/* (register, login, refresh, me)
│       ├── query.py     # /api/query + /api/query/feedback
│       ├── ingest.py    # /api/ingest/* (require_admin)
│       └── health.py    # /api/health
├── core/
│   ├── config.py        # Pydantic-settings (lru_cache)
│   ├── database.py      # SQLAlchemy async, AsyncSessionLocal, get_db
│   ├── security.py      # JWT, bcrypt, GUEST_COLLECTIONS
│   └── metrics.py       # 6 compteurs Prometheus
├── models/
│   ├── db.py            # ORM SQLAlchemy 2.0 (Document, QueryLog, User, IngestionJob)
│   └── schemas.py       # Pydantic v2 (validation entrée/sortie API)
├── ingestion/
│   ├── base.py          # Classe abstraite BaseLoader + save_to_db
│   ├── chunker.py       # Découpage section-aware + RecursiveCharacterTextSplitter
│   ├── embedder.py      # fastembed local + checksum MD5 + déduplication
│   ├── pdf_loader.py    # PyMuPDF → texte → chunks → embeddings → DB
│   ├── confluence.py    # API Confluence → chunks → embeddings → DB
│   └── slack.py         # Export JSON Slack → chunks → embeddings → DB
├── rag/
│   ├── pipeline.py      # Orchestrateur : embed → retrieve → rerank → generate → log
│   ├── retriever.py     # Dense (pgvector cosinus) + Sparse (BM25 FTS) → RRF
│   ├── reranker.py      # Cohere Rerank v3.5 (fallback cosinus si COHERE_API_KEY absent)
│   └── generator.py     # OpenRouter streaming/non-streaming via openai SDK
└── workers/
    └── tasks.py         # Celery tasks pour ingestion async
```

### Point d'entrée — `main.py`

```python
app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)
app.include_router(auth.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(health.router, prefix="/api")
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Les métriques Prometheus HTTP automatiques (`http_request_duration_seconds`, etc.) viennent de `prometheus_fastapi_instrumentator`. Les métriques RAG custom sont dans `core/metrics.py`.

### Configuration — `core/config.py`

Toute la config vient des variables d'environnement via Pydantic-settings. L'objet `Settings` est un singleton via `@lru_cache` :

```python
from app.core.config import get_settings
settings = get_settings()
```

**Ne jamais instancier `Settings()` directement** — cela casse le cache et peut lire un `.env` différent.

---

## 5. Pipeline RAG — détail technique

```
Question utilisateur
       │
       ├─► RBAC : user.can_access(collection) ?  [deps.py]
       │
       ├─► embed_query(question)                  [embedder.py]
       │    fastembed local, 384d, run_in_executor (non-bloquant)
       │
       ├─► retrieve(db, embedding, question, collection)  [retriever.py]
       │    ├─ _dense_search  : pgvector <=> opérateur cosinus, CAST(:vec AS vector)
       │    ├─ _sparse_search : to_tsvector('french') + plainto_tsquery
       │    └─ _reciprocal_rank_fusion : score = Σ 1/(rank + 60)
       │
       ├─► rerank(question, candidates)           [reranker.py]
       │    Cohere rerank-v3.5 si COHERE_API_KEY présent
       │    Fallback : ordre cosinus (top_n premiers)
       │
       ├─► generate_stream(question, sources)     [generator.py]
       │    OpenRouter (OpenAI-compatible), SSE token par token
       │    Contexte = sources formatées avec [1][2]...
       │
       └─► _log_query(...)                        [pipeline.py]
            INSERT INTO query_logs + REFRESH → retourne l'UUID
            Inclus dans le chunk "done" → client peut poster le feedback
```

### Paramètres clés (configurables via `.env`)

| Paramètre | Défaut | Effet |
|---|---|---|
| `RETRIEVAL_TOP_K` | 20 | Nombre de chunks récupérés par chaque recherche |
| `RERANK_TOP_N` | 5 | Nombre de chunks envoyés au LLM après reranking |
| `CHUNK_SIZE` | 512 | Taille max d'un chunk (caractères) |
| `CHUNK_OVERLAP` | 64 | Chevauchement entre chunks |
| `LLM_MODEL` | `anthropic/claude-haiku-4.5` | Modèle via OpenRouter |

### Astuce pour changer de modèle LLM

Modifier uniquement `LLM_MODEL` dans `.env`. OpenRouter accepte n'importe quel modèle de son catalogue : `openai/gpt-4o`, `mistralai/mistral-large-2407`, `google/gemini-pro`, etc.

### SSE (Server-Sent Events)

Le streaming fonctionne via `StreamingResponse` FastAPI. Le client reçoit une séquence de chunks JSON :

```
data: {"type":"token","content":"La politique"}
data: {"type":"token","content":" de télétravail"}
data: {"type":"sources","sources":[{"id":"...","title":"...","score":0.87,...}]}
data: {"type":"done","query_log_id":"uuid-abc-123"}
```

Le `query_log_id` dans `done` permet au client de poster le feedback 👍/👎 sur `/api/query/feedback`.

---

## 6. Auth JWT et RBAC

### Contrainte absolue

**Ne jamais bypasser `deps.py`.** Toutes les routes protégées utilisent l'une des trois dépendances FastAPI :

```python
user: CurrentUser = Depends(get_current_user)   # guest autorisé
user: CurrentUser = Depends(require_user)        # auth obligatoire
user: CurrentUser = Depends(require_admin)       # rôle admin requis
```

### Flux d'authentification

```
POST /api/auth/register  →  crée user (role=user, collections=["general"])
POST /api/auth/login     →  { access_token, refresh_token, token_type }
GET  /api/auth/me        →  { id, email, role, allowed_collections, ... }
POST /api/auth/refresh   →  { access_token, refresh_token }  (nouveau access token)
```

**Durée des tokens :**
- Access token : 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token : 7 jours (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)

### Structure du payload JWT

```json
{
  "sub": "uuid-user",
  "role": "user",
  "collections": ["general", "rh"],
  "exp": 1234567890,
  "type": "access"
}
```

Le champ `type` est validé : `"access"` pour les routes API, `"refresh"` uniquement pour `/api/auth/refresh`.

### Modèle de rôles

| Rôle | Collections accessibles | Ingestion | Notes |
|---|---|---|---|
| `guest` (sans token) | `["general"]` | Non | Retourné par `get_current_user` si pas de Bearer |
| `user` | `allowed_collections` de la DB | Non | Défini à la création, modifiable en DB |
| `admin` | Toutes | Oui | `can_access()` retourne toujours `True` |

### Modifier les collections d'un utilisateur

Il n'y a pas encore d'endpoint admin pour ça. Faire directement en DB :

```sql
UPDATE users
SET allowed_collections = '{general,rh,tech}'
WHERE email = 'user@example.com';
```

---

## 7. Ingestion de documents

### PDF (route principale)

```bash
# Via Makefile (sans token — à corriger si auth requise)
make ingest-pdf FILE=doc.pdf COLLECTION=rh

# Via API (token admin requis)
curl -X POST http://localhost:8000/api/ingest/pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@doc.pdf" \
  -F "collection=rh"
```

### Pipeline d'ingestion

```
Fichier PDF
    │
    ├─► PyMuPDF : extraction texte par page
    │
    ├─► chunk_text() : section-aware → RecursiveCharacterTextSplitter
    │    chunk_size=512, overlap=64
    │    chunks < 50 caractères filtrés
    │
    ├─► compute_checksum() : MD5 du contenu
    │
    ├─► Vérification déduplication en DB
    │    SELECT id FROM documents WHERE checksum = :checksum
    │    → chunk ignoré si déjà présent
    │
    ├─► embed_texts() : fastembed local, batch_size=64
    │    run_in_executor → non-bloquant pour FastAPI
    │
    └─► INSERT INTO documents (batch)
         + INSERT INTO ingestion_jobs (tracking)
```

### Collections disponibles

- `general` — documents accessibles à tous les utilisateurs
- `rh` — RH uniquement
- `tech` — équipe technique
- `finance` — finance

Les collections sont des strings libres côté DB. Les rôles et `allowed_collections` contrôlent l'accès.

### Ingestion Confluence

```bash
# Variables d'env requises : CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN
make ingest-confluence SPACE=ENG COLLECTION=tech
```

### Ingestion Slack

L'ingestion Slack utilise les exports JSON (fichiers zip téléchargés depuis Slack Admin). Fournir le chemin du dossier dézippé via l'API.

---

## 8. Schéma de base de données

### Table `documents`

```sql
id          UUID PK
source_type VARCHAR(50)   -- pdf | confluence | slack
source_id   VARCHAR(500)  -- chemin fichier ou URL d'origine
title       VARCHAR(1000)
content     TEXT          -- contenu du chunk
checksum    VARCHAR(64)   -- MD5(content) — clé de déduplication
embedding   vector(384)   -- fastembed paraphrase-multilingual-MiniLM-L12-v2
metadata    JSONB         -- section, chunk_index, url, etc.
collection  VARCHAR(200)  -- general | rh | tech | finance
created_at  TIMESTAMPTZ
updated_at  TIMESTAMPTZ   -- mis à jour par trigger
```

**Index :**
- `HNSW` sur `embedding` (vector_cosine_ops, m=16, ef_construction=64)
- `GIN` sur `to_tsvector('french', content)` (BM25)
- B-tree sur `collection`, `source_type`, `checksum`

### Table `query_logs`

```sql
id          UUID PK
user_id     VARCHAR(200)  -- NULL si guest
question    TEXT
answer      TEXT
sources     JSONB         -- liste de SourceDoc sérialisés
latency_ms  INTEGER
tokens_used INTEGER
collection  VARCHAR(200)
feedback    SMALLINT      -- 1 (👍) | -1 (👎) | NULL
created_at  TIMESTAMPTZ
```

**Invariant : cette table est en append-only.** Seul `feedback` est mis à jour via `UPDATE`.

### Table `users`

```sql
id                  UUID PK
email               VARCHAR(255) UNIQUE
hashed_password     VARCHAR(255)  -- bcrypt 3.2.2
full_name           VARCHAR(255)
role                VARCHAR(50)   -- user | admin
allowed_collections VARCHAR[]     -- tableau PostgreSQL
is_active           BOOLEAN
created_at          TIMESTAMPTZ
```

### Migrations

```bash
# Appliquer les migrations manuellement (dev local sans Docker)
psql postgresql://rag:rag@localhost:5432/ragdb -f backend/migrations/001_initial.sql
psql postgresql://rag:rag@localhost:5432/ragdb -f backend/migrations/002_users.sql
```

Les migrations sont idempotentes (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

**Ajouter une migration :** créer `backend/migrations/003_xxx.sql`, l'ajouter dans `.github/workflows/ci.yml` (section "Apply migrations").

---

## 9. Architecture frontend

```
frontend/src/
├── app/
│   ├── layout.tsx       # RootLayout, polices, globals.css
│   └── page.tsx         # Layout deux colonnes : DocumentPanel + Chat
├── components/
│   ├── Chat.tsx         # Zone principale, input, streaming SSE, feedback handler
│   ├── MessageBubble.tsx # Bulle message + boutons 👍/👎
│   ├── SourceCard.tsx    # Citation source avec score
│   ├── DocumentPanel.tsx # Sidebar : collection selector + UploadZone + jobs
│   ├── UploadZone.tsx    # Drag-and-drop PDF
│   ├── EmptyState.tsx    # Écran d'accueil avec questions suggérées
│   └── LoginModal.tsx    # Modal connexion + LoginButton (header)
├── store/
│   └── useStore.ts      # État Zustand global
└── lib/
    ├── api.ts           # Tous les appels API (auth headers automatiques)
    └── utils.ts         # Helpers (cn pour classnames, etc.)
```

### Zustand Store (`useStore.ts`)

État global partagé entre tous les composants. **Ne pas dupliquer d'état local** pour ce qui appartient au store.

```typescript
interface AppState {
  user: UserOut | null           // utilisateur connecté (null = guest)
  setUser: (u) => void

  collection: string             // collection active ("general" par défaut)
  setCollection: (c) => void

  messages: Message[]            // historique du chat
  addMessage / updateMessage / appendToken / clearMessages

  ingestionJobs: IngestionJob[]  // jobs upload en cours
  addIngestionJob / updateIngestionJob
}
```

**Le store ne persiste pas** (pas de `persist` middleware). Reset intentionnel au rechargement de page.

### Client API (`lib/api.ts`)

**Tous les appels réseau passent par `api.ts`**, jamais de `fetch` direct dans les composants.

```typescript
authHeaders()      // { Authorization: "Bearer <token>" } si connecté, {} sinon
login()            // POST /api/auth/login → stocke tokens localStorage → retourne UserOut
fetchMe()          // GET /api/auth/me → UserOut
logout()           // clearTokens localStorage
streamQuery()      // AsyncGenerator<StreamChunk> — SSE via ReadableStream
submitFeedback()   // POST /api/query/feedback
ingestPDF()        // POST /api/ingest/pdf (multipart)
```

### Streaming SSE côté client

```typescript
for await (const chunk of streamQuery(question, collection)) {
  if (chunk.type === "token") appendToken(msgId, chunk.content)
  if (chunk.type === "sources") updateMessage(msgId, { sources: chunk.sources })
  if (chunk.type === "done") updateMessage(msgId, { isStreaming: false, queryLogId: chunk.query_log_id })
  if (chunk.type === "error") // afficher l'erreur
}
```

### Règle d'or TypeScript

`'use client'` uniquement quand le composant utilise des hooks React (`useState`, `useEffect`, `useStore`, event handlers). Les composants purement statiques restent des Server Components.

---

## 10. Variables d'environnement

### Obligatoire

```bash
OPENROUTER_API_KEY=sk-or-v1-...   # Seule variable vraiment obligatoire
SECRET_KEY=<openssl rand -hex 32>  # Générer en prod avec : make gen-secret
```

### Recommandées en production

```bash
APP_ENV=production
LOG_LEVEL=WARNING
CORS_ORIGINS=https://rag.monentreprise.com
ACCESS_TOKEN_EXPIRE_MINUTES=15     # Ne pas augmenter sans raison
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Optionnelles

```bash
COHERE_API_KEY=           # Reranker — fallback cosinus si absent
LLM_MODEL=anthropic/claude-haiku-4.5   # Changer le modèle LLM
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSIONS=384  # DOIT correspondre au modèle ci-dessus

# Connecteurs
CONFLUENCE_URL=https://corp.atlassian.net
CONFLUENCE_USERNAME=email@corp.com
CONFLUENCE_API_TOKEN=
SLACK_BOT_TOKEN=xoxb-

# Tracing LLM (Phase 2)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
```

**Règle absolue : ne jamais committer `.env`.** Il est dans `.gitignore`. Utiliser `.env.example` pour documenter les variables.

---

## 11. Tests et qualité de code

### Tests actuels

```bash
cd backend && pytest tests/ -v         # suite complète
cd backend && pytest tests/ -v -k jwt  # filtre sur un test
make test-cov                           # avec couverture HTML
```

**Tests existants (`tests/test_config.py`) :**
- Valeurs par défaut des settings
- Validation Pydantic (QueryRequest, StreamChunk, FeedbackRequest, SourceDoc)
- Roundtrip JWT (access token, admin role, token invalide)

**Tests manquants (Phase 2) :**
- `tests/test_ingestion.py` — PDF golden, déduplication MD5
- `tests/test_rag.py` — golden dataset 20 questions (faithfulness, relevancy)
- `tests/test_api.py` — endpoints httpx (register, login, query, feedback, ingest)

### Linter Python

```bash
cd backend && ruff check app/          # vérifier (0 erreur = CI OK)
cd backend && ruff check app/ --fix    # corriger automatiquement
cd backend && ruff format app/         # formatter
```

Version fixée : `ruff==0.15.14` (dans CI et dans `pyproject.toml`).

### Linter TypeScript

```bash
cd frontend && npm run lint     # eslint
cd frontend && npx tsc --noEmit # typecheck sans compilation
cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"
```

### Pre-commit hooks

```bash
pre-commit run --all-files   # lancer manuellement
pre-commit install            # installer les hooks (fait par make setup)
```

Les hooks incluent : ruff, prettier, detect-secrets (pas de secret accidentel en commit).

---

## 12. CI/CD GitHub Actions

Fichier : `.github/workflows/ci.yml`

**Déclencheurs :** push sur `main` et `feat/**`, PR vers `main`.

### Jobs

**1. Lint** (ubuntu-latest)
- Setup Python 3.11 + cache pip
- `pip install ruff==0.15.14` + `ruff check app/`
- Setup Node 20 + `npm ci`
- `npm run lint`

**2. Tests** (ubuntu-latest, services : postgres pgvector/pg16 + redis 7)
- Variables d'env CI : `OPENROUTER_API_KEY=dummy-for-tests`, `SECRET_KEY=ci-test-secret-key`
- `psql ... -f 001_initial.sql && psql ... -f 002_users.sql`
- `pytest tests/ -v --tb=short`

**3. Build Docker** (main + PR uniquement)
- Build backend, frontend, postgres images
- Cache GitHub Actions (`type=gha`)
- Pas de push en registry (MVP)

### Ajouter une nouvelle migration en CI

Dans `.github/workflows/ci.yml`, section "Apply migrations" :

```yaml
- name: Apply migrations
  run: |
    psql postgresql://rag:rag@localhost:5432/ragdb \
      -f backend/migrations/001_initial.sql
    psql postgresql://rag:rag@localhost:5432/ragdb \
      -f backend/migrations/002_users.sql
    psql postgresql://rag:rag@localhost:5432/ragdb \
      -f backend/migrations/003_votre_migration.sql   # ← ajouter ici
```

---

## 13. Monitoring Prometheus + Grafana

### Démarrer le monitoring

```bash
make monitoring-up     # démarre prometheus + grafana (si stack Docker active)
# ou
docker compose up -d   # tout démarrer d'un coup
```

### Métriques RAG custom (`core/metrics.py`)

| Métrique | Type | Labels | Description |
|---|---|---|---|
| `rag_query_latency_seconds` | Histogram | `collection` | Latence E2E (buckets : 0.5s à 60s) |
| `rag_query_total` | Counter | `collection`, `user_role` | Volume de requêtes |
| `rag_tokens_used_total` | Counter | `collection` | Tokens LLM consommés |
| `rag_feedback_total` | Counter | `value` (positive/negative) | Feedback 👍/👎 |
| `rag_documents_ingested_total` | Counter | `collection`, `source_type` | Chunks ingérés |
| `rag_active_streams` | Gauge | — | Streams SSE ouverts simultanément |

```bash
make metrics     # voir les métriques brutes en temps réel
# ou
curl http://localhost:8000/metrics | grep "^rag_"
```

### Dashboard Grafana

- URL : http://localhost:3001 (admin / admin)
- Dashboard chargé automatiquement : **RAG Overview** (uid: `rag-overview`)
- 10 panneaux : requêtes/min, streams actifs, taux feedback+, latence P50/P95/P99, tokens, documents ingérés, requêtes par rôle, latence HTTP

**Modifier le dashboard :** dans Grafana UI → Export JSON → écraser `monitoring/grafana/dashboards/rag_overview.json` → committer.

### Alerting (Phase 2)

Alertes à configurer dans Grafana :
- Latence P95 > 30s
- Error rate > 1%
- Zéro requêtes depuis 10min (service mort ?)

---

## 14. Opérations courantes

### Créer un compte admin

```bash
make create-admin-script EMAIL=admin@corp.com PASSWORD=monpassword
# Par défaut : collections = [general, rh, tech, finance]
# Collections personnalisées :
make create-admin-script EMAIL=... PASSWORD=... COLLECTIONS=general,rh
```

### Promouvoir un user existant en admin

```sql
UPDATE users SET role = 'admin', allowed_collections = '{general,rh,tech,finance}'
WHERE email = 'user@corp.com';
```

### Interroger la DB directement

```bash
docker compose exec postgres psql -U rag -d ragdb

# Requêtes utiles :
SELECT id, email, role, allowed_collections FROM users;
SELECT collection, COUNT(*) FROM documents GROUP BY collection;
SELECT question, latency_ms, feedback FROM query_logs ORDER BY created_at DESC LIMIT 10;
```

### Voir les logs en temps réel

```bash
make logs              # tous les services
make logs-backend      # backend uniquement
docker compose logs -f worker   # worker Celery
```

### Vider et recréer la DB

```bash
make reset-db CONFIRM=yes   # DESTRUCTIF — supprime toutes les données
```

### Libérer de l'espace Docker

```bash
docker system prune -f          # supprime images/conteneurs non utilisés
docker system prune -f --volumes  # + volumes (DESTRUCTIF pour les données)
```

---

## 15. Pièges connus et décisions techniques

### bcrypt doit rester en 3.2.2

`bcrypt==4.x` est incompatible avec `passlib`. Symptôme : `ValueError: password cannot be longer than 72 bytes` au démarrage.

```
# requirements.txt
bcrypt==3.2.2   # NE PAS MONTER
```

### UserOut.id est un UUID en DB, string en API

Le modèle ORM retourne un `uuid.UUID`. Pydantic v2 ne le coerce pas automatiquement en `str`. Le `field_validator(mode="before")` dans `schemas.py` gère ça :

```python
@field_validator("id", mode="before")
@classmethod
def coerce_uuid(cls, v: object) -> str:
    return str(v)
```

Ne pas supprimer ce validator.

### pgvector : CAST(:vec AS vector) obligatoire

asyncpg ne gère pas le cast automatique `:vec::vector`. La syntaxe qui fonctionne :

```sql
ORDER BY embedding <=> CAST(:vec AS vector)
```

### Embeddings : fastembed télécharge le modèle au premier lancement

Le modèle (~90MB) est téléchargé dans `~/.cache/huggingface/` (ou équivalent) au premier démarrage. En Docker, il est téléchargé dans le conteneur à chaque `docker compose build --no-cache`. Prévoir 1-2min au premier lancement.

### La config est un singleton

`get_settings()` utilise `@lru_cache`. Modifier une variable d'env après le premier appel n'a aucun effet. En test, utiliser `get_settings.cache_clear()` si nécessaire.

### Ingest = admin uniquement

Les routes `/api/ingest/*` utilisent `require_admin`. Un user normal ne peut pas uploader. Le frontend (UploadZone) appelle `ingestPDF()` qui passe le Bearer token — si l'utilisateur n'est pas admin, il reçoit un 403.

### Le frontend n'a pas de variable d'env serveur

`NEXT_PUBLIC_API_URL` est la seule variable d'env frontend. Elle est exposée côté client (préfixe `NEXT_PUBLIC_`). Ne jamais mettre de secret dans une variable `NEXT_PUBLIC_*`.

### Celery et asyncio ne se mélangent pas

Les tasks Celery (`workers/tasks.py`) sont synchrones. Pour appeler du code async depuis Celery, utiliser `asyncio.run()`. Ne pas mélanger `async def` dans les tasks Celery.

---

## 16. Feuille de route Phase 2

Items prioritaires (voir `TODO.md` pour la liste complète) :

**Qualité retrieval :**
- **HyDE** (Hypothetical Document Embeddings) : générer un document hypothétique à partir de la question pour améliorer l'embedding de query
- **RAGAS** : évaluation automatique faithfulness + answer_relevancy sur un golden dataset
- **Cache sémantique Redis** : questions similaires → réponse directe sans appel LLM

**Sécurité :**
- **Microsoft Presidio** : détection PII avant embedding (RGPD)
- **LLM Guard** : guardrails anti-injection prompt
- **slowapi** : rate limiting par utilisateur

**Observabilité :**
- **LangSmith** : tracing des appels LLM (latence par étape, tokens, traces)
- **Alerting Grafana** : P95 > 30s ou error rate > 1%

**Connecteurs :**
- Google Drive, SharePoint, Jira

**Phase 3 (scale) :**
- Slack Bot natif (`/ask`)
- Agent multi-step (LangGraph)
- Fine-tuning reranker sur feedback 👍/👎
- Multi-tenant isolation par organisation
- Migration Qdrant si > 10M vecteurs

---

*Dernière mise à jour : 2026-05-22*
