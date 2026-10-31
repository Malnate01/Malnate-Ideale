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
    ("Sono un cittadino curioso (Voglio capire come funziona)", "Sono un cittadino esperto (Cerco documenti specifici)")
)

domanda_predefinita = ""
documento_selezionato = None
mostra_chat_libera = False

# 5. GESTIONE DEI MENU IN BASE AL PROFILO
if "curioso" in profilo.lower():
    st.subheader("💡 Non sai da dove iniziare? Prova una di queste domande frequenti:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📜 Cosa dice lo Statuto Comunale?"):
            domanda_predefinita = "Spiegami in modo semplice cos'è lo Statuto di Malnate e quali sono i punti principali."
            for f in file_presenti:
                if "statuto" in f.lower(): 
                    documento_selezionato = f
                    
    with col2:
        if st.button("👥 Come è organizzato il Comune"):
            domanda_predefinita = "Spiegami come è strutturato il Comune e la sua organizzazione"
            for f in file_presenti:
                if "statuto" in f.lower() or "organizza" in f.lower():
                    documento_selezionato = f
                    
    with col3:
        if st.button("📅 Dove trovo gli ultimi verbali?"):
            domanda_predefinita = "Quali informazioni sono presenti sui verbali del consiglio comunale?"
            for f in file_presenti:
                if "verbale" in f.lower():
                    documento_selezionato = f
                    
    # Per il cittadino curioso la chat libera rimane spenta (mostra_chat_libera = False)

else:
    # Profilo esperto: abilitiamo la selezione del file e la chat libera
    st.subheader("📂 Strumenti avanzati per cittadini informati:")
    if file_presenti:
        documento_selezionato = st.selectbox("Seleziona il documento specifico da interrogare:", file_presenti)
        mostra_chat_libera = True
    else:
        st.warning("⚠️ Nessun file PDF trovato su GitHub.")

# 6. CASSELLA DI TESTO LIBERA (SOLO SE ABILITATA)
st.write("---")
user_input = None

if mostra_chat_libera:
    user_input = st.chat_input("Scrivi qui la tua domanda sul documento selezionato...")

# Scegliamo la domanda da sottoporre all'AI
domanda_finale = domanda_predefinita if domanda_predefinita else user_input

# 7. ELABORAZIONE RISPOSTA MIRATA CON MESSAGGIO CORTESE PER ERRORI DI QUOTA
if domanda_finale:
    with st.chat_message("user"):
        st.write(domanda_finale)
        
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione risposta..."):
            testo_locale = estrai_testo_singolo_pdf(documento_selezionato) if documento_selezionato else ""
            
            if testo_locale:
                st.caption(f"🔍 Risposta generata analizzando esclusivamente il file: **{documento_selezionato}**")
                prompt = f"Rispondi in modo preciso basandoti solo su questo testo istituzionale ({documento_selezionato}):\n{testo_locale}\n\nDomanda: {domanda_finale}"
                config = types.GenerateContentConfig()
                
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=config
                    )
                    st.write(response.text)
                except Exception as e:
                    # Se va in errore 429 o altro, mostriamo un messaggio pulito anziché il codice di sistema
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⏳ L'assistente è momentaneamente occupato a causa dell'alto numero di richieste complessive su Google. Per favore, attendi un minuto e riprova la domanda.")
                    else:
                        st.error("Si è verificato un momento di manutenzione del sistema. Riprova tra poco.")
            else:
                st.write("Seleziona un documento valido per porre questa domanda.")
