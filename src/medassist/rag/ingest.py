"""CLI: medassist ingest - chunkeia os protocolos sinteticos e grava no ChromaDB."""
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb

from medassist.config import get_settings

COLLECTION_NAME = "protocolos"
_TAMANHO_MAX_CHUNK = 1200
_OVERLAP = 150

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_SECAO_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    doc_id: str
    titulo: str
    secao: str
    conteudo: str


def _parse_frontmatter(texto: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(texto)
    if not match:
        return {}, texto
    bruto, corpo = match.groups()
    meta = {}
    for linha in bruto.splitlines():
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        meta[chave.strip()] = valor.strip().strip('"')
    return meta, corpo


def _dividir_em_secoes(corpo: str) -> list[tuple[str, str]]:
    """Retorna lista de (titulo_secao, texto_secao)."""
    posicoes = list(_SECAO_RE.finditer(corpo))
    secoes = []
    for i, m in enumerate(posicoes):
        inicio = m.end()
        fim = posicoes[i + 1].start() if i + 1 < len(posicoes) else len(corpo)
        titulo_secao = m.group(1).strip()
        texto = corpo[inicio:fim].strip()
        secoes.append((titulo_secao, texto))
    return secoes


def _subdividir_com_overlap(texto: str) -> list[str]:
    if len(texto) <= _TAMANHO_MAX_CHUNK:
        return [texto]
    partes = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + _TAMANHO_MAX_CHUNK, len(texto))
        partes.append(texto[inicio:fim])
        if fim >= len(texto):
            break
        inicio = fim - _OVERLAP
    return partes


def _chunks_do_arquivo(caminho: Path) -> list[Chunk]:
    meta, corpo = _parse_frontmatter(caminho.read_text(encoding="utf-8"))
    doc_id = meta.get("doc_id", caminho.stem)
    titulo = meta.get("titulo", "")

    chunks = []
    for titulo_secao, texto_secao in _dividir_em_secoes(corpo):
        for parte in _subdividir_com_overlap(texto_secao):
            if parte:
                chunks.append(Chunk(doc_id=doc_id, titulo=titulo, secao=titulo_secao, conteudo=parte))
    return chunks


def ingest(protocolos_dir: str | None = None) -> int:
    """Le os protocolos, embute e grava (idempotente) na collection Chroma.

    Retorna a quantidade de chunks gravados.
    """
    settings = get_settings()
    diretorio = Path(protocolos_dir or "data/synthetic/protocolos")

    todos_chunks: list[Chunk] = []
    for arquivo in sorted(diretorio.glob("*.md")):
        todos_chunks.extend(_chunks_do_arquivo(arquivo))

    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_dir)

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    if not todos_chunks:
        client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        return 0

    collection = client.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    # O embedding e calculado sobre titulo+secao+corpo (melhora recall para
    # perguntas curtas), mas o "documento" retornado/citado e so o corpo,
    # que e o texto tecnico util para a resposta. Passamos os vetores prontos
    # (com o prefixo `passage:` quando o modelo e da familia E5) em vez de
    # deixar a collection embutir, para casar com o prefixo `query:` do retriever.
    from medassist.rag.embedding import embed_passagens

    textos_embedding = [f"{c.titulo}. {c.secao}. {c.conteudo}" for c in todos_chunks]
    embeddings = embed_passagens(textos_embedding)

    collection.add(
        ids=[f"{c.doc_id}-{i}" for i, c in enumerate(todos_chunks)],
        embeddings=embeddings,
        documents=[c.conteudo for c in todos_chunks],
        metadatas=[{"doc_id": c.doc_id, "titulo": c.titulo, "secao": c.secao} for c in todos_chunks],
    )
    return len(todos_chunks)


if __name__ == "__main__":
    n = ingest()
    print(f"{n} chunks indexados na collection '{COLLECTION_NAME}'")
