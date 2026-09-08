"""CLI: medassist download-data - baixa o MedQuAD (clone raso) para data/raw/.

Nao e usado pelos testes automatizados. Se nao houver acesso a rede, imprime
instrucoes manuais e encerra com sucesso (nao trava o pipeline de CI/dev).
"""
import subprocess
from pathlib import Path

_REPO_URL = "https://github.com/abachaa/MedQuAD.git"


def download_data(destino: str = "data/raw") -> bool:
    caminho = Path(destino)
    caminho.mkdir(parents=True, exist_ok=True)
    alvo = caminho / "MedQuAD"

    if alvo.exists():
        print(f"{alvo} já existe - nada a fazer.")
        return True

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", _REPO_URL, str(alvo)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        print(f"MedQuAD clonado em {alvo}.")
        return True
    except Exception as exc:
        print(
            "Não foi possível baixar o MedQuAD automaticamente "
            f"({exc}).\n"
            "Baixe manualmente com:\n"
            f"  git clone --depth 1 {_REPO_URL} {alvo}\n"
            "ou faça o download do ZIP em https://github.com/abachaa/MedQuAD "
            f"e extraia o conteúdo em {alvo}."
        )
        return False


if __name__ == "__main__":
    download_data()
