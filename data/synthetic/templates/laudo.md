---
doc_id: TPL-001
titulo: Modelo Institucional de Laudo de Exame
tipo: template
versao: "1.0"
atualizado_em: 2025-11-10
---

## 1. Quando usar
Usar este modelo para registrar o resultado interpretado de qualquer exame de imagem, endoscópico ou anatomopatológico solicitado pela equipe assistencial. O laudo é emitido pelo médico executante do exame e anexado ao prontuário eletrônico em até 24 horas do procedimento; resultados críticos exigem comunicação verbal imediata ao médico solicitante, além do registro escrito.

## 2. Estrutura do documento
    # Laudo — {{titulo_exame}}

    **Paciente:** {{paciente_id}}
    **Data:** {{data}}

    ## Descrição
    {{descricao}}

    ## Conclusão
    {{conclusao}}

    **Médico executante:** {{medico}} — {{crm}}

## 3. Exemplo preenchido
Laudo — Radiografia de tórax PA e perfil. Paciente: [PACIENTE]. Data: [DATA]. Descrição: opacidade heterogênea em lobo inferior direito, com broncograma aéreo, sem derrame pleural significativo; seios costofrênicos livres; área cardíaca dentro dos limites da normalidade. Conclusão: achados compatíveis com processo infeccioso pulmonar em lobo inferior direito; correlacionar com quadro clínico e laboratorial. Médico executante: [MEDICO] — [CRM].

## 4. Regras de preenchimento
A seção Descrição registra apenas achados objetivos, sem hipótese diagnóstica; a interpretação fica na Conclusão e deve usar linguagem de probabilidade (compatível com, sugestivo de, não se pode excluir), nunca afirmação categórica de diagnóstico. Identificar o paciente somente pelo identificador institucional, jamais por nome completo ou documento. Todo laudo exige assinatura e CRM do médico executante para ter validade; o assistente virtual pode sugerir a redação, mas o conteúdo final é de responsabilidade e validação do médico responsável.

---
*Documento sintético para fins acadêmicos — não constitui laudo real.*
