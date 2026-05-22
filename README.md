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
- **Citations de sources** — chaque réponse cite les documents utilisés avec lien et score de pertinence
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
│         Next.js 15  ·  Tailwind  ·  SSE streaming       │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   FASTAPI BACKEND                        │
│                                                          │
│  /api/query ──► Query Rewriting                          │
│                 ──► Hybrid Retrieval (dense + BM25)      │
│                     ──► RRF Fusion                       │
│                         ──► Cohere Rerank                │
│                             ──► Claude/GPT streaming     │
│                                                          │
│  /api/ingest/pdf        /api/ingest/confluence           │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
┌──────────▼──────────┐  ┌────────────▼────────────────┐
│  pgvector           │  │  Redis                       │
│  (PostgreSQL 16)    │  │  Cache + Celery broker        │
│  HNSW index         │  └─────────────────────────────┘
│  1024-dim vectors   │
│  BM25 FTS index     │
└─────────────────────┘
```

---

## Stack Technique

| Couche | Technologie |
|--------|-------------|
| **API** | FastAPI 0.115 + uvicorn (async) |
| **LLM** | OpenRouter (Claude 3.5 Sonnet, GPT-4o, Mistral…) |
| **Embeddings** | fastembed local — `BAAI/bge-m3` (1024d, multilingue) |
| **Reranker** | Cohere Rerank v3.5 (optionnel) |
| **Vector DB** | pgvector + PostgreSQL 16 — index HNSW |
| **Hybrid Search** | Dense cosinus + BM25 FTS → Reciprocal Rank Fusion |
| **Cache / Queue** | Redis 7 + Celery |
| **Frontend** | Next.js 15, React 19, Tailwind CSS, shadcn/ui |
| **Conteneurs** | Docker + Docker Compose |
| **Qualité** | Ruff, Mypy, Prettier, pre-commit, detect-secrets |

---

## Démarrage rapide

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Une clé [OpenRouter](https://openrouter.ai)

### Installation

```bash
# 1. Cloner
git clone https://github.com/SeydinaBANE/rag-enterprise.git
cd rag-enterprise

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env : renseigner OPENROUTER_API_KEY

# 3. Setup complet (install deps + DB)
make setup

# 4. Lancer
make dev
```

L'interface est disponible sur **http://localhost:3000** et l'API sur **http://localhost:8000/docs**.

---

## Utilisation

### Ingérer des documents

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
| `OPENROUTER_API_KEY` | Clé API OpenRouter | — |
| `LLM_MODEL` | Modèle LLM via OpenRouter | `anthropic/claude-3.5-sonnet` |
| `EMBEDDING_MODEL` | Modèle fastembed local | `BAAI/bge-m3` |
| `COHERE_API_KEY` | Reranker Cohere (optionnel) | — |
| `SECRET_KEY` | Clé JWT — générer avec `make gen-secret` | `changeme` |

> Voir [`.env.example`](.env.example) pour la liste complète.

---

## Commandes Makefile

```bash
make setup          # Installation complète + DB
make dev            # Backend :8000 + Frontend :3000
make test           # Tests pytest
make lint           # Ruff + ESLint
make format         # Ruff format + Prettier
make health         # Vérifier l'état de l'API
make ingest-pdf     # Ingérer un PDF (FILE=...)
make query          # Tester une requête (Q=...)
make gen-secret     # Générer un SECRET_KEY
make clean          # Nettoyer les fichiers temporaires
make reset-db       # Recréer la DB (CONFIRM=yes)
```

---

## Pipeline RAG

```
Question utilisateur
    │
    ├─► Embedding de la query (fastembed local)
    │
    ├─► Dense search    ─┐
    │   (cosinus pgvec)  ├─► RRF Fusion ─► Top 30
    ├─► Sparse search   ─┘
    │   (BM25 PostgreSQL FTS)
    │
    ├─► Cohere Rerank ─► Top 5 chunks
    │
    ├─► Context assembly + RBAC filter
    │
    └─► Génération LLM (OpenRouter streaming SSE)
             │
             └─► Réponse avec citations [1][2]
                 + Audit log (user, latence, tokens)
```

---

## Structure du projet

```
rag-enterprise/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # query.py, ingest.py, health.py
│   │   ├── core/           # config, database, security
│   │   ├── ingestion/      # pdf, confluence, slack, chunker, embedder
│   │   ├── models/         # db.py (ORM), schemas.py (Pydantic)
│   │   ├── rag/            # pipeline, retriever, reranker, generator
│   │   └── workers/        # Celery tasks
│   ├── migrations/         # SQL pgvector setup
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/            # Next.js App Router
│       ├── components/     # Chat, MessageBubble, SourceCard
│       └── lib/            # api.ts (SSE client)
├── docker-compose.yml
├── Makefile
├── .pre-commit-config.yaml
└── pyproject.toml          # Ruff + Mypy config
```

---

## Feuille de route

- [x] Pipeline RAG MVP (PDF + hybrid search + streaming)
- [x] Ingestion Confluence & Slack
- [x] Interface chat Next.js avec citations
- [x] Déduplication par checksum
- [x] Audit log complet
- [ ] Auth JWT + RBAC par collection
- [ ] RAGAS evaluation automatique
- [ ] HyDE query rewriting
- [ ] PII detection (Microsoft Presidio)
- [ ] Dashboards Grafana (latence, coûts, qualité)
- [ ] Connecteurs Google Drive & SharePoint
- [ ] Slack Bot (`/ask` command)
- [ ] Agent multi-step pour questions complexes

---

## Licence

MIT — voir [LICENSE](LICENSE)
