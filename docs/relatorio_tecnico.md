# Relatório Técnico — MedAssist (Tech Challenge Fase 3)

O relatório técnico vive no **[README do repositório](../README.md#relatório-técnico)**,
para ficar junto das instruções de uso e não divergir delas.

| Seção | Conteúdo |
|---|---|
| [§A — Decisões de engenharia de software](../README.md#a-decisões-de-engenharia-de-software) | Monolito, LangGraph e por que não uma chain, provider `Protocol` com fake determinístico, os dois modelos do grafo, guardrails determinísticos, auditoria, anonimização, Compose |
| [§B — Decisões de modelo](../README.md#b-decisões-de-modelo) | As quatro versões de fine-tuning e o diagnóstico de cada falha, hiperparâmetros QLoRA, composição do dataset, quantização/serving, escolha do embedding do RAG, reformulação de consulta, chunking |
| [§C — Avaliação](../README.md#c-avaliação) | Metodologia, resultado sem RAG (pesos), resultado com RAG (produção), limitações |
| [§D — Conclusão](../README.md#d-conclusão-fine-tuned-vs-modelo-base) | Comparação fine-tuned vs. modelo base e a divisão de responsabilidades entre fine-tuning, RAG e grafo |

Documentos de apoio:

- [`avaliacao.md`](avaliacao.md) — saída bruta de `medassist.finetune.evaluate` (tabela por exemplo).
- [`desvios.md`](desvios.md) — todo desvio da especificação, com justificativa.
- [`grafo_langgraph.md`](grafo_langgraph.md) — diagrama e especificação nó a nó do fluxo.
- [`finetuning.md`](finetuning.md) — guia do pipeline de treino.
