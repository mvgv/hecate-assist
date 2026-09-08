"""Anonimizacao de PII via regex (sem Presidio - dependencia pesada demais para o runtime)."""
import re

_PADROES: list[tuple[str, str, re.Pattern]] = [
    ("cpf", "[CPF]", re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")),
    ("crm", "[CRM]", re.compile(r"CRM[-/ ]?[A-Z]{2}?\s?\d{4,6}")),
    ("email", "[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("data", "[DATA]", re.compile(r"\d{2}/\d{2}/\d{4}")),
    ("telefone", "[TELEFONE]", re.compile(r"(\(?\d{2}\)?\s?)?9?\d{4}-?\d{4}")),
    (
        "nome",
        r"\1 [NOME]",
        re.compile(r"(paciente|Dr\.|Dra\.)\s+[A-ZÀ-Ü][a-zà-ü]+(?:\s[A-ZÀ-Ü][a-zà-ü]+)*"),
    ),
]


def anonimizar(texto: str) -> tuple[str, list[str]]:
    """Retorna (texto_limpo, tipos_de_pii_encontrados)."""
    limpo = texto
    tipos: list[str] = []
    for tipo, substituicao, padrao in _PADROES:
        if padrao.search(limpo):
            tipos.append(tipo)
            limpo = padrao.sub(substituicao, limpo)
    return limpo, tipos
