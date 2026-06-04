import streamlit as st
import os
from google import genai
from google.genai import types

# 1. CONFIGURAZIONE PAGINA WEB
st.set_page_config(page_title="Assistente Civico - Malnate", page_icon="🏛️", layout="wide")

st.title("🏛️ Assistente Civico Digitale - Comune di Malnate")
st.write("Il tuo canale diretto con le informazioni e i documenti del Comune.")

# 2. INIZIALIZZAZIONE CLIENT AI (Sicura per il Web)
try:
    chiave_segreta = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=chiave_segreta)
except Exception:
    st.error("Configurare la GEMINI_API_KEY nei Secrets di Streamlit.")

# 3. INTERACCIA: SCELTA DEL PROFILO UTENTE
st.sidebar.header("Seleziona il tuo profilo")
profilo = st.sidebar.radio(
    "Che tipo di informazioni cerchi?",
    ("Sono un cittadino curioso (Voglio capire come funziona)", 
     "Sono un cittadino esperto (Cerco documenti specifici)")
)

TESTO_STATUTO_MALNATE = """
[Qui inseriremo il testo dello Statuto di Malnate estratto dal PDF nelle prossime sessioni]
"""

# 4. GESTIONE DEI MENU IN BASE AL PROFILO
domanda_predefinita = ""

if "curioso" in profilo.lower():
    st.subheader("💡 Non sai da dove iniziare? Prova una di queste domande frequenti:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📜 Cosa dice lo Statuto Comunale?"):
            domanda_predefinita = "Spiegami in modo semplice cos'è lo Statuto di Malnate e quali sono i punti principali."
    with col2:
        if st.button("👥 Come posso partecipare al Consiglio?"):
            domanda_predefinita = "Come funziona la partecipazione dei cittadini ai consigli comunali di Malnate?"
    with col3:
        if st.button("📅 Dove trovo gli ultimi verbali?"):
            domanda_predefinita = "Qual è il link sul sito del comune per vedere i verbali del consiglio?"

else:
    st.subheader("📂 Strumenti avanzati per cittadini informati:")
    documento_selezionato = st.selectbox(
        "Su quale documento specifico vuoi indagare?",
        ("Statuto Comunale", "Verbali Sedute Consiliari 2026", "Regolamenti Tasse/Imposte")
    )
    st.info(f"Stai interrogando la sezione: {documento_selezionato}")

# 5. CASSELLA DI TESTO LIBERA (CHAT)
st.write("---")
user_input = st.chat_input("Oppure scrivi qui la tua domanda libera...")

if domanda_predefinita:
    domanda_finale = domanda_predefinita
else:
    domanda_finale = user_input

# 6. ELABORAZIONE RISPOSTA AI
if domanda_finale:
    with st.chat_message("user"):
        st.write(domanda_finale)
        
    with st.chat_message("assistant"):
        with st.spinner("Ricerca in corso..."):
            
            if "statuto" in domanda_finale.lower() and "link" not in domanda_finale.lower():
                prompt = f"Rispondi alla domanda usando questo testo dello Statuto di Malnate:\n{TESTO_STATUTO_MALNATE}\n\nDomanda: {domanda_finale}"
                config = types.GenerateContentConfig()
            else:
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
