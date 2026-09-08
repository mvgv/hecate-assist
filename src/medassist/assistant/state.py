from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages

from medassist.rag.retriever import DocRecuperado


class AssistantState(TypedDict, total=False):
    # --- entrada ---
    messages: Annotated[list, add_messages]  # historico multi-turno
    pergunta: str
    paciente_id: str | None
    thread_id: str

    # --- triagem ---
    intencao: Literal["duvida_clinica", "caso_paciente", "fora_escopo"]

    # --- contexto (nos 2 e 3) ---
    paciente: dict | None        # demografia, comorbidades, alergias, medicacoes
    exames_pendentes: list[dict]
    exames_criticos: list[dict]  # valores fora de faixa critica

    # --- RAG (no 4) ---
    docs: list[DocRecuperado]
    sem_fonte: bool              # True se nenhum doc passou do score minimo

    # --- geracao (no 5) ---
    resposta_bruta: str
    tentativas: int              # contador do loop de regeneracao

    # --- guardrails (no 6) ---
    veredito: Literal["aprovada", "regenerar", "bloqueada"]
    violacoes: list[str]         # ex.: ["prescricao_direta", "dosagem_sem_validacao"]

    # --- acoes e saida ---
    requer_aprovacao: bool       # dispara o interrupt
    aprovacao: dict | None
    alertas_emitidos: list[dict]
    resposta_final: str
    fontes: list[str]            # ["PROT-001 §2 - Manejo de sepse", ...]
    erro: str | None             # falha tecnica em qualquer no -> resposta_segura
