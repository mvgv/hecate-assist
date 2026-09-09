# CLAUDE.md

Guia de contexto para retomar o trabalho neste repositório. Para a especificação completa do produto, ver
[`../ESPECIFICACAO.md`](../ESPECIFICACAO.md), [`../PLANO.md`](../PLANO.md) e [`../docs/grafo_langgraph.md`](../docs/grafo_langgraph.md)
(esses três arquivos vivem um nível acima, em `iadt-langgraph/`, não dentro deste repo).

## O que é este projeto

MedAssist: assistente virtual médico (Tech Challenge Fase 3, IADT). Monolito Python com LangGraph
(fluxo de decisão), RAG sobre protocolos clínicos sintéticos (ChromaDB), consulta a base estruturada
de pacientes (SQLite), guardrails de segurança em 2 camadas, human-in-the-loop e logging de auditoria.
Roda em CPU via Docker Compose (app + Ollama + Caddy). Ver `README.md` para instruções de uso completas.

## Status atual (2026-09-09)

**Implementação completa e commitada.** Todas as 9 etapas do §16 da especificação foram feitas,
testadas e pushadas para `origin/main` (commit `1ffe5c0`). 38 testes passando, cobertura ≥80% em
`assistant/` e `guardrails.py`, `ruff check` limpo.

**Fine-tuning v1 (2026-09-09) — GGUF gerado, mas o modelo SAIU RUIM.**
Rodou `notebooks/02_finetune_colab.ipynb` inteiro no Colab Pro (GPU L4). `medassist-q4_k_m.gguf`
(~2 GB, QLoRA Llama-3.2-3B-Instruct) em `Drive/MyDrive/medassist/` + `models/medassist-q4_k_m.gguf`
local (gitignore — não versionado). Smoke test local **FALHOU**: geração degenera em loop, sem
citação `[PROT-...]`, sem emitir EOS. Infra de serving OK (`docker compose --profile full`, template
e `stop` corretos em `ollama show`) → o problema é o fine-tune.

**Diagnóstico do dataset v1 (2026-09-09) — confirmado.** Analisado o `train_mixed.jsonl` baixado
(1048 ex., em `../docs/train_mixed (1).jsonl`). Causas, em ordem de peso:
1. **Quase não ensina a citar:** `[DOC-ID §secao]` em só **48/1048 (4,6%)** — só a fatia de protocolo.
2. **Conteúdo fora de propósito:** boa parte do MedQuAD é lista de "recursos" (links MedlinePlus,
   fundações dos EUA), não apoio à decisão → modelo aprende a cuspir listas.
3. **Tradução opus-mt ruim** em texto médico: termos inventados, frases truncadas, gagueira →
   PT-BR de baixa fluência, e 2 épocas nisso viram loop.
4. Fecho homogêneo (127 respostas idênticas nos últimos 80 chars); cell 4 sem `train_on_responses_only`.
5. FAQs sintéticas **ausentes** (0 ex.) — era a melhor fonte de citação + tom.
O arquivo em si está íntegro (UTF-8, zero replacement chars).

**Notebook reescrito para v2 (2026-09-09) — pronto, NÃO rodado ainda.** Ver "Composição do dataset
v2" e "Pendências" abaixo. Decisão: dataset limpo (protocolo + FAQ) + fatia minoritária de MedQuAD
**em inglês, sem tradução**.

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

### Pendências — RODAR o fine-tuning v2 e fechar o Nível 2

**Onde paramos (2026-09-09):** notebook v2 reescrito e commitado, **ainda não rodado**. Infra local
100% OK (Docker `--profile full`, `ollama create`, grafo wired) — o que quebrou na v1 foi só o
**modelo/dataset**. Amanhã: rodar o notebook v2 no Colab.

**Passo 1 — preparar o Drive.** Copiar `data/processed/train.jsonl` **e** `data/processed/val.jsonl`
para `MyDrive/medassist/` (a célula de mount agora usa os dois). O `train_mixed.jsonl` da v1 pode
ficar — a v2 grava um cache novo (`train_v2.jsonl`) e não toca nele.

**Passo 2 — rodar o notebook v2** (`notebooks/02_finetune_colab.ipynb`), runtime GPU:
1. Células 1-2 (install, mount). Não precisa mais de GPU para a célula de dataset (sem tradução).
2. Célula 3 (dataset v2): confere no output que **PT-BR ≥ 55%** e MedQuAD EN ≈ 100. `REBUILD=True`
   se quiser refazer o `train_v2.jsonl`.
3. Célula 4 (train): já tem `train_on_responses_only`, `eval_dataset` (val) e `eval_strategy=epoch`.
   Olhar a **eval loss** ao fim de cada época — se subir na 2ª, baixar `EPOCHS` para 1 ou `LR` p/ 1e-4.
4. Célula 4b (sanity check — NOVA): gera 3 respostas e imprime `cita [PROT-...]` / `parou (EOS)`.
   **Só seguir para o export se as 3 citarem e pararem sozinhas.** Se degenerar → o problema ainda
   é o dataset, não hiperparâmetro (guia §7 item 4).
5. Células de export (5) → `medassist-q4_k_m.gguf` no Drive.

**Passo 3 — export + teste local** (infra já validada):
baixar o GGUF para `models/medassist-q4_k_m.gguf` (gitignore — não versionar/pushar) →
`docker compose --profile full up -d --build ollama model-init app` (sem `caddy` → dispensa
`CADDY_BASIC_AUTH_HASH`) → `ollama create` → smoke test. Depois `medassist ask "qual o protocolo de
sepse?"` deve **gerar** resposta (não cair em `resposta_segura`).
`python -m medassist.finetune.evaluate` base vs. tuned → `docs/avaliacao.md`.

### Composição do dataset de fine-tuning v2 (2026-09-09) — só dados limpos

`build_dataset.py` **não** foi alterado; a mistura é feita na **célula 3 do notebook**. A v1
(traduzida com opus-mt) foi descartada — ver diagnóstico no Status acima. A v2:
- **Núcleo limpo:** `data/processed/train.jsonl` **inteiro** (68 ex.: 12 protocolo + 56 FAQ), 100%
  citam `[PROT-NNN §x]`, PT-BR clínico. É o gradiente de estilo.
- **Expansão dos protocolos:** as 12 entradas `"Explique o protocolo ..."`, 4 fraseados cada
  (~48 ex.) — reforço do formato de citação.
- **MedQuAD (amostra) EN, SEM tradução:** `N_MEDQUAD_EN` (default **100**), sob um `system` **em
  inglês próprio** e **sem exigir citação** — dá amplitude de conhecimento sem competir com o
  contrato de formato PT-BR. Guia `../docs/finetuning.md` §2, plano A ("usar como está").
  Subir esse número afrouxa o sinal PT-BR/citação; a célula avisa se PT-BR < 55%.
- **Fecho PT-BR rotacionado** entre 4 fraseados (era 1 frase idêntica em 100% → pouca diversidade).
- **Ficam de fora:** tradução opus-mt, PubMedQA, exemplos de segurança (guardrails = grafo).
- Cache: `Drive/MyDrive/medassist/train_v2.jsonl` (`REBUILD=True` refaz). **PubMedQA e a tradução
  saíram** — reconciliar a tabela de `docs/finetuning.md` §2 (40/25/20/15) no relatório: a
  composição real com o default (216 ex.): 68 núcleo limpo (31%) + 48 expansão-protocolo (22%) +
  100 MedQuAD-EN (46%) → PT-BR 54%, segurança 0%.
- `data/processed/{train,val}.jsonl` gerados por `medassist build-dataset` (72 ex.: 68 treino / 4 val).

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

### Gotchas do Colab / fine-tuning (sessão 2026-09-09)

- **v2 não traduz nada** — a célula de dataset não baixa opus-mt nem precisa de GPU; as gotchas de
  tradução da v1 (`AutoModelForSeq2SeqLM`, exige GPU, batches fp16) não se aplicam mais. A célula 2
  não instala `sacremoses`.
- **`pip install git+transformers` quebra o pin do `unsloth`** (`transformers<=5.5.0`). A célula 1
  do notebook não instala o transformers do git — o `unsloth` resolve a versão compatível.
- **Esta versão do `SFTTrainer`/`unsloth` não aplica o chat template sozinho** — dá
  `RuntimeError: You must specify a formatting_func`. A célula 4 faz
  `get_chat_template(tokenizer, "llama-3.1")` + `dataset.map(...)` para uma coluna `text` e passa
  `dataset_text_field='text'` no `SFTConfig`. O `val_ds` passa pelo mesmo `_formatar`.
- **`train_on_responses_only`** (célula 4) precisa dos marcadores do template llama-3.1:
  `instruction_part='<|start_header_id|>user<|end_header_id|>'`,
  `response_part='<|start_header_id|>assistant<|end_header_id|>'`.
- **Célula 4b (sanity check)** roda logo após o treino, com o modelo ainda em memória
  (`FastLanguageModel.for_inference(modelo)`). Não recarrega nada do Drive — se o runtime caiu depois
  do treino, é retreinar (o notebook v2 não tem mais célula de recuperação de adaptadores).
- **Crash na célula de export = OOM de RAM de sistema** no merge 16-bit (Colab free ~12,7 GB), não
  disco nem VRAM. Resolvido com Colab Pro (High-RAM); a célula de export passa `maximum_memory_usage=0.6`.
- **`save_pretrained_gguf(dir, ...)` grava em `dir + "_gguf/"`** com nome fixo
  `llama-3.2-3b-instruct.Q4_K_M.gguf` (ignora o nome que você passou). A célula de export faz
  `glob('/content/**/*.gguf')` e pega o maior arquivo, depois copia só ele (~2 GB) para o Drive.
