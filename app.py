import streamlit as st
import os
from google import genai
from google.genai import types
from pypdf import PdfReader

# 1. CONFIGURAZIONE PAGINA WEB
st.set_page_config(page_title="Assistente Civico - Malnate", page_icon="🏛️", layout="wide")

st.title("🏛️ Assistente Civico Digitale - Comune di Malnate")
st.write("Il tuo canale diretto con le informazioni e i documenti del Comune.")

# 2. INIZIALIZZAZIONE CLIENT AI
try:
    chiave_segreta = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=chiave_segreta)
except Exception:
    st.error("Configurare la GEMINI_API_KEY nei Secrets di Streamlit.")

# FUNZIONE PER LEGGERE I PDF CARICATI NELLA CARTELLA
@st.cache_data # Questo comando fa leggere il PDF UNA SOLA VOLTA, risparmiando tempo e memoria!
def estrai_testo_pdf(nome_file):
    try:
        if os.path.exists(nome_file):
            reader = PdfReader(nome_file)
            testo = ""
            for page in reader.pages:
                testo += page.extract_text() + "\n"
            return testo
        return ""
    except Exception as e:
        return f"Errore lettura file: {e}"

# 3. INTERFACCIA: SCELTA DEL PROFILO UTENTE
st.sidebar.header("Seleziona il tuo profilo")
profilo = st.sidebar.radio(
    "Che tipo di informazioni cerchi?",
    ("Sono un cittadino curioso (Voglio capire come funziona)", 
     "Sono un cittadino esperto (Cerco documenti specifici)")
)

# 4. SCANSIONE AUTOMATICA DEI PDF PRESENTI
# Il programma cerca da solo tutti i file .pdf che hai trascinato su GitHub
file_presenti = [f for f in os.listdir(".") if f.endswith(".pdf")]

# 5. GESTIONE DEI MENU IN BASE AL PROFILO
domanda_predefinita = ""
documento_selezionato = None

if "curioso" in profilo.lower():
    st.subheader("💡 Non sai da dove iniziare? Prova una di queste domande frequenti:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📜 Cosa dice lo Statuto Comunale?"):
            domanda_predefinita = "Spiegami in modo semplice cos'è lo Statuto di Malnate e quali sono i punti principali."
            # Cerca se tra i file caricati c'è lo statuto
            for f in file_presenti:
                if "statuto" in f.lower(): documento_selezionato = f
    with col2:
        if st.button("👥 Come posso partecipare al Consiglio?"):
            domanda_predefinita = "Come funziona la partecipazione dei cittadini ai consigli comunali di Malnate?"
    with col3:
        if st.button("📅 Dove trovo gli ultimi verbali?"):
            domanda_predefinita = "Qual è il link sul sito del comune per vedere i verbali del consiglio?"

else:
    st.subheader("📂 Strumenti avanzati per cittadini informati:")
    if file_presenti:
        documento_selezionato = st.selectbox("Seleziona il documento da consultare:", file_presenti)
    else:
        st.warning("⚠️ Non hai ancora caricato nessun file PDF su GitHub. L'AI userà solo la ricerca web.")

# 6. CASSELLA DI TESTO LIBERA (CHAT)
st.write("---")
user_input = st.chat_input("Oppure scrivi qui la tua domanda libera...")

domanda_finale = domanda_predefinita if domanda_predefinita else user_input

# 7. ELABORAZIONE RISPOSTA AI
if p_file := (documento_selezionato if documento_selezionato else (file_presenti[0] if file_presenti else None)):
    if not documento_selezionato: documento_selezionato = p_file

if domanda_finale:
    with st.chat_message("user"):
        st.write(domanda_finale)
        
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione in corso..."):
            
            # Se abbiamo un documento selezionato, leggiamo il testo locale
            testo_locale = estrai_testo_pdf(documento_selezionato) if documento_selezionato else ""
            
            if testo_locale and "link" not in domanda_finale.lower():
                # CHAT SUL PDF LOCALE (Consumo ricerche web: ZERO!)
                prompt = f"Rispondi alla domanda basandoti esclusivamente su questo documento ufficiale ({documento_selezionato}):\n{testo_locale}\n\nDomanda: {domanda_finale}"
                config = types.GenerateContentConfig()
            else:
                # RICERCA SUL WEB (Se il file non c'è o l'utente chiede un link esterno)
                prompt = f"Rispondi alla domanda cercando sul sito del Comune di Malnate (comune.malnate.va.it): {domanda_finale}"
                config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config
                )
                st.write(response.text)
            except Exception as e:
                st.error(f"Errore: {e}")
