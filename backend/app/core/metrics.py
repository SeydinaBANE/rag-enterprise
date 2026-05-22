from prometheus_client import Counter, Gauge, Histogram

QUERY_LATENCY = Histogram(
    "rag_query_latency_seconds",
    "Latence des requêtes RAG end-to-end",
    ["collection"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

QUERY_TOTAL = Counter(
    "rag_query_total",
    "Nombre total de requêtes RAG",
    ["collection", "user_role"],
)

TOKENS_USED = Counter(
    "rag_tokens_used_total",
    "Tokens LLM consommés",
    ["collection"],
)

FEEDBACK_TOTAL = Counter(
    "rag_feedback_total",
    "Feedback utilisateur reçu",
    ["value"],  # "positive" | "negative"
)

DOCUMENTS_INGESTED = Counter(
    "rag_documents_ingested_total",
    "Chunks de documents ingérés",
    ["collection", "source_type"],
)

ACTIVE_STREAMS = Gauge(
    "rag_active_streams",
    "Nombre de streams SSE actifs",
)
