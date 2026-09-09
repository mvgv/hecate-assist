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
    # Teto de tokens por geracao: limita o pior caso se o modelo degenerar (nao
    # emitir EOS). Uma resposta de protocolo bem-formada cabe em ~600.
    ollama_num_predict: int = 768
    # Timeout (s) por chamada ao Ollama. Estoura -> LLMIndisponivelError -> o grafo
    # cai em resposta_segura em vez de travar. Em CPU, uma geracao sadia leva ~20-40s.
    ollama_timeout: int = 240
    ollama_num_ctx: int = 4096


@lru_cache
def get_settings() -> Settings:
    return Settings()
