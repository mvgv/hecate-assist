from typing import TypedDict

import chromadb

from medassist.config import get_settings
from medassist.rag.ingest import COLLECTION_NAME


class DocRecuperado(TypedDict):
    doc_id: str
    titulo: str
    secao: str
    conteudo: str
    score: float


def buscar(
    query: str, top_k: int | None = None, min_score: float | None = None
) -> list[DocRecuperado]:
    settings = get_settings()
    top_k = top_k or settings.rag_top_k
    min_score = settings.rag_min_score if min_score is None else min_score

    try:
        client = chromadb.PersistentClient(path=settings.chroma_dir)
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return []

    if collection.count() == 0:
        return []

    from medassist.rag.embedding import embed_consulta

    query_embedding = embed_consulta(query)
    resultado = collection.query(
        query_embeddings=[query_embedding], n_results=min(top_k, collection.count())
    )

    documentos = resultado.get("documents", [[]])[0]
    metadados = resultado.get("metadatas", [[]])[0]
    distancias = resultado.get("distances", [[]])[0]

    encontrados: list[DocRecuperado] = []
    for doc, meta, distancia in zip(documentos, metadados, distancias):
        score = 1 - distancia
        if score < min_score:
            continue
        encontrados.append(
            DocRecuperado(
                doc_id=meta.get("doc_id", ""),
                titulo=meta.get("titulo", ""),
                secao=meta.get("secao", ""),
                conteudo=doc,
                score=score,
            )
        )
    return encontrados
