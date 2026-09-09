"""Gera o dataset de fine-tuning v3 (so PT-BR limpo) — espelho da celula 3 do
notebook com N_MEDQUAD_EN=0, para rodar sem Colab.

    python scripts/gen_dataset_v3.py            # -> docs/train_v3.jsonl
    python scripts/gen_dataset_v3.py --out X    # destino alternativo

Depois: copiar o arquivo para MyDrive/medassist/train_v3.jsonl e rodar o notebook
com REBUILD=False (a celula 3 so carrega).
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DEFAULT = REPO / "data/processed/train.jsonl"
OUT_DEFAULT = REPO / "docs/train_v3.jsonl"

SEED = 42
VARIACOES_PROTOCOLO = 4

# system PT-BR identico a src/medassist/assistant/prompts.py
SYSTEM_PT = (
    "Você é um assistente virtual de apoio à decisão clínica para médicos. "
    "Você NUNCA prescreve diretamente (não indica medicação, dose ou via de administração "
    "como se fosse uma prescrição definitiva) — você apenas sugere condutas com base em "
    "protocolos institucionais e conhecimento geral, sempre deixando claro que a decisão "
    "final é do médico responsável. "
    "Sempre que usar informação de um protocolo institucional, cite a fonte no formato "
    "[DOC-ID §secao]. "
    "Sempre encerre a resposta recomendando validação humana antes de qualquer conduta. "
    "Responda sempre em português do Brasil, de forma objetiva e clinicamente precisa."
)
FECHOS_PT = [
    "\n\nRecomendo validação pelo médico responsável antes de qualquer conduta.",
    "\n\nConfirme com o médico responsável antes de aplicar qualquer conduta.",
    "\n\nA decisão final e a validação são do médico responsável.",
    "\n\nRevise com o médico responsável antes de qualquer decisão clínica.",
]
_FECHOS_CONHECIDOS = [f.strip() for f in FECHOS_PT] + [
    "Recomendo validação pelo médico responsável antes de qualquer conduta.",
]

_TEMPLATES = [
    "Explique o protocolo {doc} - {titulo}.",
    "Qual a conduta recomendada pelo protocolo {doc}?",
    "Resuma os pontos principais do protocolo {titulo}.",
    "Quando devo aplicar o protocolo {doc}?",
]


def _sem_fecho(texto: str) -> str:
    t = texto.rstrip()
    for f in _FECHOS_CONHECIDOS:
        if t.endswith(f):
            return t[: -len(f)].rstrip()
    return t


def _chat(rng: random.Random, user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PT},
            {"role": "user", "content": user.strip()},
            {"role": "assistant", "content": _sem_fecho(assistant) + rng.choice(FECHOS_PT)},
        ]
    }


def gerar(src: Path, out: Path) -> None:
    rng = random.Random(SEED)
    core = [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]

    nucleo = [
        _chat(rng, x["messages"][1]["content"], x["messages"][2]["content"])
        for x in core
        if len(x.get("messages", [])) >= 3
    ]

    expandidos: list[dict] = []
    for x in core:
        m = x.get("messages", [])
        if len(m) < 3 or not m[1]["content"].startswith("Explique o protocolo"):
            continue
        pergunta, resposta = m[1]["content"], m[2]["content"]
        mo = re.search(r"\[([A-Z]{2,}-?\d+)[^\]]*\]", resposta)
        if not mo:
            continue
        doc = mo.group(1)
        t = re.search(r" - (.+?)\.?\s*$", pergunta)
        titulo = t.group(1) if t else doc
        for frase in _TEMPLATES[: max(1, VARIACOES_PROTOCOLO)]:
            expandidos.append(_chat(rng, frase.format(doc=doc, titulo=titulo), resposta))

    exemplos = nucleo + expandidos
    rng.shuffle(exemplos)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in exemplos), encoding="utf-8"
    )

    cit = sum(
        1
        for e in exemplos
        if re.search(r"\[PROT-\d+", e["messages"][2]["content"]) or "§" in e["messages"][2]["content"]
    )
    print(f"nucleo {len(nucleo)} + expansao {len(expandidos)} = {len(exemplos)} exemplos")
    print(f"com citacao [PROT/§]: {cit}/{len(exemplos)} ({100 * cit // len(exemplos)}%)")
    print(f"-> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=SRC_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    gerar(args.src, args.out)


if __name__ == "__main__":
    main()
