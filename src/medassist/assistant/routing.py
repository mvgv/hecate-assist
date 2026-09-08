from medassist.config import get_settings


def rota_triagem(state: dict) -> str:
    if state.get("erro"):
        return "erro"
    return state.get("intencao", "fora_escopo")


def rota_guardrails(state: dict) -> str:
    if state.get("erro"):
        return "bloqueada"

    settings = get_settings()
    veredito = state.get("veredito")
    tentativas = state.get("tentativas", 0)

    if veredito == "regenerar" and tentativas < settings.max_tentativas:
        return "regenerar"
    if veredito == "bloqueada" or (veredito == "regenerar" and tentativas >= settings.max_tentativas):
        return "bloqueada"
    if veredito == "aprovada" and state.get("requer_aprovacao"):
        return "aprovar"
    return "aprovada"


def rota_aprovacao(state: dict) -> str:
    if state.get("erro"):
        return "rejeitado"
    aprovacao = state.get("aprovacao") or {}
    return "aprovado" if aprovacao.get("aprovado") else "rejeitado"
