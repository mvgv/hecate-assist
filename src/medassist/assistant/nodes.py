import re

from medassist.assistant import guardrails as guardrails_mod
from medassist.assistant.prompts import (
    DISCLAIMER,
    PROMPT_TRIAGEM,
    SYSTEM_PROMPT,
    TEMPLATE_FEEDBACK_REGENERACAO,
    TEMPLATE_RECUSA,
    TEMPLATE_RESPOSTA_SEGURA,
    TERMOS_CLINICOS,
)
from medassist.db.queries import (
    create_alert,
    get_critical_exams,
    get_patient_context,
    get_pending_exams,
)
from medassist.llm.base import get_llm
from medassist.logging_setup import auditado
from medassist.rag.retriever import buscar

_RE_DOC_CITADO = re.compile(r"PROT-\d+")


@auditado
def triagem(state: dict) -> dict:
    if state.get("paciente_id"):
        return {"intencao": "caso_paciente"}

    pergunta = (state.get("pergunta") or "").lower()
    tem_termo_clinico = any(termo in pergunta for termo in TERMOS_CLINICOS)
    if not tem_termo_clinico:
        return {"intencao": "fora_escopo"}

    llm = get_llm()
    resposta = llm.gerar(
        system=PROMPT_TRIAGEM,
        mensagens=[{"role": "user", "content": state.get("pergunta", "")}],
    )
    resposta_normalizada = resposta.strip().lower()
    for categoria in ("fora_escopo", "caso_paciente", "duvida_clinica"):
        if categoria in resposta_normalizada:
            return {"intencao": categoria}
    return {"intencao": "duvida_clinica"}


@auditado
def contexto_paciente(state: dict) -> dict:
    paciente = get_patient_context(state["paciente_id"])
    if paciente is None:
        return {"erro": "paciente_nao_encontrado"}
    return {"paciente": paciente}


@auditado
def verificar_exames(state: dict) -> dict:
    paciente_id = state["paciente_id"]
    pendentes = get_pending_exams(paciente_id)
    criticos = get_critical_exams(paciente_id)
    delta = {"exames_pendentes": pendentes, "exames_criticos": criticos}
    if criticos:
        delta["requer_aprovacao"] = True
    return delta


@auditado
def recuperar_protocolos(state: dict) -> dict:
    pergunta = state.get("pergunta", "")
    paciente = state.get("paciente") or {}
    comorbidades = paciente.get("comorbidades", [])
    query = f"{pergunta} {' '.join(comorbidades)}".strip() if comorbidades else pergunta
    docs = buscar(query)
    return {"docs": docs, "sem_fonte": len(docs) == 0}


def _montar_contexto(state: dict) -> str:
    partes: list[str] = []
    paciente = state.get("paciente")
    if paciente:
        partes.append(
            f"Paciente: {paciente['nome']}, {paciente['idade']} anos, sexo {paciente['sexo']}."
        )
        if paciente.get("comorbidades"):
            partes.append("Comorbidades: " + ", ".join(paciente["comorbidades"]) + ".")
        if paciente.get("medicacoes_em_uso"):
            partes.append("Medicações em uso: " + ", ".join(paciente["medicacoes_em_uso"]) + ".")
        if paciente.get("alergias"):
            alergias_txt = ", ".join(
                f"{a['substancia']} ({a['gravidade']})" for a in paciente["alergias"]
            )
            partes.append(f"⚠️ ALERGIAS DO PACIENTE (não sugerir estas substâncias): {alergias_txt}.")

    exames_pendentes = state.get("exames_pendentes") or []
    if exames_pendentes:
        tipos = ", ".join(e["tipo"] for e in exames_pendentes)
        partes.append(f"Exames pendentes: {tipos}.")

    exames_criticos = state.get("exames_criticos") or []
    if exames_criticos:
        criticos_txt = ", ".join(
            f"{e['tipo']}={e['resultado']}{e.get('unidade') or ''}" for e in exames_criticos
        )
        partes.append(f"⚠️ Exames com resultado crítico: {criticos_txt}.")

    for doc in state.get("docs") or []:
        partes.append(f"[{doc['doc_id']} §{doc['secao']}] {doc['conteudo']}")

    return "\n".join(partes)


@auditado
def gerar_resposta(state: dict) -> dict:
    contexto = _montar_contexto(state)
    tentativas = state.get("tentativas", 0)

    system = SYSTEM_PROMPT
    if tentativas > 0:
        system += TEMPLATE_FEEDBACK_REGENERACAO.format(
            violacoes=", ".join(state.get("violacoes", []))
        )

    llm = get_llm()
    resposta = llm.gerar(
        system=system,
        mensagens=[{"role": "user", "content": state.get("pergunta", "")}],
        contexto=contexto,
    )
    return {"resposta_bruta": resposta, "tentativas": tentativas + 1}


@auditado
def checar_guardrails(state: dict) -> dict:
    return guardrails_mod.validar(state)


@auditado
def aprovacao_humana(state: dict) -> dict:
    from langgraph.types import interrupt

    if state.get("exames_criticos"):
        motivo = "resultado de exame crítico requer validação humana antes de prosseguir"
    else:
        motivo = "sugestão de conduta/tratamento requer validação humana antes de registro"

    payload = interrupt(
        {
            "resposta_proposta": state.get("resposta_bruta"),
            "fontes": [d["doc_id"] for d in (state.get("docs") or [])],
            "motivo": motivo,
        }
    )
    return {"aprovacao": payload}


@auditado
def emitir_alertas(state: dict) -> dict:
    paciente_id = state.get("paciente_id")
    aprovacao = state.get("aprovacao") or {}
    alertas: list[dict] = []

    for exame in state.get("exames_criticos") or []:
        alerta_id = create_alert(
            paciente_id,
            "exame_critico",
            "critico",
            f"Exame {exame['tipo']} com resultado crítico: {exame.get('resultado')}"
            f"{exame.get('unidade') or ''}.",
        )
        if alerta_id is not None:
            alertas.append({"id": alerta_id, "tipo": "exame_critico"})

    if aprovacao.get("aprovado"):
        alerta_id = create_alert(
            paciente_id,
            "sugestao_tratamento",
            "atencao",
            state.get("resposta_bruta", ""),
            aprovado_por=aprovacao.get("aprovador"),
        )
        if alerta_id is not None:
            alertas.append({"id": alerta_id, "tipo": "sugestao_tratamento"})

    return {"alertas_emitidos": alertas}


@auditado
def formatar_resposta(state: dict) -> dict:
    resposta = state.get("resposta_bruta", "")
    partes = [resposta]

    pendentes = state.get("exames_pendentes") or []
    if pendentes:
        tipos = ", ".join(e["tipo"] for e in pendentes)
        partes.append(
            f"⚠️ Atenção: há exame(s) pendente(s) que podem alterar a conduta: {tipos}."
        )

    docs = state.get("docs") or []
    docs_por_id = {d["doc_id"]: d for d in docs}
    citados = set(_RE_DOC_CITADO.findall(resposta))
    fontes: list[str] = []

    if state.get("sem_fonte"):
        fontes_txt = "Sem fonte interna — conhecimento geral do modelo, validar."
    else:
        relevantes = [docs_por_id[d] for d in citados if d in docs_por_id] or docs
        for d in relevantes:
            fontes.append(f"{d['doc_id']} §{d['secao']} — {d['titulo']}")
        fontes_txt = (
            "\n".join(f"- {f}" for f in fontes)
            if fontes
            else "Sem fonte interna — conhecimento geral do modelo, validar."
        )

    partes.append(f"📚 Fontes:\n{fontes_txt}")
    partes.append(DISCLAIMER)

    resposta_final = "\n\n".join(partes)
    return {"resposta_final": resposta_final, "fontes": fontes}


@auditado(sempre_executa=True)
def resposta_segura(state: dict) -> dict:
    if state.get("erro"):
        motivo = state["erro"]
    elif state.get("violacoes"):
        motivo = "violação de segurança: " + ", ".join(state["violacoes"])
    else:
        motivo = "não foi possível validar a resposta com segurança"

    resposta = TEMPLATE_RESPOSTA_SEGURA.format(motivo=motivo)
    return {"resposta_bruta": resposta, "resposta_final": resposta, "fontes": []}


@auditado(sempre_executa=True)
def resposta_recusa(state: dict) -> dict:
    return {"resposta_bruta": TEMPLATE_RECUSA, "resposta_final": TEMPLATE_RECUSA, "fontes": []}


NOS = {
    "triagem": triagem,
    "contexto_paciente": contexto_paciente,
    "verificar_exames": verificar_exames,
    "recuperar_protocolos": recuperar_protocolos,
    "gerar_resposta": gerar_resposta,
    "guardrails": checar_guardrails,
    "aprovacao_humana": aprovacao_humana,
    "emitir_alertas": emitir_alertas,
    "formatar_resposta": formatar_resposta,
    "resposta_segura": resposta_segura,
    "resposta_recusa": resposta_recusa,
}
