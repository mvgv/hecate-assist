from medassist.data.anonymize import anonimizar


def test_cpf_e_substituido():
    limpo, tipos = anonimizar("CPF do paciente: 123.456.789-01")
    assert "[CPF]" in limpo
    assert "123.456.789-01" not in limpo
    assert "cpf" in tipos


def test_crm_e_substituido():
    limpo, tipos = anonimizar("Assinado por Dra. Ana, CRM-SP 123456")
    assert "[CRM]" in limpo
    assert "crm" in tipos


def test_email_e_substituido():
    limpo, tipos = anonimizar("Contato: medico@hospital.com.br")
    assert "[EMAIL]" in limpo
    assert "medico@hospital.com.br" not in limpo
    assert "email" in tipos


def test_data_e_substituida():
    limpo, tipos = anonimizar("Consulta em 15/03/2026")
    assert "[DATA]" in limpo
    assert "15/03/2026" not in limpo
    assert "data" in tipos


def test_telefone_e_substituido():
    limpo, tipos = anonimizar("Ligar para (11) 98765-4321")
    assert "[TELEFONE]" in limpo
    assert "telefone" in tipos


def test_nome_e_substituido_mantendo_gatilho():
    limpo, tipos = anonimizar("paciente Joao Silva foi atendido")
    assert "[NOME]" in limpo
    assert "paciente" in limpo
    assert "Joao Silva" not in limpo
    assert "nome" in tipos


def test_texto_sem_pii_nao_altera():
    texto = "Sem nenhuma informacao sensivel aqui."
    limpo, tipos = anonimizar(texto)
    assert limpo == texto
    assert tipos == []


def test_multiplos_tipos_no_mesmo_texto():
    texto = "paciente Maria Souza, CPF 111.222.333-44, tel (21) 91234-5678"
    limpo, tipos = anonimizar(texto)
    assert set(tipos) >= {"nome", "cpf", "telefone"}
    assert "Maria Souza" not in limpo
    assert "111.222.333-44" not in limpo
