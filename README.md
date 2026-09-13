# hecate-assist (MedAssist)

Assistente virtual médico para apoio à decisão clínica — terceira entrega do
Tech Challenge IADT. Monolito Python com **LangGraph** (fluxo de decisão),
**RAG** sobre protocolos institucionais sintéticos (ChromaDB), consulta a
base estruturada de pacientes (SQLite), guardrails de segurança,
human-in-the-loop e logging de auditoria. Roda em CPU via Docker Compose
(app + Ollama + Caddy).

> 📄 **[Relatório técnico](#relatório-técnico)** — decisões de engenharia (§A),
> decisões de modelo: fine-tuning e RAG (§B), avaliação (§C) e a comparação
> fine-tuned vs. base (§D). O restante deste README são as instruções de uso.

> Especificação completa: [`docs/especificacao.md`](docs/especificacao.md).
> Plano de implementação: [`docs/plano.md`](docs/plano.md).
> Design do grafo: [`docs/grafo_langgraph.md`](docs/grafo_langgraph.md).
> Desvios da especificação: [`docs/desvios.md`](docs/desvios.md).

## Arquitetura em uma imagem

```
Pergunta do médico + ID do paciente
        │
        ▼
   LangGraph: triagem → contexto do paciente (SQLite) → exames pendentes
              → RAG (protocolos) → LLM → guardrails (regras determinísticas)
              → [aprovação humana] → alertas → resposta com fontes citadas
        │                                    │
        ▼                                    ▼
   SQLite (prontuários)              ChromaDB (protocolos + citações)
```

Ver diagrama completo em [`docs/grafo_langgraph.md`](docs/grafo_langgraph.md).

## Setup local (desenvolvimento)

Requer Python 3.11+.

```bash
# 1. Instalar dependências (uv, se disponível, ou pip)
pip install -e ".[dev]"

# 2. Popular o banco de pacientes fictícios (idempotente)
medassist seed-db

# 3. Indexar protocolos e modelos de documento no ChromaDB
medassist ingest

# 4. Rodar os testes (provider "fake" — não requer Ollama nem GPU)
pytest -q --cov=medassist

# 5. Usar via CLI
medassist ask "qual o protocolo de sepse?"
medassist ask "qual a conduta para hipertensão?" --paciente P003 --thread demo1
medassist resume demo1 --aprovado --aprovador "Dr. Fulano"
medassist alerts

# 6. Ou via interface web (Streamlit)
streamlit run src/medassist/ui/app_streamlit.py
```

Todas as variáveis de configuração estão documentadas em
[`.env.example`](.env.example) (prefixo `MEDASSIST_`). Por padrão,
`MEDASSIST_LLM_PROVIDER=fake` — o sistema roda **sem Ollama** usando um
provider determinístico (é assim que os testes e o CI rodam). Para usar um
modelo real, defina `MEDASSIST_LLM_PROVIDER=ollama` com o Ollama acessível
em `OLLAMA_BASE_URL`.

## Testes

```bash
make test
# equivalente a: pytest -q --cov=medassist --cov-report=term-missing
```

Cobertura alvo: ≥ 80% em `assistant/` e `guardrails.py`. Cenários cobertos
(ver [`docs/grafo_langgraph.md` §6](docs/grafo_langgraph.md)): pergunta
geral com fontes, exame pendente, sugestão de tratamento com interrupt +
aprovação humana, prescrição direta (regenera), medicamento com alergia do
paciente (bloqueia), pergunta fora de escopo, RAG sem resultado, paciente
inexistente, LLM indisponível, anonimização de PII e idempotência de alertas.

## Dados sintéticos

`data/synthetic/` reúne as três fontes que o assistente conhece, todas geradas
de forma determinística (sem LLM) por
`python -m medassist.data.generate_synthetic` e commitadas no repositório:

| Fonte | Conteúdo |
|---|---|
| `protocolos/` | 25 protocolos clínicos (`PROT-001`…`PROT-025`), Markdown com frontmatter e seções numeradas |
| `faqs.jsonl` | 125 perguntas frequentes de médicos, cada resposta citando `[PROT-NNN §secao]` |
| `templates/` | 3 modelos institucionais de documento (`TPL-001` laudo, `TPL-002` receita, `TPL-003` descrição de procedimento) |
| `qa_clinico.jsonl` | 235 perguntas em linguagem natural ancoradas nos protocolos (só fine-tuning) |

Os modelos de documento seguem a mesma estrutura dos protocolos (quando usar,
estrutura, exemplo preenchido, regras de preenchimento), então entram tanto no
índice do RAG quanto no dataset de fine-tuning e são citáveis como `[TPL-NNN §secao]`.
Todo texto é claramente marcado como **"Documento sintético para fins
acadêmicos"** e não deve ser usado como referência clínica real.

## Fine-tuning (Colab/Kaggle — não roda na VPS)

O treino roda fora do monolito, em GPU gratuita:

```bash
# 1. Gerar o dataset de fine-tuning (FAQs + protocolos + modelos de documento)
medassist build-dataset --out data/processed/

# 1b. Montar o dataset v4 completo (núcleo + Q&A clínico + expansão) -> docs/train_v4.jsonl
python scripts/gen_dataset_v4.py

# 2. Rodar notebooks/02_finetune_colab.ipynb no Google Colab
#    (espelha src/medassist/finetune/train.py — QLoRA via Unsloth)

# 3. Avaliar base vs. fine-tuned
python -m medassist.finetune.evaluate --val data/processed/val.jsonl

# 4. Merge + conversão GGUF (ver instruções impressas pelo script)
python -m medassist.finetune.export --adapters models/adapters/
```

O runtime de produção **não instala** `torch`/`transformers`/CUDA — essas
dependências ficam isoladas no extra `[project.optional-dependencies] train`
(`pip install -e ".[train]"`), usado apenas nos notebooks/scripts de treino.

## Deploy com Docker Compose

```bash
# Ambiente local/dev: sobe só app + ollama (provider fake por padrão nos testes,
# mas o container "app" usa MEDASSIST_LLM_PROVIDER=ollama)
docker compose up app ollama

# Registrar o modelo fine-tuned no Ollama (perfil "full")
# requer o GGUF em ./models/medassist-q4_k_m.gguf
docker compose --profile full up

# Logs
make compose-logs
```

Serviços (ver [`docker-compose.yml`](docker-compose.yml)):

| Serviço | Papel |
|---|---|
| `app` | Monolito: Streamlit + LangGraph + ChromaDB + SQLite embutidos |
| `ollama` | Inferência CPU do modelo fine-tuned (GGUF via `deploy/Modelfile`) |
| `model-init` (`profile: full`) | One-shot: registra o modelo no Ollama |
| `caddy` (`profile: full`) | Único ponto público — TLS + basic auth |

Antes de expor publicamente, gere o hash da senha do Caddy:

```bash
docker run --rm caddy:2 caddy hash-password --plaintext "sua-senha"
# copiar o hash para CADDY_BASIC_AUTH_HASH no .env
```

## Deploy na VPS (16 GB RAM, sem GPU)

1. Provisionar Ubuntu 22.04/24.04 com Docker Engine + compose plugin, `ufw`
   (liberar só 22/80/443) e swap de 4 GB.
2. `git clone` deste repositório, copiar `.env.example` para `.env` e
   preencher os segredos (basic auth do Caddy).
3. Baixar o GGUF fine-tuned para `./models/medassist-q4_k_m.gguf`.
4. `docker compose --profile full up -d` e conferir os healthchecks.
5. Backup: `tar` periódico dos volumes `app_data` e `app_logs` para fora da VPS.

Detalhes de orçamento de RAM, riscos e mitigação: ver
[`docs/plano.md` §5](docs/plano.md).

## Estrutura do projeto

```
src/medassist/
├── config.py            # Settings (pydantic-settings, prefixo MEDASSIST_)
├── logging_setup.py      # structlog + decorator @auditado (auditoria por nó)
├── data/                 # anonimização, geração de sintéticos, dataset de treino
├── db/                   # schema SQLite, seed, queries (pacientes/exames/alertas)
├── rag/                  # ingest (chunking + ChromaDB) e retriever
├── llm/                  # provider Protocol: fake (determinístico) e ollama
├── assistant/            # grafo LangGraph: state, nodes, routing, guardrails
├── finetune/             # artefatos de treino (não executados em produção)
└── ui/                   # CLI (typer) e Streamlit
```

## Guardrails e segurança

O assistente **nunca prescreve diretamente**. Toda resposta passa por um
guardrail determinístico (`assistant/guardrails.py`): prescrição direta sem
menção a validação, diagnóstico definitivo sem hedge e citação de fonte não
recuperada → regeneração; substância à qual o paciente é alérgico → bloqueio.
O verificador via LLM previsto originalmente foi removido — nenhum modelo
pequeno julga a rubrica de forma confiável, gerando bloqueio falso
(`docs/desvios.md` §14). Respostas reprovadas regeneram (até
`MEDASSIST_MAX_TENTATIVAS`, padrão 2) ou caem no fallback seguro. Sugestões de
conduta para um paciente específico exigem **aprovação humana** (`interrupt()`
do LangGraph) antes de qualquer alerta ser registrado.

## Logging e auditoria

Todos os nós do grafo são decorados com `@auditado`
(`medassist/logging_setup.py`): cada execução gera um evento JSON
(`no_iniciado`/`no_concluido`/`no_falhou`/`no_pulado`) em stdout e em
`logs/audit_YYYYMMDD.jsonl`, com campos sensíveis mascarados via
`anonimizar()` antes da escrita.

---

# Relatório técnico

Esta seção documenta as decisões de projeto, os resultados da avaliação e a
comparação entre o modelo fine-tuned e o modelo base. Está dividida em
**decisões de engenharia de software** (§A), **decisões de modelo** (§B),
**avaliação** (§C) e **conclusão** (§D).

## A. Decisões de engenharia de software

### A.1 Monolito, não microsserviços

O alvo de deploy é uma VPS de 16 GB sem GPU. Repartir o sistema em serviços
(um para RAG, um para o grafo, um para a API) multiplicaria o consumo de RAM em
runtimes Python duplicados e adicionaria latência de rede entre componentes que
sempre são chamados em sequência, na mesma requisição. O monolito é um processo
só; a separação existe onde importa — nos módulos:

```
src/medassist/
├── config.py        # Settings (pydantic-settings, prefixo MEDASSIST_)
├── logging_setup.py # structlog + decorator @auditado
├── data/            # anonimização, geração de sintéticos, dataset de treino
├── db/              # schema SQLite, seed, queries
├── rag/             # ingest (chunking + ChromaDB), embedding, retriever
├── llm/             # provider Protocol: fake (determinístico) e ollama
├── assistant/       # grafo LangGraph: state, nodes, routing, guardrails
├── finetune/        # treino/export/avaliação (não roda em produção)
└── ui/              # CLI (typer) e Streamlit
```

O único componente que escala separado é a inferência, e ela já está isolada
atrás de HTTP no container `ollama` — o `llm/ollama_provider.py` só fala HTTP,
então mover o serving para GPU não exigiu **nenhuma** mudança de código
(`docker-compose.gpu.yml` é um override que reserva a GPU para aquele serviço).

### A.2 LangGraph em vez de uma chain linear

O fluxo pedido não é uma sequência: ele ramifica (pergunta geral × caso de
paciente), repete (regeneração quando o guardrail reprova) e — o ponto decisivo —
**pausa para um humano e retoma depois**, possivelmente em outro processo.

Uma chain do LangChain não sabe parar no meio e continuar. O LangGraph sabe:
`interrupt()` levanta a execução, o checkpointer (`SqliteSaver`) persiste o
estado sob um `thread_id`, e `Command(resume=...)` retoma de onde parou. É por
isso que `medassist ask` devolve o controle e `medassist resume <thread>`
continua a mesma conversa minutos depois.

```
triagem → [contexto_paciente → verificar_exames] → recuperar_protocolos
        → gerar_resposta → guardrails ⇄ (regenera até MAX_TENTATIVAS)
        → [aprovacao_humana] → emitir_alertas → formatar_resposta
```

Os colchetes são ramos condicionais (`routing.py`); a seta dupla é o ciclo de
regeneração. Detalhamento nó a nó em [`docs/grafo_langgraph.md`](docs/grafo_langgraph.md).

### A.3 Provider como `Protocol`, com um fake determinístico

`llm/base.py` define a interface e há duas implementações: `ollama_provider.py`
(real) e `fake.py` (determinístico, quatro gatilhos por palavra-chave). O
**default é o fake**.

Isso não é detalhe de teste — é o que torna o projeto testável. Os 50 testes
rodam em ~90 s sem Ollama, sem GPU e sem rede, e cobrem justamente a lógica que
mais importa e que seria impossível de testar contra um LLM não-determinístico:
roteamento, regeneração por guardrail, bloqueio por alergia, o `interrupt()` e a
retomada, idempotência de alertas.

### A.4 Dois modelos no grafo, não um

O grafo chamava LLM em três nós, todos no `medassist` fine-tuned — e o resultado
era pior, não melhor. O fine-tune treinou **uma** tarefa (`gerar_resposta`);
fora da distribuição de treino o modelo recusava demais na triagem e bloqueava
respostas limpas no verificador.

Hoje a **triagem usa `llama3.2:3b`** (`get_llm(aux=True)`). Bench de 12
perguntas de classificação: `llama3.2:3b` **11/12**, `qwen2.5:1.5b` 8/12,
`llama3.2:1b` 6/12 — os menores ignoram a instrução (contam a piada, respondem
geografia). Latência: **~1 s** contra 30–60 s do 8B para uma classificação de
uma palavra.

Detalhe de infraestrutura que virou decisão de arquitetura: o 8B e o 3B **não
cabem juntos** nos 8 GB da GPU (~7,1 GiB usáveis). Com os dois na GPU o Ollama
descarregava um a cada nó — `triagem` chegou a **86 s** e um `ask` a 3–4 min. A
solução foi rodar a triagem **na CPU** (`ollama_aux_num_gpu=0`): a GPU inteira
fica para o 8B, zero evictions, `ask` quente em **39–47 s** e triagem em ~0,5 s.

### A.5 Guardrails determinísticos — o verificador por LLM foi removido

A especificação previa duas camadas: regras + um LLM julgando a resposta contra
uma rubrica. A segunda camada foi implementada, testada e **descartada**: nem o
8B fine-tuned nem o `llama3.2:3b` julgam a rubrica de forma confiável — ambos
devolviam `{"aprovada": false}` em respostas limpas (3/3 numa resposta de
anafilaxia que já citava validação médica). Afiar o prompt com few-shot
**piorou**: passou a marcar as quatro violações.

Um guardrail que bloqueia resposta correta é pior que nenhum guardrail, porque
treina o usuário a ignorá-lo. `guardrails.validar()` é 100% determinístico:

| Regra | Veredito |
|---|---|
| Prescrição com dose sem menção a validação | `regenerar` |
| Diagnóstico definitivo sem linguagem de probabilidade | `regenerar` |
| Citação de documento que não foi recuperado | `regenerar` |
| Substância à qual o paciente é alérgico | `bloqueada` (nunca regenera) |

Determinístico significa testável, auditável, com latência zero e sem
falso-positivo — e foi exatamente essa propriedade que permitiu descobrir os
dois bugs abaixo.

**Dois achados desta natureza, encontrados ao validar o sistema rodando:**

1. **`fonte_alucinada` estava morto em produção.** O regex exigia colchete
   (`\[PROT-\d+`), mas o dataset ensina majoritariamente a forma **sem**
   colchete — 93 ocorrências de `Conforme PROT-NNN §x` contra 24 de
   `[PROT-NNN]` no `train.jsonl` — e é assim que o modelo gera. O guardrail de
   explainability, o que garante que a resposta aponta para um documento
   realmente recuperado, nunca disparava. Corrigido em
   [`docs/desvios.md` §18](docs/desvios.md).
2. **O bloco "Fontes" anunciava a seção errada.** O código casava a citação só
   pelo `doc_id`, e como o top-k quase sempre traz vários trechos do mesmo
   protocolo, o dicionário colapsava tudo no último. O corpo dizia "§2" e o
   rodapé listava "§4" — a fonte mostrada ao médico apontava para a seção
   errada. Agora a resolução é pelo par `(doc_id, §N)`
   ([`docs/desvios.md` §19](docs/desvios.md)).

### A.6 Auditoria como decorator transversal

Todo nó é decorado com `@auditado` (`logging_setup.py`), que emite
`no_iniciado`/`no_concluido`/`no_falhou`/`no_pulado` em JSON, com o `thread_id`
e as chaves alteradas no estado. Rastreabilidade sem poluir a lógica de cada nó.

Duas sutilezas que só aparecem rodando:

- O decorator **tem** que deixar `GraphBubbleUp` propagar. É a exceção que o
  `interrupt()` do LangGraph levanta; capturá-la no `except Exception` genérico
  quebrava o human-in-the-loop silenciosamente, virando `state["erro"]`.
- O `FileHandler` da trilha ficava no **root logger**, então tudo que qualquer
  biblioteca logasse em INFO caía no arquivo de compliance. Medido num
  `audit_*.jsonl` real: 1873 linhas, **1363 (73%) eram `HTTP Request` do
  `httpx`**. Hoje existe um logger dedicado `medassist.audit` com
  `propagate=False`; um `ask` completo gera exatamente 10 linhas.

### A.7 Anonimização na fronteira de escrita

`anonimizar()` roda antes de a trilha de auditoria ir para o disco e antes de
cada exemplo entrar no dataset de treino — não no meio do fluxo. PII mascarada
em um ponto só, onde o dado sai do processo.

### A.8 Docker Compose como ambiente de referência

O `docker compose` não é só empacotamento: é onde o sistema é validado. Cada
mudança relevante foi confirmada com os containers no ar (`app` + `ollama`
`healthy`, entrypoint rodando `seed-db`/`ingest` dentro do container), não
apenas com testes unitários. Os perfis separam os cenários: `up app ollama`
para desenvolver, `--profile full` acrescenta `model-init` (registra o GGUF) e
`caddy` (TLS + basic auth, único ponto público).

## B. Decisões de modelo

### B.1 Fine-tuning: quatro tentativas até funcionar

Esta é a parte mais instrutiva do projeto. Três versões falharam, e por motivos
diferentes:

| v | Dataset | Base | Resultado | Causa diagnosticada |
|---|---|---|---|---|
| v1 | 1048 ex. (MedQuAD traduzido com opus-mt) | Llama-3.2-3B | Loop infinito, sem EOS, sem citação | Só **4,6%** dos exemplos ensinavam a citar; MedQuAD é majoritariamente lista de links ("MedlinePlus Encyclopedia…"), não conduta; tradução automática produz PT-BR truncado e termos inventados |
| v2 | 216 ex. (116 PT-BR + 100 MedQuAD EN cru) | Llama-3.2-3B | Loop de novo | Não era idioma, era **conteúdo**: 29/100 do MedQuAD são listas de links, 34/100 repetem a pergunta. O modelo aprendeu esse registro (46% do dataset) e o reproduzia em PT-BR |
| v3 | 116 ex. só PT-BR limpo, 3 épocas | Llama-3.2-3B | Emite EOS e cita, mas vira salada de palavras e loop de seções | Base 3B frágil demais para QLoRA com poucos exemplos + **respostas quase idênticas reaproveitadas ×4** → decorou a estrutura e perdeu fluência |
| **v4** | **439 ex. variados** | **Llama-3.1-8B** | **PT-BR fluente, cita, para no EOS** | — |

Duas lições que valem mais que o resultado:

1. **Volume de dados não resolveu; qualidade e diversidade sim.** A v1 tinha 9×
   mais exemplos que a v3 e era pior. O que consertou foi tirar a fonte ruim.
2. **O tamanho da base importou mais que qualquer ajuste de dataset.** A v3 já
   tinha dado limpo e ainda degenerava no 3B; o mesmo tipo de dado num 8B
   funcionou. Um modelo pequeno tem pouca margem para absorver QLoRA sem perder
   fluência.

### B.2 Hiperparâmetros e por quê

```python
BASE_MODEL = 'unsloth/Meta-Llama-3.1-8B-Instruct'   # QLoRA 4-bit
R, ALPHA, LR, EPOCHS, MAX_SEQ_LEN = 16, 16, 1e-4, 2, 3072
target_modules = [q,k,v,o,gate,up,down]_proj        # todas as projeções
batch=2, grad_accum=8 (efetivo 16), adamw_8bit, linear + warmup 10
```

- **2 épocas, não 3.** A v3 usou 3 em 116 exemplos e overfitou a *forma*. Com
  `eval_dataset` configurado, a regra prática é olhar a eval loss por época: se
  subir na segunda, cair para 1.
- **LR 1e-4** (baixo) para estabilidade no 8B.
- **`train_on_responses_only`** — mascara os turnos `system`/`user` da loss.
  Sem isso o modelo gasta capacidade aprendendo a reproduzir o próprio system
  prompt em vez da resposta.
- **`max_seq_len=3072`** acomoda os exemplos "Explique o protocolo X", cuja
  resposta é o corpo inteiro do documento.

### B.3 Dataset: composição e o que ficou de fora

**439 exemplos**, montados por `scripts/gen_dataset_v4.py` (espelho da célula 3
do notebook), em três fatias:

| Fatia | Qtd. | Papel |
|---|---|---|
| Núcleo (`train.jsonl`) | 156 | 25 protocolos "Explique o protocolo…" + 125 FAQs de seção + 15 de modelo de documento; 100% citam `[PROT-NNN §x]` ou `[TPL-NNN §x]` |
| Q&A clínico | 235 | Perguntas de médico em linguagem natural — parciais, cenários, cross-protocolo — **cada resposta única** |
| Expansão | 48 | Cada "Explique o protocolo…" em +2 fraseados |

O princípio que emergiu das falhas: **cada resposta precisa ser única**. A v3
reaproveitava a mesma resposta longa quatro vezes e o modelo memorizou o molde.
O fecho em PT-BR é rotacionado entre cinco fraseados pelo mesmo motivo — a v1
tinha 127 respostas com os últimos 80 caracteres idênticos.

**Deliberadamente fora:** MedQuAD e PubMedQA (causaram v1 e v2), tradução
automática, e — decisão de projeto — **exemplos de segurança**. Guardrail não
mora nos pesos: um modelo pode ser convencido a ignorar o que aprendeu, um
regex não. A segurança vive no grafo (§A.5).

### B.4 Quantização e serving

Merge do LoRA em 16 bits e conversão para **GGUF Q4_K_M** (4,92 GB). Cabe nos
8 GB da RTX 4060 Ti junto com o KV cache a 3072 de contexto — `ollama ps`
mostra `100% GPU`, ~52 tok/s quente. O `deploy/Modelfile` fixa
`num_predict 768`: é teto anti-degeneração, não limite de qualidade (uma
resposta de protocolo bem-formada cabe em ~600 tokens). Com ele, um modelo que
degenere estoura em ~1 min e cai em `resposta_segura`, em vez de travar — o que
de fato aconteceu na v2, com uma chamada presa por **19 minutos**.

### B.5 RAG: a escolha do embedding foi o que mais moveu a qualidade

O `paraphrase-MiniLM` inicial errava o protocolo de forma grosseira: *"qual o
protocolo de sepse?"* trazia PROT-024, *"conduta inicial na sepse"* trazia
PROT-013, e *"crise hipertensiva com EAP"* devolvia conteúdo de DPOC.

Troca para **`intfloat/multilingual-e5-small`**, com três ajustes que andam
juntos:

- O E5 exige prefixos `query:` / `passage:`. Daí `rag/embedding.py`: o `ingest`
  grava os vetores já calculados e o retriever consulta com
  `query_embeddings=` — se a collection do Chroma embutisse sozinha, aplicaria o
  prefixo errado na consulta.
- `rag_min_score` de 0.35 para **0.82**: as similaridades do E5 ficam
  comprimidas no alto (~0.82+ relevante, ~0.81 ruído).
- A collection é criada com `metadata={"hnsw:space": "cosine"}` — o Chroma usa
  **L2 por padrão**, e sem isso os scores não são comparáveis ao limiar.

Bench pós-troca: **13/14** — todas as consultas clínicas recuperam o protocolo
certo em #1 (0.83–0.95), e o top-k passou a ser dominado pelo documento correto.

### B.6 RAG: reformulação da consulta

Meta-perguntas ("qual o protocolo de X?", "existe conduta para X?") carregam
ruído que dilui o embedding. `_reformular_query` remove o preâmbulo e manda só
o termo clínico para o retriever. Foi o que consertou a confabulação em
respostas longas: quando o retrieval trazia o protocolo errado ou parcial, o
modelo preenchia os buracos inventando detalhe clínico plausível. Com as seções
certas em contexto, ele recompõe fiel.

### B.7 Chunking e o que é indexado

Chunk = uma seção `##` do documento (máx. 1200 chars, overlap 150). O embedding
é calculado sobre **título + seção + corpo** (melhora recall para perguntas
curtas), mas o documento devolvido e citado é **só o corpo** — que é o texto
técnico útil para a resposta. Total: **112 chunks** (25 protocolos + 3 modelos
de documento).

## C. Avaliação

### C.1 Metodologia

`python -m medassist.finetune.evaluate --modelos medassist llama3.1:8b` roda o
mesmo conjunto de validação (9 exemplos) nos dois modelos, um passe completo por
modelo para não trocar modelo no Ollama a cada exemplo. Três métricas:

| Métrica | O que mede |
|---|---|
| `rougeL` | F-measure ROUGE-L contra a resposta de referência — proximidade textual |
| `doc_ids` | Fração das citações da referência que a resposta também cita |
| `formato` | 1.0 se cita um documento **e** encerra recomendando validação médica |

**Detalhe metodológico decisivo:** o `evaluate.py` gera **sem contexto do RAG**.
Ele mede o que ficou nos *pesos*, não o que o sistema entrega. Por isso a
avaliação foi feita duas vezes.

### C.2 Resultado — o que ficou nos pesos (sem RAG)

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` (fine-tuned) | **0.239** | 0.111 | **1.000** |
| `llama3.1:8b` (base) | 0.108 | 0.222 | 0.111 |

O número que importa não é a média de ROUGE-L, é a consistência: o `medassist`
ganhou do base **nos 9 de 9 exemplos**, com faixas que não se sobrepõem
(0.189–0.335 contra 0.051–0.168). Com n=9, uma média isolada seria frágil; uma
varredura limpa não é.

**`doc_ids` parece favorecer o base — é artefato da métrica.** Quando a
referência não cita nenhum `PROT-NNN`, o scorer dá ponto a quem *também não
citar nada*. O exemplo 9 tem referência `[TPL-002 §4]`: o base tirou 1.000 por
não saber citar, o `medassist` tirou 0.000 por citar um id errado. Somado ao
exemplo 1, dá exatamente os 2/9 do base contra 1/9 do fine-tuned. Traduzindo: o
base "vence" porque não sabe citar, então nunca é pego citando errado.

**`formato` 9/9 contra 1/9 é o resultado honesto do fine-tuning** — é a única
métrica que isola o que o QLoRA deveria ensinar. E o único acerto do base é
revelador: é o exemplo cuja pergunta já contém o id (*"Explique o protocolo
**PROT-015**…"*). Ele apenas ecoou.

### C.3 Resultado — o que o sistema entrega (com RAG)

O mesmo conjunto, mesma métrica, agora com os documentos recuperados no prompt,
como a aplicação roda de verdade:

| | ROUGE-L médio |
|---|---|
| `medassist` sem RAG (pesos) | 0.234 |
| `medassist` com RAG (produção) | **0.803** |

O ganho é uniforme — os 9 exemplos sobem, de 0.62 a 0.93.

Isso **reatribui o crédito** entre os dois componentes, e é o achado mais útil
da avaliação: o fine-tuning entregou **formato e registro**, o RAG entregou
**conteúdo**. Nenhum dos dois sozinho faz o sistema.

E explica por que 0.24 sem RAG **não é um resultado ruim**. Um ROUGE-L alto ali
seria sinal de alerta, não de sucesso: significaria que o 8B decorou os 25
protocolos sintéticos — e modelo que decora confabula com confiança quando o
retrieval erra. O par 0.23 / 0.80 é o perfil saudável: aprendeu o estilo da
casa e o vocabulário clínico, não o corpus de cor.

### C.4 Limitações da avaliação

- **n = 9.** Suficiente para "o fine-tune pegou?", insuficiente para
  significância estatística fina.
- O `val.jsonl` sai do **mesmo gerador determinístico** do treino. Isso mede
  ajuste *dentro da distribuição*, não generalização clínica.
- Nenhuma métrica aqui mede correção clínica. Os dados são sintéticos e o
  sistema é de apoio à decisão — a validação médica é parte do produto, não
  uma ressalva.

## D. Conclusão: fine-tuned vs. modelo base

**O fine-tuning entregou o que se propôs, e não entregou o que não cabia nele.**

O que mudou de forma inequívoca foi o **comportamento de saída**: citar a fonte
e encerrar pedindo validação médica, em 9 de 9 respostas contra 1 de 9 do base —
e esse único acerto do base foi eco da pergunta. Como a explicabilidade é
requisito do produto (indicar a fonte usada) e o guardrail determinístico é
quem libera a resposta, esse comportamento não é cosmético: é o que faz o
sistema funcionar de ponta a ponta. Um modelo base plugado no mesmo grafo teria
suas respostas recusadas pelo guardrail na maior parte das vezes.

O que o fine-tuning **não** fez foi ensinar os protocolos ao modelo — e isso é
projeto, não falha. ROUGE-L de 0.234 sem contexto contra 0.803 com contexto
mostra que o conhecimento vive no índice do RAG, onde pode ser atualizado
reindexando um Markdown, sem retreinar 8 bilhões de parâmetros. Um hospital que
revisa um protocolo não deveria precisar de uma GPU para o assistente saber
disso.

A divisão de trabalho que o projeto encontrou, e que sustentaria recomendar essa
arquitetura de novo:

| Componente | Responsabilidade | Evidência |
|---|---|---|
| Fine-tuning | Formato, registro clínico em PT-BR, disciplina de citação | `formato` 1.000 × 0.111 |
| RAG | Conteúdo factual e rastreável | ROUGE-L 0.234 → 0.803 |
| Grafo/guardrails | Segurança, validação humana, auditoria | 100% determinístico, testável |

Duas ressalvas honestas para fechar:

1. O checkpoint servido hoje foi treinado **antes** de os modelos de laudo,
   receita e procedimento entrarem no dataset. Na prática: o RAG recupera o
   `TPL-002` corretamente e o modelo reescreve o conteúdo com fidelidade
   (ROUGE-L **0.912** nesse exemplo), mas rotula a citação como `PROT-NNN` —
   e o guardrail, corretamente, recusa. Verificado que **não é corrigível por
   prompt**: instruir "copie o identificador do contexto" não altera o
   comportamento, porque o prefixo está soldado nos pesos por 425 exemplos.
   Fechar esse item exige retreinar com os 439.
2. Os dados são sintéticos e determinísticos por escolha — o que garante
   reprodutibilidade e ausência de PII real, mas significa que nenhum número
   aqui é evidência de desempenho clínico.
