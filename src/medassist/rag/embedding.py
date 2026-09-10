"""Embeddings dos protocolos e das consultas RAG.

Centraliza o carregamento do modelo (cache de processo) e o tratamento dos
prefixos de instrucao. Os modelos da familia E5 (`intfloat/multilingual-e5-*`)
exigem prefixar cada texto com `query: ` ou `passage: ` — sem isso a
similaridade cai muito. Modelos sem essa convencao (ex.: os
`sentence-transformers/paraphrase-*`) usam prefixo vazio.
"""
from functools import lru_cache

from medassist.config import get_settings

_MODELOS_COM_PREFIXO = ("intfloat/multilingual-e5", "intfloat/e5")


@lru_cache(maxsize=2)
def _carregar(nome: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(nome)


def _prefixos(nome: str) -> tuple[str, str]:
    """(prefixo_consulta, prefixo_documento) para o modelo."""
    if nome.startswith(_MODELOS_COM_PREFIXO):
        return "query: ", "passage: "
    return "", ""


def embed_passagens(textos: list[str]) -> list[list[float]]:
    nome = get_settings().embedding_model
    _, prefixo = _prefixos(nome)
    modelo = _carregar(nome)
    vetores = modelo.encode(
        [f"{prefixo}{t}" for t in textos], normalize_embeddings=True
    )
    return vetores.tolist()


def embed_consulta(texto: str) -> list[float]:
    nome = get_settings().embedding_model
    prefixo, _ = _prefixos(nome)
    modelo = _carregar(nome)
    vetor = modelo.encode([f"{prefixo}{texto}"], normalize_embeddings=True)[0]
    return vetor.tolist()
