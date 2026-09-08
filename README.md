# hecate-assist (MedAssist)

Assistente virtual médico para apoio à decisão clínica — terceira entrega do
Tech Challenge IADT. Monolito Python com **LangGraph** (fluxo de decisão),
**RAG** sobre protocolos institucionais sintéticos (ChromaDB), consulta a
base estruturada de pacientes (SQLite), guardrails de segurança,
human-in-the-loop e logging de auditoria. Roda em CPU via Docker Compose
(app + Ollama + Caddy).

> Especificação completa: [`../ESPECIFICACAO.md`](../ESPECIFICACAO.md).
> Plano de implementação: [`../PLANO.md`](../PLANO.md).
> Design do grafo: [`../docs/grafo_langgraph.md`](../docs/grafo_langgraph.md).
> Desvios da especificação: [`docs/desvios.md`](docs/desvios.md).

## Arquitetura em uma imagem

```
Pergunta do médico + ID do paciente
        │
        ▼
   LangGraph: triagem → contexto do paciente (SQLite) → exames pendentes
              → RAG (protocolos) → LLM → guardrails (regex + LLM verificador)
              → [aprovação humana] → alertas → resposta com fontes citadas
        │                                    │
        ▼                                    ▼
   SQLite (prontuários)              ChromaDB (protocolos + citações)
```

Ver diagrama completo em [`docs/grafo_langgraph.md`](../docs/grafo_langgraph.md).

## Setup local (desenvolvimento)

Requer Python 3.11+.

```bash
# 1. Instalar dependências (uv, se disponível, ou pip)
pip install -e ".[dev]"

# 2. Popular o banco de pacientes fictícios (idempotente)
medassist seed-db

# 3. Indexar os protocolos sintéticos no ChromaDB
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
(ver [`docs/grafo_langgraph.md` §6](../docs/grafo_langgraph.md)): pergunta
geral com fontes, exame pendente, sugestão de tratamento com interrupt +
aprovação humana, prescrição direta (regenera), medicamento com alergia do
paciente (bloqueia), pergunta fora de escopo, RAG sem resultado, paciente
inexistente, LLM indisponível, anonimização de PII e idempotência de alertas.

## Dados sintéticos

`data/synthetic/` contém 12 protocolos clínicos fictícios (`PROT-001` a
`PROT-012`, formato Markdown com frontmatter), 60 FAQs (`faqs.jsonl`) e
templates de laudo/receita/procedimento — todos gerados de forma
determinística (sem LLM) por
`python -m medassist.data.generate_synthetic` e commitados no repositório.
Todo texto é claramente marcado como **"Documento sintético para fins
acadêmicos"** e não deve ser usado como referência clínica real.

## Fine-tuning (Colab/Kaggle — não roda na VPS)

O treino roda fora do monolito, em GPU gratuita:

```bash
# 1. Gerar o dataset de fine-tuning a partir de FAQs + protocolos
medassist build-dataset --out data/processed/

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
[`../PLANO.md` §5](../PLANO.md).

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

O assistente **nunca prescreve diretamente**. Toda resposta passa por duas
camadas de validação (`assistant/guardrails.py`): regras determinísticas
(prescrição direta sem menção a validação, diagnóstico definitivo sem hedge,
citação de fonte não recuperada, substância à qual o paciente é alérgico) e,
se aprovada na primeira camada, um verificador via LLM. Respostas reprovadas
regeneram (até `MEDASSIST_MAX_TENTATIVAS`, padrão 2) ou caem no fallback
seguro. Sugestões de conduta para um paciente específico exigem **aprovação
humana** (`interrupt()` do LangGraph) antes de qualquer alerta ser registrado.

## Logging e auditoria

Todos os nós do grafo são decorados com `@auditado`
(`medassist/logging_setup.py`): cada execução gera um evento JSON
(`no_iniciado`/`no_concluido`/`no_falhou`/`no_pulado`) em stdout e em
`logs/audit_YYYYMMDD.jsonl`, com campos sensíveis mascarados via
`anonimizar()` antes da escrita.
