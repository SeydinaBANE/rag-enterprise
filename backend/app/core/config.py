from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/ragdb"
    sync_database_url: str = "postgresql://rag:rag@localhost:5432/ragdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenRouter (LLM gateway — openai-compatible)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_site_name: str = "RAG Enterprise"

    # Cohere reranker (optional)
    cohere_api_key: str = ""

    # Auth
    secret_key: str = "changeme"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # RAG
    # Embeddings: local fastembed model (no API key needed)
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024
    # LLM via OpenRouter — see https://openrouter.ai/models
    llm_model: str = "anthropic/claude-3.5-sonnet"
    retrieval_top_k: int = 20
    rerank_top_n: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Connectors
    confluence_url: str = ""
    confluence_username: str = ""
    confluence_api_token: str = ""
    slack_bot_token: str = ""

    # Observability
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "rag-enterprise"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
