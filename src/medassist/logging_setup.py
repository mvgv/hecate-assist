import logging
import sys
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import structlog
from langgraph.errors import GraphBubbleUp

from medassist.config import get_settings
from medassist.data.anonymize import anonimizar

_CONFIGURED = False

# Logger dedicado da trilha de auditoria. Recebe o FileHandler do audit_*.jsonl
# e NAO propaga para o root -> so eventos de dominio (via @auditado / get_logger)
# vao para o arquivo. Sem isso, o FileHandler no root captura tudo que qualquer
# lib loga em INFO (httpx faz 1 linha por request) e a auditoria fica afogada.
_AUDIT_LOGGER_NAME = "medassist.audit"

# Libs cujo INFO e ruido puro para este projeto.
_LIBS_RUIDOSAS = (
    "httpx",
    "httpcore",
    "urllib3",
    "sentence_transformers",
    "transformers",
    "huggingface_hub",
    "chromadb",
    "filelock",
)


def _mask_pii(_logger, _method_name, event_dict: dict[str, Any]) -> dict[str, Any]:
    for chave, valor in list(event_dict.items()):
        if isinstance(valor, str):
            limpo, _tipos = anonimizar(valor)
            event_dict[chave] = limpo
    return event_dict


def configurar_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    arquivo_log = log_dir / f"audit_{time.strftime('%Y%m%d')}.jsonl"

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _mask_pii,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )

    # Trilha de auditoria: JSON no arquivo + JSON no stdout (§ logging e auditoria).
    file_handler = logging.FileHandler(arquivo_log, encoding="utf-8")
    file_handler.setFormatter(json_formatter)
    audit_stream = logging.StreamHandler(sys.stdout)
    audit_stream.setFormatter(json_formatter)

    audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    audit_logger.setLevel(logging.INFO)
    audit_logger.handlers = [file_handler, audit_stream]
    audit_logger.propagate = False

    # Root: so stdout, texto plano, para avisos/erros operacionais do app e libs.
    root_stream = logging.StreamHandler(sys.stdout)
    root_stream.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.handlers = [root_stream]

    for lib in _LIBS_RUIDOSAS:
        logging.getLogger(lib).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(**contexto: Any):
    configurar_logging()
    return structlog.get_logger(_AUDIT_LOGGER_NAME).bind(**contexto)


def auditado(fn: Callable[[dict], dict] | None = None, *, sempre_executa: bool = False):
    """Decorator transversal: loga no_iniciado/no_concluido/no_falhou/no_pulado.

    Nenhum no implementa logging proprio - tudo passa por aqui. Por padrao, se
    `state["erro"]` ja estiver preenchido por um no anterior, o no faz no-op
    (nao-op para arestas fixas - §9.4). `sempre_executa=True` e usado pelos
    nos terminais de fallback (`resposta_segura`, `resposta_recusa`), que sao
    justamente os responsaveis por consumir o erro e nunca podem ser pulados.
    """

    def decorador(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        @wraps(fn)
        def wrapper(state: dict) -> dict:
            log = get_logger(no=fn.__name__, thread_id=state.get("thread_id"))

            if state.get("erro") and not sempre_executa:
                log.info("no_pulado")
                return {}

            log.info("no_iniciado")
            t0 = time.perf_counter()
            try:
                delta = fn(state) or {}
                duracao_ms = int((time.perf_counter() - t0) * 1000)
                log.info("no_concluido", delta_keys=list(delta.keys()), ms=duracao_ms)
                return delta
            except GraphBubbleUp:
                # interrupt()/Command do LangGraph usam excecao interna para
                # pausar o grafo - precisa propagar, nao e uma falha do no.
                raise
            except Exception as exc:  # noqa: BLE001 - captura ampla de proposito (§11)
                log.error("no_falhou", erro=str(exc))
                return {"erro": f"{fn.__name__}: {exc}"}

        return wrapper

    if fn is not None:
        return decorador(fn)
    return decorador
