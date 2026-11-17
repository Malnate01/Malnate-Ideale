import streamlit as st
import os
from google import genai
from google.genai import types
from pypdf import PdfReader

# 1. CONFIGURAZIONE PAGINA WEB
st.set_page_config(page_title="Assistente Civico - Malnate", page_icon="🏛️", layout="wide")

# RIDUZIONE SPAZIO VUOTO IN ALTO E NELLA BARRA LATERALE
# ELIMINAZIONE INTESTAZIONI VUOTE E RIDUZIONE SPAZIO IN ALTO
# RIDUZIONE SPAZIO IN ALTO MANTENENDO IL PULSANTE MENU PER CELLULARI
st.markdown("""
    <style>
        /* Rende trasparente l'intestazione superiore ma lascia attivo il pulsante > per riaprire il menu */
        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 2.5rem !important;
        }
        /* Nasconde solo i pulsanti tecnici di Streamlit in alto a destra */
        [data-testid="stToolbar"], [data-testid="stAppDeployButton"], #MainMenu {
            display: none !important;
        }
        /* Riduce lo spazio nella colonna sinistra senza nascondere la X di chiusura su mobile */
        [data-testid="stSidebarHeader"] {
            padding-top: 0.5rem !important;
            padding-bottom: 0.2rem !important;
            min-height: 2rem !important;
        }
        /* Spinge il contenuto principale verso l'alto */
        .stMainBlockContainer, [data-testid="stAppViewBlockContainer"], .block-container {
            padding-top: 2.2rem !important;
            padding-bottom: 1rem !important;
            margin-top: 0rem !important;
        }
        /* Spinge l'elenco documenti in alto a sinistra */
        [data-testid="stSidebarUserContent"], [data-testid="stSidebarContent"] {
            padding-top: 0.2rem !important;
            margin-top: 0rem !important;
        }
        /* Titoli compatti */
        h1 {
            font-size: 1.6rem !important;
            padding-top: 0rem !important;
            margin-top: 0rem !important;
            margin-bottom: 0.2rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
            padding-top: 0.3rem !important;
        }
    </style>
""", unsafe_allow_html=True)





st.title("🏛️ Assistente Civico Digitale - Comune di Malnate")
st.write("Interroga direttamente gli atti, i regolamenti e i verbali ufficiali del Comune.")

# Inizializziamo la memoria per il contatore dei token nella sessione
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

# 3. SCANSIONE E ORDINAMENTO ALFABETICO DEI PDF DISPONIBILI
file_presenti = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])

# 4. BARRA LATERALE SINISTRA: SELEZIONE DOCUMENTO E CONTATORE
st.sidebar.header("📂 Archivio Documenti")
documento_selezionato = None

if file_presenti:
    documento_selezionato = st.sidebar.radio(
        "Scegli il documento da interrogare:",
        file_presenti
    )
    st.sidebar.info("💡 Suggerimento: formula domande specifiche riferite al documento selezionato.")
else:
    st.sidebar.warning("⚠️ Nessun file PDF trovato nell'archivio.")

# Creiamo uno spazio vuoto nella barra laterale che aggiorneremo a fine risposta
st.sidebar.write("---")
riquadro_contatore = st.sidebar.empty()

def aggiorna_contatore():
    with riquadro_contatore.container():
        st.caption("📊 **Monitoraggio Consumo Token**")
        st.metric(
            label="Ultima interrogazione", 
            value=f"{st.session_state.token_ultima_domanda:,}".replace(",", ".")
        )
        st.caption(f"Totale sessione: **{st.session_state.token_totali_sessione:,}** token".replace(",", "."))

# Mostriamo subito il contatore a zero all'avvio
aggiorna_contatore()

# 5. AREA PRINCIPALE DESTRA: CHAT DI INTERROGAZIONE
if documento_selezionato:
    st.subheader(f"📄 Documento attivo: {documento_selezionato}")
    user_input = st.chat_input(f"Fai una domanda su '{documento_selezionato}'...")

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
                        
                        # Leggiamo i dati reali di consumo restituiti da Google
                        if response.usage_metadata:
                            consumo_attuale = response.usage_metadata.total_token_count or 0
                            st.session_state.token_ultima_domanda = consumo_attuale
                            st.session_state.token_totali_sessione += consumo_attuale
                            aggiorna_contatore()
                            
                    except Exception as e:
                        errore_testo = str(e)
                        if "429" in errore_testo or "RESOURCE_EXHAUSTED" in errore_testo:
                            st.warning("⏳ L'assistente è momentaneamente occupato per l'alto numero di richieste. Attendi un minuto e riprova.")
                        else:
                            st.error(f"Errore di sistema ({errore_testo}). Riprova tra poco.")
                else:
                    st.error("Impossibile leggere il contenuto di questo file PDF.")
else:
    st.info("Carica almeno un file PDF su GitHub per iniziare a usare l'assistente.")
