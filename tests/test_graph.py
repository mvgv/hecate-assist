from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from medassist.assistant.graph import construir_grafo
from medassist.llm.base import LLMIndisponivelError


def _invocar(grafo, pergunta, paciente_id, thread_id):
    entrada = {
        "messages": [],
        "pergunta": pergunta,
        "paciente_id": paciente_id,
        "thread_id": thread_id,
        "tentativas": 0,
    }
    return grafo.invoke(entrada, config={"configurable": {"thread_id": thread_id}})


def test_pergunta_geral_traz_fontes_sem_interrupt(grafo):
    r = _invocar(grafo, "como tratar anafilaxia?", None, "t1")
    assert "__interrupt__" not in r
    assert "📚 Fontes" in r["resposta_final"]
    assert "PROT-" in r["resposta_final"]
    assert r.get("erro") is None


def test_paciente_com_exame_pendente_avisa_na_resposta(grafo):
    r = _invocar(grafo, "como tratar anafilaxia?", "P002", "t2")
    if "__interrupt__" in r:
        r = grafo.invoke(
            Command(resume={"aprovado": False, "aprovador": "Dr. Teste", "observacao": ""}),
            config={"configurable": {"thread_id": "t2"}},
        )
    assert any("hemograma" in e["tipo"] for e in r.get("exames_pendentes", []))
    assert "pendente" in r["resposta_final"].lower()


def test_sugestao_de_tratamento_interrompe_e_registra_alerta_apos_aprovacao(grafo):
    thread_id = "t3"
    r = _invocar(grafo, "qual a conduta adequada para o quadro?", "P003", thread_id)
    assert "__interrupt__" in r

    payload = r["__interrupt__"][0].value
    assert "resposta_proposta" in payload
    assert "motivo" in payload

    r2 = grafo.invoke(
        Command(resume={"aprovado": True, "aprovador": "Dr. Teste", "observacao": "ok"}),
        config={"configurable": {"thread_id": thread_id}},
    )
    assert "__interrupt__" not in r2
    assert any(a["tipo"] == "sugestao_tratamento" for a in r2["alertas_emitidos"])

    from medassist.db.queries import list_alerts

    alertas = list_alerts("P003")
    assert any(a["tipo"] == "sugestao_tratamento" for a in alertas)


def test_forcar_prescricao_regenera_ate_max_tentativas(grafo):
    r = _invocar(grafo, "__forcar_prescricao__ preciso de conduta", None, "t4")
    assert r["tentativas"] == 2
    assert r["veredito"] == "regenerar"
    assert "Motivo" in r["resposta_final"]


def test_forcar_alergia_bloqueia_para_paciente_alergico(grafo):
    r = _invocar(grafo, "__forcar_alergia__ preciso de conduta", "P001", "t5")
    assert r["veredito"] == "bloqueada"
    assert "Motivo" in r["resposta_final"]
    assert "__interrupt__" not in r


def test_pergunta_fora_de_escopo_recebe_recusa(grafo):
    r = _invocar(grafo, "quanto e 2+2?", None, "t6")
    assert r["intencao"] == "fora_escopo"
    assert "não pode responder" in r["resposta_final"] or "especializado" in r["resposta_final"]


def test_rag_vazio_sem_ingest_marca_sem_fonte(tmp_settings, db_seeded):
    grafo_sem_ingest = construir_grafo(checkpointer=MemorySaver())
    r = _invocar(grafo_sem_ingest, "como tratar anafilaxia?", None, "t7")
    assert r["sem_fonte"] is True
    assert "Sem fonte interna" in r["resposta_final"]


def test_paciente_inexistente_cai_em_resposta_segura(grafo):
    r = _invocar(grafo, "duvida sobre o caso", "P999", "t8")
    assert r["erro"] == "paciente_nao_encontrado"
    assert "paciente_nao_encontrado" in r["resposta_final"]


def test_llm_indisponivel_cai_em_resposta_segura(grafo, monkeypatch):
    class _LLMQuebrado:
        def gerar(self, system, mensagens, contexto=""):
            raise LLMIndisponivelError("Ollama indisponivel (teste)")

    monkeypatch.setattr("medassist.assistant.nodes.get_llm", lambda: _LLMQuebrado())

    r = _invocar(grafo, "qual a conduta adequada?", "P003", "t9")
    assert r["erro"] is not None
    assert "gerar_resposta" in r["erro"]
    assert "Motivo" in r["resposta_final"]


def test_llm_indisponivel_na_triagem_ambigua_cai_em_resposta_segura(grafo, monkeypatch):
    """Regressao: descoberto testando o deploy Docker real com Ollama sem
    modelo registrado. Pergunta com termo clinico e sem paciente_id aciona a
    heuristica ambigua da triagem, que chama o LLM - uma falha ali NAO pode
    cair em resposta_recusa (mensagem de "fora de escopo" seria enganosa)."""

    class _LLMQuebrado:
        def gerar(self, system, mensagens, contexto=""):
            raise LLMIndisponivelError("Ollama indisponivel (teste)")

    monkeypatch.setattr("medassist.assistant.nodes.get_llm", lambda: _LLMQuebrado())

    r = _invocar(grafo, "qual o protocolo de sepse em caso ambiguo?", None, "t10")
    assert r["erro"] is not None
    assert "triagem" in r["erro"]
    assert "Motivo" in r["resposta_final"]
    assert "especializado" not in r["resposta_final"]
