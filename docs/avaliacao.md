# Avaliação — base vs. fine-tuned

Conjunto: `data/processed/val.jsonl` (9 exemplos)

Métrica ROUGE-L: disponível


## Resumo

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.239 | 0.111 | 1.000 |
| `llama3.1:8b` | 0.108 | 0.222 | 0.111 |

## Interpretação

- **`formato`** é o eixo que o fine-tune deveria mover: citar `[PROT-NNN]` e encerrar recomendando validação médica. É onde a diferença aparece.
- **`doc_ids`** é ruidoso neste conjunto — várias respostas de referência do `val.jsonl` não usam a citação em colchetes, então o score pune quem cita. E identificar o protocolo certo sem contexto é tarefa do RAG, não do fine-tune (o modelo alucina o número quando gera sem os documentos).
- **`rougeL`** mede a proximidade textual com a resposta de referência — é o sinal lexical de que o modelo aprendeu o conteúdo dos protocolos, e não só o formato.


## Detalhe por exemplo


**1. Explique o protocolo PROT-015 - Abordagem Inicial da Lesão Renal Aguda.**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.223 | 1.000 | 1.000 |
| `llama3.1:8b` | 0.168 | 1.000 | 1.000 |

**2. Qual a conduta inicial recomendada em reconhecimento e manejo da anafilaxia?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.189 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.117 | 0.000 | 0.000 |

**3. Quais os critérios diagnósticos relacionados a manejo da cetoacidose diabética no adulto?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.270 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.091 | 0.000 | 0.000 |

**4. Quais as doses de referência no manejo de investigação inicial da dor abdominal aguda?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.224 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.051 | 0.000 | 0.000 |

**5. Quais as doses de referência no manejo de manejo da fibrilação atrial aguda?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.226 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.133 | 0.000 | 0.000 |

**6. Quais os critérios diagnósticos relacionados a abordagem inicial da lesão renal aguda?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.335 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.109 | 0.000 | 0.000 |

**7. Qual a conduta inicial recomendada em investigação inicial de dor torácica aguda?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.232 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.117 | 0.000 | 0.000 |

**8. Quando escalonar ou alertar a equipe em caso de reconhecimento e manejo da anafilaxia?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.208 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.081 | 0.000 | 0.000 |

**9. Quais as regras de preenchimento do modelo de receita médica?**

| modelo | rougeL | doc_ids | formato |
|---|---|---|---|
| `medassist` | 0.241 | 0.000 | 1.000 |
| `llama3.1:8b` | 0.109 | 1.000 | 0.000 |
