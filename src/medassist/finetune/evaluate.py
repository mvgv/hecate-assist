"""Avalia o modelo fine-tuned vs. o modelo base no conjunto de validacao.

Metricas (todas calculadas por exemplo, media ao final):
- `rougeL`: F-measure ROUGE-L contra a resposta de referencia (so se
  `rouge-score` estiver instalado).
- `doc_ids`: fracao das citacoes `[PROT-NNN]` da referencia que a resposta
  gerada tambem cita (sempre disponivel).
- `formato`: 1.0 se a resposta cita ao menos um `[PROT-NNN]` E termina
  recomendando validacao medica (o que o fine-tune deveria ter aprendido).

Roda um passe completo por modelo (evita ficar trocando modelo no Ollama a
cada exemplo) e escreve a comparacao em `docs/avaliacao.md`.

Uso:
    # dentro do container app (MEDASSIST_LLM_PROVIDER=ollama):
    python -m medassist.finetune.evaluate --modelos medassist llama3.1:8b
"""
import argparse
import json
import re
from pathlib import Path

_RE_DOC = re.compile(r"PROT-\d+")
_RE_VALIDACAO = re.compile(
    r"valida\w+|médico responsável|medico responsavel|avalia\w+ (pelo|com|clínic)", re.IGNORECASE
)


def _doc_ids(texto: str) -> set[str]:
    return set(_RE_DOC.findall(texto))


def _score_doc_ids(referencia: str, gerada: str) -> float:
    docs_ref = _doc_ids(referencia)
    if not docs_ref:
        return 1.0 if not _doc_ids(gerada) else 0.0
    return len(docs_ref & _doc_ids(gerada)) / len(docs_ref)


def _score_formato(_referencia: str, gerada: str) -> float:
    cita = bool(_RE_DOC.search(gerada))
    valida = bool(_RE_VALIDACAO.search(gerada))
    return 1.0 if (cita and valida) else 0.0


def _rouge_l_scorer():
    try:
        from rouge_score import rouge_scorer
    except ImportError:
        return None
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    return lambda ref, gen: scorer.score(ref, gen)["rougeL"].fmeasure


def _carregar_val(val_path: str) -> list[tuple[str, str]]:
    pares = []
    for linha in Path(val_path).read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        exemplo = json.loads(linha)
        pergunta = next(m["content"] for m in exemplo["messages"] if m["role"] == "user")
        referencia = next(m["content"] for m in exemplo["messages"] if m["role"] == "assistant")
        pares.append((pergunta, referencia))
    return pares


def _gerar_fn(modelo: str):
    from medassist.assistant.prompts import SYSTEM_PROMPT
    from medassist.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider(model=modelo)

    def gerar(pergunta: str) -> str:
        return provider.gerar(
            system=SYSTEM_PROMPT, mensagens=[{"role": "user", "content": pergunta}]
        )

    return gerar


def avaliar_modelo(pares: list[tuple[str, str]], gerar_fn, rouge_fn=None) -> dict:
    linhas = []
    for pergunta, referencia in pares:
        gerada = gerar_fn(pergunta)
        registro = {
            "pergunta": pergunta,
            "doc_ids": _score_doc_ids(referencia, gerada),
            "formato": _score_formato(referencia, gerada),
        }
        if rouge_fn is not None:
            registro["rougeL"] = rouge_fn(referencia, gerada)
        linhas.append(registro)

    metricas = ["rougeL", "doc_ids", "formato"] if rouge_fn else ["doc_ids", "formato"]
    medias = {
        m: (sum(r[m] for r in linhas) / len(linhas) if linhas else 0.0) for m in metricas
    }
    return {"n": len(linhas), "medias": medias, "detalhe": linhas, "metricas": metricas}


def avaliar(val_path: str, modelos: list[str]) -> dict:
    pares = _carregar_val(val_path)
    rouge_fn = _rouge_l_scorer()

    resultados = {}
    for modelo in modelos:
        print(f"avaliando '{modelo}' em {len(pares)} exemplos...")
        resultados[modelo] = avaliar_modelo(pares, _gerar_fn(modelo), rouge_fn)

    metricas = next(iter(resultados.values()))["metricas"] if resultados else []

    rouge_nota = "disponível" if rouge_fn else "indisponível (rouge-score não instalado)"
    rel = ["# Avaliação — base vs. fine-tuned\n"]
    rel.append(f"Conjunto: `{val_path}` ({len(pares)} exemplos)\n")
    rel.append(f"Métrica ROUGE-L: {rouge_nota}\n")
    rel.append("\n## Resumo\n")
    rel.append("| modelo | " + " | ".join(metricas) + " |")
    rel.append("|" + "---|" * (len(metricas) + 1))
    for modelo, res in resultados.items():
        rel.append(
            f"| `{modelo}` | "
            + " | ".join(f"{res['medias'][m]:.3f}" for m in metricas)
            + " |"
        )

    rel.append("\n## Interpretação\n")
    rel.append(
        "- **`formato`** é o eixo que o fine-tune deveria mover: citar `[PROT-NNN]` "
        "e encerrar recomendando validação médica. É onde a diferença aparece.\n"
        "- **`doc_ids`** é ruidoso neste conjunto — várias respostas de referência do "
        "`val.jsonl` não usam a citação em colchetes, então o score pune quem cita. "
        "E identificar o protocolo certo sem contexto é tarefa do RAG, não do "
        "fine-tune (o modelo alucina o número quando gera sem os documentos).\n"
        "- ROUGE-L (proximidade textual da referência) daria um sinal melhor; "
        "instalar `rouge-score` e rodar de novo para tê-lo.\n"
    )
    rel.append("\n## Detalhe por exemplo\n")
    for i, (pergunta, _) in enumerate(pares):
        rel.append(f"\n**{i + 1}. {pergunta[:90]}**\n")
        rel.append("| modelo | " + " | ".join(metricas) + " |")
        rel.append("|" + "---|" * (len(metricas) + 1))
        for modelo, res in resultados.items():
            d = res["detalhe"][i]
            rel.append(f"| `{modelo}` | " + " | ".join(f"{d[m]:.3f}" for m in metricas) + " |")

    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/avaliacao.md").write_text("\n".join(rel) + "\n", encoding="utf-8")

    resumo = {modelo: res["medias"] for modelo, res in resultados.items()}
    print(f"Avaliação salva em docs/avaliacao.md\n{json.dumps(resumo, indent=2, ensure_ascii=False)}")
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--val", default="data/processed/val.jsonl")
    parser.add_argument(
        "--modelos",
        nargs="+",
        default=["medassist", "llama3.1:8b"],
        help="nomes dos modelos no Ollama (1o = fine-tuned, 2o = base).",
    )
    args = parser.parse_args()
    avaliar(args.val, args.modelos)


if __name__ == "__main__":
    main()
