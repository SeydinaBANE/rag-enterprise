# TODO — Plateforme RAG d'Entreprise

## Phase 1 — MVP ✅ Complète

### Infrastructure
- [x] Structure du projet (monorepo)
- [x] docker-compose.yml (PostgreSQL+pgvector, Redis, backend, worker, frontend)
- [x] Migration SQL initiale (tables + extension pgvector)
- [x] CI/CD GitHub Actions (lint ruff + eslint + tests pytest + build Docker)
- [x] Prometheus + Grafana (monitoring/)

### Backend — Foundation
- [x] FastAPI app entry point (`main.py`)
- [x] Config Pydantic-settings (`core/config.py`)
- [x] Database async SQLAlchemy + pgvector (`core/database.py`)
- [x] Modèles ORM (`models/db.py`) — Document, QueryLog, User, IngestionJob
- [x] Schémas Pydantic v2 (`models/schemas.py`)
- [x] Health endpoint (`api/routes/health.py`)
- [x] Auth JWT + RBAC (`core/security.py`, `api/deps.py`, `api/routes/auth.py`)
- [x] Migration users (`migrations/002_users.sql`)
- [x] Métriques Prometheus (`core/metrics.py`)

### Backend — Ingestion Pipeline
- [x] Base loader class (`ingestion/base.py`)
- [x] Chunker hybride (`ingestion/chunker.py`)
- [x] Embedder fastembed local + déduplication (`ingestion/embedder.py`)
- [x] PDF loader (`ingestion/pdf_loader.py`)
- [x] Confluence loader (`ingestion/confluence.py`)
- [x] Slack loader (`ingestion/slack.py`)
- [x] Ingest endpoint admin-only (`api/routes/ingest.py`)
- [x] Celery tasks ingestion async (`workers/tasks.py`)

### Backend — RAG Pipeline
- [x] Retriever hybrid search dense+BM25 RRF (`rag/retriever.py`)
- [x] Reranker Cohere avec fallback cosinus (`rag/reranker.py`)
- [x] Generator streaming OpenRouter (`rag/generator.py`)
- [x] Pipeline complet avec query_log_id (`rag/pipeline.py`)
- [x] Query endpoint RBAC + SSE + métriques (`api/routes/query.py`)
- [x] Feedback 👍/👎 endpoint

### Frontend
- [x] Layout deux colonnes (sidebar + chat)
- [x] Composant Chat avec streaming SSE + store Zustand
- [x] MessageBubble + boutons feedback 👍/👎
- [x] SourceCard (citations avec score)
- [x] DocumentPanel (collection selector + UploadZone + liste jobs)
- [x] UploadZone drag-and-drop PDF
- [x] EmptyState avec questions suggérées
- [x] LoginModal + LoginButton (JWT localStorage)
- [x] API client auth-aware (`lib/api.ts`) — authHeaders sur toutes les requêtes

### Tests
- [x] Tests config, schémas Pydantic, JWT roundtrip (`tests/test_config.py`)
- [x] Tests API endpoints httpx — 22 tests (auth, query, RBAC, feedback, ingest) (`tests/test_api.py`)
- [ ] Tests ingestion PDF (golden PDF)
- [ ] Tests RAG pipeline (golden dataset 20 questions)

---

## Phase 2 — Qualité & Production ✅ Complète

### Retrieval
- [x] HyDE (Hypothetical Document Embeddings) — `rag/hyde.py`, activable via `HYDE_ENABLED=true`
- [x] Golden dataset : `tests/golden_dataset.json` (20 questions, à compléter après ingestion)
- [x] Script RAGAS : `tests/evaluate_ragas.py` + `requirements-eval.txt`
- [ ] RAGAS évaluation sur données réelles (nécessite documents ingérés)

### Sécurité
- [x] Rate limiting par utilisateur — `core/rate_limit.py` (Redis INCR/EXPIRE, configurable via `RATE_LIMIT_QUERY_PER_MINUTE`)
- [x] PII detection Microsoft Presidio avant embedding — `ingestion/pii_detector.py` (`PII_DETECTION_ENABLED`, `PII_ACTION`, `PII_LANGUAGE`)
- [ ] Guardrails anti-injection prompt (LLM Guard)

### Observabilité
- [x] Cache Redis exact-match — `rag/cache.py` (TTL configurable via `CACHE_TTL_SECONDS`, non-stream uniquement)
- [ ] LangSmith integration (tracing LLM calls)
- [ ] Alerting Grafana si latence P95 > 30s ou error rate > 1%

### Connecteurs
- [ ] Google Drive connector
- [ ] SharePoint connector
- [ ] Jira connector

---

## Phase 3 — Scale (Continu)

- [ ] Slack Bot natif (`/ask` command)
- [ ] Agent multi-step pour questions complexes (LangGraph)
- [ ] Feedback loop 👍/👎 → fine-tuning reranker
- [ ] Fine-tuning embeddings sur corpus interne
- [ ] Multi-tenant isolation par organisation
- [ ] Migration Qdrant si > 10M vecteurs

---

## Bugs corrigés
- [x] `asyncpg` `:vec::vector` → `CAST(:vec AS vector)` dans `retriever.py`
- [x] fastembed `BAAI/bge-m3` absent → `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384d)
- [x] bcrypt 4.x incompatible passlib → pinner `bcrypt==3.2.2`
- [x] `UserOut.id` UUID → str → `field_validator` mode=before
- [x] 49 erreurs ruff (imports, B904, B905, C401, UP017) → corrigées + ruff pinner dans CI
- [x] slowapi casse la signature FastAPI (`req` interprété comme query param) → rate limiting via dépendance FastAPI + Redis
- [x] asyncpg `InterfaceError: another operation is in progress` en tests → `NullPool` SQLAlchemy dans `conftest.py`

## Décisions techniques
- pgvector vs Qdrant : pgvector pour MVP (simplicité, ACID, SQL natif)
- LangChain pour orchestration (mature pour streaming)
- OpenRouter comme gateway LLM (multi-modèles, no vendor lock-in)
- fastembed local pour embeddings (no API key, FR/EN, 384d)
- Prometheus + Grafana vs Datadog : stack open-source, self-hosted
- slowapi décorateurx → dépendance FastAPI pure pour rate limiting (évite conflit signature + compatible Depends)
