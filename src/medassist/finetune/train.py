"""Fine-tuning QLoRA (Unsloth) do modelo base com o dataset sintetico.

NAO roda na VPS de producao (sem GPU) - artefato pensado para execucao no
Google Colab/Kaggle (ver notebooks/02_finetune_colab.ipynb, espelho deste
script). Requer o extra `train`: `pip install -e ".[train]"`.

Uso:
    python -m medassist.finetune.train \\
        --base-model unsloth/Llama-3.2-3B-Instruct \\
        --dataset data/processed/train.jsonl \\
        --out models/adapters/
"""
import argparse
import sys
from pathlib import Path

try:
    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel
except ImportError as exc:  # pragma: no cover - so acontece fora do extra `train`
    print(
        "Dependencias de treino ausentes. Instale com:\n"
        '  pip install -e ".[train]"\n'
        f"(erro original: {exc})",
        file=sys.stderr,
    )
    sys.exit(1)

R = 16
ALPHA = 32
LR = 2e-4
EPOCHS = 2
MAX_SEQ_LEN = 2048


def treinar(base_model: str, dataset_path: str, out_dir: str) -> None:
    modelo, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=MAX_SEQ_LEN,
        load_in_4bit=True,
    )
    modelo = FastLanguageModel.get_peft_model(
        modelo,
        r=R,
        lora_alpha=ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
    )

    dataset = load_dataset("json", data_files=dataset_path, split="train")

    config = SFTConfig(
        output_dir=out_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=EPOCHS,
        learning_rate=LR,
        logging_steps=10,
        save_strategy="epoch",
        max_seq_length=MAX_SEQ_LEN,
    )

    trainer = SFTTrainer(model=modelo, args=config, train_dataset=dataset, tokenizer=tokenizer)
    trainer.train()

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    modelo.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"Adaptadores LoRA salvos em {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="unsloth/Llama-3.2-3B-Instruct")
    parser.add_argument("--dataset", default="data/processed/train.jsonl")
    parser.add_argument("--out", default="models/adapters/")
    args = parser.parse_args()
    treinar(args.base_model, args.dataset, args.out)


if __name__ == "__main__":
    main()
