# RAG Enterprise Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-6B4FBB?style=flat-square)
![CI](https://github.com/SeydinaBANE/rag-enterprise/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> Système RAG (Retrieval-Augmented Generation) d'entreprise — posez des questions en langage naturel sur vos documents internes (PDF, Confluence, Slack) et obtenez des réponses sourcées en temps réel.

---

## Fonctionnalités

- **Chat en streaming** — réponses streamées token par token via SSE
- **Upload drag-and-drop** — sidebar dédiée, glisser-déposer un PDF et le voir apparaître en base
- **Citations de sources** — chaque réponse cite les documents utilisés avec score de pertinence
- **Feedback 👍/👎** — évaluer chaque réponse, résultat tracé en base
- **Hybrid Search** — dense (embeddings) + sparse (BM25) fusionnés par Reciprocal Rank Fusion
- **Reranker** — Cohere Rerank v3.5 pour maximiser la précision (fallback cosinus si absent)
- **HyDE** — Hypothetical Document Embeddings, améliore le recall sans infra supplémentaire (`HYDE_ENABLED=true`)
- **Cache Redis** — réponses non-stream mises en cache par question normalisée (TTL configurable)
- **Rate limiting** — par utilisateur authentifié ou IP, configurable (`RATE_LIMIT_QUERY_PER_MINUTE`)
- **Auth JWT + RBAC** — inscription/connexion, accès restreint par collection et par rôle
- **Observabilité** — métriques Prometheus + dashboard Grafana pré-configuré
- **Multi-sources** — PDF, Confluence, Slack export
- **Déduplication** — checksum MD5 sur les chunks pour éviter les doublons
- **Audit log** — toutes les requêtes tracées en base (user, question, sources, latence, tokens)
- **Collections** — isolation par département (RH, Tech, Finance, Général)
- **Tests** — 32 tests pytest (API httpx + config/schémas/JWT)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      INTERFACE WEB                            │
│   Next.js 15 · Tailwind · Zustand · SSE streaming            │
│   Sidebar upload · EmptyState · Feedback 👍/👎 · LoginModal   │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    FASTAPI BACKEND                             │
│                                                               │
│  /api/auth/*   ──► JWT register / login / refresh / me        │
│  /api/query    ──► Rate limit ──► Cache Redis (non-stream)    │
│                     ──► RBAC ──► HyDE embed (optionnel)       │
│                         ──► Dense+BM25 ──► RRF ──► Rerank     │
│                             ──► LLM streaming (OpenRouter)    │
│  /api/ingest/* ──► require_admin                              │
│  /metrics      ──► Prometheus scrape                          │
└──────────┬────────────────────────────────┬──────────────────┘
           │                                │
┌──────────▼──────────┐     ┌───────────────▼────────────────┐
│  pgvector           │     │  Redis                          │
│  (PostgreSQL 16)    │     │  Cache + Celery broker           │
│  HNSW index 384d    │     └────────────────────────────────┘
│  BM25 FTS index     │
└─────────────────────┘
           │
┌──────────▼──────────┐     ┌────────────────────────────────┐
│  Prometheus         │────►│  Grafana :3001                  │
│  :9090              │     │  Dashboard RAG (10 panneaux)    │
└─────────────────────┘     └────────────────────────────────┘
```

---

## Stack Technique

| Couche | Technologie |
|--------|-------------|
| **API** | FastAPI 0.115 + uvicorn (async) |
| **Auth** | JWT (python-jose) + passlib/bcrypt — access 15min + refresh 7j |
| **LLM** | OpenRouter (`anthropic/claude-haiku-4.5` par défaut — configurable) |
| **Embeddings** | fastembed local — `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384d, FR/EN) |
| **Reranker** | Cohere Rerank v3.5 (optionnel — fallback cosinus) |
| **Vector DB** | pgvector + PostgreSQL 16 — index HNSW |
| **Hybrid Search** | Dense cosinus + BM25 FTS → Reciprocal Rank Fusion |
| **Cache** | Redis 7 — query cache exact-match + rate limiting |
| **Queue** | Redis 7 + Celery (ingestion async) |
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Zustand |
| **Monitoring** | Prometheus + Grafana 11 (dashboard pré-provisionné) |
| **Conteneurs** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions — lint (ruff + eslint), tests, build Docker |
| **Qualité** | Ruff 0.15, Mypy, Prettier, pre-commit, detect-secrets |

---

## Démarrage rapide

### Prérequis

- Docker & Docker Compose
- Une clé [OpenRouter](https://openrouter.ai) *(gratuit, modèles au choix)*

### Installation

```bash
# 1. Cloner
git clone https://github.com/SeydinaBANE/rag-enterprise.git
cd rag-enterprise

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env : renseigner OPENROUTER_API_KEY (seul champ obligatoire)

# 3. Lancer le stack complet
docker compose up -d
```

| Service | URL |
|---------|-----|
| Interface web | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (admin / admin) |
| Prometheus | http://localhost:9090 |

### Créer un compte admin

```bash
make create-admin-script EMAIL=admin@example.com PASSWORD=secret
```

### Développement local (sans Docker)

```bash
make setup   # Install + .env + pre-commit + DB
make dev     # Backend :8000 + Frontend :3000 en parallèle
```

---

## Utilisation

### Auth

```bash
# Inscription
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'

# Connexion → récupérer l'access_token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'
```

### Importer des documents *(admin requis)*

```bash
make ingest-pdf FILE=docs/politique-rh.pdf COLLECTION=rh

# Via API avec token admin
curl -X POST http://localhost:8000/api/ingest/pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mon_doc.pdf" \
  -F "collection=rh"
```

### Interroger la base

```bash
make query Q="Quelle est la politique de télétravail ?"
make query-stream Q="Résume le processus d'onboarding"

# Accès guest sans token (collection general uniquement)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"test","collection":"general","stream":false}'
```

---

## Monitoring

Le dashboard Grafana se charge automatiquement au démarrage.

```bash
make monitoring-up    # Démarrer Prometheus + Grafana
make metrics          # Voir les métriques RAG brutes
```

**Métriques disponibles :**
- `rag_query_latency_seconds` — latence P50/P95/P99 par collection
- `rag_query_total` — volume de requêtes par collection et rôle
- `rag_tokens_used_total` — tokens LLM consommés
- `rag_feedback_total` — feedback 👍/👎 reçu
- `rag_documents_ingested_total` — chunks ingérés par collection
- `rag_active_streams` — streams SSE actifs en temps réel

---

## RBAC

| Rôle | Collections accessibles | Peut ingérer |
|------|------------------------|--------------|
| `guest` (sans token) | `general` | Non |
| `user` | Selon `allowed_collections` | Non |
| `admin` | Toutes | Oui |

---

## Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OPENROUTER_API_KEY` | Clé API OpenRouter **(obligatoire)** | — |
| `SECRET_KEY` | Clé JWT — générer avec `make gen-secret` | `changeme` |
| `LLM_MODEL` | Modèle LLM via OpenRouter | `anthropic/claude-haiku-4.5` |
| `COHERE_API_KEY` | Reranker Cohere (optionnel) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée access token | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée refresh token | `7` |
| `HYDE_ENABLED` | HyDE query rewriting (+1 LLM call/query) | `false` |
| `CACHE_TTL_SECONDS` | TTL du cache Redis par question | `3600` |
| `RATE_LIMIT_QUERY_PER_MINUTE` | Limite requêtes /query par user/IP | `20` |

> Voir [`.env.example`](.env.example) pour la liste complète.

---

## Commandes Makefile

```bash
make setup                    # Installation complète + DB
make dev                      # Backend :8000 + Frontend :3000 (dev local)
make up / down / build        # Docker Compose
make test / lint / format     # Qualité
make health / metrics         # État de l'API + métriques Prometheus
make monitoring-up            # Démarrer Prometheus + Grafana
make create-admin-script      # EMAIL=... PASSWORD=... → compte admin
make ingest-pdf               # FILE=... COLLECTION=...
make query / query-stream     # Q="votre question"
make gen-secret               # Générer un SECRET_KEY sécurisé
make reset-db CONFIRM=yes     # Recréer la DB (DESTRUCTIF)
```

---

## Pipeline RAG

```
Question utilisateur
    │
    ├─► Rate limiting (Redis INCR/EXPIRE — par user ou IP)
    │
    ├─► Cache Redis (exact-match normalisé) → HIT : réponse directe
    │
    ├─► RBAC → can_access(collection) ?
    │
    ├─► Embedding (HyDE si activé → doc hypothétique, sinon question brute)
    │    fastembed local, 384d
    │
    ├─► Dense search  ─┐
    │   (cosinus pgvec) ├─► RRF Fusion ─► Top K chunks
    ├─► Sparse search  ─┘
    │   (BM25 PostgreSQL FTS)
    │
    ├─► Cohere Rerank ─► Top 5 (fallback cosinus)
    │
    └─► Génération LLM streaming (OpenRouter SSE)
             │
             └─► Réponse [1][2] + query_log_id → Feedback 👍/👎
                 + Audit log + métriques Prometheus
                 + Cache Redis SET (non-stream uniquement)
```

---

## Structure du projet

```
rag-enterprise/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # CurrentUser, RBAC (get/require_user/require_admin)
│   │   │   └── routes/          # auth.py, query.py, ingest.py, health.py
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic-settings
│   │   │   ├── metrics.py       # Compteurs Prometheus custom
│   │   │   ├── rate_limit.py    # Rate limiting Redis par user/IP
│   │   │   ├── redis.py         # Client Redis singleton
│   │   │   └── security.py      # JWT, bcrypt
│   │   ├── ingestion/           # pdf_loader, confluence, slack, chunker, embedder
│   │   ├── models/              # db.py (ORM), schemas.py (Pydantic v2)
│   │   ├── rag/                 # pipeline.py, retriever.py, reranker.py,
│   │   │                        # generator.py, cache.py, hyde.py
│   │   └── workers/             # Celery tasks
│   ├── migrations/              # 001_initial.sql, 002_users.sql
│   ├── tests/                   # pytest — test_config.py, test_api.py (32 tests)
│   └── requirements.txt
├── tests/
│   ├── golden_dataset.json      # 20 questions RAGAS (à compléter après ingestion)
│   └── evaluate_ragas.py        # Script d'évaluation RAGAS standalone
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router
│       ├── components/          # Chat, DocumentPanel, UploadZone,
│       │                        # MessageBubble, EmptyState, LoginModal
│       ├── store/               # useStore.ts (Zustand)
│       └── lib/                 # api.ts (auth + SSE + feedback)
├── monitoring/
│   ├── prometheus.yml           # Scrape config
│   └── grafana/
│       ├── provisioning/        # Datasource + dashboard auto-load
│       └── dashboards/          # rag_overview.json (10 panneaux)
├── .github/workflows/ci.yml    # Lint + tests + build Docker
├── docker-compose.yml           # postgres, redis, backend, worker, frontend,
│                                # prometheus, grafana
├── Makefile                     # ~35 cibles
└── .env.example
```

---

## Feuille de route

- [x] Pipeline RAG MVP (PDF + hybrid search + streaming SSE)
- [x] Ingestion Confluence & Slack
- [x] Déduplication par checksum MD5
- [x] Audit log complet (`query_logs`)
- [x] Interface chat Next.js avec citations de sources
- [x] Upload drag-and-drop + sidebar de gestion des documents
- [x] Feedback 👍/👎 tracé en base
- [x] Store Zustand — état partagé multi-composants
- [x] CI/CD GitHub Actions (lint ruff + eslint + tests + build Docker)
- [x] Auth JWT + RBAC par collection
- [x] Métriques Prometheus + Dashboard Grafana pré-configuré
- [x] Rate limiting par utilisateur (Redis INCR/EXPIRE)
- [x] Cache Redis exact-match sur les queries non-stream
- [x] HyDE query rewriting (activable via `HYDE_ENABLED=true`)
- [x] Tests API complets — 32 tests pytest (httpx + ASGITransport)
- [x] Golden dataset RAGAS + script d'évaluation (`tests/evaluate_ragas.py`)
- [ ] RAGAS évaluation sur données réelles (documents ingérés requis)
- [ ] PII detection (Microsoft Presidio)
- [ ] Connecteurs Google Drive & SharePoint
- [ ] Slack Bot (`/ask` command)
- [ ] Agent multi-step pour questions complexes

---

## Licence

MIT — voir [LICENSE](LICENSE)
