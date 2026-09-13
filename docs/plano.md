# Plano de Implementação — Tech Challenge Fase 3 (8IADT)

**Projeto:** Assistente Virtual Médico com LLM fine-tuned + LangChain/LangGraph
**Peso:** 90% da nota de todas as disciplinas da fase.

## 1. Visão geral da solução

Um assistente médico que responde dúvidas clínicas de médicos com base em protocolos internos do hospital, consulta prontuários estruturados, orquestra fluxos de decisão (exames pendentes → sugestão de tratamento → alertas) via LangGraph, e opera com guardrails de segurança, logging auditável e citação de fontes.

```
                          ┌─────────────────────────────────────────┐
                          │              LangGraph                  │
 Pergunta do médico ──►   │  triagem → contexto do paciente (SQL)   │
 + ID do paciente         │  → exames pendentes → RAG (protocolos)  │
                          │  → LLM fine-tuned → guardrails/validação│
                          │  → alertas → resposta com fontes        │
                          └─────────────────────────────────────────┘
                               ▲                    ▲
                       SQLite (prontuários)   ChromaDB (protocolos,
                                              laudos, FAQ) + citações
```

## 2. Stack técnica (decisões)

| Componente | Escolha | Justificativa |
|---|---|---|
| Modelo base | `Llama-3.2-3B-Instruct` (fallback: `Qwen2.5-3B` ou `TinyLlama-1.1B`) | Cabe em GPU T4 grátis (Colab/Kaggle) com QLoRA; atende ao requisito "LLaMA ou outro" |
| Fine-tuning | Unsloth + PEFT/TRL (`SFTTrainer`), QLoRA 4-bit — **fora da VPS** (Colab/Kaggle GPU) | A VPS não tem GPU; só o artefato final (GGUF) vai para produção |
| Inferência (produção) | **Ollama em CPU** servindo o modelo fine-tuned em GGUF quantizado (Q4_K_M) | 3B Q4 ocupa ~2,5 GB de RAM e roda a velocidade aceitável em CPU |
| Deploy | **Monolito em Docker Compose** numa VPS 16 GB RAM / sem GPU | Ver §5 — Infraestrutura |
| Orquestração | LangChain (chains, retriever, tools) + LangGraph (fluxo de decisão) | Requisito obrigatório |
| RAG / Vetores | ChromaDB **embutido** (modo persistente, dentro do monolito) + embeddings `sentence-transformers` (ex.: `all-MiniLM-L6-v2` ou multilíngue) | Sem serviço extra; menos RAM; metadados para citação de fonte |
| Base estruturada | SQLite com pacientes/exames/prescrições sintéticos (embutido no monolito, volume Docker) | Requisito "consultas em base de dados estruturadas" sem infra pesada |
| Anonimização | Microsoft Presidio + regex custom (CPF, CRM, nomes) | Requisito de preprocessing/anonimização |
| Logging | `structlog` (JSON) + arquivo de auditoria por sessão | Requisito de auditoria/rastreamento |
| Avaliação | ROUGE/BERTScore + LLM-as-judge + comparação base vs. fine-tuned | Requisito "avaliação do modelo" |
| UI da demo | Streamlit (chat) + CLI | Facilita o vídeo de 15 min |

## 3. Estrutura do repositório

```
iadt-langgraph/
├── README.md                  # instruções completas (requisito)
├── PLANO.md
├── pyproject.toml             # deps com uv/poetry
├── Dockerfile                 # imagem do monolito (multi-stage)
├── docker-compose.yml         # app + ollama + caddy (ver §5)
├── .dockerignore
├── .env.example
├── deploy/
│   ├── Modelfile              # ollama create medassist -f Modelfile (GGUF fine-tuned)
│   ├── Caddyfile              # reverse proxy + TLS + basic auth
│   └── entrypoint.sh          # seed do SQLite + ingest do Chroma se volumes vazios
├── data/
│   ├── raw/                   # PubMedQA / MedQuAD baixados (gitignored)
│   ├── synthetic/             # protocolos, FAQ, laudos sintéticos (entregável)
│   └── processed/             # dataset final de fine-tuning (JSONL chat format)
├── src/medassist/
│   ├── config.py
│   ├── data/                  # download, preprocessing, anonimização, curadoria
│   │   ├── download.py
│   │   ├── preprocess.py
│   │   ├── anonymize.py
│   │   └── build_dataset.py
│   ├── finetune/
│   │   ├── train.py           # QLoRA/Unsloth (roda no Colab também — notebook espelho)
│   │   ├── evaluate.py        # métricas + comparação base vs. tuned
│   │   └── export.py          # merge/GGUF p/ Ollama
│   ├── rag/
│   │   ├── ingest.py          # chunking + embeddings + ChromaDB c/ metadados de fonte
│   │   └── retriever.py
│   ├── db/
│   │   ├── schema.sql         # pacientes, exames, prescrições, alertas
│   │   ├── seed.py            # dados sintéticos
│   │   └── queries.py         # tools: exames pendentes, histórico, alergias
│   ├── assistant/
│   │   ├── llm.py             # carrega LLM fine-tuned (Ollama/HF)
│   │   ├── chains.py          # LangChain: prompt + retriever + contexto paciente
│   │   ├── graph.py           # LangGraph: nós e arestas do fluxo de decisão
│   │   ├── guardrails.py      # validação de saída, escopo, disclaimers
│   │   └── explain.py         # montagem de citações/fontes
│   ├── logging_setup.py
│   └── ui/
│       ├── cli.py
│       └── app_streamlit.py
├── notebooks/
│   ├── 01_data_prep.ipynb
│   ├── 02_finetune_colab.ipynb
│   └── 03_evaluation.ipynb
├── tests/
├── docs/
│   ├── relatorio_tecnico.md   # entregável
│   └── diagrama_fluxo.md      # mermaid do fluxo LangChain/LangGraph
└── logs/                      # auditoria (gitignored, com exemplo commitado)
```

## 4. Fases de execução

### Fase 0 — Setup (½ dia)
- [ ] `git init`, estrutura de pastas, `pyproject.toml` (Python 3.11+), `.gitignore`, `.env.example`.
- [ ] Instalar deps núcleo: `langchain`, `langgraph`, `langchain-community`, `chromadb`, `sentence-transformers`, `structlog`, `streamlit`.
- [ ] Validar acesso a GPU (Colab/Kaggle) para o fine-tuning.

### Fase 1 — Dados (1–2 dias)
- [ ] Baixar **MedQuAD** (Q&A de saúde, ~47k pares) e opcionalmente **PubMedQA** (os dois sugeridos no enunciado).
- [ ] Gerar **dados sintéticos do "hospital"** (isto é o diferencial exigido — "dados próprios do hospital"):
  - ~30–50 protocolos clínicos internos (ex.: manejo de sepse, dor torácica, hipoglicemia) em Markdown com códigos de documento (`PROT-001`) para citação;
  - ~100–200 FAQs de médicos (pergunta → resposta baseada em protocolo);
  - Modelos de laudos, receitas e procedimentos.
- [ ] Pipeline de preprocessing: limpeza, deduplicação, normalização.
- [ ] **Anonimização** (Presidio + regex p/ CPF, CRM, nomes, datas) — demonstrar antes/depois no relatório.
- [ ] Curadoria: filtro de qualidade (comprimento, relevância clínica), revisão amostral.
- [ ] Converter para formato chat JSONL (system/user/assistant) e split train/val (95/5).

### Fase 2 — Fine-tuning (2–3 dias)
- [ ] Notebook Colab com Unsloth: QLoRA 4-bit, r=16, lr 2e-4, 1–3 épocas, ~2–5k exemplos.
- [ ] System prompt fixo no treino que já ensina o comportamento seguro ("nunca prescreva sem validação humana; cite a fonte").
- [ ] Salvar adaptadores LoRA no repo (~100 MB) + push opcional ao HF Hub.
- [ ] Export GGUF quantizado → `Modelfile` do Ollama para inferência local.
- [ ] **Avaliação** (`evaluate.py` + notebook 03):
  - loss/perplexity em validação;
  - ROUGE-L / BERTScore contra respostas de referência;
  - LLM-as-judge (rubrica: correção clínica, aderência ao protocolo, segurança);
  - Tabela comparativa **modelo base vs. fine-tuned** com exemplos qualitativos.

### Fase 3 — Base estruturada + RAG (1–2 dias)
- [ ] SQLite: tabelas `pacientes`, `exames` (com status pendente/concluído), `prescricoes`, `alergias`, `alertas`; seed com 10–20 pacientes sintéticos.
- [ ] Tools LangChain: `get_patient_context(id)`, `get_pending_exams(id)`, `create_alert(...)`.
- [ ] Ingestão RAG: chunking dos protocolos/laudos com metadados (`doc_id`, `titulo`, `secao`) → ChromaDB.
- [ ] Retriever com score mínimo; se nada relevante, o assistente diz que não encontrou protocolo aplicável.

### Fase 4 — Assistente LangChain + fluxo LangGraph (2–3 dias)
Grafo (`graph.py`) com estado tipado (`TypedDict`: pergunta, paciente, contexto, docs, resposta, alertas, aprovação):

1. **`triagem`** — classifica a entrada (dúvida clínica geral / caso de paciente / fora de escopo → recusa educada);
2. **`contexto_paciente`** — consulta SQLite (histórico, alergias);
3. **`verificar_exames`** — checa exames pendentes; se houver, adiciona aviso à resposta;
4. **`recuperar_protocolos`** — RAG nos documentos internos;
5. **`gerar_resposta`** — LLM fine-tuned com contexto + docs;
6. **`guardrails`** — valida a saída (nó condicional: reprova → regenera ou bloqueia);
7. **`emitir_alertas`** — grava alerta na base p/ equipe médica quando o caso exige (ex.: valor crítico de exame);
8. **`formatar_resposta`** — anexa fontes citadas (`PROT-001 §2`) e disclaimer de validação humana.

- [ ] Aresta condicional de **human-in-the-loop** (interrupt do LangGraph) para sugestões de tratamento: exige confirmação antes de registrar.
- [ ] Diagrama do grafo exportado (mermaid via `graph.get_graph().draw_mermaid()`) para o relatório.

### Fase 5 — Segurança, logging e explainability (1 dia, transversal)
- [ ] **Guardrails** (`guardrails.py`): lista de ações proibidas (prescrição direta, dosagem sem validação, diagnóstico definitivo); validador de saída (regex + chamada de verificação ao LLM); disclaimers obrigatórios.
- [ ] **Logging**: `structlog` JSON por nó do grafo (timestamp, input, output, docs usados, decisão dos guardrails, latência) → `logs/audit_YYYYMMDD.jsonl`.
- [ ] **Explainability**: toda resposta lista as fontes (documento + seção) dos chunks usados; respostas sem fonte recuperada são marcadas como "conhecimento geral do modelo — validar".

### Fase 6 — UI e demo (1 dia)
- [ ] Streamlit: chat com seleção de paciente, exibição de fontes, painel de alertas e visualização dos logs.
- [ ] CLI equivalente para uso rápido.

### Fase 7 — Containerização e deploy na VPS (1 dia)
- [ ] `Dockerfile` multi-stage do monolito (builder com deps de compilação → runtime slim, usuário não-root).
- [ ] `docker-compose.yml` com `app`, `ollama`, `model-init` e `caddy` (ver §5).
- [ ] `entrypoint.sh`: na primeira subida, roda `db/seed.py` e `rag/ingest.py` se os volumes estiverem vazios (deploy idempotente).
- [ ] Testar o compose completo localmente **em CPU** antes da VPS (mesma imagem, mesmo compose).
- [ ] Provisionar VPS: Docker Engine + compose plugin, `ufw` (só 22/80/443), swap de 4 GB como colchão.
- [ ] Subir: `git clone` → copiar `.env` → `docker compose up -d` → smoke test dos healthchecks.
- [ ] Backup: cron de `tar` dos volumes (`app_data`, `logs`) para fora da VPS.

### Fase 8 — Documentação e entrega (1–2 dias)
- [ ] **README**: setup passo a passo (venv, deps, download de dados, treino, `docker compose up`), arquitetura, exemplos de uso.
- [ ] **Relatório técnico** (`docs/relatorio_tecnico.md`, exportar PDF): processo de fine-tuning, descrição do assistente, diagrama do fluxo, avaliação e análise de resultados.
- [ ] **Vídeo ≤15 min** — roteiro:
  1. (2 min) Arquitetura e dataset;
  2. (4 min) Fine-tuning: notebook, curvas de loss, comparação base vs. tuned;
  3. (5 min) Demo do fluxo: pergunta clínica com paciente → exames pendentes → resposta com fontes → alerta;
  4. (2 min) Guardrails em ação (tentativa de prescrição bloqueada) + logs de auditoria;
  5. (2 min) Avaliação e conclusões.

## 5. Infraestrutura e deploy (VPS 16 GB RAM, sem GPU)

### 5.1 Premissas

- **Treino e inferência são separados.** O fine-tuning roda no Colab/Kaggle (GPU); a VPS recebe apenas o artefato final: o GGUF quantizado. Nada de PyTorch/CUDA na imagem de produção.
- **Monolito**: um único container de aplicação (`app`) com UI Streamlit + grafo LangGraph + ChromaDB embutido + SQLite. Ollama é o único "serviço de dependência" real — modelo de inferência não pertence dentro do processo Python.
- **CPU-only**: modelo 3B em Q4_K_M rende ~6–15 tok/s em 4 vCPUs — aceitável para chat de demo. Modelos 7B+ ficam lentos demais; o teto prático desta VPS é 3B (ou 7B Q4 como experimento, ~4,5 GB de RAM).

### 5.2 Requisitos da VPS

| Item | Mínimo | Observação |
|---|---|---|
| RAM | 16 GB | ver orçamento em 5.4 |
| vCPU | 4+ | inferência escala com threads (`OLLAMA_NUM_THREADS`) |
| Disco | 40 GB SSD | imagem (~2 GB) + GGUF (~2,5 GB) + embeddings + volumes + folga |
| SO | Ubuntu 22.04/24.04 LTS | Docker Engine + compose plugin |
| Swap | 4 GB | colchão contra OOM-kill durante picos |
| Rede | portas 80/443 abertas; 22 restrita | `ufw` + fail2ban |

### 5.3 Topologia do Compose

```yaml
# docker-compose.yml (esboço)
services:
  ollama:
    image: ollama/ollama:latest
    volumes: ["ollama_models:/root/.ollama", "./deploy/Modelfile:/Modelfile:ro"]
    environment:
      - OLLAMA_NUM_PARALLEL=1        # 1 requisição por vez — protege a RAM
      - OLLAMA_MAX_LOADED_MODELS=1
      - OLLAMA_KEEP_ALIVE=-1         # modelo sempre carregado (evita cold start de ~30s)
    mem_limit: 6g
    restart: unless-stopped
    healthcheck: {test: ["CMD", "ollama", "ls"], interval: 30s}

  model-init:                        # one-shot: registra o modelo fine-tuned
    image: ollama/ollama:latest
    depends_on: {ollama: {condition: service_healthy}}
    environment: [OLLAMA_HOST=http://ollama:11434]
    volumes: ["./deploy:/deploy:ro", "./models:/models:ro"]  # GGUF baixado no deploy
    entrypoint: ["ollama", "create", "medassist", "-f", "/deploy/Modelfile"]
    restart: "no"

  app:                               # monolito: Streamlit + LangGraph + Chroma + SQLite
    build: .
    depends_on: {ollama: {condition: service_healthy}}
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - MEDASSIST_MODEL=medassist
    volumes: ["app_data:/app/data", "app_logs:/app/logs"]
    mem_limit: 4g
    restart: unless-stopped
    expose: ["8501"]
    healthcheck: {test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"], interval: 30s}

  caddy:                             # única porta pública; TLS automático + basic auth
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: ["./deploy/Caddyfile:/etc/caddy/Caddyfile:ro", "caddy_data:/data"]
    restart: unless-stopped

volumes: {ollama_models: {}, app_data: {}, app_logs: {}, caddy_data: {}}
```

Decisões embutidas aí:

- **`OLLAMA_NUM_PARALLEL=1` + `KEEP_ALIVE=-1`**: em CPU, duas gerações simultâneas duplicam a RAM do contexto e arrastam as duas; fila de 1 é mais rápido no agregado. Manter o modelo residente elimina o cold start a cada pergunta.
- **`model-init` como serviço one-shot**: o GGUF não vai para o Git (~2,5 GB) — o passo de deploy baixa o arquivo (HF Hub/release) para `./models/` e o `ollama create` registra com o system prompt do `Modelfile`.
- **`mem_limit` explícito em app e ollama**: se algo vazar memória, o Docker mata o container (que reinicia via `restart`) em vez de o kernel derrubar a VPS inteira.
- **Só o Caddy é público**: Streamlit e Ollama ficam na rede interna do compose. Basic auth no Caddyfile protege a demo; TLS é automático (Let's Encrypt) se houver domínio apontado.
- **Chroma e SQLite embutidos** no container `app` com volume persistente: menos serviços, menos RAM, backup = tar dos volumes.

### 5.4 Orçamento de RAM (16 GB)

| Consumidor | Estimativa |
|---|---|
| SO + Docker daemon | ~1,5 GB |
| Ollama + Llama-3.2-3B Q4_K_M + ctx 4k | ~4,0 GB (limite 6) |
| App: Streamlit + LangGraph + Chroma + embeddings (MiniLM) | ~2,0 GB (limite 4) |
| Caddy | ~50 MB |
| **Total típico** | **~7,5 GB** |
| **Folga** | **~8,5 GB** (picos de contexto, ingest, upgrade p/ 7B se quiser testar) |

### 5.5 Regras de desenvolvimento decorrentes

- **Paridade dev/prod**: rodar `docker compose up` localmente desde a Fase 3 — o compose *é* o ambiente de referência, não um passo final.
- A imagem do `app` **não instala** `torch`/`transformers` de treino; dependências de fine-tuning ficam num extra separado (`pyproject` → `[project.optional-dependencies] train`) usado só nos notebooks.
- Toda configuração via env vars (12-factor): `OLLAMA_BASE_URL`, caminhos de dados, credenciais do basic auth — nada hardcoded, `.env.example` documentado.
- Embeddings: usar cache do HF baixado no build da imagem (ou volume), para o container subir offline e rápido.

## 6. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Sem GPU / limite do Colab | Modelo 1–3B + QLoRA 4-bit; TinyLlama como plano C; treinar com subset menor |
| Inferência lenta em CPU na VPS | Q4_K_M, ctx 4k, `NUM_PARALLEL=1`, streaming de tokens na UI (percepção de velocidade); prompt enxuto (top-k=4 no RAG) |
| OOM na VPS | `mem_limit` por container + swap 4 GB + `KEEP_ALIVE=-1` com 1 modelo carregado |
| Dataset em inglês (MedQuAD) vs. demo em PT-BR | Fine-tuning com mix: MedQuAD (conhecimento) + sintéticos em PT-BR (comportamento); ou traduzir amostra |
| Qualidade baixa do modelo pequeno | O RAG carrega o conteúdo factual; o fine-tuning foca em formato, tom e segurança |
| Alucinação clínica | Guardrails + citação obrigatória + disclaimer de validação humana (também é requisito) |
| Tempo do grupo | Fases 3–4 independem do fine-tuning terminar (usar modelo base como stub até os adaptadores ficarem prontos) |

## 7. Cronograma sugerido (~2 semanas)

| Semana | Entregas |
|---|---|
| 1 | Fases 0–2: setup, dataset pronto e anonimizado, fine-tuning rodando + avaliação inicial |
| 2 | Fases 3–8: RAG + SQLite, grafo LangGraph completo, guardrails/logs, UI, **compose na VPS**, relatório e vídeo |

## 8. Checklist de conformidade com o enunciado

- [ ] Fine-tuning de LLM com protocolos, FAQs e modelos de laudos ✔ Fases 1–2
- [ ] Preprocessing, anonimização e curadoria ✔ Fase 1
- [ ] LangChain integrando a LLM customizada ✔ Fase 4
- [ ] Consultas em base estruturada (prontuários) ✔ Fase 3
- [ ] Contextualização com dados atualizados do paciente ✔ Fases 3–4
- [ ] Limites de atuação / nunca prescrever sem validação humana ✔ Fase 5
- [ ] Logging detalhado para auditoria ✔ Fase 5
- [ ] Explainability com fonte da informação ✔ Fase 5
- [ ] Projeto modularizado + README ✔ Estrutura §3 + Fase 8
- [ ] Fluxos do LangGraph ✔ Fase 4
- [ ] Dataset anonimizado/sintético no repo ✔ Fase 1
- [ ] Relatório técnico com diagrama e avaliação ✔ Fase 8
- [ ] Vídeo ≤15 min ✔ Fase 8
