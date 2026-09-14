"""Gera o dataset de fine-tuning v4 — espelho da célula 3 do notebook v4.

v4 = base 8B (Llama-3.1-8B-Instruct) + dataset ampliado e mais diverso:

  - núcleo limpo   : data/processed/train.jsonl inteiro (25 protocolos "Explique
                     o protocolo ..." + 125 FAQs de seção, todas citando
                     [PROT-NNN §x], já SEM o truncamento de 180 chars da v3).
  - Q&A clínico    : data/synthetic/qa_clinico.jsonl — perguntas de médico em
                     linguagem natural (parciais, cenários, cross-protocolo),
                     respostas ancoradas nos 25 protocolos. É a fatia que dá
                     variedade linguística real (a v3 degenerou por decorar
                     estrutura: 116 ex., respostas quase idênticas ×4).
  - expansão prot. : cada "Explique o protocolo ..." reescrito em +N fraseados
                     (N=2 por default; a v3 usava 4 e repetia a MESMA resposta
                     longa, o que reforçava a memorização de forma).

FICAM DE FORA: MedQuAD (v1/v2 degeneraram por causa dele), opus-mt, PubMedQA,
exemplos de segurança (guardrails vivem no grafo, não no modelo).

    python scripts/gen_dataset_v4.py            # -> docs/train_v4.jsonl
    python scripts/gen_dataset_v4.py --out X    # destino alternativo

Depois: subir docs/train_v4.jsonl para MyDrive/medassist/train_v4.jsonl e rodar
o notebook v4 com REBUILD=False (a célula 3 só carrega).
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORE_DEFAULT = REPO / "data/processed/train.jsonl"
QA_DEFAULT = REPO / "data/synthetic/qa_clinico.jsonl"
OUT_DEFAULT = REPO / "docs/train_v4.jsonl"

SEED = 42
VARIACOES_PROTOCOLO = 2

# system PT-BR idêntico a src/medassist/assistant/prompts.py
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
    "\n\nValide com o médico responsável antes de seguir com qualquer conduta.",
]
_FECHOS_CONHECIDOS = [f.strip() for f in FECHOS_PT] + [
    "Recomendo validação pelo médico responsável antes de qualquer conduta.",
]

_TEMPLATES = [
    "Qual a conduta recomendada pelo protocolo {doc}?",
    "Resuma os pontos principais do protocolo {titulo}.",
    "Quando devo aplicar o protocolo {doc}?",
    "O que diz o protocolo {doc} sobre {titulo}?",
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


def gerar(core_path: Path, qa_path: Path, out: Path) -> None:
    rng = random.Random(SEED)
    core = [json.loads(ln) for ln in core_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # 1. núcleo: train.jsonl inteiro, só rotacionando o fecho.
    nucleo = [
        _chat(rng, x["messages"][1]["content"], x["messages"][2]["content"])
        for x in core
        if len(x.get("messages", [])) >= 3
    ]

    # 2. Q&A clínico em linguagem natural.
    qa = []
    for ln in qa_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        qa.append(_chat(rng, d["pergunta"], d["resposta"]))

    # 3. expansão dos protocolos (VARIACOES_PROTOCOLO fraseados extras cada).
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

    exemplos = nucleo + qa + expandidos
    rng.shuffle(exemplos)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in exemplos),
        encoding="utf-8",
        newline="\n",
    )

    cit = sum(
        1
        for e in exemplos
        if re.search(r"PROT-\d", e["messages"][2]["content"])
        or "§" in e["messages"][2]["content"]
    )
    tam = [len(e["messages"][2]["content"]) for e in exemplos]
    print(f"núcleo {len(nucleo)} + Q&A {len(qa)} + expansão {len(expandidos)} = {len(exemplos)}")
    print(f"citam [PROT/§]: {cit}/{len(exemplos)} ({100 * cit // len(exemplos)}%)")
    print(f"resposta: min {min(tam)} / média {sum(tam) // len(tam)} / máx {max(tam)} chars")
    print(f"-> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", type=Path, default=CORE_DEFAULT)
    ap.add_argument("--qa", type=Path, default=QA_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    gerar(args.core, args.qa, args.out)


if __name__ == "__main__":
    main()
