# Relatório Técnico — MedAssist (Tech Challenge Fase 3)

O relatório técnico vive no **[README do repositório](../README.md#relatório-técnico)**,
para ficar junto das instruções de uso e não divergir delas.

| Seção | Conteúdo |
|---|---|
| [§A — Arquitetura do assistente](../README.md#a-arquitetura-do-assistente) | Por que LangGraph e não uma chain, o fluxo nó a nó, por que dois modelos no grafo, e os prompts de cada etapa (sistema, triagem, contexto montado, regeneração) |
| [§B — Decisões de engenharia](../README.md#b-decisões-de-engenharia-de-software) | Monolito, provider `Protocol` com fake determinístico, guardrails determinísticos e o verificador por LLM descartado, auditoria, anonimização, Docker Compose |
| [§C — O fine-tuning](../README.md#c-o-fine-tuning) | Para que serve o QLoRA, hiperparâmetros e o porquê de cada um, composição do dataset, as quatro tentativas até funcionar, quantização e serving |
| [§D — A estratégia de RAG](../README.md#d-a-estratégia-de-rag) | As quatro fontes de dados, o pipeline da indexação à resposta, e o acoplamento entre o formato do contexto e o do fine-tuning |
| [§E — Avaliação e resultados](../README.md#e-avaliação-e-resultados) | Metodologia, resultado sem RAG (pesos), resultado com RAG (produção), comportamento verificado ponta a ponta, limitações |
| [§F — Conclusão](../README.md#f-conclusão-fine-tuned-vs-modelo-base) | Comparação fine-tuned vs. modelo base e a divisão de responsabilidades entre fine-tuning, RAG e grafo |
| [Apêndice — ROUGE-L](../README.md#apêndice--o-que-é-rouge-l) | O que a métrica mede, o que não mede, e por que um valor alto sem RAG seria má notícia |

Documentos de apoio:

- [`avaliacao.md`](avaliacao.md) — saída bruta de `medassist.finetune.evaluate` (tabela por exemplo).
- [`desvios.md`](desvios.md) — todo desvio da especificação, com justificativa.
- [`grafo_langgraph.md`](grafo_langgraph.md) — diagrama e especificação nó a nó do fluxo.
