import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from medassist.config import get_settings


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    campos = [col[0] for col in cursor.description]
    return dict(zip(campos, row))


@contextmanager
def _conectar():
    settings = get_settings()
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _calcular_idade(data_nascimento: str) -> int:
    nascimento = datetime.fromisoformat(data_nascimento).date()
    hoje = date.today()
    anos = hoje.year - nascimento.year
    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        anos -= 1
    return anos


def list_patients() -> list[dict]:
    """Lista pacientes (id, nome) para uso em seletores de UI."""
    with _conectar() as conn:
        return conn.execute("SELECT id, nome FROM pacientes ORDER BY nome").fetchall()


def get_patient_context(paciente_id: str) -> dict | None:
    with _conectar() as conn:
        paciente = conn.execute(
            "SELECT * FROM pacientes WHERE id = ?", (paciente_id,)
        ).fetchone()
        if paciente is None:
            return None

        alergias = conn.execute(
            "SELECT substancia, gravidade FROM alergias WHERE paciente_id = ?",
            (paciente_id,),
        ).fetchall()

        return {
            "id": paciente["id"],
            "nome": paciente["nome"],
            "idade": _calcular_idade(paciente["data_nascimento"]),
            "sexo": paciente["sexo"],
            "comorbidades": json.loads(paciente["comorbidades"]),
            "medicacoes_em_uso": json.loads(paciente["medicacoes_em_uso"]),
            "alergias": alergias,
        }


def get_pending_exams(paciente_id: str) -> list[dict]:
    with _conectar() as conn:
        return conn.execute(
            "SELECT * FROM exames WHERE paciente_id = ? AND status = 'pendente'",
            (paciente_id,),
        ).fetchall()


def get_critical_exams(paciente_id: str) -> list[dict]:
    with _conectar() as conn:
        exames = conn.execute(
            "SELECT * FROM exames WHERE paciente_id = ? AND status = 'concluido'",
            (paciente_id,),
        ).fetchall()

    criticos = []
    for exame in exames:
        resultado = exame.get("resultado")
        minimo = exame.get("faixa_critica_min")
        maximo = exame.get("faixa_critica_max")
        if resultado is None:
            continue
        if minimo is not None and resultado < minimo:
            criticos.append(exame)
        elif maximo is not None and resultado > maximo:
            criticos.append(exame)
    return criticos


def create_alert(
    paciente_id: str,
    tipo: str,
    severidade: str,
    mensagem: str,
    aprovado_por: str | None = None,
) -> int | None:
    with _conectar() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO alertas (paciente_id, tipo, severidade, mensagem, aprovado_por)
                VALUES (?, ?, ?, ?, ?)
                """,
                (paciente_id, tipo, severidade, mensagem, aprovado_por),
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def list_alerts(paciente_id: str | None = None) -> list[dict]:
    with _conectar() as conn:
        if paciente_id is None:
            return conn.execute(
                "SELECT * FROM alertas ORDER BY criado_em DESC"
            ).fetchall()
        return conn.execute(
            "SELECT * FROM alertas WHERE paciente_id = ? ORDER BY criado_em DESC",
            (paciente_id,),
        ).fetchall()
