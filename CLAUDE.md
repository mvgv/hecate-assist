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

**v2 rodada (2026-09-09) — GGUF gerado, TESTADA no Docker full, FALHOU de novo.** `docker compose
--profile full` subiu OK, `model-init` criou `medassist`, `ollama show` correto. Mas: `medassist ask`
travou ~19 min numa chamada de triagem (geração sem EOS); testes com `num_predict` capado mostram
`done_reason: length` + loop. Saída degenerada: *"Estes recursos abordam o diagnóstico ou gestão da
sepse… - MedlinePlus Enciclopédia: Sepse, 1 - …"* repetido.

**Diagnóstico da v2 (2026-09-09).** O `train_v2.jsonl` (216 ex., em `../docs/train_v2.jsonl`) É a
estrutura desenhada (116 PT-BR + 100 MedQuAD EN), mas a **fatia MedQuAD EN é de qualidade ruim**:
- **29/100** são "These resources address the diagnosis or management of X: - Genetic Testing
  Registry… - MedlinePlus Encyclopedia…" (lista de links, zero conduta).
- **34/100** começam repetindo a pergunta ("How might lipedema be treated? Treatment options…").
O modelo aprendeu esse registro (46% do dataset, 2 épocas) e **reproduz em PT-BR** quando o system
prompt pede PT-BR. Idioma não era o problema — o **conteúdo** do MedQuAD é. Traduzir bem não
resolveria: lista de links traduzida continua lista de links.

**v3 (2026-09-09) — notebook + dataset prontos, NÃO rodado ainda.** Decisão: **treinar só nos ~116
PT-BR limpos** (protocolo + FAQ), sem MedQuAD (`N_MEDQUAD_EN=0` default). Guia §1: fine-tune ensina
comportamento, RAG fornece fatos — 116 exemplos limpos bastam. `docs/train_v3.jsonl` gerado por
`scripts/gen_dataset_v3.py` (116 ex., 90% citam) — **subir para `MyDrive/medassist/train_v3.jsonl`**
e rodar com `REBUILD=False` (célula 3 só carrega). 3 épocas (dataset pequeno), `train_on_responses_only`,
sanity check obrigatório antes do export.

**Performance no CPU (2026-09-09).** A trava de 19 min foi geração sem EOS + sem teto. Adicionados:
`OllamaProvider` agora passa `num_predict` (768) e `client_kwargs={"timeout": 240}` — geração
descontrolada estoura em ~1 min e cai em `resposta_segura` em vez de travar. `deploy/Modelfile` tem
`PARAMETER num_predict 768`. Configuráveis via `MEDASSIST_OLLAMA_NUM_PREDICT` / `_OLLAMA_TIMEOUT` /
`_OLLAMA_NUM_CTX`. Ao iterar no fine-tune: testar o modelo direto (`curl .../api/chat` com
`num_predict` capado) ANTES do grafo inteiro; `MEDASSIST_MAX_TENTATIVAS=1` corta o loop de
regeneração. `OLLAMA_KEEP_ALIVE=-1` já mantém o modelo quente. Um modelo sadio gera ~12 tok/s
(≈20-40 s/resposta); o grafo faz até 5 chamadas por `ask`.

**Inferência na GPU (2026-09-09).** Host tem RTX 4060 Ti 8 GB (driver 616.64). Fine-tuning continua
no Colab; só o serving vai pra GPU. **Nenhuma mudança de código** — o `ollama_provider` só fala HTTP.
`docker-compose.gpu.yml` é um override que reserva a GPU pro serviço `ollama`
(`make compose-up-gpu`, requer Docker Desktop com backend WSL2). O 3B Q4_K_M ocupa ~2 GB de VRAM e
gera ~80-120 tok/s (vs. ~12 no CPU) → o `ask` inteiro em segundos. Conferir:
`docker exec hecate-assist-ollama-1 ollama ps` → coluna PROCESSOR = `100% GPU`.

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

### Pendências — RODAR o fine-tuning v3 e fechar o Nível 2

**Onde paramos (2026-09-09):** notebook v3 + `docs/train_v3.jsonl` prontos e commitados, **não
rodado**. Infra Docker `--profile full` 100% validada nesta sessão (build, `model-init`, `ollama
show`, grafo). O que quebra é só o **modelo** — v1 e v2 degeneraram (ver Status).

**Passo 1 — preparar o Drive.** Subir para `MyDrive/medassist/`:
- `docs/train_v3.jsonl` → **`train_v3.jsonl`** (é o dataset; a célula 3 com `REBUILD=False` só carrega)
- `data/processed/train.jsonl` e `data/processed/val.jsonl` (train.jsonl é fallback se não houver
  `train_v3.jsonl`; val.jsonl é usado no `eval_dataset`)

**Passo 2 — rodar o notebook v3** (`notebooks/02_finetune_colab.ipynb`), runtime GPU:
1. Células 1-2 (install, mount).
2. Célula 3: deve imprimir `cache -> 116 exemplos de .../train_v3.jsonl`. Se imprimir "nucleo
   limpo / expansao prot" é porque não achou o `train_v3.jsonl` no Drive (subiu?).
3. Célula 4 (train): 3 épocas, `train_on_responses_only`, `eval_dataset`. Olhar a **eval loss** por
   época — se subir na 3ª, `EPOCHS=2`.
4. Célula 4b (sanity check): 3 respostas + `cita [PROT-...]` / `parou (EOS)`.
   **Só exportar se as 3 citarem e pararem sozinhas.**
5. Células de export → `medassist-q4_k_m.gguf` no Drive.

**Passo 3 — teste local** (infra já validada nesta sessão):
baixar o GGUF para `models/medassist-q4_k_m.gguf` (gitignore) → `docker compose --profile full up -d
--build ollama model-init app` → `ollama create` roda no `model-init`.
- **Antes do grafo**, testar o modelo cru:
  `docker exec hecate-assist-app-1 sh -c 'curl -s http://ollama:11434/api/chat -d "{\"model\":\"medassist\",\"stream\":false,\"options\":{\"num_predict\":300},\"messages\":[{\"role\":\"user\",\"content\":\"Qual a conduta inicial na sepse?\"}]}"'`
  → tem que vir `done_reason: "stop"` (não `"length"`), citar `[PROT-...]`, sem loop.
- Só então: `docker exec hecate-assist-app-1 medassist ask "qual o protocolo de sepse?"` deve
  **gerar** (não cair em `resposta_segura`). Opcional p/ acelerar: `-e MEDASSIST_MAX_TENTATIVAS=1`.
- `python -m medassist.finetune.evaluate` base vs. tuned → `docs/avaliacao.md`.

### Composição do dataset de fine-tuning v3 (2026-09-09) — só PT-BR limpo

`build_dataset.py` **não** foi alterado. v1 (opus-mt) e v2 (MedQuAD EN cru) descartadas — ver Status.
A v3 é montada na **célula 3** (ou por `scripts/gen_dataset_v3.py`, que gera o `docs/train_v3.jsonl`
idêntico sem Colab):
- **Núcleo limpo:** `data/processed/train.jsonl` **inteiro** (68 ex.: 12 protocolo + 56 FAQ), ~90%
  citam `[PROT-NNN §x]`, PT-BR clínico.
- **Expansão dos protocolos:** as 12 entradas `"Explique o protocolo ..."`, 4 fraseados cada (~48 ex.).
- **Total 116**, fecho PT-BR rotacionado entre 4 fraseados.
- **MedQuAD:** `N_MEDQUAD_EN = 0` por default. A célula 3 tem filtro `_medquad_ok` (rejeita listas
  "these resources address / MedlinePlus / Gene Review" e respostas que começam repetindo a
  pergunta — na fatia v2 isso descartaria 74/100). Só ligar depois que a v3 base passar, e mesmo
  assim é fatia de risco.
- **Ficam de fora:** opus-mt, PubMedQA, MedQuAD (default), exemplos de segurança (guardrails = grafo).
- Diverge da tabela de `docs/finetuning.md` §2 (40/25/20/15) — reconciliar no relatório: a v3 é
  ~59% FAQ+núcleo / ~41% expansão-protocolo, 0% MedQuAD, 0% segurança. Racional: guia §1 — o
  fine-tune ensina comportamento (formato/citação/tom/parada), o RAG traz os fatos.
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
make compose-up-full             # stack completa: ollama + model-init (cria `medassist`) + app
make compose-up-gpu              # idem, Ollama na GPU NVIDIA (docker-compose.gpu.yml)
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

- **v2/v3 não traduzem nada** — a célula de dataset não baixa opus-mt nem precisa de GPU; as gotchas
  de tradução da v1 (`AutoModelForSeq2SeqLM`, exige GPU, batches fp16) não se aplicam mais. A célula 2
  não instala `sacremoses`. Na v3 a célula de dataset nem baixa nada por default (`N_MEDQUAD_EN=0`).
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
  do treino, é retreinar (o notebook não tem mais célula de recuperação de adaptadores).
- **Crash na célula de export = OOM de RAM de sistema** no merge 16-bit (Colab free ~12,7 GB), não
  disco nem VRAM. Resolvido com Colab Pro (High-RAM); a célula de export passa `maximum_memory_usage=0.6`.
- **`save_pretrained_gguf(dir, ...)` grava em `dir + "_gguf/"`** com nome fixo
  `llama-3.2-3b-instruct.Q4_K_M.gguf` (ignora o nome que você passou). A célula de export faz
  `glob('/content/**/*.gguf')` e pega o maior arquivo, depois copia só ele (~2 GB) para o Drive.
