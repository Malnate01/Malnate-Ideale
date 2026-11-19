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

# 2. CSS PER ALTEZZA MINIMA, COMPATTEZZA E RESA RESPONSIVE SU MOBILE E DESKTOP
st.markdown("""
    <style>
        /* Nasconde elementi superflui di Streamlit */
        [data-testid="stSidebar"], [data-testid="collapsedControl"],
        header[data-testid="stHeader"], #MainMenu, [data-testid="stAppDeployButton"] {
            display: none !important;
        }
        /* Imposta un'altezza minima per evitare che l'iframe si schiacci su mobile */
        .stApp {
            min-height: 900px !important;
        }
        /* Margini compatti e larghezza adattiva */
        .stMainBlockContainer, [data-testid="stAppViewBlockContainer"], .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 950px !important;
            margin: 0 auto !important;
        }
        h1 {
            font-size: 1rem !important;
            padding-top: 0rem !important;
            margin-bottom: 0.3rem !important;
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

# 4. INTESTAZIONE E SCANSIONE DOCUMENTI
st.title("📂 Seleziona un atto ufficiale dall'archivio del Comune")
#st.write("Seleziona un atto ufficiale dall'archivio qui sotto per porre domande sul suo contenuto.")

file_presenti = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])

# 5. MENU A TENDINA CENTRALE (Nasconde l'estensione .pdf alla vista)
documento_selezionato = None

if file_presenti:
    documento_selezionato = st.selectbox(
        label="📂 Archivio Documenti Comunali:",
        options=file_presenti,
        index=None,
        format_func=lambda x: x.replace(".pdf", "").replace(".PDF", ""),
        placeholder="Clicca qui per scegliere il documento da interrogare..."
    )
else:
    st.warning("⚠️ Nessun file PDF trovato nell'archivio.")

# 6. MODULO DOMANDA E RISPOSTA (Ordine verticale fisso)
if documento_selezionato:
    st.divider()
    nome_pulito = documento_selezionato.replace(".pdf", "").replace(".PDF", "")
    #st.caption(f"📄 Documento attivo: **{nome_pulito}**")
    
    with st.form(key="form_domanda", clear_on_submit=False):
        user_input = st.text_input(
            label="La tua domanda:",
            placeholder="Scrivi qui cosa vuoi sapere su questo documento..."
        )
       # invia = st.form_submit_button("🔍 Chiedi all'Assistente")

   # if invia and user_input.strip():
    if user_input.strip():
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

# 7. CONTATORE SUL FONDO DELLA PAGINA
st.write("")
st.divider()
with st.expander("📊 Monitoraggio consumo token (Info tecniche)"):
    col1, col2 = st.columns(2)
    col1.metric("Ultima interrogazione", f"{st.session_state.token_ultima_domanda:,}".replace(",", "."))
    col2.metric("Totale sessione", f"{st.session_state.token_totali_sessione:,}".replace(",", "."))
