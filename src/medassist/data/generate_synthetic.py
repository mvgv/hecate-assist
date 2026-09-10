"""CLI: gera os protocolos sinteticos (PROT-NNN.md) e o faqs.jsonl.

Deterministico, sem LLM - todo o conteudo esta hardcoded nas estruturas abaixo.
Os artefatos gerados sao versionados no repositorio (nao regenerar em runtime
de producao); este script serve para reproduzir/atualizar o dataset sintetico.
"""
import json
from pathlib import Path

RODAPE = "\n\n---\n*Documento sintético para fins acadêmicos.*\n"

PROTOCOLOS = [
    {
        "id": "PROT-001",
        "titulo": "Manejo Inicial de Sepse no Adulto",
        "versao": "1.2",
        "atualizado_em": "2025-11-10",
        "secoes": {
            "Definição e critérios": (
                "Sepse é definida como disfunção orgânica ameaçadora à vida causada por "
                "resposta desregulada do hospedeiro a uma infecção. O rastreio inicial "
                "utiliza o qSOFA (frequência respiratória ≥ 22 irpm, alteração do nível de "
                "consciência, pressão arterial sistólica ≤ 100 mmHg); dois ou mais critérios "
                "indicam maior risco e devem acionar avaliação de SOFA completo. Choque "
                "séptico é reconhecido quando há necessidade de vasopressor para manter PAM "
                "≥ 65 mmHg associada a lactato > 2 mmol/L após reposição volêmica adequada."
            ),
            "Conduta inicial": (
                "Aplicar o pacote da primeira hora: coletar lactato sérico e hemoculturas "
                "(duas amostras, sítios distintos) antes da antibioticoterapia, iniciar "
                "antibiótico empírico de amplo espectro o mais rápido possível, iniciar "
                "reposição volêmica com cristaloide 30 mL/kg em pacientes hipotensos ou com "
                "lactato ≥ 4 mmol/L, e reavaliar perfusão e resposta hemodinâmica a cada 30 "
                "minutos. Monitorização contínua de sinais vitais e diurese é obrigatória."
            ),
            "Medicações e doses de referência": (
                "Antibiótico empírico conforme foco suspeito, por exemplo piperacilina-"
                "tazobactam 4,5 g EV 6/6h para foco abdominal ou desconhecido. Cristaloide "
                "balanceado (Ringer lactato) 30 mL/kg em bolus fracionado. Se refratário a "
                "volume, iniciar noradrenalina 0,05–0,5 mcg/kg/min titulada para PAM ≥ 65 "
                "mmHg. Reavaliar necessidade de corticoide (hidrocortisona 200 mg/dia) em "
                "choque refratário a vasopressor."
            ),
            "Critérios de alerta e escalonamento": (
                "Encaminhar para unidade de terapia intensiva quando houver necessidade de "
                "vasopressor, lactato persistentemente elevado após 2–4h de reanimação, "
                "rebaixamento do nível de consciência ou disfunção de múltiplos órgãos. "
                "Reavaliação médica obrigatória em 1h e 3h após o diagnóstico inicial; "
                "qualquer suspeita de foco cirúrgico exige acionamento da equipe de cirurgia "
                "em caráter de urgência."
            ),
        },
    },
    {
        "id": "PROT-002",
        "titulo": "Investigação Inicial de Dor Torácica Aguda",
        "versao": "1.1",
        "atualizado_em": "2025-10-02",
        "secoes": {
            "Definição e critérios": (
                "Dor torácica aguda de início recente exige estratificação de risco "
                "imediata para síndrome coronariana aguda (SCA), dissecção de aorta, "
                "tromboembolismo pulmonar e pneumotórax. Características de alarme incluem "
                "dor em aperto irradiada para membro superior esquerdo ou mandíbula, "
                "sudorese, dispneia associada, dor de início súbito e caráter lancinante "
                "(sugestivo de dissecção) e dor pleurítica com fatores de risco para TEP."
            ),
            "Conduta inicial": (
                "Realizar eletrocardiograma de 12 derivações em até 10 minutos da chegada. "
                "Monitorização cardíaca contínua, oximetria e acesso venoso periférico. "
                "Coletar troponina de alta sensibilidade seriada (0h e 1–3h). Radiografia "
                "de tórax para avaliação de mediastino e parênquima pulmonar. Escore de "
                "risco (HEART ou TIMI) orienta a necessidade de internação e investigação "
                "complementar."
            ),
            "Medicações e doses de referência": (
                "Na suspeita de SCA sem contraindicação: ácido acetilsalicílico 200–300 mg "
                "VO mastigável em dose única, associado a analgesia conforme necessidade. "
                "Nitrato sublingual pode ser considerado se pressão arterial sistólica > 100 "
                "mmHg e ausência de uso recente de inibidores de fosfodiesterase. Oxigênio "
                "suplementar apenas se saturação < 90%."
            ),
            "Critérios de alerta e escalonamento": (
                "Elevação de segmento ST, instabilidade hemodinâmica, troponina em ascensão "
                "ou escore de alto risco indicam acionamento imediato da cardiologia e "
                "consideração de terapia de reperfusão. Suspeita de dissecção de aorta "
                "(diferencial de pressão entre membros, alargamento de mediastino) exige "
                "angiotomografia de aorta em caráter de emergência e contato com cirurgia "
                "vascular."
            ),
        },
    },
    {
        "id": "PROT-003",
        "titulo": "Manejo da Hipoglicemia em Adultos",
        "versao": "1.0",
        "atualizado_em": "2025-09-18",
        "secoes": {
            "Definição e critérios": (
                "Hipoglicemia é definida por glicemia capilar < 70 mg/dL, sendo considerada "
                "grave quando < 54 mg/dL ou quando há necessidade de assistência de "
                "terceiros para o tratamento. Sintomas adrenérgicos (tremor, sudorese, "
                "taquicardia) costumam preceder sintomas neuroglicopênicos (confusão, "
                "convulsão, coma), que indicam maior gravidade e risco iminente."
            ),
            "Conduta inicial": (
                "Confirmar com glicemia capilar imediata. Em paciente consciente e capaz de "
                "deglutir, ofertar 15–20 g de carboidrato de absorção rápida por via oral e "
                "reavaliar em 15 minutos (regra dos 15). Em paciente inconsciente ou "
                "incapaz de deglutir com segurança, tratar por via parenteral. Investigar "
                "causa desencadeante (uso de insulina/sulfonilureia, jejum prolongado, "
                "ingestão alcoólica)."
            ),
            "Medicações e doses de referência": (
                "Glicose 50% 20–40 mL EV em bolus lento para paciente inconsciente, seguido "
                "de infusão de manutenção com glicose 5–10% conforme resposta. Alternativa "
                "sem acesso venoso: glucagon 1 mg IM ou SC. Reavaliar glicemia capilar a "
                "cada 15 minutos até estabilização acima de 100 mg/dL."
            ),
            "Critérios de alerta e escalonamento": (
                "Hipoglicemia recorrente, uso de sulfonilureia de longa ação (risco de "
                "recorrência tardia) ou ausência de recuperação do nível de consciência "
                "após correção glicêmica exigem observação prolongada e avaliação "
                "especializada. Considerar internação em casos de hipoglicemia grave "
                "recorrente ou etiologia não esclarecida."
            ),
        },
    },
    {
        "id": "PROT-004",
        "titulo": "Manejo do AVC Isquêmico Agudo na Janela Inicial",
        "versao": "1.3",
        "atualizado_em": "2025-12-01",
        "secoes": {
            "Definição e critérios": (
                "Acidente vascular cerebral isquêmico agudo caracteriza-se por déficit "
                "neurológico focal de início súbito por oclusão vascular. A escala NIHSS "
                "quantifica a gravidade do déficit. O tempo de início dos sintomas "
                "(last known well) é a variável central para definir elegibilidade a "
                "trombólise e trombectomia, sendo prioridade absoluta seu registro preciso."
            ),
            "Conduta inicial": (
                "Ativar protocolo de AVC agudo (\"tempo é cérebro\"): glicemia capilar "
                "imediata, tomografia de crânio sem contraste em até 25 minutos da chegada "
                "para excluir hemorragia, avaliação de elegibilidade para trombólise "
                "endovenosa dentro de 4,5h do início dos sintomas e para trombectomia "
                "mecânica em oclusão de grande vaso até 24h em casos selecionados."
            ),
            "Medicações e doses de referência": (
                "Alteplase 0,9 mg/kg EV (máximo 90 mg), 10% em bolus e restante em infusão "
                "ao longo de 60 minutos, respeitados os critérios de inclusão/exclusão. "
                "Controle pressórico rigoroso antes da trombólise (PA < 185/110 mmHg); "
                "não reduzir pressão arterial de forma agressiva fora desse contexto salvo "
                "emergência hipertensiva concomitante."
            ),
            "Critérios de alerta e escalonamento": (
                "Piora neurológica após trombólise sugere transformação hemorrágica e exige "
                "tomografia de crânio imediata e suspensão da infusão. Oclusão de grande "
                "vaso identificada em angiotomografia exige contato imediato com serviço de "
                "neurorradiologia intervencionista para trombectomia. Todo paciente deve "
                "ser admitido em unidade de AVC ou UTI para monitorização nas primeiras 24h."
            ),
        },
    },
    {
        "id": "PROT-005",
        "titulo": "Abordagem da Crise Hipertensiva",
        "versao": "1.1",
        "atualizado_em": "2025-08-14",
        "secoes": {
            "Definição e critérios": (
                "Crise hipertensiva é caracterizada por pressão arterial sistólica ≥ 180 "
                "mmHg e/ou diastólica ≥ 120 mmHg. Classifica-se em urgência hipertensiva "
                "(sem lesão aguda de órgão-alvo) e emergência hipertensiva (com lesão aguda "
                "de órgão-alvo, como encefalopatia, edema agudo de pulmão, síndrome "
                "coronariana aguda, dissecção de aorta ou lesão renal aguda)."
            ),
            "Conduta inicial": (
                "Confirmar a medida pressórica com técnica adequada e repetir após repouso. "
                "Investigar sinais de lesão de órgão-alvo: exame neurológico, ausculta "
                "cardiopulmonar, fundoscopia quando disponível, função renal e "
                "eletrocardiograma. Na urgência hipertensiva, reduzir a pressão de forma "
                "gradual em 24–48h com medicação oral; na emergência, reduzir com agente "
                "endovenoso titulável em ambiente monitorizado."
            ),
            "Medicações e doses de referência": (
                "Urgência: captopril 25 mg VO ou anlodipino 5 mg VO, reavaliando em 1–2h. "
                "Emergência: nitroprussiato de sódio 0,3–10 mcg/kg/min EV em infusão "
                "contínua titulada, com meta de redução de até 25% da PAM na primeira hora, "
                "salvo dissecção de aorta (redução mais rápida e agressiva) e AVC "
                "isquêmico agudo (redução mais cautelosa, ver PROT-004)."
            ),
            "Critérios de alerta e escalonamento": (
                "Sinais de encefalopatia hipertensiva, edema agudo de pulmão, dor torácica "
                "sugestiva de dissecção ou síndrome coronariana, ou lesão renal aguda "
                "configuram emergência hipertensiva e exigem internação em unidade "
                "monitorizada com acesso a infusão titulável e reavaliação médica contínua."
            ),
        },
    },
    {
        "id": "PROT-006",
        "titulo": "Reconhecimento e Manejo da Anafilaxia",
        "versao": "1.0",
        "atualizado_em": "2025-07-20",
        "secoes": {
            "Definição e critérios": (
                "Anafilaxia é reação de hipersensibilidade sistêmica grave, de início "
                "agudo, envolvendo pele/mucosas associada a comprometimento respiratório "
                "e/ou cardiovascular, ou exposição a alérgeno conhecido com queda de "
                "pressão arterial. O diagnóstico é clínico e não deve aguardar "
                "confirmação laboratorial para início do tratamento."
            ),
            "Conduta inicial": (
                "Remover o agente desencadeante quando possível, posicionar o paciente "
                "deitado com membros inferiores elevados (salvo dispneia importante), "
                "administrar adrenalina intramuscular imediatamente — é a primeira linha e "
                "não deve ser postergada. Monitorização contínua de via aérea, respiração e "
                "circulação; oxigênio suplementar e acesso venoso calibroso."
            ),
            "Medicações e doses de referência": (
                "Adrenalina 0,3–0,5 mg IM (1:1000) na face anterolateral da coxa, repetível "
                "a cada 5–15 minutos conforme resposta. Reposição volêmica com cristaloide "
                "1–2 L em bolus se hipotensão. Anti-histamínico (difenidramina 25–50 mg EV) "
                "e corticoide (hidrocortisona 200 mg EV) são medidas adjuvantes, nunca "
                "substitutas da adrenalina."
            ),
            "Critérios de alerta e escalonamento": (
                "Ausência de resposta a duas doses de adrenalina IM, estridor progressivo, "
                "broncoespasmo refratário ou choque persistente exigem manejo avançado de "
                "via aérea, infusão contínua de adrenalina e transferência para UTI. Todo "
                "paciente deve permanecer em observação por no mínimo 6–8h pelo risco de "
                "reação bifásica."
            ),
        },
    },
    {
        "id": "PROT-007",
        "titulo": "Tratamento Empírico da Pneumonia Adquirida na Comunidade",
        "versao": "1.4",
        "atualizado_em": "2025-11-28",
        "secoes": {
            "Definição e critérios": (
                "Pneumonia adquirida na comunidade (PAC) é infecção aguda do parênquima "
                "pulmonar adquirida fora do ambiente hospitalar, confirmada por infiltrado "
                "novo em radiografia de tórax associado a sintomas respiratórios e/ou "
                "sistêmicos. Escores de gravidade (CURB-65 ou PSI) orientam a decisão entre "
                "tratamento ambulatorial, internação em enfermaria ou UTI."
            ),
            "Conduta inicial": (
                "Avaliar critérios de gravidade (CURB-65: confusão, ureia elevada, "
                "frequência respiratória ≥ 30, pressão arterial baixa, idade ≥ 65 anos). "
                "Solicitar radiografia de tórax, oximetria de pulso e, em pacientes "
                "internados, hemocultura e cultura de escarro quando pertinente. Iniciar "
                "antibioticoterapia empírica o mais precocemente possível, idealmente nas "
                "primeiras 4 horas."
            ),
            "Medicações e doses de referência": (
                "Ambulatorial sem comorbidades: amoxicilina 500 mg VO 8/8h por 7 dias. "
                "Internado em enfermaria (conforme CURB-65 ≥ 2): ceftriaxona 1–2 g EV 24/24h "
                "associada a azitromicina 500 mg EV/VO 24/24h por 5 dias para cobertura de "
                "atípicos. PAC grave com necessidade de UTI: ampliar espectro conforme "
                "fatores de risco para Pseudomonas."
            ),
            "Critérios de alerta e escalonamento": (
                "CURB-65 ≥ 3, necessidade de suporte ventilatório, choque séptico ou "
                "falência em responder ao tratamento em 48–72h exigem reavaliação de "
                "imagem, ampliação do espectro antimicrobiano e consideração de UTI. "
                "Derrame pleural volumoso associado deve ser investigado quanto a "
                "empiema."
            ),
        },
    },
    {
        "id": "PROT-008",
        "titulo": "Manejo da Cetoacidose Diabética no Adulto",
        "versao": "1.2",
        "atualizado_em": "2025-10-15",
        "secoes": {
            "Definição e critérios": (
                "Cetoacidose diabética é definida pela tríade hiperglicemia (geralmente > "
                "250 mg/dL), acidose metabólica (pH < 7,3 ou bicarbonato < 18 mEq/L) e "
                "cetonemia/cetonúria significativas. É emergência endocrinológica que exige "
                "reconhecimento e tratamento imediatos, mais comum em diabetes tipo 1 mas "
                "possível no tipo 2 em situações de estresse metabólico grave."
            ),
            "Conduta inicial": (
                "Reposição volêmica agressiva com solução salina isotônica nas primeiras "
                "horas, seguida de insulinoterapia endovenosa contínua somente após "
                "potássio sérico confirmado ≥ 3,3 mEq/L (risco de arritmia grave em "
                "hipopotassemia). Monitorização horária de glicemia capilar e eletrólitos "
                "nas primeiras 6 horas."
            ),
            "Medicações e doses de referência": (
                "Solução salina 0,9% 15–20 mL/kg na primeira hora. Insulina regular EV em "
                "infusão contínua 0,1 UI/kg/h após correção do potássio, com meta de queda "
                "glicêmica de 50–75 mg/dL/h. Reposição de potássio conforme nível sérico: "
                "20–30 mEq/L de solução se potássio entre 3,3–5,3 mEq/L. Adicionar glicose "
                "5% quando glicemia atingir cerca de 200–250 mg/dL para evitar hipoglicemia."
            ),
            "Critérios de alerta e escalonamento": (
                "Potássio sérico < 3,3 mEq/L antes de iniciar insulina, rebaixamento do "
                "nível de consciência, instabilidade hemodinâmica ou pH < 7,0 indicam "
                "necessidade de UTI. Resolução da cetoacidose exige anion gap normalizado e "
                "bicarbonato ≥ 15 mEq/L, não apenas normalização da glicemia."
            ),
        },
    },
    {
        "id": "PROT-009",
        "titulo": "Suspeita e Manejo Inicial de Tromboembolismo Pulmonar",
        "versao": "1.1",
        "atualizado_em": "2025-09-30",
        "secoes": {
            "Definição e critérios": (
                "Tromboembolismo pulmonar (TEP) resulta da obstrução de artérias "
                "pulmonares por êmbolos, geralmente originados de trombose venosa profunda "
                "de membros inferiores. Escores de probabilidade clínica (Wells ou Genebra) "
                "orientam a estratégia diagnóstica: baixa probabilidade autoriza D-dímero "
                "para exclusão; alta probabilidade indica angiotomografia direta."
            ),
            "Conduta inicial": (
                "Avaliar estabilidade hemodinâmica imediatamente — TEP com choque ou "
                "hipotensão é maciço e exige conduta de emergência. Aplicar escore de Wells; "
                "se baixa/moderada probabilidade, solicitar D-dímero (exclui TEP se "
                "negativo); se alta probabilidade ou D-dímero positivo, solicitar "
                "angiotomografia de tórax. Iniciar anticoagulação empírica enquanto aguarda "
                "confirmação, se risco de sangramento for aceitável."
            ),
            "Medicações e doses de referência": (
                "Anticoagulação inicial com heparina de baixo peso molecular (enoxaparina "
                "1 mg/kg SC 12/12h) ou heparina não fracionada EV em casos de instabilidade "
                "ou insuficiência renal grave. TEP maciço com choque: considerar "
                "trombólise sistêmica com alteplase, respeitadas contraindicações."
            ),
            "Critérios de alerta e escalonamento": (
                "Hipotensão persistente, disfunção de ventrículo direito ao ecocardiograma "
                "ou elevação de troponina/BNP classificam o TEP como de alto risco e exigem "
                "internação em UTI com avaliação de terapia de reperfusão (trombólise ou "
                "embolectomia). TEP submaciço com disfunção de VD sem choque exige "
                "monitorização intensiva."
            ),
        },
    },
    {
        "id": "PROT-010",
        "titulo": "Abordagem Inicial da Hemorragia Digestiva Alta",
        "versao": "1.0",
        "atualizado_em": "2025-08-05",
        "secoes": {
            "Definição e critérios": (
                "Hemorragia digestiva alta (HDA) origina-se proximalmente ao ângulo de "
                "Treitz, manifestando-se por hematêmese, melena ou, em sangramentos "
                "maciços, hematoquezia. Causas mais comuns incluem doença ulcerosa "
                "péptica e varizes esofagogástricas em hepatopatas. Escore de Glasgow-"
                "Blatchford auxilia na estratificação de risco e necessidade de internação."
            ),
            "Conduta inicial": (
                "Avaliar estabilidade hemodinâmica e obter dois acessos venosos calibrosos. "
                "Reposição volêmica com cristaloide conforme necessidade, com meta de "
                "hemoglobina restritiva (transfusão se < 7 g/dL na maioria dos pacientes, "
                "< 9 g/dL em cardiopatas). Endoscopia digestiva alta idealmente nas "
                "primeiras 24h para diagnóstico etiológico e terapêutica."
            ),
            "Medicações e doses de referência": (
                "Inibidor de bomba de prótons em infusão: omeprazol 80 mg EV em bolus "
                "seguido de 8 mg/h em infusão contínua (ou dose intermitente equivalente) "
                "antes da endoscopia. Suspeita de varizes: associar terlipressina 2 mg EV "
                "6/6h e antibioticoprofilaxia com ceftriaxona 1 g EV 24/24h em hepatopatas."
            ),
            "Critérios de alerta e escalonamento": (
                "Instabilidade hemodinâmica persistente apesar de reposição volêmica, "
                "queda importante de hemoglobina, hematêmese volumosa recorrente ou "
                "coagulopatia associada exigem UTI e acionamento urgente de endoscopia "
                "terapêutica. Falha do controle endoscópico indica necessidade de "
                "radiologia intervencionista ou cirurgia."
            ),
        },
    },
    {
        "id": "PROT-011",
        "titulo": "Reconhecimento e Manejo do Delirium no Idoso",
        "versao": "1.0",
        "atualizado_em": "2025-12-10",
        "secoes": {
            "Definição e critérios": (
                "Delirium é síndrome de disfunção cerebral aguda caracterizada por início "
                "súbito, curso flutuante, alteração da atenção e do nível de consciência, "
                "frequentemente subdiagnosticada em idosos hospitalizados. O instrumento "
                "CAM (Confusion Assessment Method) é a ferramenta de rastreio recomendada "
                "à beira do leito."
            ),
            "Conduta inicial": (
                "Investigar e tratar causas subjacentes: infecção (especialmente urinária e "
                "respiratória), distúrbios hidroeletrolíticos, retenção urinária, "
                "constipação, dor não controlada, hipoxemia e efeitos de medicações "
                "(especialmente anticolinérgicos e benzodiazepínicos). Priorizar medidas "
                "não farmacológicas: reorientação, iluminação adequada, presença de "
                "familiares, mobilização precoce e correção sensorial (óculos, aparelho "
                "auditivo)."
            ),
            "Medicações e doses de referência": (
                "Evitar sedação farmacológica de rotina. Em agitação grave com risco à "
                "segurança do paciente ou da equipe, considerar haloperidol 0,5–1 mg VO/IM "
                "em dose baixa, evitando benzodiazepínicos (exceto delirium por abstinência "
                "alcoólica, onde são a primeira linha). Reavaliar necessidade de "
                "manutenção a cada dose."
            ),
            "Critérios de alerta e escalonamento": (
                "Delirium hipoativo pode ser confundido com depressão ou sonolência e exige "
                "vigilância ativa. Persistência dos sintomas após correção das causas "
                "identificadas, ou piora do nível de consciência, exige reavaliação "
                "neurológica ampliada e investigação de causas menos comuns (incluindo "
                "neuroimagem)."
            ),
        },
    },
    {
        "id": "PROT-012",
        "titulo": "Investigação Inicial da Dor Abdominal Aguda",
        "versao": "1.1",
        "atualizado_em": "2025-11-02",
        "secoes": {
            "Definição e critérios": (
                "Dor abdominal aguda de início recente (até 7 dias) exige diagnóstico "
                "diferencial amplo, incluindo causas cirúrgicas (apendicite, colecistite, "
                "obstrução intestinal, perfuração de víscera) e clínicas. Sinais de "
                "irritação peritoneal (defesa involuntária, descompressão dolorosa) "
                "indicam maior probabilidade de abdome cirúrgico agudo."
            ),
            "Conduta inicial": (
                "Exame físico completo com palpação sistemática, ausculta de ruídos "
                "hidroaéreos e toque retal quando indicado. Solicitar exames laboratoriais "
                "básicos (hemograma, proteína C-reativa, função renal) e exame de imagem "
                "conforme suspeita clínica (ultrassonografia para via biliar, tomografia "
                "para suspeita de apendicite ou obstrução). Analgesia não deve ser adiada "
                "por receio de mascarar sinais — evidência atual não sustenta essa prática."
            ),
            "Medicações e doses de referência": (
                "Analgesia escalonada conforme intensidade: dipirona 1 g EV até 6/6h para "
                "dor leve a moderada; opioide (tramadol 100 mg EV) para dor intensa, com "
                "reavaliação frequente. Antiemético (ondansetrona 4–8 mg EV) conforme "
                "necessidade. Jejum enquanto houver suspeita de abdome cirúrgico."
            ),
            "Critérios de alerta e escalonamento": (
                "Sinais de peritonite difusa, instabilidade hemodinâmica, distensão "
                "abdominal importante com parada de eliminação de gases e fezes, ou imagem "
                "sugestiva de perfuração/isquemia exigem acionamento imediato da cirurgia "
                "geral. Dor desproporcional ao exame físico em paciente com fatores de "
                "risco vascular sugere isquemia mesentérica e exige investigação urgente."
            ),
        },
    },
    {
        "id": "PROT-013",
        "titulo": "Manejo da Fibrilação Atrial Aguda",
        "versao": "1.0",
        "atualizado_em": "2025-10-22",
        "secoes": {
            "Definição e critérios": (
                "Fibrilação atrial (FA) aguda é a arritmia supraventricular sustentada de "
                "início recente (documentado ou presumido em até 48h) ou primeiro "
                "episódio identificado, caracterizada por ritmo irregularmente irregular "
                "sem onda P definida ao eletrocardiograma. A conduta é orientada pela "
                "estabilidade hemodinâmica, pelo tempo de início e pelo risco "
                "tromboembólico estimado pelo escore CHA2DS2-VASc."
            ),
            "Conduta inicial": (
                "Avaliar estabilidade imediatamente: FA com hipotensão, angina, congestão "
                "pulmonar ou rebaixamento de consciência indica cardioversão elétrica "
                "sincronizada de emergência. No paciente estável, definir a estratégia "
                "entre controle de frequência e controle de ritmo, investigar e tratar "
                "fatores desencadeantes (sepse, tireotoxicose, distúrbio eletrolítico, "
                "tromboembolismo pulmonar, síndrome coronariana) e estimar o tempo de "
                "início para orientar a segurança da cardioversão. Solicitar "
                "eletrocardiograma, eletrólitos, função tireoidiana e função renal."
            ),
            "Medicações e doses de referência": (
                "Controle de frequência no paciente estável sem disfunção ventricular "
                "importante: betabloqueador (metoprolol 2,5–5 mg EV lento, repetível) ou "
                "diltiazem 0,25 mg/kg EV, seguidos de dose oral de manutenção, com meta "
                "de frequência cardíaca em repouso abaixo de 110 bpm. Em disfunção "
                "sistólica significativa, preferir amiodarona 150 mg EV em 10 minutos "
                "seguida de infusão. Cardioversão química eletiva pode ser feita com "
                "amiodarona ou propafenona em casos selecionados. Anticoagulação plena "
                "conforme CHA2DS2-VASc e conforme tempo de início: FA com 48h ou mais, ou "
                "de início indeterminado, exige anticoagulação por 3 semanas antes de "
                "cardioversão eletiva ou ecocardiograma transesofágico prévio para "
                "excluir trombo."
            ),
            "Critérios de alerta e escalonamento": (
                "Instabilidade hemodinâmica, resposta ventricular não controlada apesar "
                "de medicação endovenosa, suspeita de via acessória (QRS largo e muito "
                "rápido, contraindicando bloqueadores do nó atrioventricular) ou FA "
                "associada a síndrome coronariana aguda exigem acionamento imediato da "
                "cardiologia e monitorização em unidade com suporte para cardioversão. "
                "Todo paciente com indicação de anticoagulação deve ter o risco de "
                "sangramento avaliado e documentado antes do início."
            ),
        },
    },
    {
        "id": "PROT-014",
        "titulo": "Manejo do Estado de Mal Epiléptico no Adulto",
        "versao": "1.1",
        "atualizado_em": "2025-11-18",
        "secoes": {
            "Definição e critérios": (
                "Estado de mal epiléptico é definido operacionalmente como crise "
                "convulsiva contínua por 5 minutos ou mais, ou duas ou mais crises sem "
                "recuperação completa da consciência entre elas. É emergência "
                "neurológica: o risco de lesão neuronal e de refratariedade aumenta "
                "progressivamente com a duração, tornando o controle rápido a prioridade "
                "absoluta."
            ),
            "Conduta inicial": (
                "Garantir via aérea, oxigenação e acesso venoso, e cronometrar a crise. "
                "Glicemia capilar imediata e correção se hipoglicemia. Coletar "
                "eletrólitos, cálcio, magnésio, função renal e hepática, nível sérico de "
                "anticonvulsivantes em uso e triagem toxicológica quando pertinente. "
                "Administrar benzodiazepínico como primeira linha sem aguardar exames. Se "
                "a crise persistir após a dose inicial de benzodiazepínico, iniciar "
                "imediatamente droga antiepiléptica de segunda linha em dose de ataque. "
                "Tomografia de crânio e punção lombar conforme suspeita etiológica, após "
                "estabilização."
            ),
            "Medicações e doses de referência": (
                "Primeira linha: diazepam 10 mg EV (ou midazolam 10 mg IM se não houver "
                "acesso venoso), repetível uma vez após 5 minutos. Segunda linha (dose de "
                "ataque, escolher uma): fenitoína 20 mg/kg EV em infusão lenta com "
                "monitorização cardíaca, ácido valproico 40 mg/kg EV, ou levetiracetam 60 "
                "mg/kg EV. Estado de mal refratário (persistência após primeira e segunda "
                "linhas): indução de coma com midazolam ou propofol em infusão contínua "
                "sob ventilação mecânica e monitorização eletroencefalográfica contínua."
            ),
            "Critérios de alerta e escalonamento": (
                "Persistência da crise após benzodiazepínico e droga de segunda linha "
                "caracteriza estado de mal refratário e exige intubação orotraqueal, "
                "infusão contínua de anestésico e transferência para UTI com "
                "eletroencefalograma contínuo. Crises focais que não geram rebaixamento, "
                "febre com rigidez de nuca, déficit focal novo ou primeira crise na vida "
                "adulta exigem investigação etiológica ampliada com neuroimagem e "
                "avaliação da neurologia."
            ),
        },
    },
    {
        "id": "PROT-015",
        "titulo": "Abordagem Inicial da Lesão Renal Aguda",
        "versao": "1.0",
        "atualizado_em": "2025-09-12",
        "secoes": {
            "Definição e critérios": (
                "Lesão renal aguda (LRA) é definida pelos critérios KDIGO: aumento da "
                "creatinina sérica ≥ 0,3 mg/dL em 48h, aumento ≥ 1,5 vez o valor de base "
                "em 7 dias, ou débito urinário < 0,5 mL/kg/h por 6h ou mais. A "
                "classificação em estágios 1 a 3 orienta a intensidade da investigação e "
                "do monitoramento. A abordagem diagnóstica separa causas pré-renais, "
                "renais intrínsecas e pós-renais (obstrutivas)."
            ),
            "Conduta inicial": (
                "Revisar a volemia e a perfusão: avaliar sinais de hipovolemia ou de "
                "congestão, aferir pressão e diurese, e otimizar o estado volêmico com "
                "cristaloide se houver hipoperfusão. Suspender nefrotoxinas "
                "(anti-inflamatórios não esteroidais, aminoglicosídeos, contraste iodado "
                "eletivo, inibidores da enzima conversora em contexto de instabilidade). "
                "Solicitar ultrassonografia de rins e vias urinárias para excluir "
                "obstrução, além de urina tipo 1, sódio urinário e relação "
                "proteína/creatinina. Ajustar doses de todos os fármacos à função renal "
                "estimada."
            ),
            "Medicações e doses de referência": (
                "Não há fármaco que reverta a LRA estabelecida; o tratamento é de "
                "suporte. Reposição volêmica com cristaloide balanceado titulada à "
                "resposta em LRA pré-renal. Diuréticos (furosemida) apenas para controle "
                "de hipervolemia sintomática, nunca para \"proteção renal\" ou para "
                "converter oligúria em não oligúria. Corrigir hipercalemia e acidose "
                "conforme protocolos específicos. Ajuste posológico rigoroso de "
                "antimicrobianos e anticoagulantes à taxa de filtração glomerular "
                "estimada."
            ),
            "Critérios de alerta e escalonamento": (
                "Indicações de terapia de substituição renal de urgência: hipercalemia "
                "refratária, acidose metabólica grave refratária, hipervolemia com edema "
                "agudo de pulmão sem resposta a diurético, uremia sintomática "
                "(encefalopatia, pericardite) e algumas intoxicações dialisáveis. Anúria, "
                "LRA estágio 3, ausência de causa pré-renal ou pós-renal identificável, "
                "ou suspeita de glomerulonefrite rapidamente progressiva exigem "
                "acionamento da nefrologia."
            ),
        },
    },
    {
        "id": "PROT-016",
        "titulo": "Manejo Agudo da Hipercalemia",
        "versao": "1.1",
        "atualizado_em": "2025-10-08",
        "secoes": {
            "Definição e critérios": (
                "Hipercalemia é definida por potássio sérico > 5,5 mEq/L, classificada em "
                "leve (5,5–5,9), moderada (6,0–6,4) e grave (≥ 6,5 mEq/L ou qualquer "
                "nível com alterações eletrocardiográficas ou sintomas). É emergência "
                "quando há alterações no eletrocardiograma (ondas T apiculadas, "
                "alargamento do QRS, achatamento da onda P, padrão sinusoidal) ou "
                "fraqueza muscular ascendente, pelo risco de arritmia ventricular e "
                "assistolia."
            ),
            "Conduta inicial": (
                "Obter eletrocardiograma imediato em toda hipercalemia moderada ou grave "
                "e repetir amostra para excluir pseudo-hipercalemia (hemólise da coleta) "
                "quando o quadro clínico não for compatível. Monitorização cardíaca "
                "contínua. Suspender fontes de potássio (suplementos, soluções, "
                "poupadores de potássio, inibidores da enzima conversora, bloqueadores do "
                "receptor de angiotensina, anti-inflamatórios). Identificar e tratar a "
                "causa (lesão renal aguda, rabdomiólise, acidose, medicações)."
            ),
            "Medicações e doses de referência": (
                "Com alteração eletrocardiográfica: gluconato de cálcio 10% 10–20 mL EV "
                "em 2–3 minutos para estabilização de membrana (início em minutos, sem "
                "efeito sobre o potássio sérico), repetível se não houver melhora do "
                "traçado. Deslocamento intracelular: insulina regular 10 UI EV com "
                "glicose 25 g EV (50 mL de glicose 50%), e beta-2-agonista inalatório "
                "(salbutamol 10–20 mg nebulizado). Remoção do potássio corporal: "
                "diurético de alça se o paciente responder, resina de troca "
                "(poliestirenossulfonato) para efeito mais tardio, e hemodiálise nos "
                "casos refratários ou com lesão renal grave."
            ),
            "Critérios de alerta e escalonamento": (
                "Potássio ≥ 6,5 mEq/L, alterações eletrocardiográficas, arritmia, "
                "fraqueza muscular importante ou hipercalemia refratária às medidas "
                "iniciais exigem monitorização em unidade de terapia intensiva e "
                "acionamento da nefrologia para hemodiálise. Anúria ou lesão renal aguda "
                "oligúrica associada torna as medidas de deslocamento apenas "
                "temporizadoras até a diálise."
            ),
        },
    },
    {
        "id": "PROT-017",
        "titulo": "Abordagem Inicial da Hiponatremia",
        "versao": "1.0",
        "atualizado_em": "2025-08-28",
        "secoes": {
            "Definição e critérios": (
                "Hiponatremia é definida por sódio sérico < 135 mEq/L, classificada em "
                "leve (130–134), moderada (125–129) e grave (< 125 mEq/L). A gravidade "
                "clínica depende mais da velocidade de instalação do que do valor "
                "absoluto: hiponatremia aguda (< 48h) cursa com edema cerebral e sintomas "
                "neurológicos (cefaleia, vômitos, confusão, convulsão, coma), enquanto a "
                "crônica costuma ser oligossintomática. A avaliação inicial classifica o "
                "estado volêmico em hipovolêmico, euvolêmico ou hipervolêmico e mede a "
                "osmolaridade sérica e urinária e o sódio urinário."
            ),
            "Conduta inicial": (
                "Definir se há sintomas neurológicos graves, que indicam correção "
                "imediata independentemente da causa. Coletar osmolaridade sérica "
                "(excluir pseudo-hiponatremia e hiponatremia hipertônica por "
                "hiperglicemia), osmolaridade e sódio urinários, e avaliar clinicamente a "
                "volemia. Rever medicações associadas (diuréticos tiazídicos, "
                "antidepressivos, carbamazepina). No paciente assintomático ou com "
                "sintomas leves, a correção é lenta e direcionada à causa; a restrição "
                "hídrica é a base no quadro euvolêmico por secreção inapropriada de "
                "hormônio antidiurético."
            ),
            "Medicações e doses de referência": (
                "Hiponatremia sintomática grave: salina hipertônica a 3% 100–150 mL EV em "
                "bolus em 10 minutos, repetível 1–2 vezes conforme resposta clínica, com "
                "meta de elevação do sódio de 4–6 mEq/L nas primeiras horas para reverter "
                "o edema cerebral. Limite de segurança: não ultrapassar 8 mEq/L de "
                "elevação em 24h (10–12 mEq/L como teto absoluto) pelo risco de síndrome "
                "de desmielinização osmótica. Hipovolemia: reposição com salina isotônica "
                "0,9%. Hipervolemia (insuficiência cardíaca, cirrose): restrição hídrica "
                "e de sódio, diurético de alça. Controle do sódio sérico a cada 2–4h "
                "durante a correção ativa."
            ),
            "Critérios de alerta e escalonamento": (
                "Convulsão, rebaixamento do nível de consciência, sódio < 120 mEq/L ou "
                "hiponatremia aguda sintomática exigem UTI, salina hipertônica e controle "
                "laboratorial seriado. Correção mais rápida que o limite de segurança "
                "exige medidas para reduzir a velocidade (água livre, desmopressina) e "
                "acionamento da nefrologia ou endocrinologia. Suspeita de insuficiência "
                "adrenal ou hipotireoidismo grave como causa deve ser investigada."
            ),
        },
    },
    {
        "id": "PROT-018",
        "titulo": "Manejo da Intoxicação Aguda por Paracetamol",
        "versao": "1.0",
        "atualizado_em": "2025-07-30",
        "secoes": {
            "Definição e critérios": (
                "Intoxicação por paracetamol (acetaminofeno) é uma das principais causas "
                "de insuficiência hepática aguda induzida por fármaco. A dose tóxica "
                "aguda em adultos é geralmente ≥ 7,5–10 g ou ≥ 150 mg/kg em ingestão "
                "única. A evolução clínica tem quatro fases: inespecífica nas primeiras "
                "24h, hepatotoxicidade entre 24–72h (elevação de transaminases), pico de "
                "disfunção hepática em 72–96h e recuperação ou falência. A concentração "
                "sérica de paracetamol medida 4h ou mais após a ingestão, plotada no "
                "nomograma de Rumack-Matthew, define o risco quando o horário da ingestão "
                "é conhecido."
            ),
            "Conduta inicial": (
                "Estabelecer o horário e a dose ingerida e se a ingestão foi única ou "
                "escalonada. Carvão ativado 1 g/kg VO se a apresentação ocorrer em até "
                "1–2h da ingestão e a via aérea estiver protegida. Coletar "
                "paracetamolemia (a partir de 4h da ingestão), transaminases, tempo de "
                "protrombina/RNI, função renal, gasometria e glicemia. Iniciar "
                "N-acetilcisteína se: nível acima da linha de tratamento do nomograma; "
                "ingestão ≥ 150 mg/kg com nível indisponível; apresentação tardia (> 8h) "
                "com dose tóxica; ou evidência de lesão hepática. Não atrasar a "
                "N-acetilcisteína aguardando o nível quando a apresentação for após 8h da "
                "ingestão."
            ),
            "Medicações e doses de referência": (
                "N-acetilcisteína endovenosa em regime de 21h: 150 mg/kg em 1h, seguidos "
                "de 50 mg/kg em 4h e 100 mg/kg em 16h; manter além das 21h se ainda "
                "houver transaminases em elevação, RNI alargado ou paracetamol "
                "detectável. Alternativa oral: 140 mg/kg de ataque seguidos de 70 mg/kg "
                "4/4h por 17 doses. Suporte: correção de hipoglicemia, vitamina K e "
                "hemoderivados conforme coagulopatia e sangramento."
            ),
            "Critérios de alerta e escalonamento": (
                "Critérios de encaminhamento para centro de transplante hepático (King's "
                "College): pH < 7,3 após ressuscitação, ou a combinação de RNI > 6,5, "
                "creatinina > 3,4 mg/dL e encefalopatia grau III–IV. Acidose persistente, "
                "hipoglicemia refratária, RNI em ascensão após 48h, lactato elevado ou "
                "encefalopatia exigem UTI e contato imediato com a hepatologia e o "
                "serviço de transplante. Contato com o centro de informação toxicológica "
                "é recomendado em todos os casos."
            ),
        },
    },
    {
        "id": "PROT-019",
        "titulo": "Manejo da Exacerbação Aguda da DPOC",
        "versao": "1.2",
        "atualizado_em": "2025-11-05",
        "secoes": {
            "Definição e critérios": (
                "Exacerbação aguda da doença pulmonar obstrutiva crônica (DPOC) é a piora "
                "sustentada dos sintomas respiratórios além da variação diária habitual, "
                "com aumento da dispneia, do volume ou da purulência do escarro, exigindo "
                "mudança de tratamento. A gravidade é estratificada pela intensidade da "
                "dispneia, uso de musculatura acessória, nível de consciência, saturação "
                "e gasometria arterial. Os desencadeantes mais comuns são infecções "
                "virais e bacterianas do trato respiratório e poluição; o tromboembolismo "
                "pulmonar e a insuficiência cardíaca são diagnósticos diferenciais a "
                "excluir."
            ),
            "Conduta inicial": (
                "Oxigenoterapia titulada com meta de saturação de 88–92% (evitar "
                "hiperóxia pelo risco de hipercapnia). Broncodilatadores de curta ação "
                "inalatórios de forma frequente. Gasometria arterial nos casos moderados "
                "a graves para avaliar acidose respiratória e hipercapnia. Radiografia de "
                "tórax para excluir pneumonia e pneumotórax. Iniciar ventilação não "
                "invasiva precocemente na presença de acidose respiratória (pH < 7,35 com "
                "pCO2 elevada) ou trabalho respiratório importante. Corticoide sistêmico "
                "e antibiótico conforme critérios."
            ),
            "Medicações e doses de referência": (
                "Broncodilatador: salbutamol 2,5–5 mg associado a ipratrópio 0,5 mg "
                "nebulizados a cada 20 minutos na primeira hora, depois espaçar. "
                "Corticoide: prednisona 40 mg VO por 5 dias (ou "
                "hidrocortisona/metilprednisolona EV se via oral inviável). Antibiótico "
                "quando há aumento da purulência do escarro associado a aumento do volume "
                "ou da dispneia, ou necessidade de ventilação: amoxicilina-clavulanato "
                "875/125 mg VO 12/12h ou macrolídeo por 5–7 dias, ajustando conforme "
                "fatores de risco para Pseudomonas."
            ),
            "Critérios de alerta e escalonamento": (
                "Acidose respiratória progressiva apesar de ventilação não invasiva, "
                "rebaixamento do nível de consciência, instabilidade hemodinâmica, "
                "hipoxemia refratária ou intolerância à máscara indicam intubação "
                "orotraqueal e UTI. Falha da ventilação não invasiva na primeira a "
                "segunda hora (sem melhora do pH e da pCO2) é preditor de necessidade de "
                "via aérea avançada e exige reavaliação imediata."
            ),
        },
    },
    {
        "id": "PROT-020",
        "titulo": "Manejo da Crise Asmática no Adulto",
        "versao": "1.1",
        "atualizado_em": "2025-09-25",
        "secoes": {
            "Definição e critérios": (
                "Crise asmática (exacerbação) é o agravamento progressivo de dispneia, "
                "tosse, sibilância e aperto torácico, com redução do pico de fluxo "
                "expiratório. A gravidade é classificada em leve a moderada (fala em "
                "frases, frequência respiratória aumentada, saturação ≥ 92%, pico de "
                "fluxo > 50% do previsto), grave (fala em palavras, uso de musculatura "
                "acessória, frequência respiratória ≥ 30, frequência cardíaca ≥ 120, "
                "saturação < 92%, pico de fluxo ≤ 50%) e muito grave / risco de vida "
                "(sonolência, confusão, tórax silencioso, bradicardia, esforço "
                "respiratório débil)."
            ),
            "Conduta inicial": (
                "Oxigênio suplementar para meta de saturação de 93–95%. Beta-2-agonista "
                "de curta ação por nebulização ou espaçador de forma repetida na primeira "
                "hora, associado a anticolinérgico de curta ação nas crises graves. "
                "Corticoide sistêmico precoce (na primeira hora) em toda crise moderada a "
                "grave ou em quem já usava corticoide. Reavaliar resposta clínica e pico "
                "de fluxo após cada ciclo. Radiografia de tórax apenas se suspeita de "
                "complicação (pneumotórax, pneumonia). Gasometria arterial na crise grave "
                "que não melhora: pCO2 normal ou elevada em paciente taquipneico é sinal "
                "de fadiga e alarme."
            ),
            "Medicações e doses de referência": (
                "Salbutamol 2,5–5 mg nebulizado (ou 4–10 jatos com espaçador) a cada 20 "
                "minutos por 3 doses, depois conforme resposta. Ipratrópio 0,5 mg "
                "nebulizado associado nas crises graves. Corticoide: prednisona 40–50 mg "
                "VO por 5–7 dias, ou hidrocortisona 200 mg EV se via oral inviável. "
                "Sulfato de magnésio 2 g EV em 20 minutos na crise grave sem resposta ao "
                "tratamento inicial. Considerar beta-2-agonista endovenoso e terapia "
                "intensiva nos casos refratários."
            ),
            "Critérios de alerta e escalonamento": (
                "Rebaixamento do nível de consciência, tórax silencioso, bradicardia, "
                "hipoxemia refratária, pCO2 em elevação ou exaustão respiratória indicam "
                "risco de parada e necessidade de intubação por profissional experiente e "
                "UTI. Ausência de melhora do pico de fluxo após 1h de tratamento "
                "otimizado, ou necessidade de beta-2-agonista contínuo, exige internação "
                "e monitorização intensiva."
            ),
        },
    },
    {
        "id": "PROT-021",
        "titulo": "Manejo Inicial da Suspeita de Meningite Bacteriana Aguda",
        "versao": "1.1",
        "atualizado_em": "2025-10-30",
        "secoes": {
            "Definição e critérios": (
                "Meningite bacteriana aguda é infecção supurativa das meninges, com alta "
                "letalidade e risco de sequelas, exigindo tratamento em caráter de "
                "emergência. A tríade clássica (febre, rigidez de nuca e alteração do "
                "estado mental) está completa em menos da metade dos casos; a maioria "
                "apresenta ao menos dois de quatro achados (febre, cefaleia, rigidez de "
                "nuca, alteração do estado mental). Sinais de gravidade incluem "
                "rebaixamento do nível de consciência, crise convulsiva, déficit focal e "
                "petéquias/púrpura (sugestivas de doença meningocócica)."
            ),
            "Conduta inicial": (
                "A prioridade é não atrasar o antibiótico. Coletar hemoculturas e iniciar "
                "antibioticoterapia empírica associada a dexametasona imediatamente. "
                "Realizar punção lombar assim que possível; se houver indicação de "
                "tomografia de crânio antes da punção (imunossupressão, história de "
                "doença do sistema nervoso central, crise convulsiva recente, papiledema, "
                "déficit focal, rebaixamento importante), colher hemocultura e "
                "administrar antibiótico e corticoide antes do exame de imagem, sem "
                "aguardar. Enviar líquor para celularidade, bioquímica, Gram, cultura e, "
                "quando disponível, painel molecular."
            ),
            "Medicações e doses de referência": (
                "Empírico no adulto imunocompetente: ceftriaxona 2 g EV 12/12h associada "
                "a vancomicina 15–20 mg/kg EV 8/8–12/12h. Adicionar ampicilina 2 g EV "
                "4/4h se idade > 50 anos, gestante, etilismo ou imunossupressão "
                "(cobertura de Listeria). Dexametasona 10 mg EV 6/6h por 4 dias, iniciada "
                "15–20 minutos antes ou junto com a primeira dose do antibiótico; "
                "suspender se a cultura não confirmar pneumococo. Aciclovir empírico se a "
                "encefalite herpética for diferencial relevante."
            ),
            "Critérios de alerta e escalonamento": (
                "Rebaixamento do nível de consciência, instabilidade hemodinâmica, crise "
                "convulsiva, sinais de hipertensão intracraniana ou rash purpúrico "
                "rapidamente progressivo exigem UTI e suporte avançado. Notificação "
                "compulsória e quimioprofilaxia de contactantes próximos na doença "
                "meningocócica e por Haemophilus. Reavaliação da necessidade de "
                "neuroimagem e de avaliação neurocirúrgica se houver piora ou suspeita de "
                "complicação (empiema, abscesso, hidrocefalia)."
            ),
        },
    },
    {
        "id": "PROT-022",
        "titulo": "Manejo da Pielonefrite Aguda no Adulto",
        "versao": "1.0",
        "atualizado_em": "2025-08-19",
        "secoes": {
            "Definição e critérios": (
                "Pielonefrite aguda é a infecção do trato urinário superior (parênquima e "
                "pelve renais), caracterizada por febre, dor lombar ou no flanco e sinal "
                "de Giordano positivo, com ou sem sintomas urinários baixos. Distingue-se "
                "da cistite pela presença de sinais sistêmicos. Considera-se complicada "
                "quando há gestação, obstrução, cálculo, cateter, imunossupressão, "
                "diabetes descompensado, anomalia do trato urinário ou sinais de sepse. "
                "Escores de gravidade e a avaliação de disfunção orgânica orientam a "
                "necessidade de internação."
            ),
            "Conduta inicial": (
                "Coletar urina tipo 1 e urocultura com antibiograma antes do antibiótico, "
                "além de hemograma, função renal e, nos casos com sinais sistêmicos, "
                "hemoculturas e lactato. Iniciar antibioticoterapia empírica precoce "
                "ajustada ao perfil de resistência local. Solicitar imagem "
                "(ultrassonografia ou tomografia) quando houver pielonefrite complicada, "
                "suspeita de obstrução ou de abscesso, ou ausência de melhora clínica em "
                "48–72h. Hidratação e analgesia/antitérmico conforme necessidade."
            ),
            "Medicações e doses de referência": (
                "Tratamento ambulatorial (quadro não complicado, sem vômitos, "
                "hemodinamicamente estável): ciprofloxacino 500 mg VO 12/12h por 7 dias "
                "ou ceftriaxona 1 g EV/IM em dose inicial seguida de esquema oral guiado "
                "pela cultura. Tratamento hospitalar: ceftriaxona 1–2 g EV 24/24h, ou "
                "piperacilina-tazobactam 4,5 g EV 6/6h se fatores de risco para germe "
                "resistente; ajustar conforme urocultura. Duração total de 7–14 dias "
                "conforme agente, resposta e presença de complicação. Evitar "
                "nitrofurantoína e fosfomicina, que não atingem concentração tecidual "
                "adequada no parênquima renal."
            ),
            "Critérios de alerta e escalonamento": (
                "Sinais de sepse ou choque séptico, obstrução do trato urinário com "
                "infecção (pionefrose — emergência urológica que exige drenagem "
                "imediata), abscesso renal ou perinéfrico, gestação, e falha do "
                "tratamento em 48–72h exigem internação, imagem e acionamento da "
                "urologia. Pielonefrite enfisematosa em diabéticos é grave e pode exigir "
                "intervenção cirúrgica."
            ),
        },
    },
    {
        "id": "PROT-023",
        "titulo": "Manejo da Síndrome de Abstinência Alcoólica",
        "versao": "1.0",
        "atualizado_em": "2025-11-22",
        "secoes": {
            "Definição e critérios": (
                "A síndrome de abstinência alcoólica ocorre em pacientes com uso crônico "
                "e pesado de álcool após redução ou interrupção do consumo. O espectro "
                "vai de sintomas leves (tremor, ansiedade, insonia, taquicardia, "
                "hipertensão) iniciados em 6–12h, passando por alucinose alcoólica "
                "(12–24h) e crises convulsivas tônico-clônicas (12–48h), até o delirium "
                "tremens (48–96h): confusão profunda, agitação, alucinações, "
                "hiperatividade autonômica intensa e risco de morte. A escala CIWA-Ar "
                "quantifica a gravidade e orienta a terapia guiada por sintomas."
            ),
            "Conduta inicial": (
                "Estratificar o risco com CIWA-Ar e identificar fatores de risco para "
                "abstinência grave (episódio prévio de delirium tremens ou convulsão, uso "
                "muito intenso, comorbidades agudas). Corrigir hipovolemia e distúrbios "
                "eletrolíticos, com atenção a magnésio, potássio e fósforo. Administrar "
                "tiamina antes de qualquer solução glicosada para prevenir encefalopatia "
                "de Wernicke. Ambiente calmo, monitorização de sinais vitais e "
                "reavaliação frequente com a escala. Investigar condições associadas "
                "(infecção, trauma craniano, pancreatite, hepatopatia descompensada, "
                "hematoma subdural)."
            ),
            "Medicações e doses de referência": (
                "Benzodiazepínico é a base do tratamento, preferencialmente guiado por "
                "sintomas: diazepam 10–20 mg VO/EV repetidos conforme CIWA-Ar, ou "
                "lorazepam (preferível em hepatopatia grave ou idoso) 2–4 mg. Tiamina 300 "
                "mg EV/IM ao menos nos primeiros dias, antes de glicose. Reposição de "
                "magnésio se hipomagnesemia. Em delirium tremens refratário a doses altas "
                "de benzodiazepínico, considerar fenobarbital ou infusão contínua sob "
                "monitorização em UTI. Antipsicótico apenas como adjuvante para "
                "alucinação/agitação, nunca em substituição ao benzodiazepínico (reduz "
                "limiar convulsivo)."
            ),
            "Critérios de alerta e escalonamento": (
                "Delirium tremens, convulsões repetidas, necessidade de doses muito altas "
                "ou frequentes de benzodiazepínico, hipertermia, instabilidade autonômica "
                "grave ou comorbidade aguda descompensada exigem UTI. Convulsão focal, "
                "estado de mal, déficit neurológico ou trauma craniano associado exigem "
                "neuroimagem e avaliação neurológica. Encaminhamento para acompanhamento "
                "do transtorno por uso de álcool após a fase aguda."
            ),
        },
    },
    {
        "id": "PROT-024",
        "titulo": "Analgesia Multimodal na Dor Aguda Intra-hospitalar",
        "versao": "1.0",
        "atualizado_em": "2025-12-05",
        "secoes": {
            "Definição e critérios": (
                "Dor aguda intra-hospitalar deve ser avaliada de forma sistemática e "
                "reavaliada após cada intervenção, usando escala validada (numérica de 0 "
                "a 10 ou de faces). A analgesia multimodal combina fármacos com "
                "mecanismos de ação diferentes para maximizar o efeito e reduzir a dose e "
                "os efeitos adversos de cada classe, sobretudo dos opioides. A escada "
                "analgésica orienta a escolha inicial pela intensidade: dor leve (1–3), "
                "moderada (4–6) e intensa (7–10)."
            ),
            "Conduta inicial": (
                "Identificar o mecanismo predominante (nociceptiva somática/visceral, "
                "neuropática) e a causa, tratando-a sempre que possível. Iniciar "
                "analgésico não opioide de base (paracetamol e/ou anti-inflamatório não "
                "esteroidal, se não houver contraindicação) e adicionar opioide conforme "
                "a intensidade. Prescrever de forma fixa (horário regular) e não apenas "
                "\"se necessário\" na dor moderada a intensa, com resgates definidos. "
                "Antecipar e prescrever profilaxia de efeitos adversos (antiemético, "
                "laxante com opioide). Reavaliar em 30–60 minutos após dose endovenosa."
            ),
            "Medicações e doses de referência": (
                "Base: paracetamol 1 g VO/EV 6/6h (máximo 3–4 g/dia, reduzir em "
                "hepatopatia); dipirona 1 g EV 6/6h; ou anti-inflamatório não esteroidal "
                "(cetoprofeno 100 mg EV 12/12h) por período curto, evitando em lesão "
                "renal, hipovolemia, sangramento digestivo e insuficiência cardíaca "
                "descompensada. Opioide para dor moderada a intensa: morfina 2–4 mg EV "
                "com titulação a cada 10–15 minutos até analgesia, depois dose de "
                "manutenção; tramadol 50–100 mg EV 6/6h como opção de potência "
                "intermediária. Adjuvantes na dor neuropática: gabapentina ou "
                "amitriptilina. Considerar bloqueios regionais quando aplicável."
            ),
            "Critérios de alerta e escalonamento": (
                "Dor intensa refratária às medidas iniciais, necessidade crescente de "
                "opioide, sinais de toxicidade opioide (sonolência, frequência "
                "respiratória < 8–10 irpm, miose puntiforme — reverter com naloxona) ou "
                "suspeita de complicação subjacente (isquemia, síndrome compartimental, "
                "abdome agudo) exigem reavaliação médica imediata e, conforme o caso, "
                "acionamento do serviço de dor ou da equipe cirúrgica. Dor "
                "desproporcional ao exame é sinal de alarme."
            ),
        },
    },
    {
        "id": "PROT-025",
        "titulo": "Abordagem Inicial da Trombose Venosa Profunda de Membros Inferiores",
        "versao": "1.0",
        "atualizado_em": "2025-09-08",
        "secoes": {
            "Definição e critérios": (
                "Trombose venosa profunda (TVP) de membros inferiores é a formação de "
                "trombo no sistema venoso profundo, com risco de embolia pulmonar e de "
                "síndrome pós-trombótica. Manifesta-se por edema assimétrico, dor, "
                "empastamento de panturrilha, aumento de temperatura e circulação "
                "colateral. O escore de Wells para TVP estratifica a probabilidade "
                "pré-teste em baixa, intermediária ou alta e define a estratégia "
                "diagnóstica com D-dímero e ultrassonografia com compressão."
            ),
            "Conduta inicial": (
                "Aplicar o escore de Wells. Probabilidade baixa: D-dímero — se negativo, "
                "exclui TVP e dispensa imagem; se positivo, ultrassonografia com "
                "compressão. Probabilidade intermediária ou alta: ultrassonografia com "
                "compressão diretamente; se negativa com alta suspeita, repetir em 5–7 "
                "dias ou complementar a investigação. Avaliar fatores provocadores "
                "(cirurgia, imobilização, câncer, uso de estrogênio, gestação, "
                "trombofilia) para definir a duração da anticoagulação. Iniciar "
                "anticoagulação empírica enquanto se aguarda o exame quando a suspeita "
                "for alta e o risco de sangramento aceitável."
            ),
            "Medicações e doses de referência": (
                "Anticoagulação plena: anticoagulante oral direto (rivaroxabana 15 mg VO "
                "12/12h por 21 dias, depois 20 mg/dia; ou apixabana 10 mg VO 12/12h por 7 "
                "dias, depois 5 mg 12/12h) como primeira escolha na maioria dos casos. "
                "Alternativa: enoxaparina 1 mg/kg SC 12/12h com transição para varfarina "
                "(alvo de RNI 2–3) ou para anticoagulante oral direto. Preferir heparina "
                "de baixo peso molecular na gestação e em câncer ativo (ou anticoagulante "
                "oral direto em casos selecionados). Duração mínima de 3 meses; TVP não "
                "provocada ou fator de risco persistente pode exigir anticoagulação "
                "estendida. Meias de compressão para sintomas; deambulação precoce "
                "conforme tolerância."
            ),
            "Critérios de alerta e escalonamento": (
                "Sinais de embolia pulmonar (dispneia, dor torácica, taquicardia, "
                "hipoxemia, instabilidade) exigem investigação e conduta conforme "
                "protocolo de tromboembolismo pulmonar. TVP iliofemoral extensa com edema "
                "volumoso e dor importante, ou phlegmasia cerulea dolens (cianose e "
                "comprometimento arterial), são emergências e exigem contato imediato com "
                "a cirurgia vascular para considerar trombólise dirigida por cateter ou "
                "trombectomia. Contraindicação à anticoagulação com TVP proximal "
                "confirmada indica avaliação de filtro de veia cava."
            ),
        },
    },
]

TEMPLATES = {
    "laudo.md": (
        "# Laudo — {{titulo_exame}}\n\n"
        "**Paciente:** {{paciente_id}}\n"
        "**Data:** {{data}}\n\n"
        "## Descrição\n{{descricao}}\n\n"
        "## Conclusão\n{{conclusao}}\n\n"
        "*Modelo sintético para fins acadêmicos — não constitui laudo real.*\n"
    ),
    "receita.md": (
        "# Receita Médica (modelo)\n\n"
        "**Paciente:** {{paciente_id}}\n"
        "**Data:** {{data}}\n\n"
        "{{itens}}\n\n"
        "**Médico responsável:** {{medico}} — {{crm}}\n\n"
        "*Modelo sintético para fins acadêmicos — não constitui receita real.*\n"
    ),
    "procedimento.md": (
        "# Descrição de Procedimento — {{nome_procedimento}}\n\n"
        "**Paciente:** {{paciente_id}}\n"
        "**Data:** {{data}}\n\n"
        "## Indicação\n{{indicacao}}\n\n"
        "## Técnica\n{{tecnica}}\n\n"
        "## Intercorrências\n{{intercorrencias}}\n\n"
        "*Modelo sintético para fins acadêmicos — não constitui documento real.*\n"
    ),
}


def _perguntas_faq(prot: dict) -> list[dict]:
    doc_id = prot["id"]
    titulo = prot["titulo"].lower()
    textos = list(prot["secoes"].values())
    # Resposta = texto integral da seção citada. Versões anteriores truncavam em
    # 180 caracteres + "..." (corte no meio da palavra), o que ensinava o modelo
    # a parar no meio da frase no fine-tuning — ver docs/desvios.md item 13.
    return [
        {
            "pergunta": f"Quais os critérios diagnósticos relacionados a {titulo}?",
            "resposta": f"Conforme {doc_id} §1, {textos[0]}",
        },
        {
            "pergunta": f"Qual a conduta inicial recomendada em {titulo}?",
            "resposta": f"Conforme {doc_id} §2, {textos[1]}",
        },
        {
            "pergunta": f"Quais as doses de referência no manejo de {titulo}?",
            "resposta": f"Conforme {doc_id} §3, {textos[2]}",
        },
        {
            "pergunta": f"Quando escalonar ou alertar a equipe em caso de {titulo}?",
            "resposta": f"Conforme {doc_id} §4, {textos[3]}",
        },
        {
            "pergunta": f"Existe protocolo institucional para {titulo}?",
            "resposta": (
                f"Sim, {doc_id} — {prot['titulo']} (versão {prot['versao']}) descreve "
                f"definição, conduta inicial, medicações de referência e critérios de "
                f"escalonamento."
            ),
        },
    ]


def gerar_protocolos(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for prot in PROTOCOLOS:
        linhas = [
            "---",
            f"doc_id: {prot['id']}",
            f"titulo: {prot['titulo']}",
            f'versao: "{prot["versao"]}"',
            f"atualizado_em: {prot['atualizado_em']}",
            "---",
            "",
        ]
        for i, (secao, texto) in enumerate(prot["secoes"].items(), start=1):
            linhas.append(f"## {i}. {secao}")
            linhas.append(texto)
            linhas.append("")
        conteudo = "\n".join(linhas) + RODAPE
        caminho = destino / f"{prot['id']}.md"
        caminho.write_text(conteudo, encoding="utf-8", newline="\n")
        arquivos.append(caminho)
    return arquivos


def gerar_faqs(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = []
    contador = 1
    for prot in PROTOCOLOS:
        for item in _perguntas_faq(prot):
            linhas.append(
                json.dumps(
                    {
                        "id": f"FAQ-{contador:03d}",
                        "pergunta": item["pergunta"],
                        "resposta": item["resposta"],
                        "doc_ref": prot["id"],
                    },
                    ensure_ascii=False,
                )
            )
            contador += 1
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    return destino


def gerar_templates(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for nome, conteudo in TEMPLATES.items():
        caminho = destino / nome
        caminho.write_text(conteudo, encoding="utf-8", newline="\n")
        arquivos.append(caminho)
    return arquivos


def gerar_tudo(base_dir: str = "data/synthetic") -> None:
    base = Path(base_dir)
    protocolos = gerar_protocolos(base / "protocolos")
    faqs = gerar_faqs(base / "faqs.jsonl")
    templates = gerar_templates(base / "templates")
    print(f"Gerados {len(protocolos)} protocolos em {base / 'protocolos'}")
    print(f"Gerado {faqs}")
    print(f"Gerados {len(templates)} templates em {base / 'templates'}")


if __name__ == "__main__":
    gerar_tudo()
