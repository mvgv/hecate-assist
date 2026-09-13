"""CLI: medassist build-dataset - gera o dataset de fine-tuning em formato chat JSONL."""
import json
import random
import re
from pathlib import Path

from medassist.assistant.prompts import SYSTEM_PROMPT
from medassist.data.anonymize import anonimizar
from medassist.rag.ingest import _dividir_em_secoes, _parse_frontmatter

_SEED = 42
_SPLIT_TREINO = 0.95

# Perguntas por secao do modelo de documento. O {assunto} vem do titulo do
# template (ex.: "laudo de exame") e o numero da secao vira a citacao §N.
_PERGUNTAS_TEMPLATE = {
    "1": "Quando devo usar o modelo institucional de {assunto}?",
    "2": "Qual a estrutura do modelo institucional de {assunto}?",
    "3": "Me mostre um exemplo preenchido de {assunto}.",
    "4": "Quais as regras de preenchimento do modelo de {assunto}?",
}


def _chat(pergunta: str, resposta: str) -> dict:
    """Monta um exemplo no formato chat, anonimizando as duas pontas."""
    pergunta, _ = anonimizar(pergunta)
    resposta, _ = anonimizar(resposta)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": resposta},
        ]
    }


def _corpo_sem_rodape(corpo: str) -> str:
    return corpo.split("---\n*Documento sintético")[0].strip()


def _exemplos_faqs(caminho_faqs: Path) -> list[dict]:
    exemplos = []
    if not caminho_faqs.exists():
        return exemplos
    for linha in caminho_faqs.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        item = json.loads(linha)
        exemplos.append(_chat(item["pergunta"], item["resposta"]))
    return exemplos


def _exemplos_protocolos(diretorio: Path) -> list[dict]:
    exemplos = []
    for arquivo in sorted(diretorio.glob("*.md")):
        meta, corpo = _parse_frontmatter(arquivo.read_text(encoding="utf-8"))
        doc_id = meta.get("doc_id", arquivo.stem)
        titulo = meta.get("titulo", "")

        exemplos.append(
            _chat(
                f"Explique o protocolo {doc_id} - {titulo}.",
                f"{_corpo_sem_rodape(corpo)}\n\n[{doc_id}]",
            )
        )
    return exemplos


def _exemplos_templates(diretorio: Path) -> list[dict]:
    """Exemplos a partir dos modelos de laudo, receita e procedimento (TPL-NNN).

    O enunciado da fase pede que o fine-tuning use tambem "modelos de laudos,
    receitas e procedimentos internos" — esta e a fatia que cobre esse requisito.
    Uma pergunta por secao (quando usar / estrutura / exemplo / regras) mais uma
    do documento inteiro, todas citando [TPL-NNN §secao] como os protocolos.
    """
    exemplos = []
    for arquivo in sorted(diretorio.glob("*.md")):
        meta, corpo = _parse_frontmatter(arquivo.read_text(encoding="utf-8"))
        doc_id = meta.get("doc_id", arquivo.stem)
        titulo = meta.get("titulo", "")
        assunto = re.sub(r"^Modelo Institucional de\s+", "", titulo).strip().lower()
        corpo_limpo = _corpo_sem_rodape(corpo)

        for titulo_secao, texto_secao in _dividir_em_secoes(corpo_limpo):
            numero = titulo_secao.split(".", 1)[0].strip()
            molde = _PERGUNTAS_TEMPLATE.get(numero)
            if not molde or not texto_secao.strip():
                continue
            exemplos.append(
                _chat(
                    molde.format(assunto=assunto),
                    f"Conforme [{doc_id} §{numero}], {texto_secao.strip()}",
                )
            )

        exemplos.append(
            _chat(f"Explique o modelo {doc_id} - {titulo}.", f"{corpo_limpo}\n\n[{doc_id}]")
        )
    return exemplos


def build_dataset(out_dir: str = "data/processed/", base_dir: str = "data/synthetic") -> dict:
    base = Path(base_dir)
    exemplos = (
        _exemplos_faqs(base / "faqs.jsonl")
        + _exemplos_protocolos(base / "protocolos")
        + _exemplos_templates(base / "templates")
    )

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
