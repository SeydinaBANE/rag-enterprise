# Plateforme RAG d'Entreprise — Plan Complet

> Système de question/réponse sur documents internes (PDF, Confluence, Slack) avec LLM + vector DB, pipelines d'ingestion automatisés et interface web.

---

## 1. Vue d'ensemble

### Objectif
Permettre à n'importe quel employé de poser une question en langage naturel et d'obtenir une réponse précise sourcée depuis la base documentaire interne — sans avoir à chercher manuellement dans Confluence, les PDFs ou Slack.

### Ce que ça résout
- Temps perdu à chercher l'information dans des silos (Confluence, PDF, Slack, Drive)
- Réponses incohérentes entre équipes sur les mêmes sujets
- Onboarding lent des nouveaux employés
- Perte de connaissance quand des experts quittent l'entreprise

---

## 2. Architecture Cible

```
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHE PRÉSENTATION                       │
│   Interface Web (Next.js)  │  API REST/WebSocket  │  Slack Bot   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       COUCHE ORCHESTRATION                        │
│         LangChain / LlamaIndex — Query Pipeline                  │
│   Query Rewriting → Retrieval → Reranking → Generation          │
└──────┬───────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────┐    ┌─────────────────────────────────┐
│    VECTOR STORE          │    │        LLM GATEWAY               │
│  pgvector (PostgreSQL)   │    │  Claude 3.5 Sonnet / GPT-4o     │
│  ou Qdrant (scalable)    │    │  (avec prompt caching)          │
└──────────────────────────┘    └─────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                      COUCHE INGESTION                             │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │   PDF    │  │Confluence│  │  Slack   │  │ Google Drive │    │
│  │ Loader   │  │  Loader  │  │  Loader  │  │   Loader     │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
│       │              │              │                │            │
│  ┌────▼──────────────▼──────────────▼────────────────▼────────┐ │
│  │         Preprocessing Pipeline (Chunking + Cleaning)        │ │
│  └────────────────────────────┬────────────────────────────────┘ │
│                               │                                   │
│  ┌────────────────────────────▼────────────────────────────────┐ │
│  │              Embedding Model (text-embedding-3-large)        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                       COUCHE MLOps                                │
│  Airflow (scheduling)  │  MLflow (tracking)  │  Prometheus+Grafana│
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Stack Technique

### Backend & Orchestration
| Composant | Choix | Justification |
|-----------|-------|---------------|
| Langage | Python 3.11+ | Écosystème IA dominant |
| Framework API | FastAPI | Async, rapide, auto-doc OpenAPI |
| Orchestration RAG | LangChain + LangGraph | Maturité, agentic support |
| LLM principal | Claude 3.5 Sonnet (Anthropic) | Qualité, fenêtre contextuelle 200K |
| LLM fallback | GPT-4o-mini | Coût, disponibilité |
| Embeddings | text-embedding-3-large (OpenAI) | Meilleure qualité multilingual |
| Reranker | Cohere Rerank v3 | Précision retrieval +20-30% |

### Stockage & Données
| Composant | Choix | Justification |
|-----------|-------|---------------|
| Vector Store | pgvector (PostgreSQL) | Simple, ACID, SQL natif |
| Scale-out | Qdrant | Si >10M vecteurs |
| Base relationnelle | PostgreSQL 16 | Métadonnées, audit, users |
| Cache | Redis 7 | Sessions, query cache |
| Object Storage | S3 / MinIO | Documents bruts |
| Message Queue | Celery + Redis | Ingestion asynchrone |

### Frontend
| Composant | Choix |
|-----------|-------|
| Framework | Next.js 14 (App Router) |
| UI | Tailwind CSS + shadcn/ui |
| State | Zustand |
| Streaming | Server-Sent Events (SSE) |

### Infra & DevOps
| Composant | Choix |
|-----------|-------|
| Conteneurisation | Docker + Docker Compose |
| Orchestration prod | Kubernetes (EKS/GKE) |
| CI/CD | GitHub Actions |
| IaC | Terraform |
| Monitoring | Prometheus + Grafana |
| Logs | ELK Stack (Elasticsearch + Kibana) |
| Secrets | HashiCorp Vault / AWS Secrets Manager |

---

## 4. Phases de Développement

### Phase 1 — MVP (6 semaines)
**Objectif :** Un utilisateur peut poser une question et obtenir une réponse depuis des PDFs.

**Semaines 1-2 : Foundation**
- [ ] Setup du projet (monorepo, Docker Compose, CI/CD de base)
- [ ] Pipeline ingestion PDF : extraction texte → chunking → embedding → stockage pgvector
- [ ] API FastAPI minimale : endpoint `/query` avec RAG basique
- [ ] Prompt engineering : system prompt, source citations, guardrails hallucination

**Semaines 3-4 : Connecteurs**
- [ ] Connecteur Confluence (API REST v2)
- [ ] Connecteur Slack (export ou Events API)
- [ ] Scheduler Celery pour ingestion périodique (toutes les 4h)
- [ ] Déduplication et versioning des documents

**Semaines 5-6 : Interface**
- [ ] UI Next.js : chat interface avec streaming SSE
- [ ] Affichage des sources (titre, extrait, lien)
- [ ] Auth basique (SSO / OAuth2)
- [ ] Déploiement staging sur Kubernetes

**Livrable :** Démo interne fonctionnelle, 2-3 sources documentaires, <3s latence p95.

---

### Phase 2 — Production (6 semaines)
**Objectif :** Robustesse, sécurité, observabilité.

**Semaines 7-8 : Qualité du Retrieval**
- [ ] Query rewriting (HyDE — Hypothetical Document Embeddings)
- [ ] Reranker Cohere intégré
- [ ] Hybrid search (dense + BM25 sparse)
- [ ] Évaluation automatique : RAGAS framework (faithfulness, relevancy, context precision)

**Semaines 9-10 : Sécurité & Gouvernance**
- [ ] RBAC : contrôle d'accès par document/collection
- [ ] PII detection et masquage automatique (Presidio)
- [ ] Audit log de toutes les requêtes (qui, quoi, quand)
- [ ] Guardrails : refus de requêtes hors-scope, injection prompt

**Semaines 11-12 : Observabilité & Performance**
- [ ] LLM observability : LangSmith ou Arize Phoenix (latence, coûts, qualité)
- [ ] Dashboards Grafana : requêtes/min, latence, coût par requête, taux de satisfaction
- [ ] Alerting : latence >5s, taux d'erreur >1%, coût LLM >seuil
- [ ] Cache sémantique Redis (questions similaires = réponse cachée)

**Livrable :** Prêt pour production, SLA 99.5%, audit trail complet.

---

### Phase 3 — Scale & Intelligence (en continu)
**Objectif :** Amélioration continue, nouvelles sources, capacités agentiques.

- [ ] Connecteur Google Drive, SharePoint, Jira
- [ ] Slack Bot natif (commande `/ask`)
- [ ] Agent multi-step : questions complexes avec raisonnement en plusieurs étapes
- [ ] Fine-tuning embeddings sur corpus interne (optionnel, si ROI justifié)
- [ ] Feedback loop : 👍/👎 → ré-entraînement du reranker
- [ ] Multi-tenant : isolation par département/projet

---

## 5. Pipeline d'Ingestion Détaillé

```
Source (PDF / Confluence / Slack)
    │
    ▼
[1] EXTRACTION
    │  - PDF : pdfplumber / pymupdf (tableaux, images → OCR Tesseract)
    │  - Confluence : API REST → HTML → Markdown
    │  - Slack : export JSON → messages structurés
    ▼
[2] NETTOYAGE
    │  - Suppression headers/footers répétitifs
    │  - Normalisation espaces, encodages
    │  - Détection langue (langdetect)
    ▼
[3] CHUNKING (stratégie hybride)
    │  - Recursive character splitter : 512 tokens, overlap 64
    │  - Sections détectées (titres H1/H2) → chunks sémantiques
    │  - Tables → chunks dédiés avec contexte parent
    ▼
[4] ENRICHISSEMENT MÉTADONNÉES
    │  - source_type, source_id, url, title, created_at, updated_at
    │  - author, department, tags
    │  - checksum MD5 → déduplication
    ▼
[5] EMBEDDING
    │  - text-embedding-3-large (3072 dims, réduit à 1536)
    │  - Batch processing : 100 chunks/batch
    │  - Retry avec backoff exponentiel
    ▼
[6] STOCKAGE
       pgvector : vecteur + métadonnées + texte brut
       S3 : document source original
```

---

## 6. Pipeline de Requête (Query Pipeline)

```
Question utilisateur
    │
    ▼
[1] QUERY ANALYSIS
    │  - Détection intent (factuel, comparatif, procédural)
    │  - Extraction entités clés
    │  - HyDE : génération document hypothétique pour meilleur embedding
    ▼
[2] RETRIEVAL (Hybrid Search)
    │  - Dense : similarité cosinus sur pgvector (top-20)
    │  - Sparse : BM25 sur tokens (top-20)
    │  - Fusion : Reciprocal Rank Fusion → top-30
    ▼
[3] RERANKING
    │  - Cohere Rerank v3 → top-5 chunks pertinents
    ▼
[4] CONTEXT ASSEMBLY
    │  - Filtrage RBAC (utilisateur a accès ?)
    │  - Construction du contexte : <source>...</source> tags
    │  - Token budget management (max 100K tokens context)
    ▼
[5] GENERATION
    │  - Claude 3.5 Sonnet avec prompt structuré
    │  - Streaming SSE vers frontend
    │  - Citations inline automatiques [1][2]
    ▼
[6] POST-PROCESSING
       Extraction sources citées
       Faithfulness check (optionnel, LLM-as-judge)
       Log audit (user_id, query, sources, latence, tokens)
```

---

## 7. Sécurité

### Contrôle d'accès
```
Document → [tags: dept:finance, confidential:yes]
User     → [groups: finance-team, executive]
RBAC Rule → user.groups ∩ doc.required_groups ≠ ∅ → accès autorisé
```

- **SSO/SAML** : intégration Active Directory / Okta
- **JWT** : tokens courts (15min), refresh tokens sécurisés
- **RBAC** : droits par document, collection, département
- **Principle of Least Privilege** : utilisateur ne voit que ses documents autorisés

### Protection des données
- **Encryption at rest** : AES-256 (S3, PostgreSQL)
- **Encryption in transit** : TLS 1.3
- **PII detection** : Microsoft Presidio → masquage avant embedding
- **Audit log immuable** : toutes les requêtes loggées, non modifiables

### Guardrails LLM
- Détection d'injection de prompt (LLM Guard)
- Refus automatique des requêtes hors-scope
- Pas de mémorisation entre sessions (stateless par défaut)
- Rate limiting par utilisateur (100 req/h)

---

## 8. MLOps & Observabilité

### Métriques clés à monitorer

| Métrique | Cible | Alerte si |
|----------|-------|-----------|
| Latence P95 | < 3s | > 5s |
| Taux d'erreur | < 0.5% | > 1% |
| Coût LLM / requête | < $0.02 | > $0.05 |
| Freshness index | < 4h de retard | > 12h |
| RAGAS Faithfulness | > 0.85 | < 0.70 |
| RAGAS Answer Relevancy | > 0.80 | < 0.65 |

### Pipeline MLOps
```
Code PR → Tests unitaires + intégration
       → Évaluation RAGAS sur golden dataset (50 questions)
       → Si score ≥ seuil → déploiement staging
       → Tests smoke staging → déploiement prod (canary 10%)
       → Monitoring 24h → rollout 100% ou rollback
```

### Évaluation continue
- **Golden dataset** : 50-100 questions/réponses de référence, maintenu par l'équipe
- **LLM-as-judge** : Claude évalue la qualité des réponses (faithfulness, completeness)
- **Feedback utilisateur** : 👍/👎 enregistrés, analysés hebdomadairement
- **Drift detection** : alerte si distribution des requêtes change significativement

---

## 9. Estimations

### Coûts mensuels (100 utilisateurs actifs, ~1000 requêtes/jour)

| Poste | Estimation |
|-------|-----------|
| LLM (Claude Sonnet) | ~$150/mois |
| Embeddings | ~$20/mois |
| Reranker (Cohere) | ~$50/mois |
| Infrastructure K8s | ~$300/mois |
| Stockage (S3 + DB) | ~$50/mois |
| **Total** | **~$570/mois** |

### Effort de développement

| Phase | Durée | Équipe |
|-------|-------|--------|
| Phase 1 MVP | 6 semaines | 2 ingénieurs IA + 1 frontend |
| Phase 2 Production | 6 semaines | 2 ingénieurs IA + 1 DevOps |
| Phase 3 Scale | En continu | 1-2 ingénieurs IA |

---

## 10. Risques & Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Hallucinations LLM | Élevé | Moyen | RAGAS monitoring, faithfulness check, "je ne sais pas" fallback |
| Fuite de données confidentielles | Très élevé | Faible | RBAC strict, PII masquage, audit log |
| Coûts LLM incontrôlés | Moyen | Moyen | Budget cap par user, cache sémantique, modèles légers pour tâches simples |
| Mauvaise qualité retrieval | Élevé | Moyen | Golden dataset eval, reranker, hybrid search |
| Données obsolètes | Moyen | Élevé | Scheduler d'ingestion toutes les 4h, freshness metadata |
| Dépendance fournisseur LLM | Moyen | Faible | Abstraction LLM gateway, fallback GPT-4o |

---

## 11. Prochaines étapes immédiates

1. **Semaine 1** : Valider la stack (pgvector vs Qdrant, LangChain vs LlamaIndex) avec un spike technique
2. **Semaine 1** : Identifier les 2-3 sources documentaires pilotes avec les équipes métier
3. **Semaine 1** : Setup environnement de développement (Docker Compose, CI/CD, secrets management)
4. **Semaine 2** : Premier pipeline PDF → pgvector → query fonctionnel (même rudimentaire)
5. **Semaine 2** : Construire le golden dataset de 20 questions pilotes

---

## GSTACK REVIEW REPORT

| Review | Status | Findings |
|--------|--------|----------|
| CEO Review | NO REVIEWS YET — run `/autoplan` | — |
| Eng Review | NO REVIEWS YET — run `/autoplan` | — |
| Design Review | NO REVIEWS YET — run `/autoplan` | — |
| DX Review | NO REVIEWS YET — run `/autoplan` | — |
| Security Review | NO REVIEWS YET — run `/autoplan` | — |
