import streamlit as st
import os
from google import genai
from google.genai import types
from pypdf import PdfReader

# 1. CONFIGURAZIONE PAGINA WEB (Senza barra laterale per massima resa su PC e Mobile)
st.set_page_config(
    page_title="Assistente Civico - Malnate",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# OTTIMIZZAZIONE SPAZIO VERTICALE E PULIZIA INTERFACCIA
st.markdown("""
    <style>
        /* Nasconde la barra laterale e l'intestazione superflua */
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        header[data-testid="stHeader"], #MainMenu, [data-testid="stAppDeployButton"] {
            display: none !important;
        }
        /* Compatta i margini superiori per guadagnare spazio subito */
        .stMainBlockContainer, [data-testid="stAppViewBlockContainer"], .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            max-width: 950px !important;
            margin: 0 auto !important;
        }
        /* Titolo principale elegante e compatto */
        h1 {
            font-size: 1.6rem !important;
            padding-top: 0rem !important;
            margin-bottom: 0.2rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Memoria per il contatore dei token
if "token_ultima_domanda" not in st.session_state:
    st.session_state.token_ultima_domanda = 0
if "token_totali_sessione" not in st.session_state:
    st.session_state.token_totali_sessione = 0

# 2. INIZIALIZZAZIONE CLIENT AI
try:
    chiave_segreta = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=chiave_segreta)
except Exception:
    st.error("Configurare la GEMINI_API_KEY nei Secrets di Streamlit.")

# FUNZIONE VELOCE PER LEGGERE UN SINGOLO PDF ALLA VOLTA
@st.cache_data
def estrai_testo_singolo_pdf(nome_file):
    try:
        if nome_file and os.path.exists(nome_file):
            reader = PdfReader(nome_file)
            testo = ""
            for page in reader.pages:
                testo += page.extract_text() + "\n"
            return testo
        return ""
    except Exception as e:
        return f"Errore lettura file: {e}"

# 3. INTESTAZIONE E SCANSIONE DOCUMENTI
st.title("🏛️ Assistente Civico Digitale - Comune di Malnate")
st.write("Seleziona un atto ufficiale dall'archivio qui sotto per porre domande specifiche sul suo contenuto.")

file_presenti = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])

# 4. MENU A TENDINA CENTRALE (Nessun file pre-selezionato all'apertura)
documento_selezionato = None

if file_presenti:
    documento_selezionato = st.selectbox(
        label="📂 Archivio Documenti Comunali:",
        options=file_presenti,
        index=None,
        placeholder="Clicca qui per scegliere il documento da interrogare..."
    )
else:
    st.warning("⚠️ Nessun file PDF trovato nell'archivio.")

# 5. AREA CHAT (Compare solo dopo aver scelto un documento)
if documento_selezionato:
    st.divider()
    st.caption(f"📄 Stai interrogando: **{documento_selezionato}**")
    
    user_input = st.chat_input(f"Scrivi qui la tua domanda su '{documento_selezionato}'...")

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("Analisi del documento in corso..."):
                testo_locale = estrai_testo_singolo_pdf(documento_selezionato)
                
                if testo_locale:
                    prompt = f"Rispondi in modo preciso, chiaro e istituzionale basandoti esclusivamente su questo documento ufficiale ({documento_selezionato}):\n{testo_locale}\n\nDomanda del cittadino: {user_input}"
                    config = types.GenerateContentConfig()
                    
                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                            config=config
                        )
                        st.write(response.text)
                        
                        if response.usage_metadata:
                            consumo_attuale = response.usage_metadata.total_token_count or 0
                            st.session_state.token_ultima_domanda = consumo_attuale
                            st.session_state.token_totali_sessione += consumo_attuale
                            
                    except Exception as e:
                        errore_testo = str(e)
                        if "429" in errore_testo or "RESOURCE_EXHAUSTED" in errore_testo:
                            st.warning("⏳ L'assistente è momentaneamente occupato per l'alto numero di richieste. Attendi un minuto e riprova.")
                        else:
                            st.error(f"Errore di sistema ({errore_testo}). Riprova tra poco.")
                else:
                    st.error("Impossibile leggere il contenuto di questo file PDF.")

# 6. CONTATORE DISCRETO A PIÈ DI PAGINA (Apribile con un clic)
st.write("")
with st.expander("📊 Monitoraggio consumo token (Info tecniche)"):
    col1, col2 = st.columns(2)
    col1.metric("Ultima interrogazione", f"{st.session_state.token_ultima_domanda:,}".replace(",", "."))
    col2.metric("Totale sessione", f"{st.session_state.token_totali_sessione:,}".replace(",", "."))
