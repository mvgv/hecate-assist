import uuid
from pathlib import Path

import streamlit as st

from medassist.assistant.graph import responder, retomar
from medassist.config import get_settings
from medassist.db.queries import list_alerts, list_patients

st.set_page_config(page_title="MedAssist", page_icon="⚕️", layout="wide")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "pendente" not in st.session_state:
    st.session_state.pendente = None

with st.sidebar:
    st.header("⚕️ MedAssist")

    try:
        pacientes = list_patients()
    except Exception:
        pacientes = []

    opcoes = {"(sem paciente)": None}
    for p in pacientes:
        opcoes[f"{p['id']} — {p['nome']}"] = p["id"]

    escolha = st.selectbox("Paciente", list(opcoes.keys()))
    paciente_id = opcoes[escolha]

    st.text_input("Thread (conversa)", value=st.session_state.thread_id, disabled=True)

    if st.button("Nova conversa"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.mensagens = []
        st.session_state.pendente = None
        st.rerun()

    with st.expander("🔔 Alertas"):
        try:
            alertas = list_alerts(paciente_id)
        except Exception:
            alertas = []
        if not alertas:
            st.caption("Nenhum alerta.")
        for a in alertas:
            st.write(f"**[{a['severidade']}]** {a['paciente_id']} — {a['tipo']}")
            st.caption(a["mensagem"])

    with st.expander("📜 Auditoria (hoje)"):
        settings = get_settings()
        log_path = Path(settings.log_dir) / f"audit_{__import__('time').strftime('%Y%m%d')}.jsonl"
        if log_path.exists():
            linhas = log_path.read_text(encoding="utf-8").splitlines()[-50:]
            st.code("\n".join(linhas), language="json")
        else:
            st.caption("Sem log de auditoria hoje ainda.")

st.title("Assistente Médico — Apoio à Decisão")

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.pendente:
    payload = st.session_state.pendente
    st.warning(
        f"**Aprovação humana pendente**\n\n"
        f"**Motivo:** {payload.get('motivo')}\n\n"
        f"**Resposta proposta:** {payload.get('resposta_proposta')}\n\n"
        f"**Fontes:** {', '.join(payload.get('fontes') or []) or 'nenhuma'}"
    )
    col1, col2 = st.columns(2)
    aprovador = st.text_input("Seu nome/CRM", key="aprovador_nome")
    if col1.button("✅ Aprovar", disabled=not aprovador):
        with st.spinner("Registrando aprovação..."):
            resultado = retomar(st.session_state.thread_id, True, aprovador, "")
        st.session_state.mensagens.append(
            {"role": "assistant", "content": resultado.get("resposta_final", "")}
        )
        st.session_state.pendente = None
        st.rerun()
    if col2.button("❌ Rejeitar", disabled=not aprovador):
        with st.spinner("Registrando rejeição..."):
            resultado = retomar(st.session_state.thread_id, False, aprovador, "")
        st.session_state.mensagens.append(
            {"role": "assistant", "content": resultado.get("resposta_final", "")}
        )
        st.session_state.pendente = None
        st.rerun()

pergunta = st.chat_input("Digite sua dúvida clínica ou pergunta sobre o paciente...")
if pergunta and not st.session_state.pendente:
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.spinner("Consultando protocolos e gerando resposta..."):
        resultado = responder(pergunta, paciente_id, st.session_state.thread_id)

    if "__interrupt__" in resultado:
        st.session_state.pendente = resultado["__interrupt__"][0].value
    else:
        resposta = resultado.get("resposta_final", "(sem resposta)")
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})

    st.rerun()
