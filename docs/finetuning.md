# Guia de Fine-tuning — do dataset ao GGUF servido localmente

Complementa [PLANO.md](plano.md) (Fase 2) e [ESPECIFICACAO.md](especificacao.md) §13.

## 1. Visão geral do processo

```
[local]                    [Colab GPU T4]                    [GPU local]
build-dataset  ──►  QLoRA (Unsloth + TRL)  ──►  export GGUF  ──►  ollama create
train/val.jsonl     adaptadores LoRA (~100MB)   Q4_K_M (~2GB)     medassist:latest
                          │
                          └──► HF Hub (trânsito dos artefatos entre os ambientes)
```

Princípio que guia tudo: **o fine-tuning ensina comportamento, o RAG fornece fatos.**
O modelo 3B não vai memorizar medicina — ele vai aprender: (a) o formato de resposta com citação `[PROT-NNN §x]`, (b) o tom de apoio à decisão (nunca prescritivo), (c) recusar o que está fora do escopo, (d) responder em PT-BR clínico. Isso é exatamente o que um dataset pequeno (2–5k exemplos) consegue ensinar bem.

## 2. Composição do dataset

Gerado por `medassist build-dataset`, com esta mistura:

| Fatia | % | Fonte | O que ensina |
|---|---|---|---|
| FAQs sintéticas do hospital | ~40% | `faqs.jsonl` (60 base × variações de fraseado) | formato + citação + PT-BR |
| Q&A derivadas dos protocolos | ~25% | "explique o PROT-00X", "quando escalonar em Y?" | citação por seção |
| MedQuAD (amostra) | ~20% | subset de 500–1000 pares, filtrado por tópicos clínicos | conhecimento geral + robustez |
| **Exemplos de segurança** | ~15% | sintéticos | comportamento dos guardrails |

Os **exemplos de segurança** são o diferencial — pares onde a resposta correta é o comportamento seguro:

```json
{"messages": [
  {"role": "system", "content": "<SYSTEM_PROMPT>"},
  {"role": "user", "content": "Prescreve amoxicilina 500mg pro paciente do leito 12?"},
  {"role": "assistant", "content": "Não realizo prescrições diretas. Posso apresentar o protocolo institucional aplicável [PROT-007 §3] para sua avaliação, mas a prescrição deve ser emitida e validada pelo médico responsável. Deseja que eu traga a conduta sugerida pelo protocolo?"}
]}
```

Incluir ~10 variações de: pedido de prescrição direta, pedido de diagnóstico definitivo, pergunta não-clínica (recusa de escopo), pergunta sem protocolo aplicável (admitir "sem fonte interna").

Regras de qualidade:
- **Toda resposta assistant termina** com recomendação de validação humana — consistência absoluta grava o hábito no modelo.
- Respostas entre 80 e 300 tokens (nem monossílabo, nem dissertação).
- MedQuAD é em inglês: usar como está (o modelo é multilíngue e a fatia é minoritária) **ou** traduzir a amostra via LLM antes — decisão registrada no relatório. As fatias em PT-BR dominam o gradiente de estilo.
- `max_seq_length=2048` cobre com folga (percentil 99 dos exemplos < 1024 tokens).

## 3. Ambiente de treino

| Opção | Quando usar |
|---|---|
| **Colab free (T4 16GB)** — padrão | 3B QLoRA + 5k exemplos ≈ 40–80 min/época; cabe com folga |
| Kaggle (T4×2 ou P100, 30h/semana) | se o Colab derrubar sessão ou esgotar quota |
| RunPod/Vast (~US$0,30/h) | plano C; mesmíssimo notebook |

Requisitos de conta: HF token (para subir artefatos; modelos `unsloth/*` dispensam aceite de licença Meta), Google Drive montado para checkpoints (o Colab free desconecta — ver §7).

## 4. O notebook, célula a célula (`notebooks/02_finetune_colab.ipynb`)

### Célula 1 — Instalação
```python
%pip install -q unsloth  # traz torch/bitsandbytes/trl/peft compatíveis
```

### Célula 2 — Modelo base 4-bit
```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",  # já quantizado, sem gate de licença
    max_seq_length=2048,
    load_in_4bit=True,
)
```

### Célula 3 — Adaptadores LoRA
```python
model = FastLanguageModel.get_peft_model(
    model,
    r=16, lora_alpha=32, lora_dropout=0,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    bias="none",
    use_gradient_checkpointing="unsloth",   # ~30% menos VRAM
    random_state=42,
)
```
`r=16` é o equilíbrio para dataset pequeno; só subir para 32 se a avaliação mostrar que o modelo não pegou o formato (improvável).

### Célula 4 — Dataset com chat template
```python
from datasets import load_dataset
from unsloth.chat_templates import get_chat_template

tokenizer = get_chat_template(tokenizer, chat_template="llama-3.1")  # cobre Llama 3.2

def formatar(ex):
    return {"text": tokenizer.apply_chat_template(
        ex["messages"], tokenize=False, add_generation_prompt=False)}

train = load_dataset("json", data_files="train.jsonl", split="train").map(formatar)
val   = load_dataset("json", data_files="val.jsonl",   split="train").map(formatar)
```

### Célula 5 — Trainer (só aprende com os turnos do assistant)
```python
from trl import SFTTrainer, SFTConfig
from unsloth.chat_templates import train_on_responses_only

trainer = SFTTrainer(
    model=model, tokenizer=tokenizer,
    train_dataset=train, eval_dataset=val,
    dataset_text_field="text",
    args=SFTConfig(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,      # batch efetivo 8
        num_train_epochs=2,
        learning_rate=2e-4,
        lr_scheduler_type="linear", warmup_steps=10,
        optim="adamw_8bit", weight_decay=0.01,
        logging_steps=10,
        eval_strategy="steps", eval_steps=50,
        save_strategy="steps", save_steps=100,
        output_dir="/content/drive/MyDrive/medassist_ckpt",  # sobrevive a desconexão
        seed=42, report_to="none",
    ),
)
trainer = train_on_responses_only(
    trainer,
    instruction_part="<|start_header_id|>user<|end_header_id|>",
    response_part="<|start_header_id|>assistant<|end_header_id|>",
)
stats = trainer.train()   # resume_from_checkpoint=True se retomando
```
`train_on_responses_only` mascara system/user na loss — o modelo aprende a **responder**, não a repetir perguntas. Sem isso, metade do gradiente é desperdiçada.

### Célula 6 — Sanity check qualitativo (antes de exportar)
```python
FastLanguageModel.for_inference(model)
msgs = [{"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Qual a conduta inicial na sepse?"}]
inputs = tokenizer.apply_chat_template(msgs, return_tensors="pt", add_generation_prompt=True).to("cuda")
print(tokenizer.decode(model.generate(inputs, max_new_tokens=300, temperature=0.2)[0]))
```
Checar: cita `[PROT-...]`? Termina com validação humana? PT-BR? Se não → revisar dataset, não hiperparâmetros.

### Célula 7 — Salvar adaptadores + GGUF
```python
model.save_pretrained("medassist-lora")          # ~100 MB
tokenizer.save_pretrained("medassist-lora")

# merge + conversão llama.cpp + quantização, tudo automatizado:
model.save_pretrained_gguf("medassist-gguf", tokenizer, quantization_method="q4_k_m")
```

### Célula 8 — Publicar no HF Hub (opcional, para transporte do artefato)
```python
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
api.create_repo("SEU_USER/medassist-3b-gguf", private=True, exist_ok=True)
api.upload_folder(folder_path="medassist-gguf", repo_id="SEU_USER/medassist-3b-gguf")
api.upload_folder(folder_path="medassist-lora", repo_id="SEU_USER/medassist-3b-gguf", path_in_repo="lora")
```
Baixar 2 GB do Colab pelo navegador falha com frequência; o Hub como intermediário é confiável e documenta a proveniência do artefato.

## 5. Hiperparâmetros — referência e racional

| Parâmetro | Valor | Racional |
|---|---|---|
| Quantização treino | QLoRA 4-bit (nf4) | 3B cabe em ~6 GB VRAM na T4 |
| `r` / `alpha` | 16 / 32 | capacidade suficiente p/ estilo+formato; menos overfitting |
| LR | 2e-4 | padrão QLoRA; com 5k exemplos não precisa de tuning fino |
| Épocas | **2** (máx. 3) | dataset pequeno decora rápido; ver eval loss |
| Batch efetivo | 8 | estável na T4; mais que isso não muda resultado nessa escala |
| `max_seq_length` | 2048 | cobre P99 dos exemplos; dobrar só desperdiça VRAM |
| Quantização final | **Q4_K_M** | melhor razão qualidade/RAM p/ CPU; ~2,1 GB p/ 3B |

**Critério de parada:** eval loss estabilizou ou subiu → parar. Com 5k exemplos, o overfitting aparece tipicamente no meio da 3ª época.

## 6. Avaliação (Fase 2 do plano — vai para o relatório)

Rodar `finetune/evaluate.py` sobre `val.jsonl`, **base vs. fine-tuned** (mesma quantização Q4, via Ollama, para medir o que vai a produção):

| Métrica | Como | O que prova |
|---|---|---|
| Eval loss / perplexity | do próprio trainer | aprendizado sem decoreba |
| Taxa de citação válida | % respostas com `[PROT-\d+ §\d]` cujo doc existe | formato aprendido (métrica-chave) |
| Taxa de disclaimer | % respostas recomendando validação humana | comportamento de segurança |
| Recusa correta | 10 prompts adversariais (pedir prescrição/diagnóstico) | guardrail *no modelo*, antes do nó validador |
| ROUGE-L / BERTScore | vs. respostas de referência | proximidade de conteúdo (secundária) |
| LLM-as-judge | rubrica 1–5 (correção, aderência, segurança) via um modelo forte | qualidade global; amostrar 50 itens |

Esperado e honesto para o relatório: o base já "sabe medicina" razoavelmente; o ganho do fine-tuning aparece em **citação, disclaimer, recusa e PT-BR** — e é isso que as métricas acima capturam. Incluir 5 pares antes/depois qualitativos.

## 7. Armadilhas conhecidas

1. **Chat template divergente treino ↔ Ollama** — a mais comum e a mais silenciosa (modelo "funciona" mas degrada). O template do Modelfile deve ser o do Llama 3.x. O `save_pretrained_gguf` do Unsloth embute o template no GGUF; **não** sobrescrever `TEMPLATE` no Modelfile — só `SYSTEM` e `PARAMETER`.
2. **System prompt duplicado**: o `SYSTEM` do Modelfile e o system enviado pelo LangChain se somam. Padrão do projeto: o system vive **no Modelfile**; `ollama_provider.py` não reenvia (o campo `system` de `prompts.py` fica para o provider fake e para o verificador).
3. **Colab desconecta**: checkpoints no Drive (`save_steps=100`) + `trainer.train(resume_from_checkpoint=True)`.
4. **EOS ausente** → modelo não para de gerar. O `apply_chat_template` com template llama-3.1 já fecha os turnos; conferir no sanity check (célula 6) que a geração termina sozinha.
5. **Só métrica, sem olho**: ROUGE alto com resposta clinicamente ruim acontece. Os 50 itens do judge + leitura manual de 10 são obrigatórios.
6. **Quantizar e não reavaliar**: avaliar o Q4_K_M final (o que é servido), não o modelo em fp16 do Colab.

## 8. Deploy do artefato

```bash
# na máquina que serve o modelo (uma vez por versão):
mkdir -p models
hf download SEU_USER/medassist-3b-gguf medassist-gguf-unsloth.Q4_K_M.gguf \
   --local-dir models/ --token $HF_TOKEN
mv models/*.Q4_K_M.gguf models/medassist-q4_k_m.gguf
docker compose --profile full up -d        # model-init roda `ollama create medassist -f /deploy/Modelfile`
docker compose exec ollama ollama run medassist "Qual a conduta inicial na sepse?"  # smoke test
```

`deploy/Modelfile` final:
```
FROM /models/medassist-q4_k_m.gguf
SYSTEM """<SYSTEM_PROMPT de prompts.py>"""
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
```

Versionamento: taguear o repo HF (`v1`, `v2`...) e registrar no relatório qual tag está em produção. Rollback = baixar a tag anterior e recriar o modelo.

## 9. Checklist de execução

- [ ] `medassist build-dataset` → `train.jsonl` (95%) + `val.jsonl` (5%), estatísticas anotadas
- [ ] Revisar 20 exemplos aleatórios do train.jsonl (qualidade + anonimização)
- [ ] Upload dos JSONL para o Colab/Drive
- [ ] Rodar notebook até célula 6; sanity check aprovado
- [ ] Exportar GGUF Q4_K_M + subir ao HF Hub (repo privado, tag `v1`)
- [ ] `evaluate.py` base vs. tuned → tabela em `docs/avaliacao.md`
- [ ] Download do GGUF + `model-init` + smoke test via Ollama
- [ ] Trocar `MEDASSIST_LLM_PROVIDER=ollama` no `.env` e validar o fluxo completo na UI
- [ ] Guardar curvas de loss (print do trainer) para o relatório e o vídeo
