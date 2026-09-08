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
    return [
        {
            "pergunta": f"Quais os critérios diagnósticos relacionados a {titulo}?",
            "resposta": f"Conforme {doc_id} §1, {textos[0][:180]}...",
        },
        {
            "pergunta": f"Qual a conduta inicial recomendada em {titulo}?",
            "resposta": f"Conforme {doc_id} §2, {textos[1][:180]}...",
        },
        {
            "pergunta": f"Quais as doses de referência no manejo de {titulo}?",
            "resposta": f"Conforme {doc_id} §3, {textos[2][:180]}...",
        },
        {
            "pergunta": f"Quando escalonar ou alertar a equipe em caso de {titulo}?",
            "resposta": f"Conforme {doc_id} §4, {textos[3][:180]}...",
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
        caminho.write_text(conteudo, encoding="utf-8")
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
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def gerar_templates(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for nome, conteudo in TEMPLATES.items():
        caminho = destino / nome
        caminho.write_text(conteudo, encoding="utf-8")
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
