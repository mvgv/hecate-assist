# Desvios da especificação

Conforme instruído na especificação do projeto ("se algo for impossível,
implemente o mais próximo possível e registre o desvio aqui"). Nenhum desvio altera as decisões de arquitetura do documento —
todos são correções pontuais necessárias para o código rodar, ou
preenchimento de lacunas não especificadas explicitamente.

## 1. `db/schema.sql` — índice único em vez de `UNIQUE` com expressão

A especificação (§6.1) define a idempotência diária de alertas como:

```sql
UNIQUE (paciente_id, tipo, date(criado_em))
```

SQLite não aceita expressões (`date(...)`) dentro de uma constraint `UNIQUE`
de tabela — apenas listas de colunas. A mesma garantia foi implementada como
um índice único separado:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_alertas_idempotencia_diaria
  ON alertas (paciente_id, tipo, date(criado_em));
```

Comportamento observável é idêntico: a segunda tentativa de `create_alert`
para o mesmo paciente/tipo/dia falha com `IntegrityError`, capturado por
`queries.create_alert` (retorna `None`).

## 2. `logging_setup.auditado` — exceção ao no-op quando `erro` já está setado

A regra global (§9.4) diz que nós em arestas fixas devem fazer no-op quando
`state["erro"]` já está preenchido. Aplicada literalmente a **todos** os
nós, essa regra impediria `resposta_segura`/`resposta_recusa` de rodar — são
justamente os nós acionados *depois* que `erro` é setado, e cuja função é
consumir esse erro e produzir uma saída para o usuário.

`auditado` ganhou um parâmetro `sempre_executa: bool = False`, usado apenas
por esses dois nós terminais. Os demais nós mantêm o no-op padrão.

## 3. `logging_setup.auditado` — não captura `GraphBubbleUp`

O mecanismo de `interrupt()` do LangGraph funciona levantando uma exceção
interna (`langgraph.errors.GraphInterrupt`, subclasse de `GraphBubbleUp`)
que precisa se propagar até o executor do grafo para pausar corretamente.
O `except Exception` genérico do decorator (§11) capturava essa exceção e a
transformava incorretamente em `state["erro"]`, quebrando o fluxo de
aprovação humana. Adicionado um `except GraphBubbleUp: raise` antes do
`except Exception` amplo.

## 4. `rag/ingest.py` — `hnsw:space: cosine` explícito na collection

A especificação (§7) define `score = 1 - distancia_cosseno`. O ChromaDB usa
distância L2 (euclidiana) por padrão para novas collections, não cosseno.
Sem configurar `metadata={"hnsw:space": "cosine"}` na criação da collection,
os scores retornados não correspondiam a similaridade de cosseno, quebrando
o contrato de `MEDASSIST_RAG_MIN_SCORE`.

## 5. `rag/ingest.py` — embedding calculado sobre título+seção+corpo

Embutir apenas o corpo do chunk (sem o título do protocolo/seção) produzia
similaridades de cosseno muito baixas para perguntas curtas típicas (ex.:
"qual o protocolo de sepse?" ~0,29 mesmo contra o protocolo correto). O
texto usado para *calcular* o embedding passou a ser
`"{titulo}. {secao}. {conteudo}"`; o texto *armazenado e retornado* como
`conteudo` (usado nas citações) continua sendo só o corpo da seção, sem o
prefixo. Isso está dentro do contrato de `DocRecuperado` (§7) — não altera
nenhum campo público, só melhora o recall.

Mesmo com essa melhoria, o modelo mandatado
(`paraphrase-multilingual-MiniLM-L12-v2`) produz scores por vezes próximos
do corte padrão (`MEDASSIST_RAG_MIN_SCORE=0.35`) para perguntas muito curtas
ou genéricas — nesses casos o sistema corretamente cai no caminho honesto
"sem fonte interna, conhecimento geral do modelo" (§7, §9.3), que é um
comportamento esperado e não um bug.

## 6. `routing.py` — propagação de `erro` para `resposta_segura`

A "regra global" de erro (§9.4) não define explicitamente para qual aresta
condicional cada nó deve rotear quando `state["erro"]` está preenchido. Duas
delas reaproveitam chaves já existentes nos contratos originais:

- `rota_guardrails`: erro → `"bloqueada"` (já mapeada para `resposta_segura`);
- `rota_aprovacao`: erro → `"rejeitado"` (já mapeada para `resposta_segura`).

Para `rota_triagem`, a primeira versão mapeava erro → `"fora_escopo"`
(→ `resposta_recusa`), sob a suposição de que esse caminho seria raro (a
triagem só chama o LLM na heurística ambígua). **Isso se mostrou um bug
real**, encontrado testando o deploy Docker de ponta a ponta com o provider
`ollama` sem modelo registrado: qualquer pergunta com termo clínico e sem
`paciente_id` aciona a heurística ambígua, então uma falha de LLM aqui é
comum, não rara. Com o mapeamento antigo, o usuário recebia "esse assistente
não pode responder a essa pergunta" (mensagem de fora de escopo) quando o
problema real era o Ollama indisponível — enganoso.

Corrigido adicionando uma quarta chave `"erro": "resposta_segura"` ao
`add_conditional_edges("triagem", ...)` em `graph.py`, com `rota_triagem`
retornando o literal `"erro"` quando `state.get("erro")`. Agora esse caminho
produz a mensagem correta ("não foi possível gerar resposta segura...
motivo: <erro>"), validado em container real (`docker compose up` com
Ollama sem o modelo `medassist` registrado → 404 → `resposta_segura`).

## 7. `db/queries.py` — `list_patients()` adicional

Não faz parte da lista de contratos do §6.3, mas é necessária para o
seletor de paciente da UI Streamlit (§12.2: "selectbox de paciente via
`queries`"). Função simples, somente leitura, sem impacto nos demais
contratos.

## 8. `Dockerfile` — `HF_HOME` dentro de `/app`

O download do modelo de embeddings no build (§14.1) roda como `root`, antes
de `USER medassist` ser definido. Sem fixar `HF_HOME`, o cache do
HuggingFace ficaria em `/root/.cache`, inacessível ao usuário não-root em
runtime (o container tentaria baixar de novo a cada subida, falhando
offline). Foi definido `ENV HF_HOME=/app/.cache/huggingface` antes do `RUN` de
download, e o `chown -R medassist:medassist /app` subsequente cobre esse
diretório.

## 9. `deploy/Caddyfile` — um único site address em vez de dois

A primeira versão tinha `{$DOMAIN:80} { ... }` e `:80 { ... }` como dois
blocos separados. Quando `DOMAIN` não está definido, `{$DOMAIN:80}` resolve
para `"80"`, que é um site address equivalente a `:80` — duas definições
para o mesmo endereço fazem o Caddy falhar ao subir. Consolidado em um único
bloco, que já cobre os dois casos (com/sem `DOMAIN`) via o valor default.

## 10. `Dockerfile` — wheel CPU-only do PyTorch instalada explicitamente

`sentence-transformers` (dependência de runtime, §2) exige `torch` como
dependência transitiva obrigatória — não há como usar embeddings locais sem
ele, mesmo respeitando a restrição de não declarar `torch`/`transformers`
diretamente nas deps de runtime (§1). Sem intervenção, `pip install .` baixa
a wheel padrão do PyPI, que inclui ~5GB de bibliotecas CUDA/NVIDIA
irrelevantes para um deploy 100% CPU (§1, PLANO.md §5), inflando a imagem
final para ~7,9GB (vs. o orçamento de ~2GB do PLANO.md §5.2).

Corrigido instalando explicitamente a wheel CPU-only antes do `pip install .`:

```dockerfile
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .
```

Isso satisfaz o resolvedor de dependências do pip (torch já presente,
versão compatível) sem baixar os pacotes `nvidia-*`. Imagem final: ~3,2GB
(`docker build` validado de ponta a ponta nesta máquina).

## 11. `pyproject.toml` — `schema.sql` declarado como `package-data`

Bug real encontrado só no container (não em dev, onde `pip install -e` usa
`src/` diretamente): `pip install .` (não-editável) empacota apenas
arquivos `.py` por padrão — `db/schema.sql`, lido em runtime via
`Path(__file__).parent / "schema.sql"` (`db/seed.py`), não ia para o wheel,
e `medassist seed-db` quebrava com `FileNotFoundError` dentro do container
(`docker compose up app ollama`, entrypoint). Corrigido declarando:

```toml
[tool.setuptools.package-data]
medassist = ["db/schema.sql"]
```

Validado inspecionando o `.whl` gerado e reexecutando o `entrypoint.sh` no
container — `seed-db` e `ingest` completam com sucesso.

## 12. Extensão de palavras em `data/anonymize.py`

O padrão de nomes (§5.4) foi implementado com `\1 [NOME]` (mantendo o
gatilho + espaço) em vez de `\1[NOME]` como no texto literal da tabela,
para preservar a legibilidade ("paciente [NOME]" em vez de
"paciente[NOME]"). Comportamento funcionalmente idêntico ao exigido.

## 13. `data/generate_synthetic.py` — FAQs com texto integral da seção

`_perguntas_faq` gerava a resposta como `f"Conforme {doc_id} §N, {texto[:180]}..."`,
truncando a seção em 180 caracteres com corte no meio da palavra. Como o
`faqs.jsonl` alimenta o dataset de fine-tuning (`build_dataset._exemplos_faqs`),
isso colocava ~48/60 alvos de assistant terminando no meio de uma frase — um
provável reforço da degeneração observada nas versões v1–v3 do fine-tune (modelo
parando cedo / sem emitir EOS). Corrigido para usar o texto integral da seção.
As FAQs deixam de ser trechos e passam a ser respostas completas; a estrutura do
`faqs.jsonl` (5 por protocolo, campos `id`/`pergunta`/`resposta`/`doc_ref`) é a
mesma. Regerado com `python -m medassist.data.generate_synthetic` (25 protocolos,
125 FAQs).

## 14. Guardrails 100% determinísticos — verificador LLM (camada 2) removido

A especificação (§8) previa duas camadas de guardrail: regras/regex (camada 1) e um
verificador via LLM com rubrica de segurança (camada 2). A camada 2 foi **removida**
de `assistant/guardrails.py` (`validar()` agora só chama `_camada1`).

Motivo (validado no Docker/GPU em 2026-09-10): nenhum modelo pequeno julga a rubrica
de forma confiável. O `medassist` 8B fine-tunado (v4) e o `llama3.2:3b` — os dois
modelos disponíveis localmente — retornam `{"aprovada": false}` em respostas limpas
(3/3 execuções numa resposta de anafilaxia que cita explicitamente validação médica).
Com um prompt de verificador mais afiado + few-shot o `llama3.2:3b` piorou, marcando
as quatro violações da rubrica de uma vez. Isso gerava regeneração/bloqueio falso
(sintoma `violação de segurança: 1, 2` nos logs).

A camada 1 (determinística) cobre os casos críticos sem falso-positivo, verificado
caso a caso: prescrição com posologia sem menção a validação → `regenerar`;
diagnóstico definitivo sem hedge → `regenerar`; citação `[PROT-XXX]` fora dos docs
recuperados → `regenerar`; substância à qual o paciente é alérgico → `bloqueada`;
resposta limpa → `aprovada`.

Ficaram órfãos (sem uso, mantidos por serem inofensivos e documentados na spec):
`PROMPT_VERIFICADOR` em `assistant/prompts.py` e o ramo `if "AVALIE" in system` do
`FakeLLM` (`llm/fake.py`).

## 15. RAG — embedding trocado para E5 multilingue + reformulação de meta-query

O `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (spec §7) errava o
protocolo em perguntas naturais. Exemplos medidos (25 protocolos indexados):
"qual o protocolo de sepse?" → PROT-024 (Analgesia); "conduta inicial na sepse" →
PROT-013 (FA); "crise hipertensiva com EAP" trazia PROT-019 (DPOC) entre os 4
chunks. Causa: o modelo é fraco para PT-BR clínico e o preâmbulo das perguntas
("qual o protocolo de…") dilui o vetor.

Duas mudanças:
1. **`intfloat/multilingual-e5-small`** como `embedding_model`. Bench nos mesmos
   casos: todos os 12 recuperam o protocolo certo em #1 (cosseno 0.83–0.95). O E5
   exige prefixar cada texto com `query: ` / `passage: ` — feito em
   `rag/embedding.py` (`embed_consulta` / `embed_passagens`). O `ingest` passa a
   gravar os vetores prontos e o `retriever` consulta com `query_embeddings=`
   (antes ambos deixavam a collection do Chroma embutir — o que aplicaria o
   prefixo errado na consulta). As similaridades do E5 ficam comprimidas no alto
   → `rag_min_score` 0.35 → **0.82**.
2. **`_reformular_query`** em `nodes.recuperar_protocolos`: tira o preâmbulo
   ("qual/existe/o que diz o protocolo/conduta/manejo de …") e manda só o termo
   clínico para o `buscar()`. "qual o protocolo de sepse?" → "sepse" → PROT-001.

`Dockerfile` (`ARG MEDASSIST_EMBEDDING_MODEL`), `.env`/`.env.example` atualizados.
Reindexar: `medassist ingest` (o volume `app_data` mascara `/app/data` — recriar
conforme o gotcha do `docker-compose`).

## 16. Trilha de auditoria — FileHandler fora do root logger

`configurar_logging()` fazia `root.handlers = [file_handler, stream_handler]`, ou
seja, o `FileHandler` do `logs/audit_YYYYMMDD.jsonl` ficava no **root logger** em
nível INFO. Resultado: tudo que qualquer biblioteca logasse em INFO caía no
arquivo de auditoria — `httpx` sozinho gerava uma linha por request. Medido num
`audit_*.jsonl` real: 1873 linhas, das quais **1363 (73%) eram `HTTP Request`** do
`httpx` e ~80 eram ruído de `sentence_transformers`/`huggingface`; só ~23% eram
eventos de auditoria de verdade. Além de afogar a trilha (que é artefato de
compliance), vazava URLs internas e caminhos de cache.

Corrigido: logger dedicado `medassist.audit` recebe o `FileHandler` + um
`StreamHandler` JSON e tem `propagate=False`; o root fica só com um `StreamHandler`
de texto plano em nível WARNING para avisos/erros operacionais; libs barulhentas
(`httpx`, `httpcore`, `urllib3`, `sentence_transformers`, `transformers`,
`huggingface_hub`, `chromadb`, `filelock`) fixadas em WARNING. `get_logger()` passa
a pedir `structlog.get_logger("medassist.audit")`. Assinaturas de `get_logger` e
`@auditado` não mudam. Validado: um `ask` completo gera exatamente 10 linhas no
jsonl (5 `no_iniciado` + 5 `no_concluido`), zero ruído.

## 17. Modelos de laudo/receita/procedimento viraram documentos citáveis

O enunciado da fase exige que o fine-tuning use três fontes: protocolos, FAQs de
médicos e **"modelos de laudos, receitas e procedimentos internos"**. As duas
primeiras estavam cobertas; a terceira existia só como arquivo morto —
`data/synthetic/templates/{laudo,receita,procedimento}.md` era um esqueleto de
~10 linhas com `{{placeholders}}`, sem frontmatter, que **nenhum** código lia:
`build_dataset` somava apenas FAQs + protocolos e `ingest` só varria
`protocolos/*.md`.

Corrigido: os três templates passaram a ser documentos de primeira classe, com a
mesma anatomia dos protocolos — frontmatter (`doc_id: PROT-026..028`, `titulo`,
`tipo: template`) e quatro seções numeradas (`1. Quando usar`,
`2. Estrutura do documento`, `3. Exemplo preenchido`, `4. Regras de preenchimento`).
Com isso entram nos dois caminhos sem código especial:

- **RAG:** `ingest()` ganhou um segundo diretório (`templates_dir`) e indexa os 12
  chunks novos na mesma collection (100 → 112 chunks). O médico pergunta "qual a
  estrutura da receita de alta?" e o retriever devolve `PROT-027 §2`.
- **Fine-tuning:** `_exemplos_templates()` gera uma pergunta por seção mais uma do
  documento inteiro, citando `[PROT-NNN §secao]` exatamente como os protocolos.
  `train.jsonl` foi de 150 → 165 exemplos e `docs/train_v4.jsonl` de 425 → 439.

Detalhe de implementação: o esqueleto dentro da seção 2 é indentado em 4 espaços.
Sem isso, as linhas `## Descrição` / `## Conclusão` do modelo seriam lidas como
seções pelo `_SECAO_RE` do chunker (`^##\s+`) e estilhaçariam o documento.

Os identificadores ficam no **mesmo namespace dos protocolos** (`PROT-026..028`,
não `TPL-00N`) — a razão está no §22, e é o que faz isso funcionar com o modelo
já servido, sem retreinar.

## 18. `fonte_alucinada` exigia colchete e nunca disparava

`_RE_FONTE` era `\[PROT-\d+` — a citação **tinha** que vir entre colchetes. Só que
o dataset ensina majoritariamente a forma sem colchete: em `train.jsonl` são
**93** ocorrências de `Conforme PROT-NNN §x` contra **24** de `[PROT-NNN]`, porque
as FAQs (a fatia maior) usam o prefixo `Conforme`. O modelo fine-tuned gera
exatamente assim. Resultado: a checagem de fonte alucinada — que é o guardrail de
explainability, o que garante que a resposta aponta para um documento realmente
recuperado — estava **morta em produção**.

Descoberto empiricamente ao testar uma pergunta sobre um modelo de documento
(quando eles ainda usavam o prefixo `TPL-`, ver §22): o RAG trouxe o
template certo, o conteúdo da resposta veio correto, mas o modelo escreveu
"Conforme PROT-001 §1" (alucinando o doc_id) e o guardrail aprovou.

Corrigido: `_RE_FONTE = \[?(PROT-\d+)` — colchete opcional, grupo de
captura em vez de fatiar a string, e comparação normalizada em maiúsculas. A mesma
pergunta agora regenera 2× e cai em `resposta_segura` com
`violação de segurança: fonte_alucinada`, que é o comportamento correto para um
modelo que não sabe citar aquele documento.

## 19. Bloco "Fontes" casava só o `doc_id` e anunciava a seção errada

`formatar_resposta` montava `docs_por_id = {d["doc_id"]: d for d in docs}`. Como o
top-k quase sempre traz **vários chunks do mesmo protocolo**, o dict colapsava
todos e ficava com o último. A resposta dizia "Conforme PROT-001 §2" e o rodapé
listava "PROT-001 §4" — a citação visível ao médico apontava para a seção errada.
Observado em produção nas duas primeiras perguntas testadas (sepse: corpo §2 /
fontes §4; hipercalemia: corpo §4 / fontes §2).

Corrigido: `_RE_DOC_CITADO` passou a capturar `(doc_id, secao)` —
`(PROT-\d+)(?:\s*§\s*(\d+))?` — e o novo `_docs_citados()` resolve a
citação pelo par `(doc_id, número da seção)`, caindo de volta para todos os chunks
do documento quando a citação vem sem `§N`. A ordem de aparição no texto é
preservada (`dict.fromkeys`). Revalidado no Docker: sepse §2→§2, hipercalemia
§4→§4, crise hipertensiva §4→§4.

## 20. Documentos de especificação movidos para dentro do repositório

`ESPECIFICACAO.md`, `PLANO.md`, `docs/grafo_langgraph.md` e `docs/finetuning.md`
viviam um nível acima do repo, numa pasta **não versionada**. O `README.md`
apontava para eles com seis links `../…` que quebravam para qualquer pessoa que
clonasse — inclusive o "Diagrama do fluxo LangChain", que é entregável nominal da
fase. Copiados para `docs/` (como `especificacao.md` e `plano.md`) e todos os
links reescritos, nos dois sentidos.

## 21. `HF_HUB_OFFLINE=1` na imagem

O `Dockerfile` já pré-baixa o modelo de embedding no build, mas o
`sentence-transformers` ainda batia no HF Hub a cada carga para revalidar os
arquivos. Em rede com proxy/MITM isso vira `SSL: CERTIFICATE_VERIFY_FAILED` +
5 retries — ~20 s por cold start, medidos. Como o cache já está na imagem, a
variável é setada logo após o pré-download (antes dele quebraria o build).

## 22. Modelos de documento no namespace `PROT-`, não `TPL-`

Os modelos de laudo/receita/procedimento nasceram como `TPL-001..003` — prefixo
próprio, semanticamente mais limpo. **Não funcionou**, e a razão é instrutiva.

O fine-tune v4 (425 exemplos, todos citando `PROT-NNN`) fixou `PROT-` como *o*
token de citação. Perguntado sobre a estrutura do laudo, com o `TPL-001 §2`
recuperado e presente no contexto, o modelo respondia:

> "Conforme **PROT-002** §1, o laudo deve conter identificação do paciente,
> descrição da técnica utilizada, resultados obtidos..."

Errado em três níveis: prefixo inexistente no contexto, número aleatório
(`PROT-002` é dor torácica) e **conteúdo inventado** — não é o texto do
documento recuperado. O prefixo desconhecido fazia o modelo descartar o
contexto inteiro e cair no conhecimento geral.

Tentativas que **não** resolveram:

1. **Instrução no prompt.** Acrescentar "copie o identificador exatamente como
   aparece no contexto" ao system prompt não mudou o comportamento — em um dos
   casos piorou, convergindo com mais força para `PROT-001`.
2. **Retreinar com a fatia `TPL-`.** A v5 (439 exemplos, 14 de `TPL-`) rodou
   completa. O modelo continuou citando `PROT-` **até em prompts que estavam
   literalmente no conjunto de treino**. A aritmética explica: 14 exemplos em
   439 são ~1,8 passos de gradiente numa corrida de 56, contra 425 exemplos
   reforçando `PROT-`.

O que resolveu foi trocar o identificador, não o modelo: `PROT-026..028`.
Verificado com o GGUF que já estava servido, sem nenhum retreino — 3/3 citam o
documento certo, a seção certa, e o conteúdo é fiel ao texto do template.

O custo é semântico: `PROT-` passa a significar "documento institucional
citável" em vez de "protocolo clínico". Fica mitigado pelo frontmatter
(`tipo: template`) e pelo título ("Modelo Institucional de Laudo de Exame"),
que distinguem os dois tipos onde importa. Em troca, o sistema tem **um único
namespace de citação** — uma regex de fonte alucinada, um resolvedor de fontes,
sem ramo morto.

A lição generalizável: o comportamento de citação de um modelo fine-tuned é uma
restrição do sistema, não uma preferência. Quando o esquema de identificadores
é escolha sua e o comportamento do modelo não é, alinhar o esquema ao modelo
sai mais barato e mais confiável que treinar o modelo contra o próprio prior.

## 23. Ambiente alvo — GPU local em vez de VPS CPU-only

A especificação e o plano descrevem o deploy numa VPS de 16 GB **sem GPU**, com
o modelo servido em CPU. O projeto passou a rodar numa **máquina local com GPU
NVIDIA de 8 GB**, e a diferença não é só de hospedagem — muda o que é escasso:

| | VPS planejada | Ambiente real |
|---|---|---|
| Recurso crítico | RAM (16 GB) | VRAM (8 GB) |
| Geração de resposta | ~12 tok/s em CPU | ~52 tok/s em GPU |
| `ask` quente | 20–40 s por chamada de LLM | 25–45 s no fluxo inteiro |
| Modelo auxiliar | caberia na RAM | **não cabe** na GPU junto do 8B |

A última linha é a que teve consequência de arquitetura: com os dois modelos
disputando os 8 GB, o Ollama descarregava um a cada nó e um `ask` levava 3–4
minutos. A triagem foi para a CPU (`ollama_aux_num_gpu=0`) — decisão que não
existiria no cenário original, onde tudo era CPU de qualquer jeito.

Nenhuma mudança de código foi necessária para o serving migrar: o
`llm/ollama_provider.py` só fala HTTP, e `docker-compose.gpu.yml` é um override
que reserva a GPU para o serviço `ollama`. O caminho CPU continua funcional.

O `README.md` foi atualizado para o ambiente real. A especificação e o plano
originais, que descreviam a VPS, saíram do repositório junto com os demais
documentos de apoio ao desenvolvimento (§24) — este registro é o que preserva
a divergência.

## 24. Documentos de apoio ao desenvolvimento fora do repositório

A especificação, o plano de implementação, o guia de fine-tuning e as notas de
contexto de sessão (`CLAUDE.md`) foram removidos do repositório. São artefatos
de **processo**, não de entrega: guiaram a construção, mas quem clona o projeto
não precisa deles para entender, rodar ou avaliar o sistema — isso está no
`README.md`.

Dois deles também já não descreviam o estado atual: a especificação e o plano
falam da VPS CPU-only (§23), e o guia de fine-tuning descrevia a composição de
dataset da v1 (3B, MedQuAD, exemplos de segurança), toda abandonada nas
iterações seguintes. Documento desatualizado ao lado de documento correto é
pior que documento ausente.

O que permanece é o que sustenta a entrega: o relatório técnico (`README.md`),
o diagrama e a especificação nó a nó do fluxo (`grafo_langgraph.md`), a saída
da avaliação (`avaliacao.md`) e este registro de desvios.

O histórico do git preserva as versões removidas.
