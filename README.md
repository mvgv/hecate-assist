# hecate-assist (MedAssist)

Assistente virtual médico para apoio à decisão clínica — terceira entrega do
Tech Challenge IADT. Monolito Python com **LangGraph** (fluxo de decisão),
**RAG** sobre protocolos institucionais sintéticos (ChromaDB), consulta a
base estruturada de pacientes (SQLite), guardrails de segurança,
human-in-the-loop e logging de auditoria. Roda em CPU via Docker Compose
(app + Ollama + Caddy).

> 📄 **[Relatório técnico](#relatório-técnico)** — arquitetura e prompts do grafo
> (§A), decisões de engenharia (§B), fine-tuning e QLoRA (§C), estratégia de RAG
> (§D), avaliação (§E) e a comparação fine-tuned vs. base (§F), com um apêndice
> sobre a métrica usada. O restante deste README são as instruções de uso.

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
| `templates/` | 3 modelos institucionais de documento (`PROT-026` laudo, `PROT-027` receita, `PROT-028` descrição de procedimento) |
| `qa_clinico.jsonl` | 235 perguntas em linguagem natural ancoradas nos protocolos (só fine-tuning) |

Os modelos de documento seguem a mesma estrutura dos protocolos (quando usar,
estrutura, exemplo preenchido, regras de preenchimento), então entram tanto no
índice do RAG quanto no dataset de fine-tuning, e são citáveis exatamente como
eles — o namespace `PROT-` é único de propósito ([`docs/desvios.md` §22](docs/desvios.md)).
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

## Guardrails, auditoria e privacidade

O assistente **nunca prescreve diretamente**. Toda resposta passa por um
guardrail determinístico (`assistant/guardrails.py`) antes de chegar ao médico,
e sugestões de conduta para um paciente específico exigem **aprovação humana**
(`interrupt()` do LangGraph) antes de qualquer alerta ser registrado. Todos os
nós do grafo emitem eventos JSON de auditoria em stdout e em
`logs/audit_YYYYMMDD.jsonl`.

As decisões por trás disso — por que o verificador por LLM foi removido, o que
a trilha registra e onde a anonimização se aplica (e onde deliberadamente não
se aplica) — estão em [§B.3](#b3-guardrails-determinísticos--o-verificador-por-llm-foi-removido),
[§B.4](#b4-auditoria-como-decorator-transversal) e
[§B.5](#b5-anonimização-onde-se-aplica-e-por-quê-não-em-todo-lugar) do relatório.

---

# Relatório técnico

Decisões de projeto, resultados da avaliação e a comparação entre o modelo
fine-tuned e o modelo base. Dividido em **arquitetura do assistente** (§A),
**decisões de engenharia** (§B), **fine-tuning** (§C), **RAG** (§D),
**avaliação** (§E) e **conclusão** (§F), com um apêndice sobre a métrica usada.

## A. Arquitetura do assistente

### A.1 LangGraph em vez de uma chain linear

O fluxo pedido não é uma sequência: ele ramifica (pergunta geral × caso de
paciente), repete (regeneração quando o guardrail reprova) e — o ponto decisivo
— **pausa para um humano e retoma depois**, possivelmente em outro processo.

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
regeneração. Montagem em [`assistant/graph.py`](src/medassist/assistant/graph.py),
detalhamento em [`docs/grafo_langgraph.md`](docs/grafo_langgraph.md).

### A.2 O fluxo, nó a nó

| Nó | O que faz | Decisão de projeto |
|---|---|---|
| `triagem` | Classifica a intenção em dúvida clínica, caso de paciente ou fora de escopo | Filtro determinístico por termo clínico **antes** do LLM; pergunta com paciente selecionado nem chega ao modelo — já é caso de paciente |
| `contexto_paciente` | Lê o SQLite: idade, sexo, comorbidades, medicações em uso, alergias | É o "contextualizar as respostas com informações atualizadas do paciente" do enunciado |
| `verificar_exames` | Separa exames pendentes dos que vieram com resultado crítico | Um resultado crítico já marca `requer_aprovacao` aqui — o fluxo sabe, antes de gerar qualquer texto, que vai precisar de um humano |
| `recuperar_protocolos` | Reformula a consulta, embute e busca no ChromaDB por cosseno | Top-4 trechos, score mínimo 0.82 (§D) |
| `gerar_resposta` | O 8B fine-tunado escreve a resposta com os trechos recuperados no prompt | Teto de 768 tokens: se o modelo degenerar, estoura em ~1 min e cai no fallback seguro em vez de travar |
| `guardrails` | Quatro regras determinísticas sobre o texto gerado | Prescrição com dose sem validação, diagnóstico categórico sem hedge e fonte não recuperada → **regenera**; substância com alergia do paciente → **bloqueia**, sem segunda chance |
| `aprovacao_humana` | Interrompe o grafo e devolve a resposta proposta para um médico aprovar | O estado é persistido sob o `thread_id`; o processo pode morrer e a conversa retoma depois |
| `emitir_alertas` | Registra os alertas na base — exame crítico e sugestão de conduta | Só roda **depois** do aprovado. Nada é registrado em nome do médico sem o aceite dele |
| `formatar_resposta` | Anexa as fontes citadas e o disclaimer | A fonte casa documento **e seção**: se o corpo diz §2, o rodapé mostra §2 |
| `resposta_segura` | Fallback quando o guardrail bloqueia ou algo falha | Sempre informa o motivo |
| `resposta_recusa` | Saída para pergunta fora de escopo | Nenhum LLM é chamado nesse caminho |

### A.3 Dois modelos no grafo, não um

O grafo chamava LLM em três nós, todos no `medassist` fine-tuned — e o resultado
era pior, não melhor. O fine-tune treinou **uma** tarefa (`gerar_resposta`);
fora da distribuição de treino o modelo recusava demais na triagem e bloqueava
respostas limpas no verificador.

| Nó | Modelo | Motivo |
|---|---|---|
| `triagem` | `llama3.2:3b` | Classificar não é a tarefa treinada. Bench de 12 perguntas: **3B acerta 11**, `qwen2.5:1.5b` acerta 8, `llama3.2:1b` acerta 6. Latência ~1 s contra 30–60 s do 8B |
| `gerar_resposta` | `medassist` (8B) | Onde o estilo institucional importa: citar a fonte e encerrar pedindo validação |

Detalhe de infraestrutura que virou decisão de arquitetura: o 8B e o 3B **não
cabem juntos** nos 8 GB da GPU. Com os dois na GPU o Ollama descarregava um a
cada nó — a triagem chegou a **86 s** e um `ask` a 3–4 min. A solução foi rodar
a triagem **na CPU** (`ollama_aux_num_gpu=0`): a GPU inteira fica para o 8B,
zero evictions, `ask` quente em 25–45 s.

### A.4 Os prompts de cada etapa

Todos os prompts vivem em
[`assistant/prompts.py`](src/medassist/assistant/prompts.py) — nenhum está
espalhado dentro da lógica dos nós.

**O prompt de sistema** (`gerar_resposta`) carrega quatro instruções, e cada uma
responde a um requisito: nunca prescrever diretamente (limite de atuação), citar
no formato `[DOC-ID §secao]` (explainability), encerrar recomendando validação
(validação humana) e responder em PT-BR clínico.

O mesmo texto está gravado como `SYSTEM` no
[`deploy/Modelfile`](deploy/Modelfile): mesmo que alguém chame o `medassist`
direto pelo Ollama, sem passar pelo grafo, ele já carrega as regras da casa.

**O prompt de triagem** é **binário** — `duvida_clinica` ou `fora_escopo` — com
seis exemplos few-shot. A terceira intenção (`caso_paciente`) é decidida por
código, antes do LLM: se há `paciente_id`, é caso de paciente. Não se pergunta
ao modelo o que já se sabe. A versão anterior era em prosa e de três vias, e
modelos pequenos não a seguiam. O fecho `"Na dúvida, responda duvida_clinica"`
faz a falha cair deliberadamente para o lado de responder: recusa indevida
frustra o médico e não protege ninguém, e uma resposta indevida ainda passa
pelo RAG e pelos guardrails.

**O contexto** é o único que não está no arquivo: `_montar_contexto` constrói um
bloco novo a cada requisição. Exemplo real, para uma paciente alérgica a
dipirona:

```
Paciente: [NOME], 53 anos, sexo F.
Comorbidades: asma.
Medicações em uso: salbutamol.
⚠️ ALERGIAS DO PACIENTE (não sugerir estas substâncias): dipirona (moderada).
[PROT-012 §3. Medicações e doses de referência] Analgesia escalonada conforme
  intensidade: dipirona 1 g EV até 6/6h para dor leve a moderada; opioide […]
[PROT-024 §3. Medicações e doses de referência] Base: paracetamol 1 g VO/EV
  6/6h; dipirona 1 g EV 6/6h; ou anti-inflamatório não esteroidal […]
```

Três origens num bloco só: os dados do paciente vêm do SQLite, o aviso de
alergia é gerado por código, os trechos vêm do RAG. E o formato
`[PROT-NNN §secao]` não é decorativo — é **exatamente** o formato das citações
no dataset de fine-tuning (§D.3).

Repare na tensão do exemplo: o contexto manda não sugerir dipirona *e* traz dois
protocolos que a recomendam. É o caso que exercita as duas camadas de proteção
contra alergia — a instrução no prompt e, se ela falhar, o guardrail.

**O prompt de regeneração** é anexado ao sistema na segunda tentativa com os
códigos de violação preenchidos: o modelo recebe o motivo específico da
reprovação, não um "tente de novo" genérico.

## B. Decisões de engenharia de software

### B.1 Monolito, não microsserviços

O alvo de deploy é uma VPS de 16 GB sem GPU. Repartir o sistema em serviços
multiplicaria o consumo de RAM em runtimes Python duplicados e adicionaria
latência de rede entre componentes que sempre são chamados em sequência, na
mesma requisição. O monolito é um processo só; a separação existe onde importa,
nos módulos.

O único componente que escala separado é a inferência, e ela já está isolada
atrás de HTTP no container `ollama` — o `llm/ollama_provider.py` só fala HTTP,
então mover o serving para GPU não exigiu **nenhuma** mudança de código
(`docker-compose.gpu.yml` é um override que reserva a GPU para aquele serviço).

### B.2 Provider como `Protocol`, com um fake determinístico

`llm/base.py` define a interface e há duas implementações: `ollama_provider.py`
(real) e `fake.py` (determinístico, quatro gatilhos por palavra-chave). O
**default é o fake**.

Isso não é detalhe de teste — é o que torna o projeto testável. Os 52 testes
rodam em ~90 s sem Ollama, sem GPU e sem rede, e cobrem justamente a lógica que
seria impossível de testar contra um LLM não-determinístico: roteamento,
regeneração por guardrail, bloqueio por alergia, o `interrupt()` e a retomada,
idempotência de alertas.

### B.3 Guardrails determinísticos — o verificador por LLM foi removido

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
falso-positivo — e foi essa propriedade que permitiu descobrir dois defeitos
reais durante a validação:

1. **`fonte_alucinada` estava morto em produção.** O regex exigia colchete
   (`\[PROT-\d+`), mas o dataset ensina majoritariamente a forma **sem**
   colchete — 93 ocorrências de `Conforme PROT-NNN §x` contra 24 de
   `[PROT-NNN]` no `train.jsonl` — e é assim que o modelo gera. O guardrail de
   explainability nunca disparava ([`docs/desvios.md` §18](docs/desvios.md)).
2. **O bloco "Fontes" anunciava a seção errada.** O código casava a citação só
   pelo `doc_id`, e como o top-k traz vários trechos do mesmo protocolo, o
   dicionário colapsava tudo no último: o corpo dizia "§2" e o rodapé listava
   "§4" ([`docs/desvios.md` §19](docs/desvios.md)).

O `PROMPT_VERIFICADOR` continua no arquivo, órfão, como registro da decisão.

### B.4 Auditoria como decorator transversal

Todo nó é decorado com `@auditado` (`logging_setup.py`), que emite
`no_iniciado`/`no_concluido`/`no_falhou`/`no_pulado` em JSON, com o `thread_id`
e as chaves alteradas no estado:

```json
{"no": "checar_guardrails", "thread_id": "67dde5a2-2d7d-43ec-aed1-8fc0b2fdbacb",
 "delta_keys": ["veredito", "violacoes"], "ms": 0, "event": "no_concluido"}
```

Dá para reconstruir por que uma resposta foi bloqueada, qual protocolo foi
consultado e quem aprovou o quê. Três sutilezas que só aparecem rodando:

- O decorator **tem** que deixar `GraphBubbleUp` propagar. É a exceção que o
  `interrupt()` levanta; capturá-la no `except Exception` genérico quebrava o
  human-in-the-loop silenciosamente.
- O `FileHandler` da trilha ficava no **root logger**, então tudo que qualquer
  biblioteca logasse em INFO caía no arquivo de compliance. Medido num
  `audit_*.jsonl` real: 1873 linhas, **1363 (73%) eram `HTTP Request` do
  `httpx`**. Hoje existe um logger dedicado com `propagate=False`; um `ask`
  completo gera exatamente 10 linhas.
- O mascaramento de PII aplicava-se a **todo** valor string do evento, inclusive
  ao `thread_id` — e o regex de telefone casa com segmentos de 8 dígitos de um
  UUID. A trilha saía com `"thread_id": "[TELEFONE]-3193-…"`, mascarada de forma
  imprevisível justamente no campo que existe para correlacionar. Chaves
  estruturais ficaram fora da máscara.

### B.5 Anonimização: onde se aplica, e por quê não em todo lugar

O enunciado pede anonimização no preparo dos dados de fine-tuning. O critério
adotado é **onde o dado sobrevive ao atendimento**, e há exatamente dois pontos
de chamada no código:

| Onde | Anonimiza | Por quê |
|---|---|---|
| Dataset de fine-tuning (`build_dataset`) | **Sim** | PII absorvida em peso de modelo é irreversível — não há como remover depois |
| Trilha de auditoria (`logging_setup`) | **Sim** | Artefato de compliance, vida longa, sai da máquina |
| Prompt enviado ao LLM | Não | O modelo precisa do contexto para responder sobre *este* paciente |
| Resposta na interface | Não | O médico precisa saber de quem se trata |
| Tabela de alertas | Não | Já é registro clínico, chaveado por `paciente_id` |

Mostrar o nome e as comorbidades ao médico **é** o requisito "contextualizar as
respostas com informações atualizadas do paciente". Um apoio à decisão que
esconde de qual paciente se trata não é mais seguro — é perigoso.

Na trilha, a proteção é mais forte que o mascaramento: o decorator loga
`delta_keys`, os *nomes* dos campos alterados, nunca os valores. Verificado — o
log não contém nenhum nome de paciente. O `anonimizar()` ali é rede de
segurança, não o mecanismo principal.

**Limitação conhecida:** o padrão de nome exige espaço logo após a palavra-gatilho
(`paciente|Dr\.|Dra\.`), então `"Paciente: Fulano"` — com dois-pontos, que é o
formato do contexto — não é mascarado, nem um nome sem gatilho antes. Hoje isso
não vaza nada, porque os dois pontos de chamada não veem nome de paciente (os
dados sintéticos usam `[PACIENTE]` desde a origem). Mas é um *fail open*: com
prontuário real na entrada, a rede de segurança não pegaria.

**Fronteira de rede:** o nome do paciente vai no prompt do LLM. Com o Ollama
local, nada sai da máquina — é decisão de arquitetura, não acidente. Com um
provider em nuvem, isso seria PII cruzando fronteira organizacional e exigiria
pseudonimizar o contexto antes de enviar.

### B.6 Docker Compose como ambiente de referência

O `docker compose` não é só empacotamento: é onde o sistema é validado. Cada
mudança relevante foi confirmada com os containers no ar, não apenas com testes
unitários. Os perfis separam os cenários: `up app ollama` para desenvolver,
`--profile full` acrescenta `model-init` (registra o GGUF) e `caddy` (TLS +
basic auth, único ponto público).

## C. O fine-tuning

### C.1 Para que serve o QLoRA

Treinar um modelo de 8 bilhões de parâmetros do jeito tradicional exigiria
**mais de 100 GB** de memória de vídeo — os pesos são só uma parte; para cada
peso também ficam na memória o gradiente, dois valores de estado do otimizador e
uma cópia em precisão alta. Nenhuma GPU gratuita chega perto disso.

A ideia do QLoRA: em vez de reescrever o modelo inteiro, **anexa-se uma peça
pequena ao lado dele e treina-se só essa peça** — e guarda-se o modelo original
numa versão comprimida, já que ele não vai mudar mesmo.

> É como estudar por um livro que não se pode rasurar. Em vez de reescrever os
> capítulos, escrevem-se **anotações nas margens**. O livro continua igual; o
> que se aprendeu está nas anotações. E como não se vai mexer nele, dá para
> guardar uma **edição de bolso**, que ocupa muito menos espaço na estante.

As anotações são os **adaptadores** — a única parte que treina, duas matrizes
finas de largura 16 ao lado de cada projeção. A edição de bolso é a
**quantização em 4 bits** (NF4) do modelo congelado: como esses pesos não
mudam, não precisam de precisão alta. A precisão fica onde há aprendizado.

| | Com QLoRA | Treino tradicional |
|---|---|---|
| Parâmetros que realmente treinam | **42 milhões** (0,5%) | 8 bilhões (100%) |
| Memória de vídeo necessária | **~10 GB** | mais de 100 GB |

Uma das duas matrizes começa zerada, então no passo zero a peça anexada soma
exatamente nada e o modelo é idêntico ao original — o treino só constrói a
partir dali. E o que se salva no fim são só as anotações: dezenas de megabytes.

**O que o fine-tuning ensinou — e o que não ensinou.** O QLoRA aqui não ensinou
medicina ao modelo. Ensinou *como responder*: citar a fonte no formato da casa,
encerrar pedindo validação, escrever em português clínico objetivo. O conteúdo
clínico vem do RAG (§D). Estilo cabe numa peça pequena; conhecimento não caberia.

### C.2 Os ajustes que importam

| Ajuste | Valor | Por quê |
|---|---|---|
| Modelo base | `Llama-3.1-8B` | O de 3 bilhões degenerava mesmo com dado limpo. O tamanho da base importou mais que qualquer ajuste no dataset |
| Tamanho da anotação (posto) | 16 | Pequeno basta, porque se ensina estilo, não conhecimento |
| Learning rate | 1e-4 | Baixo, para estabilidade no 8B |
| Épocas | 2 | Uma versão anterior usou 3 num conjunto pequeno e memorizou a *forma* das respostas |
| Batch efetivo | 16 | 2 por passo × 8 de acumulação — simula batch grande sem a VRAM de um |
| O que entra na conta do erro | só as respostas | `train_on_responses_only` mascara sistema e usuário. Sem isso o modelo gasta capacidade aprendendo a repetir o próprio enunciado |

**A rodada:** 56 passos, **217 segundos**. O erro de validação caiu de
**1,4915** na primeira época para **1,3296** na segunda — ainda melhorando, sem
overfit — e ficou praticamente colado no erro de treino (1,3073), confirmando
que o modelo não memorizou o conjunto.

### C.3 O dataset

**465 exemplos**, montados por `scripts/gen_dataset_v4.py` (espelho da célula 3
do notebook), em três fatias:

| Fatia | Qtd. | Papel |
|---|---|---|
| Núcleo (`train.jsonl`) | 182 | 25 protocolos "Explique o protocolo…" + 125 FAQs de seção + 45 de modelo de documento; 100% citam `[PROT-NNN §x]` |
| Q&A clínico | 235 | Perguntas de médico em linguagem natural — parciais, cenários, cross-protocolo — **cada resposta única** |
| Expansão | 48 | Cada "Explique o protocolo…" em +2 fraseados |

O princípio que emergiu das falhas: **cada resposta precisa ser única**. A v3
reaproveitava a mesma resposta longa quatro vezes e o modelo memorizou o molde.
O fecho em PT-BR é rotacionado entre cinco fraseados pelo mesmo motivo — a v1
tinha 127 respostas com os últimos 80 caracteres idênticos.

**Deliberadamente fora:** MedQuAD e PubMedQA (causaram v1 e v2), tradução
automática, e — decisão de projeto — **exemplos de segurança**. Guardrail não
mora nos pesos: um modelo pode ser convencido a ignorar o que aprendeu, um regex
não. A segurança vive no grafo (§B.3).

### C.4 Quatro tentativas até funcionar

| v | Dataset | Base | Resultado | Causa diagnosticada |
|---|---|---|---|---|
| v1 | 1048 ex. (MedQuAD traduzido com opus-mt) | Llama-3.2-3B | Loop infinito, sem EOS, sem citação | Só **4,6%** dos exemplos ensinavam a citar; MedQuAD é majoritariamente lista de links, não conduta; tradução automática produz PT-BR truncado |
| v2 | 216 ex. (116 PT-BR + 100 MedQuAD EN cru) | Llama-3.2-3B | Loop de novo | Não era idioma, era **conteúdo**: 29/100 do MedQuAD são listas de links, 34/100 repetem a pergunta |
| v3 | 116 ex. só PT-BR limpo, 3 épocas | Llama-3.2-3B | Emite EOS e cita, mas vira salada de palavras | Base 3B frágil demais para QLoRA com poucos exemplos + **respostas quase idênticas ×4** → decorou a estrutura e perdeu fluência |
| **v4** | **425+ ex. variados** | **Llama-3.1-8B** | **PT-BR fluente, cita, para no EOS** | — |

Duas lições que valem mais que o resultado:

1. **Volume de dados não resolveu; qualidade e diversidade sim.** A v1 tinha 9×
   mais exemplos que a v3 e era pior. O que consertou foi tirar a fonte ruim.
2. **O tamanho da base importou mais que qualquer ajuste de dataset.** A v3 já
   tinha dado limpo e ainda degenerava no 3B; o mesmo tipo de dado num 8B
   funcionou.

### C.5 Do adaptador ao serving

A exportação faz duas coisas distintas: primeiro o **merge**, que soma o delta
aos pesos originais e devolve um modelo denso de 16 bits — a partir daí não há
mais adaptador, é um Llama comum. Depois a **quantização de serviço**, para
**GGUF Q4_K_M**: 4,92 GB, que o Ollama carrega na GPU de 8 GB a ~52 tokens/s.
O `deploy/Modelfile` fixa `num_predict 768` como teto anti-degeneração.

## D. A estratégia de RAG

O fine-tuning ensinou o *jeito* de responder. O conteúdo não está nos pesos —
está no índice. É por isso que atualizar um protocolo do hospital é reindexar um
Markdown, não retreinar oito bilhões de parâmetros.

### D.1 As quatro fontes de dados

Tudo em `data/synthetic/` é sintético e determinístico — gerado por código, sem
LLM, e marcado como material acadêmico.

| Fonte | Qtd. | Exemplo |
|---|---|---|
| `protocolos/` | 25 | PROT-001 Sepse, com seções numeradas: definição, conduta inicial, doses de referência, critérios de alerta |
| `faqs.jsonl` | 125 | *"Quais os critérios diagnósticos relacionados a manejo inicial de sepse no adulto?"* → resposta que abre com `Conforme PROT-001 §1, …` |
| `templates/` | 3 | Modelos de laudo, receita e descrição de procedimento (PROT-026 a 028) — a terceira fonte que o enunciado exige |
| `qa_clinico.jsonl` | 235 | *"Paciente com foco pulmonar, PA 80/50 e lactato 5. Qual a conduta inicial?"* — linguagem de médico. Só entra no fine-tuning |

### D.2 O pipeline, da indexação à resposta

1. **Chunking por seção.** Cada trecho indexado é uma seção `##`, com teto de
   1200 caracteres e 150 de sobreposição. A escolha não é arbitrária: uma seção
   de protocolo já é uma unidade clínica completa ("conduta inicial", "doses de
   referência") **e** é a granularidade da citação — o `§N`. A fronteira do
   chunk é a fronteira da fonte que o médico vai conferir. São 112 chunks.
2. **O que é embutido ≠ o que é devolvido.** O vetor é calculado sobre *título +
   seção + corpo*, porque melhora o recall de perguntas curtas ("sepse" casa com
   o título). Mas o texto que volta e entra no prompt é **só o corpo**.
3. **Embedding assimétrico.** O `multilingual-e5-small` foi treinado exigindo
   prefixos diferentes para cada lado: `query:` na pergunta e `passage:` no
   documento. É o que faz uma pergunta curta e um parágrafo técnico caírem perto
   no espaço vetorial. Por isso o `ingest` grava os vetores já calculados e o
   retriever consulta com o vetor pronto — se a collection do Chroma embutisse
   sozinha, aplicaria o prefixo errado do lado da consulta.
4. **Cosseno explícito.** A collection é criada com `hnsw:space: cosine`. O
   Chroma usa distância euclidiana por padrão, e sem isso os scores não são
   comparáveis ao limiar.
5. **Limiar de 0,82.** As similaridades do E5 ficam comprimidas no alto:
   relevante em 0,83–0,95 e ruído em ~0,81. A faixa útil é estreita. O valor
   anterior, 0,35, era do modelo antigo e deixava passar qualquer coisa.
6. **Reformulação da consulta.** "Qual o protocolo de X?" vira só "X". O
   preâmbulo é texto que aparece em toda pergunta e não discrimina nada. Quando
   há paciente selecionado, as comorbidades entram na consulta.
7. **Montagem do contexto.** Cada trecho entra como `[PROT-001 §2] <texto>`. Se
   nada passa do limiar, o estado marca `sem_fonte` e a resposta avisa que é
   conhecimento geral do modelo.

O embedding foi o que mais moveu a qualidade: o `paraphrase-MiniLM` inicial
errava de forma grosseira — *"qual o protocolo de sepse?"* trazia o protocolo de
abstinência alcoólica. Depois da troca, bench de **13 em 14** consultas
recuperando o documento certo em primeiro lugar, com score entre 0,83 e 0,95.

### D.3 O acoplamento entre RAG e fine-tuning

O passo 7 é a costura entre os dois, e foi aprendido do jeito difícil. O formato
`[PROT-NNN §secao]` do contexto é **idêntico** ao das citações no dataset de
treino: o modelo aprendeu a citar assim, então copiar o identificador que está
ali na frente é o caminho natural.

Os modelos de documento nasceram com um prefixo próprio, `TPL-`. O modelo —
treinado só com `PROT-` — **ignorava o contexto inteiro** e inventava um número,
com conteúdo genérico em vez do texto recuperado. Nem instrução no prompt nem
retreino com uma fatia `TPL-` resolveram. Renomear os documentos para
`PROT-026..028` resolveu na hora, com o mesmo modelo já servido
([`docs/desvios.md` §22](docs/desvios.md)). **O formato do contexto tem que
falar a mesma língua que o fine-tuning ensinou.**

## E. Avaliação e resultados

### E.1 Metodologia

`python -m medassist.finetune.evaluate --modelos medassist llama3.1:8b` roda o
mesmo conjunto de validação (9 exemplos) nos dois modelos, um passe completo por
modelo. Três métricas:

| Métrica | O que mede |
|---|---|
| `rougeL` | F-measure ROUGE-L contra a resposta de referência — proximidade textual (ver apêndice) |
| `doc_ids` | Fração das citações da referência que a resposta também cita |
| `formato` | 1.0 se cita um documento **e** encerra recomendando validação médica |

**Detalhe metodológico decisivo:** o `evaluate.py` gera **sem contexto do RAG**.
Ele mede o que ficou nos *pesos*, não o que o sistema entrega. Por isso a
avaliação foi feita duas vezes.

### E.2 O que ficou nos pesos (sem RAG)

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` (fine-tuned) | **0,239** | 0,111 | **1,000** |
| `llama3.1:8b` (base) | 0,108 | 0,222 | 0,111 |

O número que importa não é a média de ROUGE-L, é a consistência: o `medassist`
ganhou do base **nos 9 de 9 exemplos**, com faixas que não se sobrepõem
(0,189–0,335 contra 0,051–0,168). Com n=9, uma média isolada seria frágil; uma
varredura limpa não é.

**`formato` 9/9 contra 1/9 é o resultado honesto do fine-tuning** — é a única
métrica que isola o que o QLoRA deveria ensinar. E o único acerto do base é
revelador: é o exemplo cuja pergunta já contém o identificador (*"Explique o
protocolo **PROT-015**…"*). Ele apenas ecoou.

**`doc_ids` parece favorecer o base — é artefato da métrica.** Quando a
referência não cita documento, o scorer dá ponto a quem *também* não citar nada.
O base tira nota cheia por não saber citar, e assim nunca é pego citando errado.

### E.3 O que o sistema entrega (com RAG)

O mesmo conjunto, mesma métrica, agora com os documentos recuperados no prompt:

| | ROUGE-L médio |
|---|---|
| `medassist` sem RAG (pesos) | 0,234 |
| `medassist` com RAG (produção) | **0,803** |

O ganho é uniforme — os 9 exemplos sobem, de 0,62 a 0,93. Isso **reatribui o
crédito** entre os componentes: o fine-tuning entregou **formato e registro**, o
RAG entregou **conteúdo**.

E explica por que 0,24 sem RAG **não é um resultado ruim**. Um valor alto ali
seria sinal de alerta: significaria que o 8B decorou os 25 protocolos — e modelo
que decora confabula com confiança quando o retrieval erra. O par 0,23 / 0,80 é
o perfil saudável.

### E.4 Comportamento verificado ponta a ponta

Além das métricas, estes cenários foram executados na stack completa (Docker +
GPU), com o modelo fine-tuned servido pelo Ollama:

| Cenário | Resultado |
|---|---|
| Pergunta clínica sem paciente | Cita `PROT-001 §2`, fontes no rodapé casando com a seção do corpo |
| Pergunta sobre modelo de documento | Cita `PROT-026 §2` com a estrutura real do laudo |
| Pergunta fora de escopo | Recusa imediata, sem chamar LLM |
| Paciente com exame crítico (K+ 6,2) | Pausa para aprovação humana; após aprovar, registra alerta crítico e alerta de conduta |
| Paciente com exame pendente | Resposta acrescenta "há exame(s) pendente(s) que podem alterar a conduta" |
| Paciente alérgico + pergunta por doses | `resposta_segura` com `violação de segurança: alergia_paciente` |
| Trilha de auditoria | 10 eventos JSON por `ask`, com `thread_id` íntegro, sem PII |

### E.5 Limitações

- **n = 9.** Suficiente para "o fine-tune pegou?", insuficiente para
  significância estatística fina.
- O `val.jsonl` sai do **mesmo gerador determinístico** do treino. Mede ajuste
  *dentro da distribuição*, não generalização clínica.
- O bloqueio por alergia é a **segunda** camada: a instrução no contexto costuma
  bastar, então o guardrail só dispara quando o modelo desobedece. Medido: 0
  bloqueios em 3 execuções de uma pergunta genérica, 3 em 3 quando a pergunta
  força a seção de doses.
- Nenhuma métrica aqui mede correção clínica.

## F. Conclusão: fine-tuned vs. modelo base

**O fine-tuning entregou o que se propôs, e não entregou o que não cabia nele.**

O que mudou de forma inequívoca foi o **comportamento de saída**: citar a fonte
e encerrar pedindo validação médica, em 9 de 9 respostas contra 1 de 9 do base —
e esse único acerto foi eco da pergunta. Como a explicabilidade é requisito do
produto e o guardrail determinístico é quem libera a resposta, esse
comportamento não é cosmético: é o que faz o sistema funcionar de ponta a ponta.
Um modelo base plugado no mesmo grafo teria suas respostas recusadas na maior
parte das vezes.

O que o fine-tuning **não** fez foi ensinar os protocolos ao modelo — e isso é
projeto, não falha. ROUGE-L de 0,234 sem contexto contra 0,803 com contexto
mostra que o conhecimento vive no índice do RAG, onde pode ser atualizado
reindexando um Markdown. Um hospital que revisa um protocolo não deveria
precisar de uma GPU para o assistente saber disso.

| Componente | Responsabilidade | Evidência |
|---|---|---|
| Fine-tuning | Formato, registro clínico em PT-BR, disciplina de citação | `formato` 1,000 × 0,111 |
| RAG | Conteúdo factual e rastreável | ROUGE-L 0,234 → 0,803 |
| Grafo/guardrails | Segurança, validação humana, auditoria | 100% determinístico, testável |

### F.1 Um corolário: o comportamento do modelo como restrição de projeto

O episódio mais útil do projeto não está em nenhuma métrica. Os modelos de
documento nasceram com identificadores próprios (`TPL-001..003`), o que é
semanticamente mais limpo. O modelo, fine-tuned em 425 exemplos que citam
`PROT-NNN`, **não conseguia usá-los**: com o documento certo recuperado e
presente no contexto, respondia *"Conforme PROT-002 §1…"* — prefixo inexistente,
número aleatório e conteúdo inventado.

Duas correções falharam. Instruir no system prompt "copie o identificador
exatamente como aparece no contexto" não mudou nada — em um caso piorou.
Retreinar com uma fatia `TPL-` (14 exemplos em 439) também não: o modelo
continuou citando `PROT-` até em prompts que estavam literalmente no treino,
porque 14 exemplos são ~1,8 passos de gradiente numa corrida de 56, contra 425
reforçando o padrão oposto.

O que resolveu foi **renomear os documentos para `PROT-026..028`** — 3/3
corretos com o mesmo GGUF já servido, sem nenhum retreino.

A generalização vale mais que o caso: o comportamento de citação de um modelo
fine-tuned é uma **restrição do sistema**, não uma preferência ajustável. Quando
o esquema de identificadores é escolha do projeto e o comportamento do modelo
não é, alinhar o esquema ao modelo sai mais barato e mais confiável do que
treinar o modelo contra o próprio prior.

### F.2 Ressalva

Os dados são sintéticos e determinísticos por escolha — o que garante
reprodutibilidade e ausência de PII real, mas significa que nenhum número aqui
é evidência de desempenho clínico. A validação médica não é uma ressalva do
relatório: é parte do produto.

## Apêndice — o que é ROUGE-L

ROUGE é uma família de métricas criada para avaliar sumarização automática — a
sigla é *Recall-Oriented Understudy for Gisting Evaluation*. Todas comparam um
texto gerado com um texto de referência escrito por humanos. O que muda entre as
variantes é **o que** se compara.

A **ROUGE-L** usa a **maior subsequência comum** (LCS). "Subsequência", não
"substring": as palavras precisam aparecer **na mesma ordem**, mas não precisam
estar coladas. Inserções no meio da frase não destroem a pontuação — o que faz
sentido para texto livre, onde duas respostas corretas raramente têm as mesmas
palavras seguidas.

```
referência: "aplicar o pacote da primeira hora coletando lactato"
gerado:     "aplicar imediatamente o pacote da primeira hora e coletar lactato"

LCS = "aplicar o pacote da primeira hora lactato"   →  7 palavras

precisão  = 7 / 11  (tamanho do gerado)     = 0,64
recall    = 7 / 9   (tamanho da referência) = 0,78
F-measure = média harmônica                 = 0,70   ← é este que o relatório usa
```

| Mede | Não mede |
|---|---|
| Sobreposição lexical na ordem certa | **Correção factual.** Uma resposta clinicamente errada com as palavras certas pontua alto |
| Se o modelo aprendeu o vocabulário e o fraseado do domínio | **Sinônimo e paráfrase.** "Reposição volêmica" e "hidratação endovenosa" contam como divergência total |
| Cobertura — o recall pune resposta curta que deixa conteúdo de fora | **Utilidade clínica** |

**Que valor é "bom"?** Não há escala absoluta — depende da tarefa e de quão
livre é a formulação da referência. Em benchmarks públicos de sumarização,
ROUGE-L costuma ficar entre 0,2 e 0,4, e o estado da arte não chega perto de
1,0. Comparar valores entre projetos diferentes não significa nada; o uso
legítimo é **comparar dois sistemas no mesmo conjunto**, que é o que §E.2 faz.

E há o ponto contraintuitivo deste projeto: aqui, **ROUGE-L alto sem RAG seria
um mau sinal**. As referências são trechos dos protocolos; um modelo que os
reproduzisse de memória teria decorado o corpus — e um modelo que decorou é
exatamente o que alucina com confiança quando o retrieval falha. Os 0,234 medem
"aprendeu o registro"; os 0,803 com RAG medem "reescreve com fidelidade o que
recebe".

Outras variantes, para referência: **ROUGE-N** (1, 2) compara n-gramas, exigindo
adjacência; **ROUGE-W** pesa subsequências contíguas; **BERTScore** e afins
comparam *embeddings* em vez de palavras, reconhecendo paráfrase ao custo de
depender de outro modelo para avaliar.
