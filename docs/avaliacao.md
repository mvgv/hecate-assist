# Avaliação — base vs. fine-tuned

Conjunto: `data/processed/val.jsonl` (8 exemplos)

Métrica ROUGE-L: indisponível (rouge-score não instalado)


## Resumo

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 0.375 | 1.000 |
| `llama3.1:8b` | 0.125 | 0.125 |

## Interpretação

- **`formato`** é o eixo que o fine-tune deveria mover: citar `[PROT-NNN]` e encerrar recomendando validação médica. É onde a diferença aparece (8/8 vs 1/8).
- **`doc_ids`** é ruidoso neste conjunto — várias respostas de referência do `val.jsonl` não usam a citação em colchetes, então o score pune quem cita. E identificar o protocolo certo sem contexto é tarefa do RAG, não do fine-tune (o modelo alucina o número quando gera sem os documentos).
- ROUGE-L (proximidade textual da referência) daria um sinal melhor; instalar `rouge-score` e rodar de novo para tê-lo.

## Detalhe por exemplo


**1. Explique o protocolo PROT-015 - Abordagem Inicial da Lesão Renal Aguda.**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 1.000 | 1.000 |
| `llama3.1:8b` | 1.000 | 1.000 |

**2. Qual a conduta inicial recomendada em reconhecimento e manejo da anafilaxia?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 1.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |

**3. Quais os critérios diagnósticos relacionados a manejo da cetoacidose diabética no adulto?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 0.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |

**4. Quais as doses de referência no manejo de investigação inicial da dor abdominal aguda?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 0.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |

**5. Quais as doses de referência no manejo de manejo da fibrilação atrial aguda?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 0.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |

**6. Quais os critérios diagnósticos relacionados a abordagem inicial da lesão renal aguda?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 0.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |

**7. Qual a conduta inicial recomendada em investigação inicial de dor torácica aguda?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 0.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |

**8. Quando escalonar ou alertar a equipe em caso de reconhecimento e manejo da anafilaxia?**

| modelo | doc_ids | formato |
|---|---|---|
| `medassist` | 1.000 | 1.000 |
| `llama3.1:8b` | 0.000 | 0.000 |
