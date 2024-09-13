import streamlit as st
from utils.openai_utils import generate_content
from utils.tavily_utils import search_and_scrape

def business_plan_sections():
    sections = [
        "Sommario esecutivo",
        "Visione e missione aziendale",
        "Descrizione dell'azienda",
        "Analisi di mercato",
        "Prodotti o servizi",
        "Piano di marketing e vendita",
        "Struttura organizzativa e gestione",
        "Piano operativo",
        "Piano finanziario",
        "Milestones e tempistiche",
        "Analisi dei rischi e piano di mitigazione"
    ]

    st.subheader("Generazione delle Sezioni del Business Plan")
    for section in sections:
        st.write(f"### {section}")
        
        if section == "Sommario esecutivo":
            st.text_area("Fornisci un sommario esecutivo della tua azienda che includa:", height=100)
            st.text_input("Breve descrizione della tua azienda:")
            st.text_input("Prodotti o servizi principali che offri:")
            st.text_input("Mercato target a cui ti rivolgi:")
            st.text_input("Obiettivi finanziari e principali previsioni di crescita per i prossimi 3 anni:")
        
        elif section == "Visione e missione aziendale":
            st.text_area("Descrivi la tua visione e missione aziendale:", height=100)
            st.text_input("Visione a lungo termine:")
            st.text_input("Missione attuale:")
            st.text_input("Valori fondamentali:")
            st.text_input("Impatto sociale o industriale:")
        
        # Aggiungi qui le altre sezioni seguendo lo stesso schema...

        if st.button(f"Rigenera {section}"):
            prompt = f"Genera una sezione del business plan per {section} con i seguenti dettagli: {section_content}"
            generated_section = generate_content(prompt)
            st.write(generated_section)
        
        search_query = st.text_input(f"Ricerca con Tavily per {section}")
        if st.button(f"Ricerca e Scraping per {section}"):
            search_results = search_and_scrape(search_query)
            st.write(search_results)

def generate_section_page():
    st.header("Generazione delle Sezioni del Business Plan")
    
    if not st.session_state['sections']:
        st.warning("Non ci sono sezioni definite. Vai alla pagina 'Gestione Sezioni' per aggiungere sezioni.")
        return
    
    selected_section = st.selectbox("Seleziona la sezione da generare", list(st.session_state['sections'].keys()))
    
    prompt = st.text_area("Modifica il prompt per la generazione", value=st.session_state['sections'][selected_section])
    
    target_words = st.number_input("Numero target di parole", min_value=1, max_value=1000, value=1000)
    
    if st.button("Genera contenuto per " + selected_section):
        generated_content = generate_content_from_prompt(prompt)
        st.session_state['business_plan_sections'][selected_section] = generated_content
        st.success(f"Contenuto generato con successo! ({count_words(generated_content)} parole)")
        st.text_area("Contenuto generato", value=generated_content, height=300)