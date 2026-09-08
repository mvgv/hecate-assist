import sqlite3
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from medassist.assistant.nodes import NOS
from medassist.assistant.routing import rota_aprovacao, rota_guardrails, rota_triagem
from medassist.assistant.state import AssistantState
from medassist.config import get_settings


def _sqlite_checkpointer() -> SqliteSaver:
    settings = get_settings()
    Path(settings.checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_path, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver


def construir_grafo(checkpointer: BaseCheckpointSaver | None = None):
    g = StateGraph(AssistantState)

    for nome, fn in NOS.items():
        g.add_node(nome, fn)

    g.add_edge(START, "triagem")
    g.add_conditional_edges(
        "triagem",
        rota_triagem,
        {
            "fora_escopo": "resposta_recusa",
            "duvida_clinica": "recuperar_protocolos",
            "caso_paciente": "contexto_paciente",
            "erro": "resposta_segura",
        },
    )
    g.add_edge("contexto_paciente", "verificar_exames")
    g.add_edge("verificar_exames", "recuperar_protocolos")
    g.add_edge("recuperar_protocolos", "gerar_resposta")
    g.add_edge("gerar_resposta", "guardrails")
    g.add_conditional_edges(
        "guardrails",
        rota_guardrails,
        {
            "regenerar": "gerar_resposta",
            "bloqueada": "resposta_segura",
            "aprovar": "aprovacao_humana",
            "aprovada": "formatar_resposta",
        },
    )
    g.add_conditional_edges(
        "aprovacao_humana",
        rota_aprovacao,
        {
            "aprovado": "emitir_alertas",
            "rejeitado": "resposta_segura",
        },
    )
    g.add_edge("emitir_alertas", "formatar_resposta")
    g.add_edge("resposta_segura", "formatar_resposta")
    g.add_edge("formatar_resposta", END)
    g.add_edge("resposta_recusa", END)

    saver = checkpointer if checkpointer is not None else _sqlite_checkpointer()
    return g.compile(checkpointer=saver)


def responder(pergunta: str, paciente_id: str | None, thread_id: str) -> AssistantState:
    grafo = construir_grafo()
    entrada = {
        "messages": [{"role": "user", "content": pergunta}],
        "pergunta": pergunta,
        "paciente_id": paciente_id,
        "thread_id": thread_id,
        "tentativas": 0,
    }
    config = {"configurable": {"thread_id": thread_id}}
    return grafo.invoke(entrada, config=config)


def retomar(thread_id: str, aprovado: bool, aprovador: str, observacao: str = "") -> AssistantState:
    grafo = construir_grafo()
    config = {"configurable": {"thread_id": thread_id}}
    payload = {"aprovado": aprovado, "aprovador": aprovador, "observacao": observacao}
    return grafo.invoke(Command(resume=payload), config=config)
