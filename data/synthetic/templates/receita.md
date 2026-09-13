---
doc_id: TPL-002
titulo: Modelo Institucional de Receita Médica
tipo: template
versao: "1.0"
atualizado_em: 2025-11-10
---

## 1. Quando usar
Usar este modelo na prescrição de alta hospitalar ou ambulatorial. A receita é sempre emitida e assinada por médico habilitado; medicamentos sujeitos a controle especial exigem receituário próprio e via adicional retida pela farmácia. O assistente virtual não emite receitas — apenas apresenta o modelo e apoia a redação, cabendo ao médico responsável definir fármaco, dose e via.

## 2. Estrutura do documento
    # Receita Médica

    **Paciente:** {{paciente_id}}
    **Data:** {{data}}

    {{itens}}

    **Médico responsável:** {{medico}} — {{crm}}

Cada item de {{itens}} segue o padrão: nome do fármaco, concentração, forma farmacêutica, via de administração, intervalo e duração do tratamento.

## 3. Exemplo preenchido
Receita Médica. Paciente: [PACIENTE]. Data: [DATA]. 1. Amoxicilina + clavulanato 875/125 mg, comprimido, via oral, de 12 em 12 horas, por 7 dias. 2. Dipirona sódica 500 mg, comprimido, via oral, de 6 em 6 horas, se dor ou febre, por até 5 dias. 3. Retorno ambulatorial em 7 dias ou antes se piora clínica. Médico responsável: [MEDICO] — [CRM].

## 4. Regras de preenchimento
Escrever a posologia por extenso, sem abreviaturas ambíguas (usar unidade internacional em vez de UI, micrograma em vez de mcg quando manuscrito). Registrar alergias conhecidas do paciente antes de emitir e conferir interações com as medicações em uso. Não há receita válida sem data, assinatura e CRM do médico responsável. Sugestões geradas por sistema de apoio à decisão são rascunho e exigem validação médica antes de qualquer entrega ao paciente.

---
*Documento sintético para fins acadêmicos — não constitui receita real.*
