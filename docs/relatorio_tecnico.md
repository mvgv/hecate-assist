# Relatório Técnico — MedAssist (Tech Challenge Fase 3)

> Esqueleto a ser preenchido após a execução do fine-tuning (Colab) e da
> avaliação (`python -m medassist.finetune.evaluate`). Ver
> [`../ESPECIFICACAO.md`](../ESPECIFICACAO.md) e [`../PLANO.md`](../PLANO.md)
> para o contexto completo do projeto.

## 1. Visão geral

- [ ] Objetivo do assistente e problema que resolve
- [ ] Resumo da arquitetura (monolito + LangGraph + RAG + SQLite + Ollama)
- [ ] Escopo e limites de atuação (nunca prescreve, sempre exige validação humana)

## 2. Dados

- [ ] Fontes: MedQuAD (externo, opcional) + protocolos/FAQs sintéticos (`data/synthetic/`)
- [ ] Processo de geração dos dados sintéticos (`generate_synthetic.py`)
- [ ] Anonimização: exemplos antes/depois (`anonymize.py`)
- [ ] Estatísticas do dataset de fine-tuning (saída de `medassist build-dataset`)

## 3. Fine-tuning

- [ ] Modelo base escolhido e justificativa
- [ ] Hiperparâmetros (QLoRA: r, alpha, lr, épocas) — ver `finetune/train.py`
- [ ] Curvas de loss/perplexidade (capturas do notebook Colab)
- [ ] Ambiente de treino (GPU, tempo de treino)

## 4. Arquitetura do assistente (LangChain + LangGraph)

- [ ] Diagrama do grafo (gerar com `grafo.get_graph().draw_mermaid()` para
      não desatualizar — ver [`../docs/grafo_langgraph.md`](grafo_langgraph.md))
- [ ] Descrição nó a nó
- [ ] Guardrails: camadas de validação e exemplos de bloqueio/regeneração
- [ ] Human-in-the-loop: quando e por quê o grafo interrompe
- [ ] Logging/auditoria: exemplo de trilha completa de uma conversa

## 5. Avaliação

- [ ] Métricas base vs. fine-tuned (`docs/avaliacao.md`, gerado por `finetune/evaluate.py`)
- [ ] Exemplos qualitativos (pergunta → resposta base vs. tuned)
- [ ] Limitações observadas

## 6. Deploy

- [ ] Topologia do Docker Compose e decisões de infraestrutura (ver `../PLANO.md §5`)
- [ ] Orçamento de RAM observado na VPS
- [ ] Checklist de smoke test pós-deploy

## 7. Conclusões e trabalhos futuros

- [ ] Principais aprendizados
- [ ] O que faria diferente
- [ ] Próximos passos (ex.: dataset maior, modelo maior, mais protocolos)
