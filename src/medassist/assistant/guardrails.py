import re

_RE_PRESCRICAO = re.compile(
    r"\b(prescrever|prescrevo|administrar|tomar|aplicar)\b.*\d+\s?(mg|g|ml|mcg|ui)\b",
    re.IGNORECASE | re.DOTALL,
)
_RE_VALIDACAO = re.compile(r"validação|validacao|médico responsável|medico responsavel|avaliar", re.IGNORECASE)
_RE_DIAGNOSTICO = re.compile(r"\bo paciente (tem|está com|esta com|é portador de|e portador de)\b", re.IGNORECASE)
_RE_HEDGE = re.compile(r"compatível|compativel|sugestivo|possível|possivel|provável|provavel", re.IGNORECASE)
_RE_FONTE = re.compile(r"\[PROT-\d+", re.IGNORECASE)
_RE_SUGESTAO_CONDUTA = re.compile(r"\b(sugere-se|recomenda-se|conduta|iniciar|tratamento)\b", re.IGNORECASE)


def _checar_alergia(resposta: str, alergias: list[dict]) -> bool:
    for alergia in alergias or []:
        substancia = re.escape(alergia.get("substancia", ""))
        if not substancia:
            continue
        padrao = re.compile(rf"\b{substancia}s?\b", re.IGNORECASE)
        if padrao.search(resposta):
            return True
    return False


def _camada1(state: dict) -> tuple[str | None, list[str]]:
    resposta = state.get("resposta_bruta", "")
    violacoes: list[str] = []

    paciente = state.get("paciente") or {}
    alergias = paciente.get("alergias", [])
    if _checar_alergia(resposta, alergias):
        return "bloqueada", ["alergia_paciente"]

    if _RE_PRESCRICAO.search(resposta) and not _RE_VALIDACAO.search(resposta):
        violacoes.append("prescricao_direta")

    for match in _RE_DIAGNOSTICO.finditer(resposta):
        janela = resposta[match.start(): match.start() + 200]
        if not _RE_HEDGE.search(janela):
            violacoes.append("diagnostico_definitivo")
            break

    docs_validos = {d["doc_id"] for d in state.get("docs", [])}
    for match in _RE_FONTE.finditer(resposta):
        trecho = resposta[match.start(): match.start() + 20]
        doc_citado = trecho[1:].split()[0].rstrip("§,.;")
        if doc_citado not in docs_validos:
            violacoes.append("fonte_alucinada")
            break

    if violacoes:
        return "regenerar", violacoes
    return None, []


def validar(state: dict) -> dict:
    # Guardrail 100% deterministico (regras/regex). O verificador via LLM foi
    # removido: nenhum modelo pequeno (nem o 8B fine-tunado, nem o llama3.2:3b)
    # julga a rubrica de seguranca de forma confiavel — ambos davam
    # `aprovada: false` em respostas limpas (falso-bloqueio). As regras de
    # `_camada1` cobrem os casos criticos sem falso-positivo:
    # prescricao sem validacao, diagnostico definitivo sem hedge, fonte
    # alucinada (-> regenerar) e substancia com alergia do paciente (-> bloqueada).
    veredito_c1, violacoes_c1 = _camada1(state)
    if veredito_c1 == "bloqueada":
        return {"veredito": "bloqueada", "violacoes": violacoes_c1}
    if veredito_c1 == "regenerar":
        return {"veredito": "regenerar", "violacoes": violacoes_c1}

    resposta = state.get("resposta_bruta", "")
    requer_aprovacao = bool(state.get("requer_aprovacao"))
    if state.get("paciente_id") and _RE_SUGESTAO_CONDUTA.search(resposta):
        requer_aprovacao = True

    return {"veredito": "aprovada", "violacoes": [], "requer_aprovacao": requer_aprovacao}
