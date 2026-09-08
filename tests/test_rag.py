from medassist.rag.ingest import ingest
from medassist.rag.retriever import buscar


def test_ingest_gera_chunks(tmp_settings):
    n = ingest()
    assert n > 0


def test_buscar_sem_ingest_retorna_lista_vazia(tmp_settings):
    resultado = buscar("qualquer pergunta")
    assert resultado == []


def test_buscar_apos_ingest_retorna_docs_relevantes(chroma_ingested):
    resultados = buscar("como tratar anafilaxia", top_k=3)
    assert len(resultados) > 0
    top = resultados[0]
    assert top["doc_id"] == "PROT-006"
    assert set(top.keys()) == {"doc_id", "titulo", "secao", "conteudo", "score"}
    assert 0.0 <= top["score"] <= 1.0


def test_buscar_respeita_min_score_alto(chroma_ingested):
    resultados = buscar("como tratar anafilaxia", min_score=0.99)
    assert resultados == []


def test_buscar_respeita_top_k(chroma_ingested):
    resultados = buscar("protocolo", top_k=2, min_score=-1)
    assert len(resultados) <= 2
