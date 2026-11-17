import streamlit as st
import os
from google import genai
from google.genai import types
from pypdf import PdfReader

# 1. CONFIGURAZIONE PAGINA WEB
st.set_page_config(page_title="Assistente Civico - Malnate", page_icon="🏛️", layout="wide")
st.title("🏛️ Assistente Civico Digitale - Comune di Malnate")
st.write("Interroga direttamente gli atti, i regolamenti e i verbali ufficiali del Comune.")

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

# 4. BARRA LATERALE SINISTRA: SELEZIONE DIRETTA DEL DOCUMENTO
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
                    except Exception as e:
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            st.warning("⏳ L'assistente è momentaneamente occupato a causa dell'alto numero di richieste. Attendi un minuto e riprova.")
                        else:
                            st.error("Si è verificato un errore temporaneo di connessione. Riprova tra poco.")
                else:
                    st.error("Impossibile leggere il contenuto di questo file PDF.")
else:
    st.info("Carica almeno un file PDF su GitHub per iniziare a usare l'assistente.")
