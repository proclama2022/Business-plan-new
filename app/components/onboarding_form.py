import streamlit as st
import re

def onboarding_form():
    st.header("Informazioni Aziendali")
    st.write("Questa applicazione ti guiderà attraverso il processo di onboarding e raccolta dati.")

    company_name = st.text_input("Nome Azienda")
    industry = st.text_input("Settore")

    # Validazione dell'URL
    website_url = st.text_input("URL del Sito Web")
    if website_url:
        if not re.match(r"https?://(?:www\.)?[\w-]+(?:\.[a-z]{2,})+(?:/[\w-./?%&=]*)?", website_url):
            st.warning("Inserisci un URL valido.")

    uploaded_files = st.file_uploader("Carica documenti (PDF, Word, Excel)", accept_multiple_files=True, type=['pdf', 'docx', 'xlsx'])
    social_links = st.text_area("Collegamenti ai profili social (separati da virgola)")

    # Validazione del logo
    logo = st.file_uploader("Carica il logo aziendale", type=['jpg', 'png'])
    if logo:
        if logo.size > 1024 * 1024:  # Limite di 1 MB
            st.warning("Il logo è troppo grande. Il limite massimo è 1 MB.")

    # Prompt strutturati
    st.header("Sommario Esecutivo")
    st.write("Fornisci un sommario esecutivo della tua azienda che includa:")
    st.text_input("Breve descrizione della tua azienda:")
    st.text_input("Prodotti o servizi principali che offri:")
    st.text_input("Mercato target a cui ti rivolgi:")
    st.text_input("Obiettivi finanziari e principali previsioni di crescita per i prossimi 3 anni:")

    st.header("Visione e Missione Aziendale")
    st.write("Descrivi la tua visione e missione aziendale:")
    st.text_input("Visione a lungo termine:")
    st.text_input("Missione attuale:")
    st.text_input("Valori fondamentali:")
    st.text_input("Impatto sociale o industriale:")

    st.header("Descrizione dell'Azienda")
    st.write("Descrivi la tua azienda considerando i seguenti aspetti:")
    st.text_input("Storia aziendale:")
    st.text_input("Settore e attività:")
    st.text_input("Struttura legale:")
    st.text_input("Valori distintivi:")

    st.header("Analisi di Mercato")
    st.write("Crea un'analisi di mercato per la tua azienda. Assicurati di rispondere a queste domande:")
    st.text_input("Target di mercato:")
    st.text_input("Concorrenti principali:")
    st.text_input("Tendenze di settore:")
    st.text_input("Opportunità di crescita:")

    # Aggiungi qui le altre sezioni come Prodotti o Servizi, Piano di Marketing e Vendite, ecc.

    if st.button("Invia"):
        if company_name and industry and website_url and re.match(r"https?://(?:www\.)?[\w-]+(?:\.[a-z]{2,})+(?:/[\w-./?%&=]*)?", website_url):
            st.success("Dati inviati con successo!")
        else:
            st.error("Per favore, compila tutti i campi correttamente.")