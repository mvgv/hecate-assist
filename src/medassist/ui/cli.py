import sys
import uuid

import typer

app = typer.Typer(help="MedAssist - assistente virtual medico (apoio a decisao)")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@app.command("seed-db")
def seed_db_cmd() -> None:
    """Popula o SQLite com pacientes ficticios (idempotente)."""
    from medassist.db.seed import seed_db

    n = seed_db()
    if n:
        typer.echo(f"{n} pacientes inseridos.")
    else:
        typer.echo("Banco ja possui dados - nada a fazer (idempotente).")


@app.command("ingest")
def ingest_cmd() -> None:
    """Indexa os protocolos sinteticos no ChromaDB."""
    from medassist.rag.ingest import ingest

    n = ingest()
    typer.echo(f"{n} chunks indexados.")


@app.command("build-dataset")
def build_dataset_cmd(
    out: str = typer.Option("data/processed/", "--out", help="Diretorio de saida"),
) -> None:
    """Gera o dataset de fine-tuning (train/val JSONL) a partir de FAQs e protocolos."""
    from medassist.data.build_dataset import build_dataset

    build_dataset(out)


@app.command("download-data")
def download_data_cmd() -> None:
    """Baixa o dataset externo MedQuAD (clone raso) para data/raw/."""
    from medassist.data.download import download_data

    download_data()


@app.command("ask")
def ask_cmd(
    pergunta: str = typer.Argument(..., help="Pergunta do medico"),
    paciente: str | None = typer.Option(None, "--paciente", help="ID do paciente (ex.: P001)"),
    thread: str | None = typer.Option(None, "--thread", help="ID da conversa (thread)"),
) -> None:
    """Envia uma pergunta ao assistente e imprime a resposta."""
    from medassist.assistant.graph import responder

    thread_id = thread or str(uuid.uuid4())
    resultado = responder(pergunta, paciente, thread_id)

    if "__interrupt__" in resultado:
        interrupt = resultado["__interrupt__"][0]
        typer.echo("⏸  Aprovacao humana pendente:")
        typer.echo(f"  Resposta proposta: {interrupt.value.get('resposta_proposta')}")
        typer.echo(f"  Fontes: {interrupt.value.get('fontes')}")
        typer.echo(f"  Motivo: {interrupt.value.get('motivo')}")
        typer.echo(f"\nPara continuar: medassist resume {thread_id} --aprovado --aprovador \"Dr. Fulano\"")
        return

    typer.echo(resultado.get("resposta_final", "(sem resposta)"))


@app.command("resume")
def resume_cmd(
    thread: str = typer.Argument(..., help="ID da conversa (thread) pendente de aprovacao"),
    aprovado: bool = typer.Option(..., "--aprovado/--rejeitado", help="Decisao do medico"),
    aprovador: str = typer.Option("desconhecido", "--aprovador", help="Nome/CRM de quem aprovou"),
    observacao: str = typer.Option("", "--observacao", help="Observacao opcional"),
) -> None:
    """Retoma uma conversa pausada aguardando aprovacao humana."""
    from medassist.assistant.graph import retomar

    resultado = retomar(thread, aprovado, aprovador, observacao)
    typer.echo(resultado.get("resposta_final", "(sem resposta)"))


@app.command("alerts")
def alerts_cmd(
    paciente: str | None = typer.Option(None, "--paciente", help="Filtrar por ID do paciente"),
) -> None:
    """Lista alertas registrados."""
    from medassist.db.queries import list_alerts

    alertas = list_alerts(paciente)
    if not alertas:
        typer.echo("Nenhum alerta encontrado.")
        return
    for alerta in alertas:
        typer.echo(
            f"[{alerta['severidade']}] {alerta['paciente_id']} - {alerta['tipo']}: "
            f"{alerta['mensagem']} ({alerta['criado_em']})"
        )


if __name__ == "__main__":
    app()
