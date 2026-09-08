from typing import Protocol


class LLMIndisponivelError(Exception):
    """Levantada quando o provider de LLM nao consegue responder (ex.: Ollama fora do ar)."""


class LLMProvider(Protocol):
    def gerar(self, system: str, mensagens: list[dict], contexto: str = "") -> str: ...


def get_llm() -> LLMProvider:
    from medassist.config import get_settings

    settings = get_settings()
    if settings.llm_provider == "ollama":
        from medassist.llm.ollama_provider import OllamaProvider

        return OllamaProvider()

    from medassist.llm.fake import FakeLLM

    return FakeLLM()
