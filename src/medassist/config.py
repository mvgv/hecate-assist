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
    # Modelo auxiliar de proposito geral para a triagem (classificacao de intencao).
    # O `medassist` fine-tunado so treinou a tarefa do `gerar_resposta` -> fora dela
    # ele recusa demais. Um 3B generico classifica bem e e rapido (~1 s/chamada).
    model_aux: str = "llama3.2:3b"

    data_dir: str = "data"
    db_path: str = "data/medassist.db"
    checkpoint_path: str = "data/checkpoints.db"
    chroma_dir: str = "data/chroma"
    log_dir: str = "logs"

    # E5 multilingue: bem superior ao paraphrase-MiniLM para retrieval em PT-BR
    # (ver docs/desvios.md #15). Exige prefixo `query:`/`passage:` — tratado em
    # rag/embedding.py. As similaridades do E5 ficam comprimidas no alto (~0.82+
    # p/ relevante, ~0.81 p/ ruido) -> min_score 0.82.
    embedding_model: str = "intfloat/multilingual-e5-small"
    rag_top_k: int = 4
    rag_min_score: float = 0.82

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
    # 3072 e suficiente p/ contexto RAG + pergunta + 768 de geracao; deixa folga
    # de VRAM na GPU de 8 GB (pode voltar a 4096 se algum prompt truncar).
    ollama_num_ctx: int = 3072
    # Modelo auxiliar (triagem) roda na CPU (`num_gpu=0`): a GPU inteira fica para
    # o 8B (senao o Ollama fica descarregando um modelo a cada chamada, pois os
    # dois nao cabem nos 8 GB). A triagem e uma classificacao de 1 palavra ->
    # ~0.5 s por chamada na CPU depois do load inicial (`OLLAMA_KEEP_ALIVE=-1`).
    ollama_aux_num_gpu: int = 0
    ollama_aux_num_ctx: int = 1024
    ollama_aux_num_predict: int = 32


@lru_cache
def get_settings() -> Settings:
    return Settings()
