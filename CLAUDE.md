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

**v3 (2026-09-09) — rodada no Colab, TESTADA no Docker/GPU, FALHOU.** GGUF v3 (só ~116 PT-BR limpos,
3 épocas, base Llama-3.2-3B) gerado e servido na GPU (`docker-compose.gpu.yml`, `ollama ps` = 100%
GPU, 90–106 tok/s). **Progresso:** passou a emitir EOS (`done_reason: "stop"`) e a "citar". **Mas
degenerou igual v1/v2:** PT-BR virou salada de palavras ("Sepse origina-se quando dissecion...",
"Rebaixo de..." repetido) e em perguntas longas entrou em loop de seções `## 1..## 12` até estourar
`num_predict`. Diagnóstico: base 3B frágil demais para QLoRA + poucos exemplos + respostas quase
idênticas (mesma resposta longa reaproveitada ×4) → o modelo decorou a **estrutura** e perdeu
fluência. Além disso, 48/60 FAQs do `faqs.jsonl` estavam truncadas em 180 chars com corte no meio da
palavra (`_perguntas_faq`), reforçando "parar no meio da frase" — corrigido, ver `docs/desvios.md` §13.

**v4 (2026-09-09) — notebook + dataset prontos, NÃO rodado ainda.** Duas mudanças sobre a v3:
1. **Base 8B** (`unsloth/Meta-Llama-3.1-8B-Instruct`) — mais robusta; template `llama-3.1` e
   `train_on_responses_only` já estavam certos, só trocou `BASE_MODEL`. 8B Q4_K_M ~4.9 GB de VRAM
   para servir (cabe nos 8 GB da RTX 4060 Ti; `mem_limit` do `ollama` no compose subiu 6g→10g).
2. **Dataset ~425 ex. com variedade linguística real** (`docs/train_v4.jsonl`, gerado por
   `scripts/gen_dataset_v4.py`): núcleo `data/processed/train.jsonl` (25 protocolos + 125 FAQs
   **completas**) + `data/synthetic/qa_clinico.jsonl` (235 perguntas de médico em linguagem natural
   — parciais, cenários, cross-protocolo — ancoradas nos protocolos, cada uma única) + expansão ×2.
   **13 protocolos novos** (PROT-013..025: FA, estado de mal, LRA, hipercalemia, hiponatremia,
   paracetamol, DPOC, asma, meningite, pielonefrite, abstinência alcoólica, analgesia, TVP) somados
   ao `PROTOCOLOS` de `generate_synthetic.py`. Treino: **2 épocas**, LR 1e-4, `MAX_SEQ_LEN=3072`,
   `grad_accum=8`. Sanity check (célula 4b) ampliado com protocolos novos + perguntas naturais.

**v4 RODADA no Colab e TESTADA no Docker/GPU (2026-09-09 23h) — degeneração RESOLVIDA, mas
grounding ainda irregular.** GGUF 8B (md5 `1774a951...`, 4.92 GB) treinado, `ollama create` (ver
gotcha abaixo sobre RAM), servido **100% GPU** (`ollama ps` = `100% GPU`, 5.3 GB, ~52 tok/s warm).
- **Geração crua:** PT-BR **fluente**, emite **EOS** (`done_reason: "stop"`), formato de citação
  `[PROT-NNN §x]` correto, sem loop nem salada de palavras. **Fim do problema v1/v2/v3.** Sem
  contexto RAG o modelo alucina o número do protocolo e as doses (esperado — guia §1).
- **Grafo com RAG (25 protocolos reindexados):** perguntas clínicas curtas e diretas → resposta
  fiel e correta, cita o protocolo certo (CAD, anafilaxia, HDA, pneumonia, hemoglobina/transfusão).
  **Mas:** respostas longas ("Explique o protocolo ...") o modelo **enche de detalhe clínico
  inventado** e plausível; algumas queries pegam o protocolo errado no RAG (ex.: "crise
  hipertensiva com EAP" → responde com conteúdo de DPOC); 1-2 respostas bloqueadas pelo guardrail.
- **Corrigido nesta sessão:** `TERMOS_CLINICOS` (`prompts.py`) só cobria os 12 protocolos antigos
  → perguntas sobre hipercalemia/DPOC/HDA/TVP caíam em `fora_escopo` **antes** do LLM. Ampliado
  para os 25 protocolos + abreviações (HDA, DPOC, LRA, TVP, VNI...). App rebuildado, revalidado.
- **Pendente (decisão do usuário):** (a) triagem/guardrail chamam o MESMO modelo fine-tuned —
  ele ficou pior nessas tarefas fora da distribuição de treino; considerar usar o Llama-3.1-8B
  **base** (ou regras) nesses nós e só `gerar_resposta` usar `medassist`; (b) RAG: reformular a
  query em `recuperar_protocolos` (tirar "qual o protocolo de"/"existe protocolo para"), rever
  `rag_min_score`, talvez trocar o embedding PT; (c) tirar/encurtar os exemplos "Explique o
  protocolo" (corpo inteiro) que puxam respostas longas e confabuladas. `evaluate.py` não rodado
  (precisa do base 8B no Ollama p/ comparar).

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
(`make compose-up-gpu`, requer Docker Desktop com backend WSL2). GPU passthrough VALIDADO nesta
sessão (`nvidia-smi` dentro da `ollama/ollama:latest`, `ollama ps` = `100% GPU`, 90-106 tok/s no 3B
warm vs. ~12 no CPU). O 3B Q4 ocupava ~2 GB de VRAM; o **8B Q4 da v4 ocupa ~6-6.5 GB** (pesos + KV
a 4096 de contexto) — cabe nos 8 GB, mas sem folga; se `ollama ps` mostrar split GPU/CPU, baixar
`num_ctx` no `deploy/Modelfile`. Conferir: `docker exec hecate-assist-ollama-1 ollama ps` → coluna
PROCESSOR = `100% GPU`.

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

### Pendências — afinar a v4 e fechar o Nível 2

**Onde paramos (2026-09-09, noite):** v4 8B **treinada, servida na GPU e testada no grafo**
(ver Status "v4 RODADA"). A degeneração v1/v2/v3 acabou — o modelo é fluente, cita e para no EOS.
O que falta é **grounding/roteamento**, não mais "o modelo é lixo".

**Item 1 (separar os modelos do grafo) — FEITO e VALIDADO no Docker GPU (2026-09-10).**
O grafo chamava LLM em 3 nós, todos no `medassist` fine-tuned. O fine-tune v4 só treinou a
tarefa do `gerar_resposta` (425 ex.) → o modelo ficava pior em classificar (triagem) e julgar
(verificador) — recusas falsas e blocks `violação de segurança: 1, 2`. **Solução aplicada:**
- **Triagem** (`nodes.py`) agora usa `get_llm(aux=True)` → `settings.model_aux` (`llama3.2:3b`).
  Validado no Docker GPU: 6/6 classificações corretas, **~1 s** cada (vs. ~30-60 s no 8B), inclui
  "dose de noradrenalina no choque séptico" → `duvida_clinica` (o 8B fine-tuned recusava),
  "me conte uma piada" → `fora_escopo`, "paciente 3 pode ter alta?" → `caso_paciente`.
- **Verificador LLM (camada 2) dos guardrails: REMOVIDO.** Testado no Docker GPU: nem o 8B
  fine-tuned nem o `llama3.2:3b` julgam a rubrica de forma confiável — ambos retornam
  `{"aprovada": false}` em respostas limpas (3/3 numa resposta de anafilaxia que cita validação
  médica; com prompt afiado + few-shot **piorou**, marcou as 4 violações). `guardrails.validar()`
  agora é 100% determinístico (`_camada1`): prescrição sem validação / diagnóstico definitivo sem
  hedge / fonte alucinada → `regenerar`; substância com alergia do paciente → `bloqueada`.
  Verificado que `_camada1` acerta os 5 casos sem falso-positivo. `PROMPT_VERIFICADOR` em
  `prompts.py` e o ramo `if "AVALIE" in system` do `FakeLLM` ficaram órfãos (inofensivos; ver
  `docs/desvios.md` §14).
  - `PROMPT_TRIAGEM` reescrito: era 3-way (`duvida_clinica`/`caso_paciente`/`fora_escopo`) em
    prosa; agora é **binário** (`duvida_clinica` vs `fora_escopo`) com 6 exemplos few-shot —
    `caso_paciente` já é decidido antes do LLM pelo `paciente_id`, e os modelos pequenos só
    seguem a instrução com o prompt curto + exemplos. Bench pós-prompt: `llama3.2:3b` **11/12**,
    `qwen2.5:1.5b` 8/12, `llama3.2:1b` 6/12 → **o 3B é o único aux viável**; 1B/1.5B ignoram a
    instrução (contam piada, respondem geografia).
  - `config.py`: `model_aux="llama3.2:3b"`, `ollama_num_ctx` 4096→**3072**, novos
    `ollama_aux_num_gpu=0` / `ollama_aux_num_ctx=1024` / `ollama_aux_num_predict=32`.
  - `OllamaProvider.__init__(model, num_ctx, num_predict, num_gpu)` — passa `num_gpu` só quando
    não-`None`. `llm/base.py` `get_llm(aux=True)` → 3B com `num_gpu=0, num_ctx=1024, num_predict=32`.
  - `deploy/Modelfile`: `PARAMETER num_ctx 3072`. `docker-compose.yml`: `model-init` faz
    `ollama pull llama3.2:3b`, `OLLAMA_MAX_LOADED_MODELS=2`. `.env.example` atualizado.
  - `pytest` 39/39, `ruff` limpo.
  **VRAM / thrash — RESOLVIDO (rodar a triagem na CPU).** Antes: 8B + 3B na GPU não cabiam nos
  8 GB (só ~7,1 GiB usáveis) → o Ollama descarregava um a cada nó; `triagem no_concluido` chegou
  a **86 s**, `ask` ~3-4 min. Tentativa de encolher os dois (8B@3072, 3B@1024) ainda deu
  `evicting` (7,0 vs 7,1 GiB — na margem). **Solução:** o 3B da triagem roda na CPU
  (`num_gpu=0`) — a GPU inteira fica para o 8B, zero disputa. **Validado no Docker GPU
  (2026-09-10):** `ollama ps` = `medassist` `100% GPU` (5,1 GB) + `llama3.2:3b` `100% CPU`
  (2,2 GB), os dois residentes (`OLLAMA_KEEP_ALIVE=-1`); **0 evictions** em 3 asks; `ask` quente
  **39-47 s** (1º ~120 s: load dos dois modelos + stall de metadados do HF no 1º embedding);
  triagem quente ~0,5 s. Respostas citam o protocolo certo (PROT-006/008/010), param no EOS,
  sem falso-bloqueio.

**Item 2 (RAG grounding) — FEITO (2026-09-10), falta revalidar no grafo em Docker.**
O `paraphrase-MiniLM` errava o protocolo: "qual o protocolo de sepse?" → PROT-024, "conduta
inicial na sepse" → PROT-013, "crise hipertensiva c/ EAP" trazia PROT-019 (DPOC). **Solução:**
- **Embedding `intfloat/multilingual-e5-small`** (`config.py`, `Dockerfile ARG`, `.env`). Exige
  prefixo `query:`/`passage:` → novo `rag/embedding.py` (`embed_consulta`/`embed_passagens`);
  `ingest` grava os vetores prontos e `retriever` usa `query_embeddings=` (antes a collection do
  Chroma embutia e aplicaria o prefixo errado na consulta). `rag_min_score` 0.35 → **0.82** (as
  sims do E5 ficam comprimidas: ~0.82+ relevante, ~0.81 ruído).
- **`_reformular_query`** (`nodes.py`) tira o preâmbulo "qual/existe/o que diz o protocolo/
  conduta/manejo de …" e manda só o termo clínico pro `buscar()`.
- **Bench (host, 25 protocolos reindexados): 13/14** — todas as queries clínicas recuperam o
  protocolo certo em #1 (0.83–0.95), top-k dominado pelo protocolo certo (fim da poluição DPOC);
  "me conte uma piada" → `sem_fonte` (e a triagem já barra antes). `docs/desvios.md` §15.
- `pytest` 39/39, `ruff` limpo. Rebuild do `app` + `docker volume rm hecate-assist_app_data`
  feitos; revalidado no grafo (sepse→PROT-001, crise hipertensiva c/ EAP→PROT-005, noradrenalina
  no choque séptico→PROT-001 §3). Commit `5f6bf7e`, pushado.

**Item 3 (respostas longas confabulam) — RESOLVIDO pelo item 2 (2026-09-10), sem mudança de código.**
A confabulação em "Explique o protocolo X" era sintoma do RAG errado: quando o retrieval trazia
o protocolo errado/parcial, o modelo preenchia os buracos inventando detalhe clínico plausível.
Com o e5 trazendo as seções reais do protocolo certo, ele recompõe fiel. Testado: CAD,
anafilaxia, hipercalemia, FA — 4/4 texto ~verbatim das seções, **zero detalhe inventado**.
Sobra (não vale retrain): a cobertura de seções varia (às vezes pula §2/§3) e o `§N` em "Fontes"
nem sempre bate com o que foi resumido (o `doc_id` está certo, guardrail `fonte_alucinada` OK).
`num_predict` fica em 768 — é teto anti-degeneração, o modelo não está degenerando.

**Item 4 (avaliação base vs fine-tuned) — FEITO (2026-09-10).** `evaluate.py` reescrito para A/B
real: `--modelos medassist llama3.1:8b`, um passe completo por modelo (evita thrash), métricas
`doc_ids` (sobreposição de citações `[PROT-NNN]` com a referência), `formato` (cita + encerra com
validação) e `rougeL` (se `rouge-score` instalado — adicionado ao extra `dev`). Rodado no
container (`ollama pull llama3.1:8b` = base; `docker cp` do `val.jsonl` — gitignored). Resultado
em `docs/avaliacao.md`: **formato `medassist` 1.000 vs base 0.125** (o fine-tune aprendeu o
estilo da casa — cita e recomenda validação); `doc_ids` 0.375 vs 0.125 (ruidoso: as referências
do `val.jsonl` nem sempre citam em colchetes, e acertar o nº do protocolo sem RAG é tarefa do
retrieval). `rouge-score` não estava no container → métrica ROUGE-L pendente (instalar e rodar
de novo para o sinal lexical).

**Já feito nesta sessão:** `TERMOS_CLINICOS` ampliado p/ os 25 protocolos (recusas falsas de
hipercalemia/DPOC/HDA/TVP resolvidas). 39 testes passando, `ruff` limpo. Stack de GPU no ar
(`medassist:latest` 8B, `ollama ps` = 100% GPU).

**Passo 1 — preparar o Drive.** Subir para `MyDrive/medassist/`:
- `docs/train_v4.jsonl` → **`train_v4.jsonl`** (é o dataset pronto; a célula 3 com `REBUILD=False` só carrega)
- `data/synthetic/qa_clinico.jsonl` → `qa_clinico.jsonl` (só usado se `REBUILD=True`)
- `data/processed/train.jsonl` → `train.jsonl` (núcleo, fallback se não houver `train_v4.jsonl`)
- `data/processed/val.jsonl` → `val.jsonl` (`eval_dataset`)

**Passo 2 — rodar o notebook v4** (`notebooks/02_finetune_colab.ipynb`), runtime GPU (Colab Pro):
1. Células 1-2 (install, mount).
2. Célula 3: deve imprimir `cache -> 425 exemplos de .../train_v4.jsonl`. Se imprimir
   "nucleo / Q&A clinico / expansao prot" é porque não achou o `train_v4.jsonl` no Drive.
3. Célula 4 (train): **2 épocas**, LR 1e-4, base 8B, `train_on_responses_only`, `eval_dataset`.
   Olhar a **eval loss** por época — se subir na 2ª, `EPOCHS=1`.
4. Célula 4b (sanity check): 6 respostas (protocolos antigos + novos, pergunta natural +
   "explique o protocolo"). **Só exportar se todas citarem `[PROT-...]`, pararem sozinhas (EOS)
   e o PT-BR estiver fluente (sem salada de palavras / loop de seções).**
5. Células de export → `medassist-q4_k_m.gguf` (~4.9 GB) no Drive.

**Passo 3 — teste local** (infra já validada):
baixar o GGUF para `models/medassist-q4_k_m.gguf` (gitignore) → **na GPU**:
`docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full up -d --build
ollama model-init app` → `ollama create` roda no `model-init`.
- Conferir GPU: `docker exec hecate-assist-ollama-1 ollama ps` → `PROCESSOR` = `100% GPU`
  (o 8B Q4 ocupa ~6-6.5 GB dos 8 GB; se aparecer split GPU/CPU, baixar `num_ctx` no `deploy/Modelfile`).
- **Antes do grafo**, testar o modelo cru:
  `docker exec hecate-assist-app-1 sh -c 'curl -s http://ollama:11434/api/chat -d "{\"model\":\"medassist\",\"stream\":false,\"options\":{\"num_predict\":300},\"messages\":[{\"role\":\"user\",\"content\":\"Qual a conduta inicial na sepse?\"}]}"'`
  → tem que vir `done_reason: "stop"` (não `"length"`), citar `[PROT-...]`, PT-BR fluente, sem loop.
- Só então: `docker exec hecate-assist-app-1 medassist ask "qual o protocolo de sepse?"` deve
  **gerar**. Opcional p/ acelerar: `-e MEDASSIST_MAX_TENTATIVAS=1`.
- `python -m medassist.finetune.evaluate` base vs. tuned → `docs/avaliacao.md`.

### Composição do dataset de fine-tuning v4 (2026-09-09) — 8B + Q&A clínico

v1 (opus-mt), v2 (MedQuAD EN cru) e v3 (116 ex. + 3B) descartadas — ver Status. A v4 é montada na
**célula 3** (ou por `scripts/gen_dataset_v4.py`, que gera o `docs/train_v4.jsonl` idêntico sem Colab):
- **Núcleo:** `data/processed/train.jsonl` **inteiro** (~142 ex.: 25 protocolo "Explique o
  protocolo ..." + 125 FAQ de seção), 100% citam `[PROT-NNN §x]`, FAQs agora **completas**
  (era truncado em 180 chars — `docs/desvios.md` §13).
- **Q&A clínico:** `data/synthetic/qa_clinico.jsonl` (235 ex.) — perguntas de médico em linguagem
  natural, respostas ancoradas nos 25 protocolos, **cada uma única** (nada de mesma resposta ×N).
- **Expansão dos protocolos:** cada "Explique o protocolo ..." em **+2** fraseados (~48 ex.) —
  a v3 usava 4 e repetia a mesma resposta longa, reforçando a memorização de forma.
- **Total ~425**, fecho PT-BR rotacionado entre 5 fraseados.
- **13 protocolos novos** (PROT-013..025) somados ao `PROTOCOLOS` de `generate_synthetic.py`;
  `medassist build-dataset` e `generate_synthetic` regerados. RAG do grafo passa a indexar os 25.
- **Ficam de fora:** MedQuAD, opus-mt, PubMedQA, exemplos de segurança (guardrails = grafo).
- `data/processed/{train,val}.jsonl` gerados por `medassist build-dataset` (150 ex.: 142 treino / 8 val).

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
- **`model-init` (POST HTTP do blob) estoura a RAM da VM WSL2 com GGUF grande.** Host tem 16 GB
  físicos → VM Docker Desktop = ~8 GB (default `min(50%, 8GB)`). O `model-init` lê o GGUF e faz
  `POST /api/blobs`, bufferizando → `Error: ... cannot allocate memory` no 8B (4.9 GB). **Fix
  aplicado:** `docker-compose.yml` monta `./models:/models:ro` **também no serviço `ollama`**, e o
  `ollama create` roda DENTRO do container `ollama` (cópia em disco, mmap):
  `docker exec hecate-assist-ollama-1 sh -c 'cp /Modelfile /root/Modelfile && cd /root && ollama
  create medassist -f /root/Modelfile'` (o `-f /Modelfile` na raiz dá "no Modelfile found" nesta
  versão do ollama 0.33.3 — precisa rodar de um diretório de trabalho gravável). O `model-init`
  continua no compose e funciona p/ modelos pequenos; p/ o 8B, usar o `docker exec`.
- **Volume `hecate-assist_app_data` mascara `/app/data`.** É um named volume populado no 1º `up` e
  **não** atualizado por `--build`. Ao mudar `data/synthetic/` (protocolos, qa_clinico), o RAG do
  container fica com a versão antiga. Recriar: `docker compose ... rm -sf app && docker volume rm
  hecate-assist_app_data && docker compose ... up -d app` (o entrypoint refaz `seed-db`/`ingest`).
  `ollama_models` fica intacto.
- Todos os desvios de implementação (correções necessárias para o código rodar) estão documentados
  com justificativa em `docs/desvios.md` — ler antes de "corrigir" algo que já foi corrigido de propósito.

### Gotchas do Colab / fine-tuning (sessão 2026-09-09)

- **v2/v3/v4 não traduzem nada** — a célula de dataset não baixa opus-mt nem MedQuAD; as gotchas de
  tradução da v1 (`AutoModelForSeq2SeqLM`, GPU, fp16) não se aplicam. A célula 2 não instala
  `sacremoses`. Na v4 a célula 3 só lê `train_v4.jsonl` (ou reconstrói do `train.jsonl` + `qa_clinico.jsonl`).
- **v4 usa base 8B** (`unsloth/Meta-Llama-3.1-8B-Instruct`). QLoRA 4-bit cabe em T4/L4; o merge 16-bit
  do export consome ~o dobro de RAM do 3B (Colab Pro High-RAM recomendado). GGUF final ~4.9 GB.
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
- **`save_pretrained_gguf(dir, ...)` grava em `dir + "_gguf/"`** com nome fixo derivado do modelo
  (no 8B, algo como `llama-3.1-8b-instruct.Q4_K_M.gguf`; ignora o nome que você passou). A célula de
  export faz `glob('/content/**/*.gguf')` e pega o maior arquivo, depois copia só ele (~4.9 GB no 8B)
  para o Drive.
