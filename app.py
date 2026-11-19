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

# 2. CSS PULITO (Senza elementi fissi che coprono il testo)
st.markdown("""
    <style>
        /* Nasconde elementi superflui di Streamlit */
        [data-testid="stSidebar"], [data-testid="collapsedControl"],
        header[data-testid="stHeader"], #MainMenu, [data-testid="stAppDeployButton"],
        footer, div[class*="viewerBadge"], [data-testid="stStatusWidget"] {
            display: none !important;
        }
        /* Margini compatti e spazio extra in basso per non finire sotto il banner Streamlit */
        .stMainBlockContainer, [data-testid="stAppViewBlockContainer"], .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 4rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 950px !important;
            margin: 0 auto !important;
        }
        /* Evita che il menu a tendina venga tagliato */
        [data-baseweb="popover"] {
            max-height: 320px !important;
            overflow-y: auto !important;
        }
    </style>
""", unsafe_allow_html=True)

# Memoria di sessione per token e domanda inviata
if "token_ultima_domanda" not in st.session_state:
    st.session_state.token_ultima_domanda = 0
if "token_totali_sessione" not in st.session_state:
    st.session_state.token_totali_sessione = 0
if "domanda_da_eseguire" not in st.session_state:
    st.session_state.domanda_da_eseguire = ""

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

# Funzione che cattura la domanda e svuota subito la casella di testo
def invia_e_pulisci():
    chiave_input = f"domanda_{documento_selezionato}"
    testo_scritto = st.session_state.get(chiave_input, "").strip()
    if testo_scritto:
        st.session_state.domanda_da_eseguire = testo_scritto
        st.session_state[chiave_input] = ""

# 5. CASELLA DOMANDA CON PULIZIA AUTOMATICA DOPO L'INVIO
if documento_selezionato:
    nome_pulito = documento_selezionato.replace(".pdf", "").replace(".PDF", "")
    
    st.text_input(
        label="La tua domanda:",
        placeholder="Scrivi qui la tua domanda e premi Invio...",
        key=f"domanda_{documento_selezionato}",
        on_change=invia_e_pulisci
    )

    domanda_corrente = st.session_state.domanda_da_eseguire
    if domanda_corrente:
        # Azzera subito lo stato per evitare doppi invii al cambio documento
        st.session_state.domanda_da_eseguire = ""
        
        st.info(f"**Domanda:** {domanda_corrente}")
        with st.spinner("Analisi del documento in corso..."):
            testo_locale = estrai_testo_singolo_pdf(documento_selezionato)
            
            if testo_locale:
                prompt = f"Rispondi in modo preciso, chiaro e istituzionale basandoti esclusivamente su questo documento ufficiale ({nome_pulito}):\n{testo_locale}\n\nDomanda del cittadino: {domanda_corrente}"
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

# 6. CONTATORE NEL FLUSSO NATURALE (Non copre mai il testo)
st.write("")
with st.expander("📊 Monitoraggio consumo token (Info tecniche)"):
    col1, col2 = st.columns(2)
    col1.metric("Ultima interrogazione", f"{st.session_state.token_ultima_domanda:,}".replace(",", "."))
    col2.metric("Totale sessione", f"{st.session_state.token_totali_sessione:,}".replace(",", "."))
