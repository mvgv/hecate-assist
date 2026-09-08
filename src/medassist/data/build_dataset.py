"""CLI: medassist build-dataset - gera o dataset de fine-tuning em formato chat JSONL."""
import json
import random
from pathlib import Path

from medassist.assistant.prompts import SYSTEM_PROMPT
from medassist.data.anonymize import anonimizar
from medassist.rag.ingest import _parse_frontmatter

_SEED = 42
_SPLIT_TREINO = 0.95


def _exemplos_faqs(caminho_faqs: Path) -> list[dict]:
    exemplos = []
    if not caminho_faqs.exists():
        return exemplos
    for linha in caminho_faqs.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        item = json.loads(linha)
        pergunta, _ = anonimizar(item["pergunta"])
        resposta, _ = anonimizar(item["resposta"])
        exemplos.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pergunta},
                    {"role": "assistant", "content": resposta},
                ]
            }
        )
    return exemplos


def _exemplos_protocolos(diretorio: Path) -> list[dict]:
    exemplos = []
    for arquivo in sorted(diretorio.glob("*.md")):
        meta, corpo = _parse_frontmatter(arquivo.read_text(encoding="utf-8"))
        doc_id = meta.get("doc_id", arquivo.stem)
        titulo = meta.get("titulo", "")

        corpo_limpo = corpo.split("---\n*Documento sintético")[0].strip()
        pergunta = f"Explique o protocolo {doc_id} - {titulo}."
        resposta = f"{corpo_limpo}\n\n[{doc_id}]"

        pergunta, _ = anonimizar(pergunta)
        resposta, _ = anonimizar(resposta)

        exemplos.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pergunta},
                    {"role": "assistant", "content": resposta},
                ]
            }
        )
    return exemplos


def build_dataset(out_dir: str = "data/processed/", base_dir: str = "data/synthetic") -> dict:
    base = Path(base_dir)
    exemplos = _exemplos_faqs(base / "faqs.jsonl") + _exemplos_protocolos(base / "protocolos")

    rng = random.Random(_SEED)
    rng.shuffle(exemplos)

    corte = int(len(exemplos) * _SPLIT_TREINO)
    treino, val = exemplos[:corte], exemplos[corte:]

    destino = Path(out_dir)
    destino.mkdir(parents=True, exist_ok=True)

    def _escrever(caminho: Path, itens: list[dict]) -> None:
        with caminho.open("w", encoding="utf-8") as f:
            for item in itens:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    _escrever(destino / "train.jsonl", treino)
    _escrever(destino / "val.jsonl", val)

    tokens_aprox = sum(
        len(m["content"].split()) for ex in exemplos for m in ex["messages"]
    )

    stats = {
        "n_exemplos": len(exemplos),
        "n_treino": len(treino),
        "n_val": len(val),
        "tokens_aproximados": tokens_aprox,
    }
    print(
        f"Dataset gerado: {stats['n_exemplos']} exemplos "
        f"({stats['n_treino']} treino / {stats['n_val']} val), "
        f"~{stats['tokens_aproximados']} tokens (aprox., contagem por palavras)."
    )
    return stats


if __name__ == "__main__":
    build_dataset()
