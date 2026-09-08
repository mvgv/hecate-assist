# CLAUDE.md

Guia de contexto para retomar o trabalho neste repositório. Para a especificação completa do produto, ver
[`../ESPECIFICACAO.md`](../ESPECIFICACAO.md), [`../PLANO.md`](../PLANO.md) e [`../docs/grafo_langgraph.md`](../docs/grafo_langgraph.md)
(esses três arquivos vivem um nível acima, em `iadt-langgraph/`, não dentro deste repo).

## O que é este projeto

MedAssist: assistente virtual médico (Tech Challenge Fase 3, IADT). Monolito Python com LangGraph
(fluxo de decisão), RAG sobre protocolos clínicos sintéticos (ChromaDB), consulta a base estruturada
de pacientes (SQLite), guardrails de segurança em 2 camadas, human-in-the-loop e logging de auditoria.
Roda em CPU via Docker Compose (app + Ollama + Caddy). Ver `README.md` para instruções de uso completas.

## Status atual (2026-09-08)

**Implementação completa e commitada.** Todas as 9 etapas do §16 da especificação foram feitas,
testadas e pushadas para `origin/main` (commit `1ffe5c0`). 38 testes passando, cobertura ≥80% em
`assistant/` e `guardrails.py`, `ruff check` limpo.

**Validado rodando de verdade** (não só testes unitários): `docker build` e
`docker compose up app ollama` com os dois containers `healthy`, entrypoint rodando `seed-db`/`ingest`
dentro do container, app conversando com o Ollama pela rede interna do compose.

### Correção de roteamento — REVALIDADA (2026-09-08)

Bug de roteamento (`routing.py`/`graph.py` — erro na triagem ambígua caindo em `resposta_recusa` em vez
de `resposta_segura`, ver `docs/desvios.md` item 6) estava corrigido no código mas o rebuild da imagem
Docker não tinha sido revalidado (Docker Desktop havia travado por falta de espaço em disco no C:).

**Resolvido:** disco com espaço, `docker compose up -d --build app ollama` refeito, os dois containers
subiram `healthy`, e o teste de aceitação passou:
```
docker exec hecate-assist-app-1 medassist ask "qual o protocolo de sepse?"
# -> triagem falha ("Ollama indisponivel: model 'medassist' not found")
# -> roteia para resposta_segura (NAO resposta_recusa)
# -> resposta comeca com "Motivo: triagem: ..."  ✓ comportamento esperado
```
`pytest tests/test_graph.py` — 10/10 passando, incluindo a regressão
`test_llm_indisponivel_na_triagem_ambigua_cai_em_resposta_segura`.

### Pendências para amanhã — rodar o "projeto completo"

Duas frentes, escolher por objetivo. Descrição detalhada estava na conversa; resumo aqui.

**Nível 1 — stack `--profile full` com LLM real, SEM fine-tuning (viável já, ~15 min).**
`docker compose --profile full up` sobe `model-init` (roda `ollama create medassist -f
/deploy/Modelfile`) e `caddy` (proxy + basic auth, portas 80/443). Bloqueios e passos:
1. `deploy/Modelfile` linha `FROM /models/medassist-q4_k_m.gguf` → trocar por `FROM llama3.2:3b`
   (stub com modelo base; o próprio arquivo comenta essa opção). `SYSTEM`/`PARAMETER` ficam.
2. Pré-baixar o base p/ `model-init` não falhar:
   `docker compose up -d ollama && docker compose exec ollama ollama pull llama3.2:3b`
3. `.env`: `CADDY_BASIC_AUTH_HASH` está vazio. Gerar:
   `docker run --rm caddy:2 caddy hash-password --plaintext 'senha'` → colar no `.env`.
4. `docker compose --profile full up -d --build`; esperar `model-init` sair 0, `ollama`/`app`
   `healthy`, `caddy` `Up`. Portas 80/443 do host precisam estar livres.
5. Smoke: `docker compose exec ollama ollama run medassist "Qual a conduta inicial na sepse?"`;
   `docker exec hecate-assist-app-1 medassist ask "qual o protocolo de sepse?"` (agora deve GERAR
   resposta de verdade, passar por `gerar_resposta`→`guardrails`, não cair em `resposta_segura`);
   UI em `http://localhost` (login `medico` / senha do passo 3).

**Nível 2 — projeto completo conforme §13 (fine-tuning real).** Exige GPU T4 no Colab (não dá
local). Segue `../docs/finetuning.md`:
`medassist download-data` + `medassist build-dataset` → revisar 20 exemplos → rodar
`notebooks/02_finetune_colab.ipynb` (QLoRA Llama-3.2-3B, ~1-2h) → `save_pretrained_gguf` q4_k_m →
subir ao HF Hub (repo privado, tag `v1`) → `hf download ... --local-dir models/` e renomear p/
`models/medassist-q4_k_m.gguf` → `finetune.evaluate` base vs tuned → `docs/avaliacao.md` →
`docker compose --profile full up -d` (agora `model-init` usa o GGUF real, Modelfile sem edição) →
validar fluxo na UI + guardar curvas de loss p/ o relatório.

**Nível 2.a — datasets externos do enunciado (MedQuAD + PubMedQA) NÃO estão integrados.**
Por desenho (§5.5) o RAG usa só os protocolos sintéticos; os datasets HF eram previstos apenas
como fatia do dataset de fine-tuning (`docs/finetuning.md` §2: MedQuAD ~20% "conhecimento geral +
robustez"; PubMedQA opcional). Estado real hoje:
- `data/raw/` só tem `.gitkeep` — `medassist download-data` nunca rodou.
- `download.py` cobre só MedQuAD e via clone do GitHub `abachaa/MedQuAD` (não o dataset HF).
  PubMedQA não tem nenhum código de download.
- `build_dataset.py` lê só `data/synthetic/` — **não** mistura MedQuAD. O notebook do Colab faz
  `load_dataset("json", data_files="train.jsonl")`, ou seja espera o `train.jsonl` já com a fatia
  MedQuAD dentro. Ninguém produz essa fatia hoje.
Para fechar: (1) script de download real dos dois via `datasets` do HF; (2) estender
`build_dataset.py` para amostrar 500–1000 pares de MedQuAD, formatar como chat e misturar antes do
split 95/5 — ou fazer isso à mão numa célula do notebook; (3) registrar a decisão (usar em inglês
vs. traduzir amostra) no relatório.

Recomendação: fazer o Nível 1 primeiro (stack completo ponta a ponta com LLM real); Nível 2 é
entrega separada.

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
  **Resolvido em 2026-09-08:** disco de imagem do Docker movido para um drive com espaço; daemon
  (Server 29.7.2) rodando estável, build+compose voltaram a funcionar.
- Todos os desvios de implementação (correções necessárias para o código rodar) estão documentados
  com justificativa em `docs/desvios.md` — ler antes de "corrigir" algo que já foi corrigido de propósito.
