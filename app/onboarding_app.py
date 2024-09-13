import streamlit as st
import time
from utils.openai_utils import generate_content_from_prompt, count_words
from utils.tavily_utils import run_agent_query, search_and_scrape
from dotenv import load_dotenv
import os
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage, BaseMessage, SystemMessage
from components.editing import editing_section
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
import json
import re
import requests

# Carica le variabili ambiente dal file .env
load_dotenv()

# Ottieni le chiavi API
openai_api_key = os.getenv("OPENAI_API_KEY")
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not openai_api_key:
    st.error("La chiave API di OpenAI non è stata trovata.")
    st.stop()

# Inizializzazione dello stato della sessione
if 'uploaded_files' not in st.session_state:
    st.session_state['uploaded_files'] = []
if 'business_plan_sections' not in st.session_state:
    st.session_state['business_plan_sections'] = {}
if 'custom_sections' not in st.session_state:
    st.session_state['custom_sections'] = {}
if 'sections' not in st.session_state:
    st.session_state['sections'] = {}
if 'vector_store' not in st.session_state:
    st.session_state['vector_store'] = None
if 'generated_content' not in st.session_state:
    st.session_state['generated_content'] = {}

# Prompt predefiniti per le sezioni
default_prompts = {
    "Sommario Esecutivo": (
        "Fornisci un sommario esecutivo della tua azienda che includa i seguenti elementi:\n"
        "1. Breve descrizione della tua azienda.\n"
        "2. Prodotti o servizi principali che offri.\n"
        "3. Mercato target a cui ti rivolgi.\n"
        "4. Obiettivi finanziari e principali previsioni di crescita per i prossimi 3 anni."
    ),
    "Analisi di Mercato": (
        "Crea un'analisi di mercato per la tua azienda. Assicurati di rispondere a queste domande:\n"
        "1. Chi sono i tuoi clienti ideali?\n"
        "2. Chi sono i tuoi principali concorrenti e qual è la loro quota di mercato?\n"
        "3. Quali sono le tendenze attuali nel settore che potrebbero influenzare il tuo business?\n"
        "4. Quali opportunità di espansione hai identificato nel mercato?"
    ),
    "Struttura Organizzativa": (
        "Descrivi la struttura organizzativa della tua azienda:\n"
        "1. Quanti dipendenti hai attualmente e quanti prevedi di avere nei prossimi anni?\n"
        "2. Chi sono le figure chiave nella tua azienda e quali sono i loro ruoli?\n"
        "3. Qual è la struttura gerarchica della tua azienda?\n"
        "4. Prevedi di aggiungere nuovi ruoli o modificare la struttura organizzativa?"
    ),
    "Visione e Missione Aziendale": (
        "Descrivi la tua visione e missione aziendale coprendo i seguenti punti:\n"
        "1. Dove vedi la tua azienda nei prossimi 5-10 anni?\n"
        "2. Qual è l'obiettivo primario che la tua azienda sta cercando di raggiungere oggi?\n"
        "3. Quali sono i principi su cui si basa il tuo business?\n"
        "4. Che contributo vuoi dare alla società o al settore in cui operi?"
    ),
    "Descrizione dell'Azienda": (
        "Descrivi la tua azienda considerando i seguenti aspetti:\n"
        "1. Quando e perché è stata fondata la tua azienda?\n"
        "2. In quale settore operi e quali sono le principali attività svolte dalla tua azienda?\n"
        "3. Qual è la forma giuridica della tua azienda (es. SRL, SPA, ecc.)?\n"
        "4. Quali sono i valori che differenziano la tua azienda dalle altre?"
    ),
    "Prodotti o Servizi": (
        "Descrivi i tuoi prodotti o servizi, rispondendo alle seguenti domande:\n"
        "1. Quali prodotti o servizi offri ai tuoi clienti?\n"
        "2. Quali problemi risolvono o quali bisogni soddisfano i tuoi prodotti o servizi?\n"
        "3. Cosa distingue i tuoi prodotti o servizi dalla concorrenza?\n"
        "4. Hai in programma di migliorare o ampliare l'offerta in futuro?"
    ),
    "Piano di Marketing e Vendite": (
        "Definisci il tuo piano di marketing e vendite, tenendo in considerazione:\n"
        "1. Quali strategie utilizzi per attrarre il tuo pubblico target?\n"
        "2. Attraverso quali canali vendi i tuoi prodotti o servizi?\n"
        "3. Come posizioni il tuo prodotto o servizio rispetto alla concorrenza?\n"
        "4. Come intendi acquisire nuovi clienti e mantenere quelli esistenti?"
    )
}

# Funzione per contare le parole
def count_words(text: str) -> int:
    return len(re.findall(r'\w+', text))

# Funzione per la navigazione tra le pagine
def navigate():
    st.sidebar.title("Navigazione")
    # Usa st.session_state per mantenere il valore selezionato
    if 'selected_page' not in st.session_state:
        st.session_state['selected_page'] = "Caricamento Documenti"  # Imposta un valore predefinito

    page = st.sidebar.radio(
        "Vai a", 
        ["Caricamento Documenti", "Gestione Sezioni", "Generazione Contenuti", "Modifica e Miglioramento", "Analisi di Mercato", "Ricerca dei Concorrenti", "Analisi Finanziaria"],
        key="navigation_radio"  # Chiave unica
    )
    
    # Aggiorna lo stato della sessione con la pagina selezionata
    st.session_state['selected_page'] = page
    return page

# Pagina di caricamento dei documenti
def upload_page():
    st.title("Caricamento Documenti")
    
    # Sezione per caricare documenti
    st.subheader("Carica i tuoi documenti")
    uploaded_files = st.file_uploader("Carica documenti (PDF, Word, Excel)", accept_multiple_files=True, type=['pdf', 'docx', 'xlsx'])
    
    # Sezione per inserire un URL
    url_input = st.text_input("Inserisci l'URL per l'analisi di mercato:")
    
    # Sezione per inserire informazioni testuali
    st.subheader("Informazioni Testuali per il Business Plan")
    business_info = st.text_area("Inserisci le informazioni testuali che desideri includere nel business plan:", height=200)
    
    if st.button("Salva Informazioni"):
        if business_info:
            st.session_state['business_plan_info'] = business_info
            st.success("Informazioni salvate con successo!")
        else:
            st.warning("Per favore, inserisci delle informazioni testuali.")

    # Sezione per inserire domande
    st.subheader("Domande per la Generazione del Business Plan")
    questions = [
        "Qual è il tuo obiettivo principale per questo business plan?",
        "Chi è il tuo pubblico target?",
        "Quali sono i tuoi principali concorrenti?",
        "Quali sono i punti di forza del tuo prodotto/servizio?",
        "Qual è la tua strategia di marketing?",
        "Quali sono le tue aspettative finanziarie?",
        "Qual è il tuo piano di crescita a lungo termine?",
        "Come intendi affrontare i rischi del mercato?",
        "Quali canali utilizzerai per la distribuzione?",
        "Qual è la tua proposta di valore unica?"
    ]
    
    answers = {}
    for question in questions:
        answer = st.text_input(question)
        if answer:
            answers[question] = answer

    if st.button("Salva Risposte"):
        if answers:
            st.session_state['business_plan_answers'] = answers
            st.success("Risposte salvate con successo!")
        else:
            st.warning("Per favore, rispondi a almeno una domanda.")

    # Mostra le risposte salvate, se presenti
    if 'business_plan_answers' in st.session_state:
        st.subheader("Risposte Salvate")
        for q, a in st.session_state['business_plan_answers'].items():
            st.write(f"{q}: {a}")

    if uploaded_files:
        st.session_state['uploaded_files'].extend(uploaded_files)

    st.write("Documenti e URL caricati:")
    st.write(st.session_state['uploaded_files'])

    # Caricamento dei documenti dal sito
    if url_input:
        loader = WebBaseLoader(url_input)
        docs = loader.load()

        # Dividere i documenti in frammenti
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)

        # Creare un vector store per memorizzare i frammenti
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.from_documents(splits, embeddings)
        st.session_state['vector_store'] = vector_store

# Pagina di gestione delle sezioni
def manage_sections_page():
    st.header("Gestione delle Sezioni del Business Plan")
    
    # Selezione delle sezioni predefinite
    selected_section = st.selectbox("Scegli le sezioni predefinite", list(default_prompts.keys()))

    # Prompt predefinito per la sezione selezionata
    if selected_section:
        # Carichiamo il prompt dall'archivio della sessione o usiamo quello di default
        if selected_section not in st.session_state['sections']:
            st.session_state['sections'][selected_section] = default_prompts[selected_section]
        
        # Mostra il prompt attuale e consenti la modifica
        st.subheader(f"Prompt per la sezione: {selected_section}")
        prompt = st.text_area("Modifica il prompt per questa sezione", value=st.session_state['sections'][selected_section], height=150)

        # Salva il prompt modificato
        if st.button(f"Salva Prompt per {selected_section}"):
            st.session_state['sections'][selected_section] = prompt
            st.success(f"Prompt per la sezione '{selected_section}' salvato con successo!")
        
        # Ripristina il prompt predefinito
        if st.button(f"Ripristina Prompt Predefinito per {selected_section}"):
            st.session_state['sections'][selected_section] = default_prompts[selected_section]
            st.success(f"Prompt per la sezione '{selected_section}' ripristinato al predefinito!")

    # Elenco delle sezioni aggiunte e modificate
    st.subheader("Sezioni Personalizzate e i loro Prompt")
    if st.session_state['sections']:
        for section, prompt in st.session_state['sections'].items():
            st.write(f"**{section}**: {prompt}")

# Pagina di generazione dei contenuti
def generate_section_page():
    st.header("Generazione delle Sezioni del Business Plan")
    
    if not st.session_state['sections']:
        st.warning("Non ci sono sezioni definite. Vai alla pagina 'Gestione Sezioni' per aggiungere sezioni.")
        return
    
    selected_section = st.selectbox("Seleziona la sezione da generare", list(st.session_state['sections'].keys()) + ["Analisi di Mercato e Concorrenza"])
    
    if selected_section == "Analisi di Mercato e Concorrenza":
        initial_prompt = "Crea un'analisi di mercato e della concorrenza dettagliata per un'azienda nel settore della tecnologia, includendo tendenze di mercato, analisi dei concorrenti e opportunità di crescita."
        target_words = st.number_input("Numero target di parole", min_value=500, max_value=2000, value=500)
        
        if st.button("Genera contenuto per Analisi di Mercato e Concorrenza"):
            generated_content, final_word_count = generate_and_refine_content(initial_prompt, target_words)
            st.session_state['business_plan_sections'][selected_section] = generated_content
            st.success(f"Contenuto generato con successo! ({final_word_count} parole)")
            st.text_area("Contenuto generato", value=generated_content, height=300)
    else:
        prompt = st.text_area("Modifica il prompt per la generazione", value=st.session_state['sections'][selected_section])
        target_words = st.number_input("Numero target di parole", min_value=1, max_value=1000, value=1000)
        
        if st.button("Genera contenuto per " + selected_section):
            generated_content = generate_content_from_prompt(prompt)
            st.session_state['business_plan_sections'][selected_section] = generated_content
            st.success(f"Contenuto generato con successo! ({count_words(generated_content)} parole)")
            st.text_area("Contenuto generato", value=generated_content, height=300)

# Pagina di modifica e miglioramento
def editing_section():
    st.subheader("Modifica e Miglioramento delle Sezioni")
    
    if 'business_plan_sections' not in st.session_state:
        st.warning("Non ci sono sezioni da modificare. Genera prima il contenuto nella sezione 'Generazione Contenuti'.")
        return
    
    for section, content in st.session_state['business_plan_sections'].items():
        st.subheader(section)
        
        # Mostra il contenuto attuale
        st.text_area(f"Contenuto attuale per {section}", value=content, height=200, disabled=True)
        
        # Area di testo per la modifica
        edited_content = st.text_area(f"Modifica il contenuto per {section}", value=content, height=200)
        
        # Mostra il numero di parole attuali
        current_word_count = count_words(edited_content)
        st.write(f"Numero di parole attuali: {current_word_count}")

        # Richiesta di modifica
        modification_request = st.text_input(f"Richiesta di modifica per {section}", placeholder="Cosa vuoi modificare?")

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"Rigenera Contenuto per {section}") and modification_request:
                prompt = f"Modifica il seguente contenuto in base alla richiesta: '{modification_request}'.\n\nContenuto attuale:\n{edited_content}"
                new_content = generate_content_from_prompt(prompt)
                st.session_state['business_plan_sections'][section] = new_content
                st.success(f"Contenuto modificato per {section}")
                st.text_area(f"Contenuto modificato per {section}", value=new_content, height=200)

        with col2:
            if st.button(f"Salva Modifiche per {section}"):
                st.session_state['business_plan_sections'][section] = edited_content
                st.success(f"Modifiche salvate per {section}")

# Funzione per chiamare l'API di Perplexity
def call_perplexity_api(query):
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {perplexity_api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'llama-3.1-sonar-small-128k-online',
        'messages': [
            {"role": "system", "content": "Fornisci un'analisi dettagliata e approfondita."},
            {"role": "user", "content": query}
        ],
        'max_tokens': 4000  # Aumenta il numero massimo di token
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"Error occurred: {req_err}")
    except json.JSONDecodeError as json_err:
        st.error(f"JSON decode error: {json_err}")
    
    return {}

def format_analysis_output(analysis):
    formatted_output = ""
    if 'choices' in analysis:
        for choice in analysis['choices']:
            formatted_output += f"### {choice['message']['role'].capitalize()}\n"
            formatted_output += f"{choice['message']['content']}\n\n"
    return formatted_output

# Funzione per chiamare l'API di Tavily
def call_tavily_api(query):
    url = 'https://api.tavily.com/search'
    headers = {
        'Authorization': f'Bearer {tavily_api_key}',
        'Content-Type': 'application/json'
    }
    
    # Limita la lunghezza della query a 400 caratteri
    truncated_query = query[:400]
    
    data = {
        'query': truncated_query,
        'search_depth': 'advanced',
        'max_results': 10,
        'include_answer': True,
        'include_images': False,
        'include_raw_content': True,
        'api_key': tavily_api_key
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        st.error(f"Errore HTTP: {http_err}")
        st.error(f"Dettagli della risposta: {response.text}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"Errore nella richiesta: {req_err}")
    
    return {}

def financial_analysis_page():
    st.header("Analisi Finanziaria")

    # Controlla se ci sono informazioni finanziarie salvate
    if 'business_plan_info' not in st.session_state:
        st.warning("Non ci sono informazioni finanziarie disponibili. Carica prima i dati nella pagina 'Caricamento Documenti'.")
        return

    # Richiesta di analisi
    st.subheader("Genera Documenti Finanziari")
    
    # Selezione degli anni di previsione
    years = st.number_input("Inserisci il numero di anni di previsione", min_value=1, max_value=10, value=3)
    
    # Blocco di testo per eventuali modifiche
    modifications = st.text_area("Specificare eventuali modifiche o note:", height=100)

    # Input per i bilanci degli anni precedenti
    st.write("### Bilanci Anni Precedenti")
    previous_years_data = {}
    for i in range(1, years + 1):
        st.subheader(f"Anno {i}")
        previous_years_data[i] = {
            "sales_revenue": st.number_input(f"Ricavi delle vendite e delle prestazioni (Anno {i})", min_value=0.0, format="%.2f"),
            "costs": st.number_input(f"Costi totali (Anno {i})", min_value=0.0, format="%.2f"),
            "net_result": st.number_input(f"Utile (perdite) dell'esercizio (Anno {i})", min_value=0.0, format="%.2f"),
        }

    # A) Valore della produzione
    st.write("### A) Valore della Produzione")
    sales_revenue = st.number_input("1) Ricavi delle vendite e delle prestazioni", min_value=0.0, format="%.2f")
    inventory_variations = st.number_input("2) Variazioni delle rimanenze", min_value=0.0, format="%.2f")
    work_in_progress_variations = st.number_input("3) Variazioni dei lavori in corso su ordinazione", min_value=0.0, format="%.2f")
    internal_works_increases = st.number_input("4) Incrementi di immobilizzazioni per lavori interni", min_value=0.0, format="%.2f")
    other_revenues = st.number_input("5) Altri ricavi e proventi", min_value=0.0, format="%.2f")

    total_production_value = sales_revenue + inventory_variations + work_in_progress_variations + internal_works_increases + other_revenues
    st.write(f"**Totale Valore della Produzione: {total_production_value:.2f}**")

    # B) Costi della produzione
    st.write("### B) Costi della Produzione")
    raw_materials_cost = st.number_input("6) Costi per materie prime", min_value=0.0, format="%.2f")
    services_cost = st.number_input("7) Costi per servizi", min_value=0.0, format="%.2f")
    lease_cost = st.number_input("8) Costi per godimento di beni di terzi", min_value=0.0, format="%.2f")
    
    # Costi per il personale
    st.write("9) Costi per il personale")
    salaries = st.number_input("a) Salari e stipendi", min_value=0.0, format="%.2f")
    social_charges = st.number_input("b) Oneri sociali", min_value=0.0, format="%.2f")
    severance_pay = st.number_input("c) Trattamento di fine rapporto", min_value=0.0, format="%.2f")
    retirement_pay = st.number_input("d) Trattamento di quiescenza e simili", min_value=0.0, format="%.2f")
    other_personnel_costs = st.number_input("e) Altri costi", min_value=0.0, format="%.2f")

    total_personnel_costs = salaries + social_charges + severance_pay + retirement_pay + other_personnel_costs

    # Ammortamenti e svalutazioni
    st.write("10) Ammortamenti e svalutazioni")
    intangible_amortization = st.number_input("a) Ammortamento delle immobilizzazioni immateriali", min_value=0.0, format="%.2f")
    tangible_amortization = st.number_input("b) Ammortamento delle immobilizzazioni materiali", min_value=0.0, format="%.2f")
    other_depreciations = st.number_input("c) Altre svalutazioni delle immobilizzazioni", min_value=0.0, format="%.2f")
    credit_depreciations = st.number_input("d) Svalutazioni dei crediti", min_value=0.0, format="%.2f")

    total_depreciations = intangible_amortization + tangible_amortization + other_depreciations + credit_depreciations

    # Altri costi
    inventory_variations_cost = st.number_input("11) Variazioni delle rimanenze di materie prime", min_value=0.0, format="%.2f")
    risk_provisions = st.number_input("12) Accantonamenti per rischi", min_value=0.0, format="%.2f")
    other_provisions = st.number_input("13) Altri accantonamenti", min_value=0.0, format="%.2f")
    other_management_costs = st.number_input("14) Oneri diversi di gestione", min_value=0.0, format="%.2f")

    total_costs = (raw_materials_cost + services_cost + lease_cost + total_personnel_costs +
                   total_depreciations + inventory_variations_cost + risk_provisions +
                   other_provisions + other_management_costs)

    st.write(f"**Totale Costi della Produzione: {total_costs:.2f}**")
    production_difference = total_production_value - total_costs
    st.write(f"**Differenza tra valore e costi della produzione (A - B): {production_difference:.2f}**")

    # C) Proventi e oneri finanziari
    st.write("### C) Proventi e Oneri Finanziari")
    financial_income = st.number_input("15) Proventi da partecipazioni", min_value=0.0, format="%.2f")
    other_financial_income = st.number_input("16) Altri proventi finanziari", min_value=0.0, format="%.2f")
    financial_expenses = st.number_input("17) Oneri finanziari", min_value=0.0, format="%.2f")

    total_financial = financial_income + other_financial_income - financial_expenses
    st.write(f"**Totale Proventi e Oneri Finanziari: {total_financial:.2f}**")

    # D) Rettifiche di valore di attività e passività finanziarie
    st.write("### D) Rettifiche di valore di attività e passività finanziarie")
    revaluations = st.number_input("18) Rivalutazioni", min_value=0.0, format="%.2f")
    depreciations = st.number_input("19) Svalutazioni", min_value=0.0, format="%.2f")

    total_adjustments = revaluations - depreciations
    st.write(f"**Totale Rettifiche: {total_adjustments:.2f}**")

    # Risultato prima delle imposte
    result_before_taxes = production_difference + total_financial + total_adjustments
    st.write(f"**Risultato prima delle imposte: {result_before_taxes:.2f}**")

    # Imposte sul reddito
    taxes = st.number_input("20) Imposte sul reddito dell'esercizio", min_value=0.0, format="%.2f")
    net_result = result_before_taxes - taxes
    st.write(f"**Utile (perdite) dell'esercizio: {net_result:.2f}**")

    # Rendiconto Finanziario
    st.write("### Rendiconto Finanziario")
    operating_cash_flows = st.number_input("Flussi di cassa dalle attività operative", min_value=0.0, format="%.2f")
    investing_cash_flows = st.number_input("Flussi di cassa dalle attività di investimento", min_value=0.0, format="%.2f")
    financing_cash_flows = st.number_input("Flussi di cassa dalle attività di finanziamento", min_value=0.0, format="%.2f")

    if st.button("Genera Rendiconto Finanziario"):
        net_cash_flow = operating_cash_flows + investing_cash_flows + financing_cash_flows
        st.write(f"**Variazione netta di cassa: {net_cash_flow:.2f}**")

# Aggiorna la funzione di navigazione per includere la nuova pagina
def navigate():
    st.sidebar.title("Navigazione")
    if 'selected_page' not in st.session_state:
        st.session_state['selected_page'] = "Caricamento Documenti"  # Imposta un valore predefinito

    page = st.sidebar.radio(
        "Vai a", 
        ["Caricamento Documenti", "Gestione Sezioni", "Generazione Contenuti", "Modifica e Miglioramento", "Analisi di Mercato", "Ricerca dei Concorrenti", "Analisi Finanziaria"],
        key="navigation_radio"  # Chiave unica
    )
    
    st.session_state['selected_page'] = page
    return page

# Aggiorna la funzione main per gestire la nuova pagina
def main():
    page = navigate()
    
    if page == "Caricamento Documenti":
        upload_page()
    elif page == "Gestione Sezioni":
        manage_sections_page()
    elif page == "Generazione Contenuti":
        generate_section_page()
    elif page == "Modifica e Miglioramento":
        editing_section()
    elif page == "Analisi di Mercato":
        market_analysis_page()
    elif page == "Ricerca dei Concorrenti":
        competitor_analysis_page()
    elif page == "Analisi Finanziaria":  # Nuova pagina
        financial_analysis_page()

if __name__ == "__main__":
    main()