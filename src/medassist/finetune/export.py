"""Merge dos adaptadores LoRA no modelo base + instrucoes de conversao GGUF.

A conversao final para GGUF usa o conversor do llama.cpp (fora do escopo
Python deste projeto). Este script faz o merge dos pesos e imprime o comando
exato a rodar em seguida.

Uso:
    python -m medassist.finetune.export --adapters models/adapters/ --out models/merged/
"""
import argparse
import sys
from pathlib import Path

try:
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError as exc:  # pragma: no cover
    print(
        "Dependencias de treino ausentes. Instale com:\n"
        '  pip install -e ".[train]"\n'
        f"(erro original: {exc})",
        file=sys.stderr,
    )
    sys.exit(1)


def merge(base_model: str, adapters_dir: str, out_dir: str) -> None:
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    modelo_base = AutoModelForCausalLM.from_pretrained(base_model)
    modelo = PeftModel.from_pretrained(modelo_base, adapters_dir)
    modelo = modelo.merge_and_unload()

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    modelo.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"Modelo mesclado salvo em {out_dir}")

    print(
        "\nPróximo passo (fora deste script, requer llama.cpp compilado):\n"
        f"  python convert_hf_to_gguf.py {out_dir} --outfile models/medassist-f16.gguf\n"
        "  ./llama-quantize models/medassist-f16.gguf "
        "models/medassist-q4_k_m.gguf Q4_K_M\n"
        "\nO GGUF resultante é referenciado em deploy/Modelfile "
        "(`FROM /models/medassist-q4_k_m.gguf`)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="unsloth/Llama-3.2-3B-Instruct")
    parser.add_argument("--adapters", default="models/adapters/")
    parser.add_argument("--out", default="models/merged/")
    args = parser.parse_args()
    merge(args.base_model, args.adapters, args.out)


if __name__ == "__main__":
    main()
