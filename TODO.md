# TODO — Plateforme RAG d'Entreprise

## Phase 1 — MVP (Semaines 1-6)

### Infrastructure
- [x] Structure du projet (monorepo)
- [x] docker-compose.yml (PostgreSQL+pgvector, Redis, backend, frontend)
- [x] Migration SQL initiale (tables + extension pgvector)
- [ ] CI/CD GitHub Actions (lint + tests + build)
- [ ] .github/workflows/ci.yml

### Backend — Foundation
- [x] FastAPI app entry point (`main.py`)
- [x] Config Pydantic-settings (`core/config.py`)
- [x] Database async SQLAlchemy + pgvector (`core/database.py`)
- [x] Modèles ORM (`models/db.py`)
- [x] Schémas Pydantic (`models/schemas.py`)
- [x] Health endpoint (`api/routes/health.py`)
- [ ] Auth JWT + middleware (`core/security.py`, `api/deps.py`)

### Backend — Ingestion Pipeline
- [x] Base loader class (`ingestion/base.py`)
- [x] Chunker hybride (`ingestion/chunker.py`)
- [x] Embedder avec déduplication (`ingestion/embedder.py`)
- [x] PDF loader (`ingestion/pdf_loader.py`)
- [ ] Confluence loader (`ingestion/confluence.py`)
- [ ] Slack loader (`ingestion/slack.py`)
- [x] Ingest endpoint (`api/routes/ingest.py`)
- [ ] Celery tasks pour ingestion async (`workers/tasks.py`)
- [ ] Scheduler toutes les 4h

### Backend — RAG Pipeline
- [x] Retriever hybrid search (`rag/retriever.py`)
- [x] Reranker Cohere avec fallback (`rag/reranker.py`)
- [x] Generator streaming Claude (`rag/generator.py`)
- [x] Pipeline principal (`rag/pipeline.py`)
- [x] Query endpoint avec SSE (`api/routes/query.py`)

### Frontend
- [x] Layout + page principale
- [x] Composant Chat avec streaming SSE
- [x] MessageBubble (user/assistant)
- [x] SourceCard (citations)
- [x] API client (`lib/api.ts`)
- [ ] Auth login page
- [ ] Page historique des conversations

### Tests
- [ ] Tests ingestion PDF
- [ ] Tests RAG pipeline (golden dataset 20 questions)
- [ ] Tests API endpoints
- [ ] Golden dataset : `tests/golden_dataset.json`

---

## Phase 2 — Production (Semaines 7-12)

### Qualité Retrieval
- [ ] HyDE (Hypothetical Document Embeddings) query rewriting
- [ ] BM25 sparse search avec rank fusion
- [ ] RAGAS evaluation automatique (faithfulness, relevancy)
- [ ] Dashboard métriques qualité

### Sécurité & Gouvernance
- [ ] RBAC complet (documents taggés par département)
- [ ] PII detection Microsoft Presidio avant embedding
- [ ] Audit log immuable (table `query_logs`)
- [ ] Guardrails anti-injection prompt (LLM Guard)
- [ ] Rate limiting par utilisateur

### Observabilité
- [ ] LangSmith integration (tracing LLM)
- [ ] Dashboards Grafana (latence, coûts, satisfaction)
- [ ] Alerting PagerDuty/Slack si latence >5s ou erreur >1%
- [ ] Cache sémantique Redis (questions similaires)

### Connecteurs supplémentaires
- [ ] Google Drive connector
- [ ] SharePoint connector
- [ ] Jira connector

---

## Phase 3 — Scale (Continu)

- [ ] Slack Bot natif (`/ask` command)
- [ ] Agent multi-step pour questions complexes
- [ ] Feedback loop 👍/👎 → amélioration reranker
- [ ] Fine-tuning embeddings sur corpus interne
- [ ] Multi-tenant isolation par projet
- [ ] Migration Qdrant si >10M vecteurs

---

## Bugs connus
_(à remplir au fur et à mesure)_

## Décisions techniques prises
- pgvector vs Qdrant : pgvector choisi pour MVP (simplicité, ACID, SQL natif)
- LangChain vs LlamaIndex : LangChain pour orchestration (plus mature pour streaming)
- Claude 3.5 Sonnet comme LLM principal (200K context, prompt caching)
- text-embedding-3-large pour embeddings (1536 dims après réduction)
