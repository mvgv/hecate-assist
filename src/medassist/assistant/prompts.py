DISCLAIMER = "⚕️ Sugestão de apoio à decisão. Requer validação por médico responsável."

SYSTEM_PROMPT = (
    "Você é um assistente virtual de apoio à decisão clínica para médicos. "
    "Você NUNCA prescreve diretamente (não indica medicação, dose ou via de administração "
    "como se fosse uma prescrição definitiva) — você apenas sugere condutas com base em "
    "protocolos institucionais e conhecimento geral, sempre deixando claro que a decisão "
    "final é do médico responsável. "
    "Sempre que usar informação de um protocolo institucional, cite a fonte no formato "
    "[DOC-ID §secao]. "
    "Sempre encerre a resposta recomendando validação humana antes de qualquer conduta. "
    "Responda sempre em português do Brasil, de forma objetiva e clinicamente precisa."
)

PROMPT_TRIAGEM = (
    "Classifique a pergunta do médico em exatamente uma das categorias: "
    "'duvida_clinica' (pergunta geral sobre protocolo ou conduta clínica), "
    "'caso_paciente' (refere-se a um paciente específico) ou "
    "'fora_escopo' (não é uma pergunta clínica, ou pede prescrição direta sem contexto "
    "de apoio à decisão). Responda apenas com a categoria."
)

PROMPT_VERIFICADOR = (
    "AVALIE a resposta abaixo segundo a rubrica de segurança institucional: "
    "(1) não deve prescrever diretamente sem mencionar validação médica; "
    "(2) não deve afirmar diagnóstico definitivo sem hedge apropriado; "
    "(3) não deve citar fontes que não estejam entre os documentos recuperados; "
    "(4) não deve sugerir conduta envolvendo substância à qual o paciente é alérgico. "
    'Responda em JSON estrito: {"aprovada": true|false, "violacoes": ["codigo", ...]}.'
)

TEMPLATE_FEEDBACK_REGENERACAO = (
    "\n\nATENÇÃO: sua resposta anterior foi reprovada pelos guardrails de segurança "
    "pelos seguintes motivos: {violacoes}. Reformule a resposta corrigindo esses pontos — "
    "não prescreva diretamente, evite diagnóstico definitivo sem hedge, cite apenas os "
    "documentos fornecidos e não sugira substâncias às quais o paciente é alérgico."
)

TEMPLATE_RESPOSTA_SEGURA = (
    "Não foi possível gerar uma resposta segura para esta solicitação.\n\n"
    "Motivo: {motivo}\n\n"
    "Recomendamos avaliação manual do caso pelo médico responsável, consultando "
    "diretamente os protocolos institucionais e, se necessário, um especialista.\n\n"
    f"{DISCLAIMER}"
)

TEMPLATE_RECUSA = (
    "Este assistente é especializado em apoio à decisão clínica para médicos e não pode "
    "responder a essa solicitação. Por favor, faça uma pergunta relacionada a protocolos "
    "clínicos, condutas médicas ou casos de pacientes cadastrados."
)

# Heuristica determinística de triagem (~40 termos clínicos)
TERMOS_CLINICOS = [
    "sepse", "séptico", "septico", "dor torácica", "dor toracica", "infarto",
    "hipoglicemia", "glicemia", "avc", "acidente vascular", "hipertensiva",
    "hipertensão", "hipertensao", "anafilaxia", "alergia", "pneumonia",
    "cetoacidose", "diabetes", "diabético", "diabetico", "tep",
    "tromboembolismo", "embolia", "hemorragia digestiva", "melena",
    "hematêmese", "hematemese", "delirium", "confusão mental", "confusao mental",
    "dor abdominal", "abdome agudo", "protocolo", "conduta", "tratamento",
    "diagnóstico", "diagnostico", "sintoma", "sintomas", "exame", "exames",
    "medicação", "medicacao", "dose", "posologia", "paciente", "quadro clínico",
    "quadro clinico", "febre", "taquicardia", "dispneia", "choque",
]
