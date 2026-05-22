# RAG Enterprise Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-6B4FBB?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> Système RAG (Retrieval-Augmented Generation) d'entreprise — posez des questions en langage naturel sur vos documents internes (PDF, Confluence, Slack) et obtenez des réponses sourcées en temps réel.

![Demo Screenshot](https://placehold.co/1200x600/1a1a2e/4a9eff?text=RAG+Enterprise+Platform)

---

## Fonctionnalités

- **Chat en streaming** — réponses streamées token par token via SSE
- **Upload drag-and-drop** — sidebar dédiée, glisser-déposer un PDF et le voir apparaître en base
- **Citations de sources** — chaque réponse cite les documents utilisés avec score de pertinence
- **Feedback 👍/👎** — évaluer chaque réponse, résultat tracé en base pour améliorer le modèle
- **Hybrid Search** — dense (embeddings) + sparse (BM25) fusionnés par Reciprocal Rank Fusion
- **Reranker** — Cohere Rerank v3.5 pour maximiser la précision (fallback cosinus si absent)
- **Multi-sources** — PDF, Confluence, Slack export (Google Drive, SharePoint à venir)
- **Déduplication** — checksum MD5 sur les chunks pour éviter les doublons lors de la réingestion
- **Audit log** — toutes les requêtes tracées en base (user, question, sources, latence, tokens)
- **Collections** — isolation par département (RH, Tech, Finance, Général)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INTERFACE WEB                         │
│   Next.js 15  ·  Tailwind  ·  Zustand  ·  SSE streaming │
│   Sidebar upload  ·  EmptyState  ·  Feedback 👍/👎       │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   FASTAPI BACKEND                        │
│                                                          │
│  /api/query ──► Hybrid Retrieval (dense + BM25)          │
│                 ──► RRF Fusion ──► Cohere Rerank         │
│                     ──► LLM streaming (OpenRouter)       │
│                                                          │
│  /api/ingest/pdf        /api/ingest/confluence           │
│  /api/query/feedback    /api/health                      │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
┌──────────▼──────────┐  ┌────────────▼────────────────┐
│  pgvector           │  │  Redis                       │
│  (PostgreSQL 16)    │  │  Cache + Celery broker        │
│  HNSW index         │  └─────────────────────────────┘
│  384-dim vectors    │
│  BM25 FTS index     │
└─────────────────────┘
```

---

## Stack Technique

| Couche | Technologie |
|--------|-------------|
| **API** | FastAPI 0.115 + uvicorn (async) |
| **LLM** | OpenRouter (`anthropic/claude-haiku-4.5` par défaut — configurable) |
| **Embeddings** | fastembed local — `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384d, FR/EN) |
| **Reranker** | Cohere Rerank v3.5 (optionnel — fallback cosinus) |
| **Vector DB** | pgvector + PostgreSQL 16 — index HNSW |
| **Hybrid Search** | Dense cosinus + BM25 FTS → Reciprocal Rank Fusion |
| **Cache / Queue** | Redis 7 + Celery |
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Zustand |
| **Conteneurs** | Docker + Docker Compose |
| **Qualité** | Ruff, Mypy, Prettier, pre-commit, detect-secrets |

---

## Démarrage rapide

### Prérequis

- Docker & Docker Compose
- Python 3.11+ *(pour développement local sans Docker)*
- Node.js 20+ *(pour développement local sans Docker)*
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

L'interface est disponible sur **http://localhost:3000** et l'API sur **http://localhost:8000/docs**.

### Développement local (sans Docker)

```bash
# Installer les dépendances
make setup

# Lancer backend + frontend en parallèle
make dev
```

---

## Utilisation

### Importer des documents

**Via l'interface** — glisser-déposer un PDF dans la sidebar gauche, choisir la collection.

**Via la CLI :**

```bash
# PDF
make ingest-pdf FILE=docs/politique-rh.pdf COLLECTION=rh

# Confluence
make ingest-confluence SPACE=ENG COLLECTION=tech

# Via API directement
curl -X POST http://localhost:8000/api/ingest/pdf \
  -F "file=@mon_doc.pdf" \
  -F "collection=general"
```

### Interroger la base

```bash
# Test rapide CLI
make query Q="Quelle est la politique de télétravail ?"

# Streaming SSE
make query-stream Q="Résume le processus d'onboarding"
```

---

## Configuration

Les variables d'environnement clés dans `.env` :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OPENROUTER_API_KEY` | Clé API OpenRouter **(obligatoire)** | — |
| `LLM_MODEL` | Modèle LLM via OpenRouter | `anthropic/claude-haiku-4.5` |
| `EMBEDDING_MODEL` | Modèle fastembed local (384d) | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `EMBEDDING_DIMENSIONS` | Dimensions des vecteurs | `384` |
| `COHERE_API_KEY` | Reranker Cohere (optionnel) | — |
| `SECRET_KEY` | Clé JWT — générer avec `make gen-secret` | `changeme` |
| `CORS_ORIGINS` | Origines autorisées | `http://localhost:3000` |

> Voir [`.env.example`](.env.example) pour la liste complète avec commentaires.

---

## Commandes Makefile

```bash
make setup          # Installation complète + DB
make dev            # Backend :8000 + Frontend :3000 (dev local)
make up             # Docker Compose up -d
make down           # Docker Compose down
make build          # Rebuild les images Docker
make logs           # Logs de tous les services
make test           # Tests pytest
make lint           # Ruff + ESLint
make format         # Ruff format + Prettier
make health         # Vérifier l'état de l'API
make ingest-pdf     # Ingérer un PDF (FILE=... COLLECTION=...)
make query          # Tester une requête (Q=...)
make gen-secret     # Générer un SECRET_KEY sécurisé
make reset-db       # Recréer la DB (CONFIRM=yes)
make clean          # Nettoyer les fichiers temporaires
```

---

## Pipeline RAG

```
Question utilisateur
    │
    ├─► Embedding de la query (fastembed local, 384d)
    │
    ├─► Dense search    ─┐
    │   (cosinus pgvec)  ├─► RRF Fusion ─► Top K chunks
    ├─► Sparse search   ─┘
    │   (BM25 PostgreSQL FTS)
    │
    ├─► Cohere Rerank ─► Top 5 chunks (fallback cosinus)
    │
    └─► Génération LLM (OpenRouter streaming SSE)
             │
             └─► Réponse avec citations [1][2]
                 + query_log_id → Feedback 👍/👎
                 + Audit log (user, latence, tokens)
```

---

## Structure du projet

```
rag-enterprise/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # query.py, ingest.py, health.py
│   │   ├── core/           # config.py, database.py, security.py
│   │   ├── ingestion/      # pdf_loader, confluence, slack, chunker, embedder
│   │   ├── models/         # db.py (ORM SQLAlchemy), schemas.py (Pydantic v2)
│   │   ├── rag/            # pipeline.py, retriever.py, reranker.py, generator.py
│   │   └── workers/        # Celery tasks (ingestion async)
│   ├── migrations/         # 001_initial.sql (pgvector + tables)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/            # Next.js App Router (layout + page)
│       ├── components/     # Chat, MessageBubble, SourceCard,
│       │                   # DocumentPanel, UploadZone, EmptyState
│       ├── store/          # useStore.ts (Zustand — collection, messages, jobs)
│       └── lib/            # api.ts (SSE client, ingest, feedback)
├── docker-compose.yml      # postgres, redis, backend, worker, frontend
├── postgres.Dockerfile     # pgvector:pg16 + migration SQL
├── Makefile                # ~30 cibles de développement
├── .env.example            # Variables d'environnement documentées
├── .pre-commit-config.yaml # ruff, mypy, detect-secrets, prettier, sqlfluff
└── pyproject.toml          # Config ruff + mypy + pytest
```

---

## Feuille de route

- [x] Pipeline RAG MVP (PDF + hybrid search + streaming SSE)
- [x] Ingestion Confluence & Slack
- [x] Déduplication par checksum MD5
- [x] Audit log complet (query_logs)
- [x] Interface chat Next.js avec citations de sources
- [x] Upload drag-and-drop + sidebar de gestion des documents
- [x] Feedback 👍/👎 tracé en base
- [x] Store Zustand — état partagé multi-composants
- [ ] Auth JWT + RBAC par collection
- [ ] CI/CD GitHub Actions (lint + tests + build)
- [ ] RAGAS evaluation automatique (faithfulness, relevancy)
- [ ] HyDE query rewriting
- [ ] Cache sémantique Redis (questions similaires)
- [ ] PII detection (Microsoft Presidio)
- [ ] Dashboards Grafana (latence, coûts, qualité)
- [ ] Connecteurs Google Drive & SharePoint
- [ ] Slack Bot (`/ask` command)
- [ ] Agent multi-step pour questions complexes

---

## Licence

MIT — voir [LICENSE](LICENSE)
