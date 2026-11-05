import streamlit as st
from dotenv import load_dotenv
from google import genai
from time import perf_counter
from html import escape
from pathlib import Path

from src.agent.agent import criar_chat
from src.ui.graficos import renderizar_resultado


ASSETS = Path(__file__).parent / "assets"

st.html(ASSETS / "ferramentas.css")

JS_CRONOMETRO = (
    ASSETS / "cronometro.js"
).read_text(encoding="utf-8")


load_dotenv()

st.set_page_config(
    page_title="TransitMind AI",
    page_icon="🚇",
    layout="wide",
)



def encaminhar_evento(evento):
    observador = st.session_state.get("observador_eventos")

    if observador is not None:
        observador(evento)

# Inicializamos os dados somente uma vez por sessão.
if "resultados_pendentes" not in st.session_state:
    st.session_state.resultados_pendentes = []

def encaminhar_resultado(resultado: dict):
    st.session_state.resultados_pendentes.append(resultado)

if "cliente" not in st.session_state:
    st.session_state.cliente = genai.Client()

if "chat" not in st.session_state:
    st.session_state.chat = criar_chat(
        st.session_state.cliente,
        callback=encaminhar_evento,
        registrar_resultado=encaminhar_resultado,
    )

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

if "eventos" not in st.session_state:
    st.session_state.eventos = []


@st.dialog("Reiniciar conversa?")
def confirmar_reinicio():
    st.write(
        "O histórico desta conversa será descartado. "
        "Deseja continuar?"
    )

    cancelar, confirmar = st.columns(2)

    with cancelar:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

    with confirmar:
        if st.button(
            "Reiniciar",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.chat = criar_chat(
                st.session_state.cliente,
                callback=encaminhar_evento,
                registrar_resultado=encaminhar_resultado,
            )
            st.session_state.mensagens = []
            st.session_state.eventos = []
            st.rerun()


# Barra lateral
with st.sidebar:
    st.subheader("🔧 Ferramentas")
    st.caption("Execuções realizadas pelo agente")

    painel_eventos = st.empty()


NOMES_FERRAMENTAS = {
    "pesquisar_linhas": "Pesquisar linhas",
    "analisar_validacoes_por_veiculo": "Analisar validações",
}

ESTADOS = {
    "executando": ("Em execução", '<span class="tm-spinner"></span>'),
    "concluida": ("Concluída", "✓"),
    "erro": ("Erro", "!"),
}

def renderizar_eventos():
    cards = []

    for evento in st.session_state.eventos[-12:]:
        estado = evento["estado"]
        rotulo, icone = ESTADOS[estado]

        nome = NOMES_FERRAMENTAS.get(
            evento["ferramenta"],
            evento["ferramenta"].replace("_", " ").capitalize(),
        )

        nome = escape(nome)
        detalhes = escape(str(evento.get("detalhes") or ""))

        tempo = evento.get("tempo")
        iniciado_em = evento.get("iniciado_em")

        # A ferramenta terminou: tempo definitivo.
        if tempo is not None:
            tempo_html = (
                f'<span class="tm-time">'
                f'◷ {tempo:.2f} s'
                f'</span>'
            )

        # A ferramenta está executando: cronômetro ao vivo.
        elif estado == "executando" and iniciado_em is not None:
            inicio_ms = int(iniciado_em * 1000)

            tempo_html = (
                f'<span class="tm-time" '
                f'data-iniciado-ms="{inicio_ms}">'
                f'◷ 0.00 s'
                f'</span>'
            )

        # Evento antigo ou sem informações de tempo.
        else:
            tempo_html = ""

        cards.append(f"""
            <div class="tm-card {estado}">
                <div class="tm-icon">{icone}</div>

                <div class="tm-content">
                    <div class="tm-title">{nome}</div>
                    <div class="tm-details">{detalhes}</div>

                    <div class="tm-meta">
                        <span class="tm-state">{rotulo}</span>
                        {tempo_html}
                    </div>
                </div>
            </div>
        """)

    conteudo = "".join(cards)

    if not conteudo:
        conteudo = """
            <div class="tm-details">
                Nenhuma ferramenta executada ainda.
            </div>
        """

    painel_eventos.html(
        f'<div class="tm-list">{conteudo}</div>'
        f'<script>{JS_CRONOMETRO}</script>',
        unsafe_allow_javascript=True,
    )




def receber_evento(evento):
    """Registra e apresenta alterações de estado."""
    if evento["estado"] == "executando":
        st.session_state.eventos.append(evento.copy())

    else:
        # Atualiza a execução mais recente ainda em andamento.
        for registro in reversed(st.session_state.eventos):
            if (
                registro["ferramenta"] == evento["ferramenta"]
                and registro["estado"] == "executando"
            ):
                registro.update(evento)
                break
        else:
            st.session_state.eventos.append(evento.copy())

    renderizar_eventos()


# Conecta a interface atual ao callback persistente.
st.session_state.observador_eventos = receber_evento

# Exibe os eventos anteriores após cada rerun.
renderizar_eventos()



# Área central
st.title("🚇 TransitMind AI")
st.caption(
    "Explore dados públicos de transporte do Rio de Janeiro."
)

area_chat = st.container(
    height=480,
    border=False,
    autoscroll=True,
)

with area_chat:
    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["papel"]):
            st.markdown(mensagem["conteudo"])

            for resultado in mensagem.get("resultados", []):
                renderizar_resultado(resultado)


# Rodapé fixo
with st.bottom:
    coluna_chat, coluna_reinicio = st.columns(
        [12, 1],
        vertical_alignment="bottom",
    )

    with coluna_chat:
        pergunta = st.chat_input(
            "Pergunte algo sobre os transportes..."
        )

    with coluna_reinicio:
        if st.button(
            "↻",
            help="Reiniciar conversa",
            use_container_width=True,
        ):
            confirmar_reinicio()


# Processamento da mensagem
if pergunta:
    st.session_state.resultados_pendentes = []

    st.session_state.mensagens.append({
        "papel": "user",
        "conteudo": pergunta,
    })

    with area_chat:
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Consultando..."):
                try:
                    resposta = st.session_state.chat.send_message(pergunta)
                    texto = resposta.text or "Sem resposta textual."
                except Exception as erro:
                    print(f"[APP ERROR] {erro!r}")
                    st.error("Não foi possível obter a resposta.")
                    st.stop()

            st.markdown(texto)

            resultados = list(
                st.session_state.resultados_pendentes
            )

            for resultado in resultados:
                renderizar_resultado(resultado)

    st.session_state.mensagens.append({
        "papel": "assistant",
        "conteudo": texto,
        "resultados": resultados,
    })
