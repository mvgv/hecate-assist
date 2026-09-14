from medassist.assistant import guardrails


def test_prescricao_direta_sem_validacao_regenera(tmp_settings):
    state = {
        "resposta_bruta": "Prescrever amoxicilina 500 mg VO 8/8h por 7 dias.",
        "docs": [],
        "paciente": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "regenerar"
    assert "prescricao_direta" in resultado["violacoes"]


def test_prescricao_com_mencao_a_validacao_nao_viola(tmp_settings):
    state = {
        "resposta_bruta": (
            "Prescrever amoxicilina 500 mg VO 8/8h por 7 dias, sujeito a validação "
            "pelo médico responsável."
        ),
        "docs": [],
        "paciente": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "aprovada"


def test_diagnostico_definitivo_sem_hedge_regenera(tmp_settings):
    state = {
        "resposta_bruta": "O paciente tem pneumonia bacteriana grave.",
        "docs": [],
        "paciente": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "regenerar"
    assert "diagnostico_definitivo" in resultado["violacoes"]


def test_diagnostico_com_hedge_nao_viola(tmp_settings):
    state = {
        "resposta_bruta": "O quadro é compatível com pneumonia bacteriana.",
        "docs": [],
        "paciente": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "aprovada"


def test_fonte_alucinada_regenera(tmp_settings):
    state = {
        "resposta_bruta": "Conforme [PROT-099 §1], a conduta é observação.",
        "docs": [{"doc_id": "PROT-001", "titulo": "x", "secao": "1", "conteudo": "y", "score": 0.9}],
        "paciente": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "regenerar"
    assert "fonte_alucinada" in resultado["violacoes"]


def test_fonte_valida_nao_viola(tmp_settings):
    state = {
        "resposta_bruta": "Conforme [PROT-001 §1], a conduta é observação.",
        "docs": [{"doc_id": "PROT-001", "titulo": "x", "secao": "1", "conteudo": "y", "score": 0.9}],
        "paciente": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "aprovada"


def test_alergia_paciente_bloqueia_e_nunca_regenera(tmp_settings):
    state = {
        "resposta_bruta": "Sugere-se penicilina cristalina para o quadro.",
        "docs": [],
        "paciente": {"alergias": [{"substancia": "penicilina", "gravidade": "grave"}]},
        "tentativas": 0,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "bloqueada"
    assert resultado["violacoes"] == ["alergia_paciente"]


def test_requer_aprovacao_quando_sugere_conduta_com_paciente(tmp_settings):
    state = {
        "resposta_bruta": "Recomenda-se iniciar tratamento sintomático.",
        "docs": [],
        "paciente": {"alergias": []},
        "paciente_id": "P003",
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "aprovada"
    assert resultado["requer_aprovacao"] is True


def test_nao_requer_aprovacao_sem_paciente(tmp_settings):
    state = {
        "resposta_bruta": "Recomenda-se iniciar tratamento sintomático.",
        "docs": [],
        "paciente": None,
        "paciente_id": None,
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "aprovada"
    assert resultado["requer_aprovacao"] is False


def test_fonte_de_modelo_de_documento_alucinada_regenera(tmp_settings):
    """Citacao [PROT-026..028] passa pela mesma checagem de fonte que os protocolos."""
    state = {
        "resposta_bruta": "Use a estrutura descrita em [PROT-099 §2].",
        "docs": [{"doc_id": "PROT-026", "secao": "2. Estrutura do documento"}],
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "regenerar"
    assert "fonte_alucinada" in resultado["violacoes"]


def test_fonte_de_modelo_de_documento_valida_nao_viola(tmp_settings):
    state = {
        "resposta_bruta": "Conforme [PROT-026 §2], o laudo tem descricao e conclusao.",
        "docs": [{"doc_id": "PROT-026", "secao": "2. Estrutura do documento"}],
    }
    assert guardrails.validar(state)["veredito"] == "aprovada"


def test_fonte_alucinada_sem_colchete_regenera(tmp_settings):
    """A forma dominante no dataset e "Conforme PROT-001 §2" — sem colchete."""
    state = {
        "resposta_bruta": "Conforme PROT-001 §1, o laudo tem descricao e conclusao.",
        "docs": [{"doc_id": "PROT-026", "secao": "2. Estrutura do documento"}],
    }
    resultado = guardrails.validar(state)
    assert resultado["veredito"] == "regenerar"
    assert "fonte_alucinada" in resultado["violacoes"]


def test_fonte_valida_sem_colchete_nao_viola(tmp_settings):
    state = {
        "resposta_bruta": "Conforme PROT-026 §2, o laudo tem descricao e conclusao.",
        "docs": [{"doc_id": "PROT-026", "secao": "2. Estrutura do documento"}],
    }
    assert guardrails.validar(state)["veredito"] == "aprovada"
