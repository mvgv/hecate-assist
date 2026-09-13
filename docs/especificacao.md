# ESPECIFICACAO.md — Assistente Médico (Tech Challenge Fase 3)

> **Para o agente implementador:** este documento é autocontido e prescritivo. Siga-o na ordem do §16.
> Não altere decisões de arquitetura; se algo for impossível, implemente o mais próximo possível e registre o desvio em `docs/desvios.md`.
> Contexto adicional (não obrigatório para implementar): [PLANO.md](plano.md) e [docs/grafo_langgraph.md](grafo_langgraph.md).

## 1. Objetivo

Monolito Python que implementa um assistente virtual médico:
- responde dúvidas clínicas de médicos com base em protocolos internos (RAG com citação de fonte);
- consulta base estruturada de pacientes (SQLite): histórico, alergias, exames pendentes/críticos;
- orquestra o fluxo em **LangGraph** com guardrails, human-in-the-loop e alertas;
- roda em **CPU** (VPS 16 GB, sem GPU) via **Docker Compose** (app + Ollama + Caddy);
- logging estruturado de auditoria em todos os nós.

### Fora do escopo desta implementação
- **Executar** o fine-tuning (roda em Colab; você só cria os scripts/notebooks — §13).
- Baixar datasets externos reais (PubMedQA/MedQuAD) — criar apenas o script de download (§5.5).
- Autenticação de usuários na aplicação (basic auth fica no Caddy).

### Restrições obrigatórias
- Python **3.11+**. Sem `torch`/`transformers`/CUDA nas dependências de runtime (só no extra `train`).
- Todo o sistema deve funcionar **sem Ollama disponível**, usando o provider `fake` (§8) — é assim que os testes rodam.
- Idioma de todo texto voltado ao usuário: **PT-BR**.
- Nenhum segredo hardcoded; tudo via env vars (§4).

## 2. Dependências

`pyproject.toml` (gerenciador: `uv`; se indisponível, `pip` + `requirements.txt` gerado):

```toml
[project]
name = "medassist"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "langchain>=0.3",
  "langchain-community>=0.3",
  "langchain-ollama>=0.2",
  "langgraph>=0.2",
  "langgraph-checkpoint-sqlite>=2.0",
  "chromadb>=0.5",
  "sentence-transformers>=3.0",
  "structlog>=24.0",
  "streamlit>=1.38",
  "typer>=0.12",
  "pydantic>=2.8",
  "pydantic-settings>=2.4",
  "requests>=2.32",
]

[project.optional-dependencies]
train = ["datasets", "peft", "trl", "bitsandbytes", "unsloth"]  # usado só em notebooks/Colab
dev = ["pytest>=8.0", "pytest-cov", "ruff"]

[project.scripts]
medassist = "medassist.ui.cli:app"
```

## 3. Estrutura de arquivos (obrigatória)

```
iadt-langgraph/
├── README.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── .gitignore
├── Makefile
├── deploy/
│   ├── Modelfile
│   ├── Caddyfile
│   └── entrypoint.sh
├── data/
│   ├── raw/.gitkeep
│   ├── synthetic/
│   │   ├── protocolos/            # PROT-001.md ... (gerados pelo seed, commitados)
│   │   ├── faqs.jsonl
│   │   └── templates/             # laudo.md, receita.md, procedimento.md
│   └── processed/.gitkeep
├── src/medassist/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_setup.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── download.py
│   │   ├── anonymize.py
│   │   ├── generate_synthetic.py
│   │   └── build_dataset.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql
│   │   ├── seed.py
│   │   └── queries.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   └── retriever.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── fake.py
│   │   └── ollama_provider.py
│   ├── assistant/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── routing.py
│   │   ├── guardrails.py
│   │   ├── prompts.py
│   │   └── graph.py
│   ├── finetune/
│   │   ├── __init__.py
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   └── export.py
│   └── ui/
│       ├── __init__.py
│       ├── cli.py
│       └── app_streamlit.py
├── notebooks/
│   └── 02_finetune_colab.ipynb
├── tests/
│   ├── conftest.py
│   ├── test_anonymize.py
│   ├── test_db.py
│   ├── test_rag.py
│   ├── test_guardrails.py
│   └── test_graph.py
└── docs/
    ├── grafo_langgraph.md         # já existe
    └── relatorio_tecnico.md       # esqueleto com seções (preenchido depois)
```

## 4. Configuração — `config.py`

`pydantic_settings.BaseSettings`, prefixo `MEDASSIST_`, carrega `.env`:

| Env var | Default | Uso |
|---|---|---|
| `MEDASSIST_LLM_PROVIDER` | `fake` | `fake` \| `ollama` |
| `MEDASSIST_MODEL` | `medassist` | nome do modelo no Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | endpoint Ollama (sem prefixo MEDASSIST) |
| `MEDASSIST_DATA_DIR` | `data` | raiz de dados |
| `MEDASSIST_DB_PATH` | `data/medassist.db` | SQLite de pacientes |
| `MEDASSIST_CHECKPOINT_PATH` | `data/checkpoints.db` | SQLite do LangGraph |
| `MEDASSIST_CHROMA_DIR` | `data/chroma` | persistência do Chroma |
| `MEDASSIST_LOG_DIR` | `logs` | auditoria JSONL |
| `MEDASSIST_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | embeddings PT-BR |
| `MEDASSIST_RAG_TOP_K` | `4` | top-k do retriever |
| `MEDASSIST_RAG_MIN_SCORE` | `0.35` | corte de similaridade |
| `MEDASSIST_MAX_TENTATIVAS` | `2` | loop de regeneração |

Singleton acessível via `medassist.config.get_settings()` (com `lru_cache`).

## 5. Dados

### 5.1 Protocolos sintéticos — `data/synthetic/protocolos/PROT-NNN.md`

`generate_synthetic.py` gera (determinístico, sem LLM — conteúdo hardcoded em templates Python) **12 protocolos** com este formato exato:

```markdown
---
doc_id: PROT-001
titulo: Manejo Inicial de Sepse no Adulto
versao: "1.2"
atualizado_em: 2025-11-10
---

## 1. Definição e critérios
...

## 2. Conduta inicial
...

## 3. Medicações e doses de referência
...

## 4. Critérios de alerta e escalonamento
...
```

Temas (fixos): sepse, dor torácica, hipoglicemia, AVC isquêmico agudo, crise hipertensiva, anafilaxia, pneumonia comunitária, cetoacidose diabética, TEP, hemorragia digestiva alta, delirium no idoso, dor abdominal aguda. Cada protocolo: 300–600 palavras, seções `##` numeradas, conteúdo clinicamente plausível porém **fictício** (rodapé: "Documento sintético para fins acadêmicos").

### 5.2 FAQs — `data/synthetic/faqs.jsonl`

60 linhas, uma por pergunta:

```json
{"id": "FAQ-001", "pergunta": "Qual antibiótico empírico para PAC em paciente internado?", "resposta": "...", "doc_ref": "PROT-007"}
```

Respostas devem citar o `doc_ref` no texto (ex.: "Conforme PROT-007 §3, ...").

### 5.3 Dataset de fine-tuning — `build_dataset.py`

CLI (typer): `medassist build-dataset --out data/processed/`. Converte FAQs + protocolos (transformados em pares Q&A "explique o protocolo X") para JSONL formato chat:

```json
{"messages": [
  {"role": "system", "content": "<SYSTEM_PROMPT de prompts.py>"},
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "... [PROT-007 §3]"}
]}
```

Aplica `anonymize.py` em todos os textos; split 95/5 → `train.jsonl` / `val.jsonl`; imprime estatísticas (n exemplos, tokens aproximados).

### 5.4 Anonimização — `anonymize.py`

Função pura `anonimizar(texto: str) -> tuple[str, list[str]]` (texto limpo, lista de tipos de PII encontrados). Implementar com **regex** (sem Presidio — dependência pesada demais para o runtime):

| Padrão | Substituição |
|---|---|
| CPF (`\d{3}\.?\d{3}\.?\d{3}-?\d{2}`) | `[CPF]` |
| CRM (`CRM[-/ ]?[A-Z]{2}?\s?\d{4,6}`) | `[CRM]` |
| Telefone BR (`(\(?\d{2}\)?\s?)?9?\d{4}-?\d{4}`) | `[TELEFONE]` |
| E-mail | `[EMAIL]` |
| Datas completas (`\d{2}/\d{2}/\d{4}`) | `[DATA]` |
| Nomes após "paciente", "Dr.", "Dra." (`(?:paciente|Dr\.|Dra\.)\s+[A-ZÀ-Ü][a-zà-ü]+(\s[A-ZÀ-Ü][a-zà-ü]+)*`) | mantém o gatilho + `[NOME]` |

### 5.5 Download externo — `download.py`

CLI: `medassist download-data`. Baixa MedQuAD (clone raso do GitHub `abachaa/MedQuAD`) para `data/raw/`. Se offline, imprime instrução manual e sai com código 0. **Não é usado pelos testes.**

## 6. Banco estruturado — `db/`

### 6.1 `schema.sql`

```sql
CREATE TABLE IF NOT EXISTS pacientes (
  id TEXT PRIMARY KEY,              -- "P001"
  nome TEXT NOT NULL,               -- fictício
  data_nascimento TEXT NOT NULL,    -- ISO
  sexo TEXT CHECK (sexo IN ('M','F','O')),
  comorbidades TEXT NOT NULL DEFAULT '[]',   -- JSON array de strings
  medicacoes_em_uso TEXT NOT NULL DEFAULT '[]',
  criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alergias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paciente_id TEXT NOT NULL REFERENCES pacientes(id),
  substancia TEXT NOT NULL,         -- ex.: "penicilina"
  gravidade TEXT CHECK (gravidade IN ('leve','moderada','grave'))
);

CREATE TABLE IF NOT EXISTS exames (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paciente_id TEXT NOT NULL REFERENCES pacientes(id),
  tipo TEXT NOT NULL,               -- ex.: "potassio_serico"
  status TEXT NOT NULL CHECK (status IN ('pendente','concluido')),
  resultado REAL,                   -- NULL se pendente
  unidade TEXT,
  faixa_critica_min REAL,           -- fora de [min,max] => crítico
  faixa_critica_max REAL,
  solicitado_em TEXT NOT NULL,
  concluido_em TEXT
);

CREATE TABLE IF NOT EXISTS alertas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paciente_id TEXT NOT NULL REFERENCES pacientes(id),
  tipo TEXT NOT NULL,               -- 'exame_critico' | 'sugestao_tratamento'
  severidade TEXT NOT NULL CHECK (severidade IN ('info','atencao','critico')),
  mensagem TEXT NOT NULL,
  aprovado_por TEXT,
  criado_em TEXT DEFAULT (datetime('now')),
  UNIQUE (paciente_id, tipo, date(criado_em))   -- idempotência diária
);
```

### 6.2 `seed.py`

CLI: `medassist seed-db`. Idempotente (só insere se `pacientes` vazio). Cria **12 pacientes** fictícios cobrindo os casos de teste, obrigatoriamente incluindo:
- `P001`: alergia **grave a penicilina**, exame `potassio_serico` **concluído crítico** (6.2, faixa 3.5–5.5);
- `P002`: exame `hemograma` **pendente**;
- `P003`: sem alergias, sem pendências (caminho feliz).

### 6.3 `queries.py` — contratos

```python
def get_patient_context(paciente_id: str) -> dict | None
# {"id","nome","idade","sexo","comorbidades":[...],"medicacoes_em_uso":[...],
#  "alergias":[{"substancia","gravidade"}]}  | None se não existe

def get_pending_exams(paciente_id: str) -> list[dict]      # exames status='pendente'
def get_critical_exams(paciente_id: str) -> list[dict]     # concluídos fora da faixa crítica
def create_alert(paciente_id, tipo, severidade, mensagem, aprovado_por=None) -> int | None
# retorna id; None se violou UNIQUE (já existia hoje) — sem exceção
def list_alerts(paciente_id: str | None = None) -> list[dict]
```

Conexão via `sqlite3` stdlib, `row_factory` para dicts, context manager. Sem ORM.

## 7. RAG — `rag/`

- **`ingest.py`** — CLI `medassist ingest`: lê `data/synthetic/protocolos/*.md`, divide por seção `##` (1 chunk = 1 seção; se seção > 1200 chars, subdivide com overlap de 150), embute com `MEDASSIST_EMBEDDING_MODEL` e grava na collection Chroma `protocolos` (client persistente em `MEDASSIST_CHROMA_DIR`). Metadados por chunk: `{"doc_id","titulo","secao"}` (`secao` = título do `##`). Idempotente: apaga e recria a collection.
- **`retriever.py`**:

```python
class DocRecuperado(TypedDict):
    doc_id: str; titulo: str; secao: str; conteudo: str; score: float

def buscar(query: str, top_k: int | None = None, min_score: float | None = None) -> list[DocRecuperado]
```

Score = `1 - distancia_cosseno`, filtra por `min_score`. Collection vazia/ausente → `[]` (sem exceção).

## 8. Camada LLM — `llm/`

### 8.1 `base.py`

```python
class LLMProvider(Protocol):
    def gerar(self, system: str, mensagens: list[dict], contexto: str = "") -> str: ...
def get_llm() -> LLMProvider   # factory pela env MEDASSIST_LLM_PROVIDER
```

### 8.2 `fake.py` — FakeLLM (usado em testes e default)

Determinístico, roteado por palavras-chave do último turno do usuário (nesta ordem; primeira que casar vence):

| Gatilho na entrada | Resposta gerada |
|---|---|
| contém `"__forcar_prescricao__"` | `"Prescrever amoxicilina 500 mg VO 8/8h por 7 dias."` (viola guardrails — p/ teste de regeneração) |
| contém `"__forcar_alergia__"` | `"Sugere-se penicilina cristalina conforme [PROT-007 §3]."` (p/ teste de bloqueio com P001) |
| contexto RAG não-vazio | `"Com base no protocolo institucional [<doc_id do 1º doc> §<secao>], a conduta sugerida é ... Recomenda-se validação pelo médico responsável."` |
| contexto RAG vazio | `"Não há protocolo interno aplicável. Com base em conhecimento geral, ... Recomenda-se validação pelo médico responsável."` |

Se chamado como verificador de guardrails (system contém `"AVALIE"`), responde JSON `{"aprovada": true, "violacoes": []}` — a checagem cara no fake sempre aprova; os testes de reprovação usam a camada regex.

### 8.3 `ollama_provider.py`

`langchain_ollama.ChatOllama(model=settings.model, base_url=..., temperature=0.2, num_ctx=4096)`. Erro de conexão → `raise LLMIndisponivelError` (capturada pelo wrapper de nó → `erro` no estado).

## 9. Grafo — `assistant/`

### 9.1 `state.py` — copiar exatamente o `AssistantState` de [docs/grafo_langgraph.md](grafo_langgraph.md) §2.

### 9.2 `prompts.py`

Constantes: `SYSTEM_PROMPT` (assistente de apoio à decisão; NUNCA prescreve diretamente; sempre cita fonte `[DOC-ID §secao]`; sempre encerra recomendando validação humana), `PROMPT_TRIAGEM`, `PROMPT_VERIFICADOR` (contém a palavra `AVALIE`), `TEMPLATE_FEEDBACK_REGENERACAO`, `TEMPLATE_RESPOSTA_SEGURA`, `TEMPLATE_RECUSA`, `DISCLAIMER = "⚕️ Sugestão de apoio à decisão. Requer validação por médico responsável."`.

### 9.3 `nodes.py` — um função por nó, assinatura `def nome(state: AssistantState) -> dict`

Todos decorados com `@auditado` (§11). Comportamento conforme [docs/grafo_langgraph.md](grafo_langgraph.md) §3, com estas precisões:

- **`triagem`**: se `state["paciente_id"]` → `caso_paciente` sem chamar LLM. Senão, heurística determinística primeiro (sem termos clínicos de `TERMOS_CLINICOS` [lista ~40 palavras em `prompts.py`] → `fora_escopo`); em ambiguidade, chama o LLM de triagem.
- **`contexto_paciente`**: `get_patient_context`; `None` → `{"erro": "paciente_nao_encontrado"}`.
- **`verificar_exames`**: preenche `exames_pendentes` e `exames_criticos`; críticos ⇒ `requer_aprovacao: True`.
- **`recuperar_protocolos`**: query = pergunta + comorbidades (se houver paciente); preenche `docs`, `sem_fonte`.
- **`gerar_resposta`**: monta contexto (paciente + alergias em destaque + exames + chunks prefixados por `[doc_id §secao]`); se `tentativas > 0`, anexa `TEMPLATE_FEEDBACK_REGENERACAO` com `violacoes`; incrementa `tentativas`.
- **`guardrails`**: chama `guardrails.validar(state)` (§10) → `{"veredito", "violacoes", "requer_aprovacao"?}`.
- **`aprovacao_humana`**: `payload = interrupt({"resposta_proposta", "fontes", "motivo"})`; retorna `{"aprovacao": payload}` — payload esperado `{"aprovado": bool, "aprovador": str, "observacao": str}`.
- **`emitir_alertas`**: um alerta por exame crítico (`tipo='exame_critico'`, severidade `'critico'`) e/ou `'sugestao_tratamento'` aprovada (severidade `'atencao'`, `aprovado_por` do payload).
- **`formatar_resposta`**: `resposta_final` = resposta + avisos de exames pendentes + bloco `"📚 Fontes:"` (doc_ids citados na resposta ∩ `docs`; se `sem_fonte`, linha "Sem fonte interna — conhecimento geral do modelo, validar") + `DISCLAIMER`.
- **`resposta_segura`** / **`resposta_recusa`**: templates, sem LLM.

### 9.4 `routing.py`

```python
def rota_triagem(state) -> str      # "fora_escopo" | "duvida_clinica" | "caso_paciente"
def rota_guardrails(state) -> str   # "regenerar" | "bloqueada" | "aprovar" | "aprovada"
def rota_aprovacao(state) -> str    # "aprovado" | "rejeitado"
```

Regra global: qualquer nó que retorne `erro` ⇒ a próxima aresta condicional roteia para `resposta_segura`. Para arestas fixas, os nós seguintes fazem no-op se `state.get("erro")` (checagem no início de cada nó, dentro do decorator).

`rota_guardrails`: `veredito=="regenerar" and tentativas < MAX` → `"regenerar"`; `veredito=="bloqueada" or (regenerar and tentativas>=MAX)` → `"bloqueada"`; `aprovada and requer_aprovacao` → `"aprovar"`; senão `"aprovada"`.

### 9.5 `graph.py`

Montagem exata de [docs/grafo_langgraph.md](grafo_langgraph.md) §4. `construir_grafo(checkpointer=None)` — default `SqliteSaver` em `MEDASSIST_CHECKPOINT_PATH`; testes injetam `MemorySaver`. Expor `def responder(pergunta, paciente_id, thread_id) -> AssistantState` e `def retomar(thread_id, aprovado, aprovador, observacao) -> AssistantState` (usa `Command(resume=...)`).

## 10. Guardrails — `guardrails.py`

`def validar(state: AssistantState) -> dict` — duas camadas, na ordem:

**Camada 1 (regex/determinística)** sobre `resposta_bruta`:

| Código da violação | Detecção | Consequência |
|---|---|---|
| `alergia_paciente` | qualquer `substancia` das alergias do paciente (case-insensitive, singular/plural) aparece na resposta em contexto de sugestão | **`bloqueada`** (nunca regenera) |
| `prescricao_direta` | regex `\b(prescrever|prescrevo|administrar|tomar|aplicar)\b.*\d+\s?(mg|g|ml|mcg|ui)\b` (case-insensitive, DOTALL) **e** ausência de menção a validação (`validação|médico responsável|avaliar`) | `regenerar` |
| `diagnostico_definitivo` | `\bo paciente (tem|está com|é portador de)\b` sem hedge (`compatível|sugestivo|possível|provável`) | `regenerar` |
| `fonte_alucinada` | cita `[PROT-\d+` cujo doc_id ∉ `docs` | `regenerar` |

**Camada 2 (LLM verificador)** — executa somente se a camada 1 aprovou. Chama o provider ativo com `PROMPT_VERIFICADOR` (rubrica de segurança); resposta esperada em JSON `{"aprovada": bool, "violacoes": [...]}`; parse tolerante (falha de parse ⇒ considera aprovada e loga evento `verificador_ilegivel`). Com o provider `fake` esta camada sempre aprova (§8.2) — os testes de reprovação exercitam a camada 1.

`requer_aprovacao` adicional: resposta aprovada que contenha sugestão de conduta (`\b(sugere-se|recomenda-se|conduta|iniciar|tratamento)\b`) **e** `paciente_id` presente ⇒ `True`.

## 11. Logging — `logging_setup.py`

- `structlog` com processors: timestamp ISO, nível, mascaramento de PII (aplica `anonimizar()` nos valores string do evento) e `JSONRenderer`.
- Saída dupla: stdout + arquivo `MEDASSIST_LOG_DIR/audit_YYYYMMDD.jsonl`.
- Decorator `@auditado` (em `logging_setup.py`, importado por `nodes.py`): loga `no_iniciado`/`no_concluido` (nome do nó, `thread_id`, chaves do delta, duração ms) e captura exceção → `no_falhou` + retorna `{"erro": "<nó>: <msg>"}`. Também implementa o no-op quando `state.get("erro")` (retorna `{}` e loga `no_pulado`).

## 12. UI

### 12.1 CLI — `ui/cli.py` (typer, entry point `medassist`)

Comandos: `seed-db`, `ingest`, `build-dataset`, `download-data`, `ask "<pergunta>" [--paciente P001] [--thread t1]`, `resume <thread> --aprovado/--rejeitado [--aprovador NOME]`, `alerts [--paciente P001]`. `ask` imprime `resposta_final` e, se interrompido, o payload de aprovação pendente.

### 12.2 Streamlit — `ui/app_streamlit.py`

Uma página: sidebar (selectbox de paciente via `queries` + "sem paciente", campo thread_id auto), chat (`st.chat_message`/`st.chat_input`), respostas exibem fontes e disclaimer. Se o grafo interromper: `st.warning` com a resposta proposta + botões **Aprovar**/**Rejeitar** (chamam `retomar`). Expander "🔔 Alertas" listando `list_alerts()`. Expander "📜 Auditoria" com as últimas 50 linhas do log do dia. Sem streaming de tokens (provider síncrono) — usar `st.spinner`.

## 13. Fine-tuning (artefatos, não executar)

- `finetune/train.py`: script standalone (deps do extra `train`, import guard com mensagem clara se ausentes) — carrega `data/processed/train.jsonl`, QLoRA via Unsloth (`r=16, alpha=32, lr=2e-4, epochs=2, max_seq=2048`), salva adaptadores em `models/adapters/`.
- `finetune/evaluate.py`: compara base vs. tuned no `val.jsonl` (ROUGE-L via `rouge-score` se instalado; senão exact-substring de doc_ids citados) → `docs/avaliacao.md`.
- `finetune/export.py`: merge + instruções de conversão GGUF (llama.cpp) → `models/medassist-q4_k_m.gguf`.
- `notebooks/02_finetune_colab.ipynb`: espelho do train.py para Colab (células: install, mount, train, export, download).

## 14. Docker

### 14.1 `Dockerfile`
Multi-stage: `python:3.11-slim` builder (instala deps em venv) → runtime copia venv + `src/` + `data/synthetic/` + `deploy/entrypoint.sh`; usuário não-root `medassist`; **pré-baixa o modelo de embeddings no build** (`RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('<modelo>')"`); `ENTRYPOINT ["/app/deploy/entrypoint.sh"]`, CMD streamlit na porta 8501, endereço `0.0.0.0`.

### 14.2 `deploy/entrypoint.sh`
`set -e`; roda `medassist seed-db` e `medassist ingest` (idempotentes); depois `exec "$@"`.

### 14.3 `docker-compose.yml`
Copiar a topologia do [PLANO.md](plano.md) §5.3 (serviços `ollama`, `model-init`, `app`, `caddy`; volumes; mem_limits; healthchecks; `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=-1`). `app` com `MEDASSIST_LLM_PROVIDER=ollama`. Adicionar `profiles: ["full"]` a `model-init` e `caddy` para que `docker compose up` local suba só `app`+`ollama`.

### 14.4 `deploy/Modelfile`
`FROM /models/medassist-q4_k_m.gguf`, `SYSTEM` = `SYSTEM_PROMPT`, `PARAMETER temperature 0.2`, `PARAMETER num_ctx 4096`. Comentário: enquanto não houver GGUF fine-tuned, usar `FROM llama3.2:3b`.

### 14.5 `deploy/Caddyfile`
Reverse proxy `:443` → `app:8501` com `basic_auth` (hash via env) e fallback `:80` para ambiente sem domínio.

## 15. Testes — `tests/`

`conftest.py`: fixtures `tmp_settings` (redireciona todos os paths para `tmp_path`, provider `fake`), `db_seeded`, `chroma_ingested`, `grafo` (com `MemorySaver`). Cenários obrigatórios (tabela de [docs/grafo_langgraph.md](grafo_langgraph.md) §6):

| Teste | Asserções principais |
|---|---|
| pergunta geral | `resposta_final` contém "📚 Fontes" e um `PROT-`; sem interrupt |
| P002 + exame pendente | resposta contém aviso de pendência |
| sugestão de tratamento p/ P003 | grafo interrompe; `retomar(aprovado=True)` grava alerta `sugestao_tratamento` |
| `__forcar_prescricao__` | 1ª resposta reprovada (`prescricao_direta`), `tentativas==2`, final aprovada ou segura |
| `__forcar_alergia__` + P001 | `veredito=="bloqueada"`, `resposta_final` é a segura |
| "quanto é 2+2?" | rota recusa; resposta de escopo |
| RAG vazio (sem ingest) | `sem_fonte==True`; resposta marca "Sem fonte interna" |
| paciente `P999` | resposta segura menciona paciente não encontrado |
| provider lança `LLMIndisponivelError` | resposta segura; log `no_falhou` |
| anonimizar | CPF/CRM/telefone/email/data/nome viram placeholders |
| create_alert 2x no mesmo dia | segunda retorna `None`, tabela tem 1 linha |

Meta: `pytest -q` verde, cobertura ≥ 80% em `assistant/` e `guardrails.py`.

## 16. Ordem de implementação e critérios de aceite

| # | Entrega | Aceite |
|---|---|---|
| 1 | `pyproject`, `config.py`, `logging_setup.py`, `Makefile`, `.env.example`, `.gitignore` | `uv sync` (ou pip install -e `.[dev]`) ok; `pytest` roda (0 testes) |
| 2 | `db/` completo + `generate_synthetic.py` + dados sintéticos commitados | `medassist seed-db` idempotente; `test_db.py` verde |
| 3 | `anonymize.py` + `rag/` | `medassist ingest` ok; `test_anonymize.py`, `test_rag.py` verdes |
| 4 | `llm/` (base, fake, ollama) | fake responde pelos 4 gatilhos |
| 5 | `assistant/` completo (estado, nós, rotas, guardrails, prompts, grafo) | `test_guardrails.py` e `test_graph.py` verdes (11 cenários) |
| 6 | `ui/cli.py` + `ui/app_streamlit.py` | `medassist ask "qual o protocolo de sepse?"` responde com fonte; Streamlit sobe |
| 7 | `build_dataset.py`, `download.py`, `finetune/` (artefatos) | `medassist build-dataset` gera train/val JSONL válidos |
| 8 | Docker (`Dockerfile`, compose, deploy/) | `docker compose up app` local: Streamlit em :8501 com provider fake; com Ollama disponível, `MEDASSIST_LLM_PROVIDER=ollama` responde |
| 9 | `README.md` completo + `docs/relatorio_tecnico.md` (esqueleto) | README cobre: setup local, testes, compose, treino no Colab, deploy VPS |

**Definition of Done global:** `make test` verde; `make run` sobe a UI com provider fake sem nenhum serviço externo; `docker compose build` conclui; nenhum segredo em código; todo texto de UI em PT-BR.

`Makefile`: alvos `install`, `seed`, `ingest`, `test`, `run` (streamlit), `compose-up`, `compose-logs`, `lint` (ruff).
