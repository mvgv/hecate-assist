from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from medassist.config import get_settings
from medassist.llm.base import LLMIndisponivelError


class OllamaProvider:
    def __init__(
        self,
        model: str | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
        num_gpu: int | None = None,
    ) -> None:
        settings = get_settings()
        extra: dict = {}
        if num_gpu is not None:
            # num_gpu=0 forca a inferencia na CPU (usado pelo modelo auxiliar da
            # triagem, para nao disputar VRAM com o 8B). None = offload automatico.
            extra["num_gpu"] = num_gpu
        self._chat = ChatOllama(
            model=model or settings.model,
            base_url=settings.ollama_base_url,
            temperature=0.2,
            num_ctx=num_ctx or settings.ollama_num_ctx,
            num_predict=num_predict or settings.ollama_num_predict,
            client_kwargs={"timeout": settings.ollama_timeout},
            **extra,
        )

    def gerar(self, system: str, mensagens: list[dict], contexto: str = "") -> str:
        conteudo_sistema = f"{system}\n\n{contexto}" if contexto.strip() else system

        lc_mensagens = [SystemMessage(content=conteudo_sistema)]
        for msg in mensagens:
            if msg.get("role") == "user":
                lc_mensagens.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                lc_mensagens.append(AIMessage(content=msg.get("content", "")))

        try:
            resposta = self._chat.invoke(lc_mensagens)
        except Exception as exc:
            raise LLMIndisponivelError(f"Ollama indisponivel: {exc}") from exc

        return resposta.content
