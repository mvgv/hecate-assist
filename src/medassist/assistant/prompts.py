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
    "Você classifica a mensagem de um médico em UMA palavra, sem explicação.\n"
    "- duvida_clinica: é uma pergunta sobre conduta, protocolo, diagnóstico, "
    "dose, exame ou manejo clínico de qualquer doença ou situação médica.\n"
    "- fora_escopo: não tem nada a ver com medicina (ex.: piadas, geografia, "
    "conversa fiada, pedidos administrativos).\n"
    "Na dúvida, responda duvida_clinica.\n\n"
    "Exemplos:\n"
    "Q: Qual a conduta inicial na sepse?\nA: duvida_clinica\n"
    "Q: Qual a dose de noradrenalina no choque séptico?\nA: duvida_clinica\n"
    "Q: Como investigo TEP?\nA: duvida_clinica\n"
    "Q: manejo de hipercalemia grave\nA: duvida_clinica\n"
    "Q: Me conte uma piada\nA: fora_escopo\n"
    "Q: Qual a capital da França?\nA: fora_escopo\n\n"
    "Responda apenas com duvida_clinica ou fora_escopo."
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

# Heuristica determinística de triagem (pré-filtro por palavra-chave antes do LLM).
# Cobre o vocabulário dos 25 protocolos (PROT-001..025) + termos genéricos.
TERMOS_CLINICOS = [
    # genéricos
    "protocolo", "conduta", "tratamento", "manejo", "abordagem", "diagnóstico",
    "diagnostico", "sintoma", "sintomas", "exame", "exames", "medicação", "medicacao",
    "dose", "posologia", "paciente", "quadro clínico", "quadro clinico", "febre",
    "taquicardia", "dispneia", "dispnéia", "choque", "hipotensão", "hipotensao",
    "hipoxemia", "saturação", "saturacao", "gasometria", "uti", "escalonar",
    "internação", "internacao", "antibiótico", "antibiotico", "anticoagulação",
    "anticoagulacao", "reposição volêmica", "cristaloide", "vasopressor",
    # PROT-001..012
    "sepse", "séptico", "septico", "dor torácica", "dor toracica", "infarto",
    "síndrome coronariana", "sindrome coronariana", "sca", "dissecção de aorta",
    "hipoglicemia", "glicemia", "avc", "acidente vascular", "trombólise", "trombolise",
    "alteplase", "hipertensiva", "hipertensão", "hipertensao", "crise hipertensiva",
    "anafilaxia", "alergia", "adrenalina", "pneumonia", "pac", "curb-65",
    "cetoacidose", "cad", "diabetes", "diabético", "diabetico", "tep",
    "tromboembolismo", "embolia pulmonar", "hemorragia digestiva", "hda", "melena",
    "hematêmese", "hematemese", "varizes", "delirium", "confusão mental",
    "confusao mental", "dor abdominal", "abdome agudo", "apendicite", "peritonite",
    # PROT-013..025
    "fibrilação atrial", "fibrilacao atrial", "fa aguda", "arritmia", "cardioversão",
    "cardioversao", "estado de mal", "convulsão", "convulsao", "crise convulsiva",
    "epiléptico", "epileptico", "benzodiazepínico", "benzodiazepinico",
    "lesão renal", "lesao renal", "lra", "creatinina", "diálise", "dialise",
    "hipercalemia", "potássio", "potassio", "gluconato de cálcio", "hiponatremia",
    "sódio", "sodio", "salina hipertônica", "hipertonica", "paracetamol",
    "acetaminofeno", "intoxicação", "intoxicacao", "n-acetilcisteína", "overdose",
    "dpoc", "exacerbação", "exacerbacao", "ventilação não invasiva", "vni",
    "broncodilatador", "asma", "asmática", "asmatica", "sibilância", "pico de fluxo",
    "meningite", "rigidez de nuca", "líquor", "liquor", "punção lombar",
    "puncao lombar", "dexametasona", "pielonefrite", "itu", "infecção urinária",
    "infeccao urinaria", "dor lombar", "giordano", "urocultura", "abstinência",
    "abstinencia", "alcoólica", "alcoolica", "delirium tremens", "ciwa", "tiamina",
    "analgesia", "dor aguda", "opioide", "morfina", "dipirona", "escala de dor",
    "trombose venosa", "tvp", "d-dímero", "d-dimero", "wells", "hemoglobina",
    "transfusão", "transfusao",
]
