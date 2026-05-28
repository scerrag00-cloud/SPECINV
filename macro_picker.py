import os
import requests
import json
import datetime
import google.generativeai as genai

# --- CHIAVI SEGRETE (DA INSERIRE SU GITHUB SECRETS) ---
news_api_key = os.environ.get("NEWS_API_KEY")
fred_api_key = os.environ.get("FRED_API_KEY")
telegram_token = os.environ.get("TELEGRAM_TOKEN")
telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
gemini_api_key = os.environ.get("GEMINI_API_KEY") 

# --- CONFIGURAZIONE GEMINI ---
genai.configure(api_key=gemini_api_key)
# Sintassi corretta in minuscolo
model = genai.GenerativeModel('gemini-3.1-flash-lite')

def scarica_top_news(chiave_api):
    query = "(\"interest rates\" OR \"inflation\" OR \"global economy\" OR \"tech sector\" OR \"geopolitics\")"
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=10&apiKey={chiave_api}"
    try:
        risposta = requests.get(url).json()
        if risposta.get('status') != 'ok': return "Errore download notizie."
        articles = risposta.get('articles', [])
        return "\n".join([f"- {art['title']}" for art in articles if art.get('title')])
    except Exception:
        return "Errore connessione NewsAPI."

def preleva_fred(serie, chiave):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={serie}&api_key={chiave}&file_type=json&sort_order=desc&limit=1"
    try:
        risposta = requests.get(url).json()
        valore = risposta['observations'][0]['value']
        data = risposta['observations'][0]['date']
        return f"{valore}% (Ultimo aggiornamento: {data})"
    except Exception:
        return "Dato non disponibile."

def invia_telegram(testo):
    if not telegram_token or not telegram_chat_id: return
    # Telegram ha un limite di lunghezza, lo spezziamo se troppo lungo
    if len(testo) > 4000:
        testo = testo[:3900] + "\n\n[...Testo tagliato per limiti di spazio]"
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": telegram_chat_id, "text": testo, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# 1. RACCOLTA DATI
print("Raccolta notizie...")
testo_notizie = scarica_top_news(news_api_key)

print("Raccolta dati macro...")
if fred_api_key:
    tasso_disoccupazione = preleva_fred('UNRATE', fred_api_key)
    inflazione = preleva_fred('CPIAUCSL', fred_api_key)
else:
    tasso_disoccupazione = "Non disponibile"
    inflazione = "Non disponibile"

# 2. COSTRUZIONE DEL PROMPT DINAMICO
prompt_ottimizzato = f"""
Agisci come un analista azionario quantitativo e un gestore di portafoglio macro-driven. Il tuo compito è analizzare una serie di eventi macroeconomici globali di OGGI e dedurre quali specifiche aziende quotate nell'indice S&P 500 potrebbero subirne un impatto diretto sui prezzi nel breve/medio termine.

A seguito dell'analisi di questi dati, non limitarti a fornirmi previsioni su interi settori. Voglio che tu estragga i nomi di **massimo 3 specifiche aziende** che subiranno le conseguenze (positive o negative) maggiori di questi eventi.

Per ogni azienda individuata, restituiscimi l'analisi utilizzando esattamente questa struttura:

* **Azienda e Ticker:** (es. NVIDIA Corporation - NVDA)
* **Direzione Prevista:** (Rialzo 📈 o Ribasso 📉)
* **Catalizzatore (La Notizia):** (Quale specifica notizia tra quelle fornite ha innescato la tua scelta)
* **Il Razionale Economico:** (Spiega oggettivamente e in massimo 3 righe perché questa notizia impatta il bilancio o i ricavi di questa azienda).

Regole di ingaggio:
Sii estremamente oggettivo. Seleziona solo i titoli per i quali il nesso causa-effetto tra l'evento e il business dell'azienda è forte ed evidente. Non inserire disclaimer generici alla fine, mantieni il testo pulito.

--- DATI DA ANALIZZARE OGGI ({datetime.date.today().strftime("%Y-%m-%d")}) ---

🔴 ULTIME NOTIZIE GLOBALI:
{testo_notizie}

🔴 DATI MACROECONOMICI (USA):
- Tasso di Disoccupazione (UNRATE): {tasso_disoccupazione}
- Indice dei Prezzi al Consumo (CPI): {inflazione}
"""

# 3. INTERROGAZIONE DELL'IA (GEMINI)
print("Invio dati a Gemini per l'analisi...")
try:
    response = model.generate_content(prompt_ottimizzato)
    analisi_ia = response.text
except Exception as e:
    analisi_ia = f"❌ Errore durante la generazione dell'analisi con Gemini: {str(e)}"

# 4. IMPACCHETTAMENTO E INVIO
messaggio_finale = (
    f"🤖 *Macro-Stock Picker AI*\n"
    f"📅 *Report del {datetime.date.today().strftime('%d/%m/%Y')}*\n\n"
    f"{analisi_ia}\n\n"
    f"---\n"
    f"📊 *Dati analizzati dal bot:*\n"
    f"• 10 Top News Globali\n"
    f"• Disoccupazione USA: {tasso_disoccupazione}"
)

print("Invio report su Telegram...")
invia_telegram(messaggio_finale)
print("Processo completato.")
