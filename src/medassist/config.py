from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDASSIST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["fake", "ollama"] = "fake"
    model: str = "medassist"

    data_dir: str = "data"
    db_path: str = "data/medassist.db"
    checkpoint_path: str = "data/checkpoints.db"
    chroma_dir: str = "data/chroma"
    log_dir: str = "logs"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_top_k: int = 4
    rag_min_score: float = 0.35

    max_tentativas: int = 2

    ollama_base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
