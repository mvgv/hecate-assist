"""CLI: medassist seed-db - popula o SQLite com pacientes ficticios (idempotente)."""
import json
import sqlite3
from pathlib import Path

from medassist.config import get_settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_PACIENTES = [
    {
        "id": "P001",
        "nome": "Joaquim Alves da Silva",
        "data_nascimento": "1958-03-12",
        "sexo": "M",
        "comorbidades": ["hipertensao", "diabetes_tipo_2"],
        "medicacoes_em_uso": ["losartana", "metformina"],
        "alergias": [{"substancia": "penicilina", "gravidade": "grave"}],
        "exames": [
            {
                "tipo": "potassio_serico",
                "status": "concluido",
                "resultado": 6.2,
                "unidade": "mEq/L",
                "faixa_critica_min": 3.5,
                "faixa_critica_max": 5.5,
                "solicitado_em": "2026-09-01",
                "concluido_em": "2026-09-02",
            }
        ],
    },
    {
        "id": "P002",
        "nome": "Marina Costa Ribeiro",
        "data_nascimento": "1990-07-22",
        "sexo": "F",
        "comorbidades": [],
        "medicacoes_em_uso": [],
        "alergias": [],
        "exames": [
            {
                "tipo": "hemograma",
                "status": "pendente",
                "resultado": None,
                "unidade": None,
                "faixa_critica_min": None,
                "faixa_critica_max": None,
                "solicitado_em": "2026-09-05",
                "concluido_em": None,
            }
        ],
    },
    {
        "id": "P003",
        "nome": "Carlos Eduardo Pereira",
        "data_nascimento": "1985-01-30",
        "sexo": "M",
        "comorbidades": [],
        "medicacoes_em_uso": [],
        "alergias": [],
        "exames": [],
    },
    {
        "id": "P004",
        "nome": "Beatriz Fernandes Lima",
        "data_nascimento": "1972-11-05",
        "sexo": "F",
        "comorbidades": ["asma"],
        "medicacoes_em_uso": ["salbutamol"],
        "alergias": [{"substancia": "dipirona", "gravidade": "moderada"}],
        "exames": [],
    },
    {
        "id": "P005",
        "nome": "Ricardo Souza Martins",
        "data_nascimento": "1965-04-18",
        "sexo": "M",
        "comorbidades": ["doenca_renal_cronica"],
        "medicacoes_em_uso": ["enalapril"],
        "alergias": [],
        "exames": [
            {
                "tipo": "creatinina",
                "status": "concluido",
                "resultado": 1.1,
                "unidade": "mg/dL",
                "faixa_critica_min": 0.6,
                "faixa_critica_max": 1.3,
                "solicitado_em": "2026-08-20",
                "concluido_em": "2026-08-21",
            }
        ],
    },
    {
        "id": "P006",
        "nome": "Fernanda Oliveira Santos",
        "data_nascimento": "1998-09-09",
        "sexo": "F",
        "comorbidades": [],
        "medicacoes_em_uso": [],
        "alergias": [{"substancia": "latex", "gravidade": "leve"}],
        "exames": [
            {
                "tipo": "glicemia_jejum",
                "status": "pendente",
                "resultado": None,
                "unidade": None,
                "faixa_critica_min": None,
                "faixa_critica_max": None,
                "solicitado_em": "2026-09-04",
                "concluido_em": None,
            }
        ],
    },
    {
        "id": "P007",
        "nome": "Antonio Carlos Nogueira",
        "data_nascimento": "1950-02-14",
        "sexo": "M",
        "comorbidades": ["insuficiencia_cardiaca", "fibrilacao_atrial"],
        "medicacoes_em_uso": ["varfarina", "furosemida"],
        "alergias": [],
        "exames": [
            {
                "tipo": "sodio_serico",
                "status": "concluido",
                "resultado": 128,
                "unidade": "mEq/L",
                "faixa_critica_min": 135,
                "faixa_critica_max": 145,
                "solicitado_em": "2026-09-03",
                "concluido_em": "2026-09-03",
            }
        ],
    },
    {
        "id": "P008",
        "nome": "Juliana Rocha Barbosa",
        "data_nascimento": "1993-06-27",
        "sexo": "F",
        "comorbidades": ["enxaqueca"],
        "medicacoes_em_uso": [],
        "alergias": [],
        "exames": [],
    },
    {
        "id": "P009",
        "nome": "Paulo Henrique Cardoso",
        "data_nascimento": "1978-12-01",
        "sexo": "M",
        "comorbidades": ["obesidade"],
        "medicacoes_em_uso": [],
        "alergias": [{"substancia": "aas", "gravidade": "moderada"}],
        "exames": [
            {
                "tipo": "colesterol_total",
                "status": "pendente",
                "resultado": None,
                "unidade": None,
                "faixa_critica_min": None,
                "faixa_critica_max": None,
                "solicitado_em": "2026-09-06",
                "concluido_em": None,
            }
        ],
    },
    {
        "id": "P010",
        "nome": "Camila Azevedo Teixeira",
        "data_nascimento": "1960-08-19",
        "sexo": "F",
        "comorbidades": ["diabetes_tipo_2", "hipertensao"],
        "medicacoes_em_uso": ["insulina_nph", "losartana"],
        "alergias": [],
        "exames": [
            {
                "tipo": "hemoglobina_glicada",
                "status": "concluido",
                "resultado": 7.1,
                "unidade": "%",
                "faixa_critica_min": 4.0,
                "faixa_critica_max": 7.0,
                "solicitado_em": "2026-08-15",
                "concluido_em": "2026-08-16",
            }
        ],
    },
    {
        "id": "P011",
        "nome": "Gustavo Henrique Moreira",
        "data_nascimento": "2001-05-10",
        "sexo": "M",
        "comorbidades": [],
        "medicacoes_em_uso": [],
        "alergias": [],
        "exames": [],
    },
    {
        "id": "P012",
        "nome": "Larissa Mendes Carvalho",
        "data_nascimento": "1945-10-23",
        "sexo": "F",
        "comorbidades": ["demencia_leve", "hipertensao"],
        "medicacoes_em_uso": ["anlodipino"],
        "alergias": [{"substancia": "penicilina", "gravidade": "leve"}],
        "exames": [
            {
                "tipo": "hemograma",
                "status": "pendente",
                "resultado": None,
                "unidade": None,
                "faixa_critica_min": None,
                "faixa_critica_max": None,
                "solicitado_em": "2026-09-06",
                "concluido_em": None,
            }
        ],
    },
]


def seed_db() -> int:
    """Popula o banco. Idempotente: so insere se `pacientes` estiver vazio.

    Retorna a quantidade de pacientes inseridos (0 se ja havia dados).
    """
    settings = get_settings()
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(settings.db_path)
    try:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))

        existentes = conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
        if existentes > 0:
            return 0

        for paciente in _PACIENTES:
            conn.execute(
                """
                INSERT INTO pacientes (id, nome, data_nascimento, sexo, comorbidades, medicacoes_em_uso)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    paciente["id"],
                    paciente["nome"],
                    paciente["data_nascimento"],
                    paciente["sexo"],
                    json.dumps(paciente["comorbidades"], ensure_ascii=False),
                    json.dumps(paciente["medicacoes_em_uso"], ensure_ascii=False),
                ),
            )
            for alergia in paciente["alergias"]:
                conn.execute(
                    "INSERT INTO alergias (paciente_id, substancia, gravidade) VALUES (?, ?, ?)",
                    (paciente["id"], alergia["substancia"], alergia["gravidade"]),
                )
            for exame in paciente["exames"]:
                conn.execute(
                    """
                    INSERT INTO exames (
                        paciente_id, tipo, status, resultado, unidade,
                        faixa_critica_min, faixa_critica_max, solicitado_em, concluido_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paciente["id"],
                        exame["tipo"],
                        exame["status"],
                        exame["resultado"],
                        exame["unidade"],
                        exame["faixa_critica_min"],
                        exame["faixa_critica_max"],
                        exame["solicitado_em"],
                        exame["concluido_em"],
                    ),
                )
        conn.commit()
        return len(_PACIENTES)
    finally:
        conn.close()
