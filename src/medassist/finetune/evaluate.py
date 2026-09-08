"""Avalia o modelo fine-tuned vs. o modelo base no conjunto de validacao.

Metrica preferencial: ROUGE-L (via `rouge-score`, se instalado). Fallback sem
dependencias externas: sobreposicao exata dos doc_ids citados (`[PROT-NNN]`)
entre resposta gerada e resposta de referencia. Gera `docs/avaliacao.md`.

Uso:
    python -m medassist.finetune.evaluate --val data/processed/val.jsonl
"""
import argparse
import json
import re
from pathlib import Path

_RE_DOC = re.compile(r"PROT-\d+")


def _doc_ids(texto: str) -> set[str]:
    return set(_RE_DOC.findall(texto))


def _score_fallback(referencia: str, gerada: str) -> float:
    docs_ref = _doc_ids(referencia)
    if not docs_ref:
        return 1.0 if not _doc_ids(gerada) else 0.0
    docs_gerada = _doc_ids(gerada)
    return len(docs_ref & docs_gerada) / len(docs_ref)


def _score_rouge_l(referencia: str, gerada: str) -> float:
    from rouge_score import rouge_scorer

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    return scorer.score(referencia, gerada)["rougeL"].fmeasure


def avaliar(val_path: str, gerar_resposta_fn=None) -> dict:
    """gerar_resposta_fn(pergunta) -> str; default usa o provider configurado (fake por padrao)."""
    if gerar_resposta_fn is None:
        from medassist.assistant.prompts import SYSTEM_PROMPT
        from medassist.llm.base import get_llm

        llm = get_llm()

        def gerar_resposta_fn(pergunta: str) -> str:
            return llm.gerar(system=SYSTEM_PROMPT, mensagens=[{"role": "user", "content": pergunta}])

    try:
        from rouge_score import rouge_scorer  # noqa: F401

        metrica = "rougeL"
        score_fn = _score_rouge_l
    except ImportError:
        metrica = "sobreposicao_doc_ids (fallback, rouge-score nao instalado)"
        score_fn = _score_fallback

    linhas = Path(val_path).read_text(encoding="utf-8").splitlines()
    resultados = []
    for linha in linhas:
        if not linha.strip():
            continue
        exemplo = json.loads(linha)
        pergunta = next(m["content"] for m in exemplo["messages"] if m["role"] == "user")
        referencia = next(m["content"] for m in exemplo["messages"] if m["role"] == "assistant")
        gerada = gerar_resposta_fn(pergunta)
        resultados.append({"pergunta": pergunta, "score": score_fn(referencia, gerada)})

    media = sum(r["score"] for r in resultados) / len(resultados) if resultados else 0.0

    relatorio = [
        "# Avaliação — base vs. fine-tuned\n",
        f"Métrica: **{metrica}**\n",
        f"N exemplos: {len(resultados)}\n",
        f"Score médio: **{media:.3f}**\n",
        "\n## Detalhe por exemplo\n",
    ]
    for r in resultados[:20]:
        relatorio.append(f"- score={r['score']:.3f} — {r['pergunta'][:80]}")

    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/avaliacao.md").write_text("\n".join(relatorio) + "\n", encoding="utf-8")
    print(f"Avaliação salva em docs/avaliacao.md (score médio: {media:.3f})")
    return {"metrica": metrica, "n": len(resultados), "score_medio": media}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--val", default="data/processed/val.jsonl")
    args = parser.parse_args()
    avaliar(args.val)


if __name__ == "__main__":
    main()
