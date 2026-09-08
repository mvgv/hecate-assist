# CLAUDE.md

Guia de contexto para retomar o trabalho neste repositório. Para a especificação completa do produto, ver
[`../ESPECIFICACAO.md`](../ESPECIFICACAO.md), [`../PLANO.md`](../PLANO.md) e [`../docs/grafo_langgraph.md`](../docs/grafo_langgraph.md)
(esses três arquivos vivem um nível acima, em `iadt-langgraph/`, não dentro deste repo).

## O que é este projeto

MedAssist: assistente virtual médico (Tech Challenge Fase 3, IADT). Monolito Python com LangGraph
(fluxo de decisão), RAG sobre protocolos clínicos sintéticos (ChromaDB), consulta a base estruturada
de pacientes (SQLite), guardrails de segurança em 2 camadas, human-in-the-loop e logging de auditoria.
Roda em CPU via Docker Compose (app + Ollama + Caddy). Ver `README.md` para instruções de uso completas.

## Status atual (2026-09-07)

**Implementação completa e commitada.** Todas as 9 etapas do §16 da especificação foram feitas,
testadas e pushadas para `origin/main` (commit `1ffe5c0`). 38 testes passando, cobertura ≥80% em
`assistant/` e `guardrails.py`, `ruff check` limpo.

**Validado rodando de verdade** (não só testes unitários): `docker build` (imagem 3.19GB) e
`docker compose up app ollama` com os dois containers `healthy`, entrypoint rodando `seed-db`/`ingest`
dentro do container, app conversando com o Ollama pela rede interna do compose.

### Pendência para amanhã

A máquina de dev ficou sem espaço em disco no C: (ver seção "Gotchas" abaixo) bem no momento em que eu
tinha acabado de corrigir um bug de roteamento (`routing.py`/`graph.py` — erro na triagem ambígua caindo
em `resposta_recusa` em vez de `resposta_segura`, ver `docs/desvios.md` item 6). Essa correção **já foi
commitada e pushada**, mas o rebuild+redeploy da imagem Docker com ela **não foi revalidado** porque o
Docker Desktop travou por falta de espaço logo depois de eu confirmar a correção nos testes locais
(`pytest tests/test_graph.py` — 10/10 passando, incluindo o novo teste de regressão
`test_llm_indisponivel_na_triagem_ambigua_cai_em_resposta_segura`).

**Próximo passo:** depois que o espaço em disco estiver resolvido:
```bash
cd hecate-assist
docker compose up -d --build app ollama
docker compose ps                       # esperar os dois "healthy"
docker exec hecate-assist-app-1 medassist ask "qual o protocolo de sepse?"
# esperado: como nao ha modelo "medassist" registrado no ollama, deve cair
# em resposta_segura (mensagem "Motivo: triagem: ...") e NAO na recusa de
# "fora de escopo" - essa e a correcao que precisa ser reconfirmada.
```

Depois disso, falta opcionalmente: `docker compose --profile full up` (sobe também `model-init` e
`caddy` — requer um GGUF fine-tuned em `./models/`, que não existe ainda pois o fine-tuning real no
Colab não foi executado, é só artefato/script por design — ver §13 da especificação).

## Comandos úteis

```bash
pip install -e ".[dev]"          # setup local
medassist seed-db                # popula SQLite (idempotente)
medassist ingest                 # indexa protocolos no ChromaDB
pytest -q --cov=medassist        # roda testes (provider "fake", sem Ollama)
ruff check src tests
streamlit run src/medassist/ui/app_streamlit.py
docker compose up app ollama     # sobe local (compose = ambiente de referência)
```

## Arquitetura (resumo — detalhe completo em `docs/grafo_langgraph.md`)

`src/medassist/assistant/graph.py` monta o grafo: `triagem → [contexto_paciente → verificar_exames] →
recuperar_protocolos → gerar_resposta → guardrails → [aprovacao_humana] → emitir_alertas →
formatar_resposta`. Todo nó em `nodes.py` é decorado com `@auditado` (`logging_setup.py`), que loga em
JSON (stdout + `logs/audit_YYYYMMDD.jsonl`) e implementa o no-op quando `state["erro"]` já está setado
(exceto `resposta_segura`/`resposta_recusa`, que usam `@auditado(sempre_executa=True)` pois são
justamente os nós que consomem o erro).

`llm/fake.py` é o provider default (determinístico, usado em testes e no CI) — 4 gatilhos por
palavra-chave documentados em §8.2 da especificação. `llm/ollama_provider.py` é o provider real.

## Gotchas descobertos nesta sessão (não óbvios pelo código)

- **pip com SSL corporativo/MITM**: `pip install` puro falha com `CERTIFICATE_VERIFY_FAILED`. Usar
  `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host
  pypi.python.org ...`.
- **`sentence-transformers` puxa `torch` com CUDA por padrão** (~5GB desnecessários numa imagem
  CPU-only). O `Dockerfile` já instala a wheel CPU-only do torch antes (`--index-url
  https://download.pytorch.org/whl/cpu`) — não remover essa linha.
- **`pip install .` (não-editável) não empacota `schema.sql` sem `[tool.setuptools.package-data]`** no
  `pyproject.toml` — já corrigido, mas é fácil quebrar de novo se adicionar outro arquivo não-`.py`
  lido via `Path(__file__).parent / "..."` sem declarar como package-data.
- **Chroma usa distância L2 por padrão, não cosseno** — a collection é criada com
  `metadata={"hnsw:space": "cosine"}` em `rag/ingest.py`; sem isso os scores do retriever ficam
  incorretos frente a `MEDASSIST_RAG_MIN_SCORE`.
- **`interrupt()` do LangGraph levanta `GraphBubbleUp`** — o decorator `@auditado` tem que deixar essa
  exceção propagar (`except GraphBubbleUp: raise` antes do `except Exception` genérico), senão o
  human-in-the-loop quebra silenciosamente virando `state["erro"]`.
- **Máquina de dev com pouco espaço em C:**: Docker Desktop trava/crasha repetidamente quando o C:
  enche. Os dois maiores consumidores encontrados: `AppData\Local\NVIDIA\DXCache` (~35GB, cache de
  shader, seguro apagar) e `AppData\Local\Docker\wsl\disk\docker_data.vhdx` (~33GB — mover via Docker
  Desktop Settings → Resources → Advanced → Disk image location; a primeira tentativa de mover não
  "pegou" de verdade, confirmar que o vhdx antigo em C: realmente sumiu depois do Apply & Restart).
- Todos os desvios de implementação (correções necessárias para o código rodar) estão documentados
  com justificativa em `docs/desvios.md` — ler antes de "corrigir" algo que já foi corrigido de propósito.
