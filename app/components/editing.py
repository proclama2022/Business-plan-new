import streamlit as st
from utils.openai_utils import generate_content_from_prompt, count_words

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

def add_editing_section(app):
    app.add_page("Modifica e Miglioramento", editing_section)