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

# 3. SCANSIONE DEI PDF DISPONIBILI
file_presenti = [f for f in os.listdir(".") if f.endswith(".pdf")]

# 4. INTERFACCIA: SCELTA DEL PROFILO UTENTE
st.sidebar.header("Seleziona il tuo profilo")
profilo = st.sidebar.radio(
    "Che tipo di informazioni cerchi?",
    ("Sono un cittadino curioso (Voglio capire come funziona)", 
     "Sono un cittadino esperto (Cerco documenti specifici)")
)

domanda_predefinita = ""
documento_selezionato = None

# 5. GESTIONE DEI MENU
if "curioso" in profilo.lower():
    st.subheader("💡 Non sai da dove iniziare? Prova una di queste domande frequenti:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📜 Cosa dice lo Statuto Comunale?"):
            domanda_predefinita = "Spiegami in modo semplice cos'è lo Statuto di Malnate e quali sono i punti principali."
            for f in file_presenti:
                if "statuto" in f.lower(): documento_selezionato = f
    with col2:
        if st.button("👥 Come è organizzato il Comune"):
            domanda_predefinita = "Spiegami come è strutturato il Comune e la  sua organizzazione"
    with col3:
        if st.button("📅 Dove trovo gli ultimi verbali?"):
            domanda_predefinita = "Qual è il link sul sito del comune per vedere i verbali del consiglio?"

else:
    st.subheader("📂 Strumenti avanzati per cittadini informati:")
    if file_presenti:
        # L'utente esperto sceglie lui il binario su cui muoversi
        documento_selezionato = st.selectbox("Seleziona il documento specifico da interrogare:", file_presenti)
    else:
        st.warning("⚠️ Nessun file PDF trovato su GitHub.")

# 6. CASSELLA DI TESTO LIBERA (CHAT)
st.write("---")
user_input = st.chat_input("Oppure scrivi qui la tua domanda libera...")

domanda_finale = domanda_predefinita if domanda_predefinita else user_input

# 7. FILTRO INTELLIGENTE: SELEZIONE DEL FILE CORRETTO PER LE DOMANDE LIBERE
if user_input and file_presenti and not documento_selezionato:
    with st.spinner("Individuazione del documento pertinente..."):
        # Chiediamo a Gemini di fare da vigile urbano: deve solo scegliere il nome del file migliore, senza rispondere
        prompt_filtro = f"""
        Analizza la domanda del cittadino e seleziona il nome del file PDF più pertinente tra quelli elencati.
        Rispondi ESCLUSIVAMENTE con il nome del file esatto, senza aggiungere altre parole, spiegazioni o saluti.
        Se nessuno dei file è pertinente, rispondi con la parola 'WEB'.

        File disponibili: {file_presenti}
        Domanda: {user_input}
        """
        try:
            res_filtro = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_filtro)
            scelta_ai = res_filtro.text.strip()
            if scelta_ai in file_presenti:
                documento_selezionato = scelta_ai
        except:
            documento_selezionato = None

# 8. ELABORAZIONE RISPOSTA MIRATA
if domanda_finale:
    with st.chat_message("user"):
        st.write(domanda_finale)
        
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione risposta..."):
            
            # Ora leggiamo SOLO il file scelto, non tutti insieme!
            testo_locale = estrai_testo_singolo_pdf(documento_selezionato) if documento_selezionato else ""
            
            if testo_locale and "link" not in domanda_finale.lower():
                st.caption(f"🔍 Risposta generata analizzando esclusivamente il file: **{documento_selezionato}**")
                prompt = f"Rispondi in modo preciso basandoti solo su questo testo istituzionale ({documento_selezionato}):\n{testo_locale}\n\nDomanda: {domanda_finale}"
                config = types.GenerateContentConfig()
            else:
                st.caption("🌐 Risposta generata tramite ricerca web sul sito del Comune")
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
