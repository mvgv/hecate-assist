from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from medassist.config import get_settings
from medassist.llm.base import LLMIndisponivelError


class OllamaProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self._chat = ChatOllama(
            model=settings.model,
            base_url=settings.ollama_base_url,
            temperature=0.2,
            num_ctx=4096,
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
