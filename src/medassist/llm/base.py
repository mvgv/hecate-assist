from typing import Protocol


class LLMIndisponivelError(Exception):
    """Levantada quando o provider de LLM nao consegue responder (ex.: Ollama fora do ar)."""


class LLMProvider(Protocol):
    def gerar(self, system: str, mensagens: list[dict], contexto: str = "") -> str: ...


def get_llm(aux: bool = False) -> LLMProvider:
    """Retorna o provider de LLM.

    `aux=True` seleciona o modelo auxiliar de proposito geral (`settings.model_aux`),
    usado na triagem (classificacao). `aux=False` (default) usa o modelo principal
    (`settings.model`, o fine-tunado). Sem efeito no provider "fake".
    """
    from medassist.config import get_settings

    settings = get_settings()
    if settings.llm_provider == "ollama":
        from medassist.llm.ollama_provider import OllamaProvider

        if aux:
            return OllamaProvider(
                model=settings.model_aux,
                num_ctx=settings.ollama_aux_num_ctx,
                num_predict=settings.ollama_aux_num_predict,
                num_gpu=settings.ollama_aux_num_gpu,
            )
        return OllamaProvider()

    from medassist.llm.fake import FakeLLM

    return FakeLLM()
