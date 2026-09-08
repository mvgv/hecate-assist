"""FakeLLM - provider deterministico usado em testes e como default (§8.2)."""
import re

_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


class FakeLLM:
    def gerar(self, system: str, mensagens: list[dict], contexto: str = "") -> str:
        if "AVALIE" in system:
            return '{"aprovada": true, "violacoes": []}'

        ultimo_turno = ""
        for msg in reversed(mensagens):
            if msg.get("role") == "user":
                ultimo_turno = msg.get("content", "")
                break

        if "__forcar_prescricao__" in ultimo_turno:
            return "Prescrever amoxicilina 500 mg VO 8/8h por 7 dias."

        if "__forcar_alergia__" in ultimo_turno:
            return "Sugere-se penicilina cristalina conforme [PROT-007 §3]."

        if contexto.strip():
            match = _BRACKET_RE.search(contexto)
            citacao = match.group(1) if match else "protocolo institucional"
            return (
                f"Com base no protocolo institucional [{citacao}], a conduta sugerida é "
                "seguir as diretrizes descritas na seção indicada. "
                "Recomenda-se validação pelo médico responsável."
            )

        return (
            "Não há protocolo interno aplicável. Com base em conhecimento geral, "
            "avalie clinicamente o quadro apresentado. "
            "Recomenda-se validação pelo médico responsável."
        )
