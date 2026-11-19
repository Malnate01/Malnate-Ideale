import streamlit as st
import os
from google import genai
from google.genai import types
from pypdf import PdfReader

# 1. CONFIGURAZIONE PAGINA WEB
st.set_page_config(
    page_title="Assistente Civico - Malnate",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS PER STABILIZZARE L'IFRAME E ANCORARE IL CONTATORE SUL FONDO
st.markdown("""
    <style>
        /* Nasconde elementi superflui di Streamlit */
        [data-testid="stSidebar"], [data-testid="collapsedControl"],
        header[data-testid="stHeader"], #MainMenu, [data-testid="stAppDeployButton"] {
            display: none !important;
        }
        /* Stabilizza l'altezza per evitare sbalzi e chiusure improvvise del menu */
        html, body, [data-testid="stAppViewContainer"] {
            height: 100vh !important;
            overflow-x: hidden !important;
        }
        /* Struttura flessibile che spinge l'ultimo elemento (i token) sempre in fondo */
        .stMainBlockContainer, [data-testid="stAppViewBlockContainer"], .block-container {
            display: flex !important;
            flex-direction: column !important;
            min-height: 96vh !important;
            padding-top: 1.2rem !important;
            padding-bottom: 0.8rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 950px !important;
            margin: 0 auto !important;
        }
        /* Spinge in basso il contenitore finale dei token */
        .stMainBlockContainer > div:last-child,
        [data-testid="stAppViewBlockContainer"] > div:last-child,
        .block-container > div:last-child {
            margin-top: auto !important;
        }
        /* Evita che il menu a tendina venga tagliato */
        [data-baseweb="popover"] {
            max-height: 320px !important;
            overflow-y: auto !important;
        }
    </style>
""", unsafe_allow_html=True)

# Memoria per il contatore dei token
if "token_ultima_domanda" not in st.session_state:
    st.session_state.token_ultima_domanda = 0
if "token_totali_sessione" not in st.session_state:
    st.session_state.token_totali_sessione = 0

# 3. INIZIALIZZAZIONE CLIENT AI
try:
    chiave_segreta = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=chiave_segreta)
except Exception:
    st.error("Configurare la GEMINI_API_KEY nei Secrets di Streamlit.")

# LETTURA SINGOLO PDF
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

# 4. SCANSIONE DOCUMENTI E MENU A TENDINA UNICO
file_presenti = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
documento_selezionato = None

if file_presenti:
    documento_selezionato = st.selectbox(
        label="Archivio Documenti",
        label_visibility="collapsed",
        options=file_presenti,
        index=None,
        format_func=lambda x: x.replace(".pdf", "").replace(".PDF", ""),
        placeholder="📚 Seleziona un atto ufficiale dall'archivio del Comune..."
    )
else:
    st.warning("⚠️ Nessun file PDF trovato nell'archivio.")

# 5. MODULO DOMANDA E RISPOSTA (Compatto, senza righe vuote o ripetizioni)
if documento_selezionato:
    nome_pulito = documento_selezionato.replace(".pdf", "").replace(".PDF", "")
    
    with st.form(key="form_domanda", clear_on_submit=False):
        user_input = st.text_input(
            label="La tua domanda:",
            placeholder="Scrivi qui cosa vuoi sapere su questo documento..."
        )
        invia = st.form_submit_button("🔍 Chiedi all'Assistente")

    if invia and user_input.strip():
        with st.spinner("Analisi del documento in corso..."):
            testo_locale = estrai_testo_singolo_pdf(documento_selezionato)
            
            if testo_locale:
                prompt = f"Rispondi in modo preciso, chiaro e istituzionale basandoti esclusivamente su questo documento ufficiale ({nome_pulito}):\n{testo_locale}\n\nDomanda del cittadino: {user_input}"
                config = types.GenerateContentConfig()
                
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=config
                    )
                    st.markdown("### Risposta:")
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

# 6. CONTATORE ANCORATO SUL FONDO DELL'IFRAME
with st.expander("📊 Monitoraggio consumo token (Info tecniche)"):
    col1, col2 = st.columns(2)
    col1.metric("Ultima interrogazione", f"{st.session_state.token_ultima_domanda:,}".replace(",", "."))
    col2.metric("Totale sessione", f"{st.session_state.token_totali_sessione:,}".replace(",", "."))
