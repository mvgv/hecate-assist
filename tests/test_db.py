from medassist.db.queries import (
    create_alert,
    get_critical_exams,
    get_patient_context,
    get_pending_exams,
    list_alerts,
)
from medassist.db.seed import seed_db


def test_seed_e_idempotente(tmp_settings):
    n1 = seed_db()
    assert n1 == 12
    n2 = seed_db()
    assert n2 == 0


def test_p001_tem_alergia_grave_e_exame_critico(db_seeded):
    ctx = get_patient_context("P001")
    assert ctx is not None
    assert any(a["substancia"] == "penicilina" and a["gravidade"] == "grave" for a in ctx["alergias"])

    criticos = get_critical_exams("P001")
    assert len(criticos) == 1
    assert criticos[0]["tipo"] == "potassio_serico"
    assert criticos[0]["resultado"] == 6.2


def test_p002_tem_exame_pendente(db_seeded):
    pendentes = get_pending_exams("P002")
    assert len(pendentes) == 1
    assert pendentes[0]["tipo"] == "hemograma"
    assert pendentes[0]["status"] == "pendente"


def test_p003_caminho_feliz_sem_alergias_nem_pendencias(db_seeded):
    ctx = get_patient_context("P003")
    assert ctx["alergias"] == []
    assert get_pending_exams("P003") == []
    assert get_critical_exams("P003") == []


def test_paciente_inexistente_retorna_none(db_seeded):
    assert get_patient_context("P999") is None


def test_create_alert_duas_vezes_no_mesmo_dia(db_seeded):
    id1 = create_alert("P003", "sugestao_tratamento", "atencao", "primeira mensagem")
    id2 = create_alert("P003", "sugestao_tratamento", "atencao", "segunda mensagem, mesmo dia")

    assert id1 is not None
    assert id2 is None

    alertas = list_alerts("P003")
    assert len(alertas) == 1


def test_list_alerts_sem_filtro_retorna_todos(db_seeded):
    create_alert("P001", "exame_critico", "critico", "potassio alto")
    create_alert("P002", "exame_critico", "critico", "outro alerta")

    todos = list_alerts()
    assert len(todos) == 2
