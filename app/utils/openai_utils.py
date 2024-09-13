import os
import streamlit as st  # Aggiungi questa riga
from openai import OpenAI
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from langchain_core.messages import HumanMessage  # Modifica qui

# Carica le variabili ambiente dal file .env
load_dotenv()

# Ottieni la chiave API di OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")

# Verifica che la chiave API sia stata trovata
if not openai_api_key:
    raise ValueError("La chiave API di OpenAI non è stata trovata. Assicurati di averla impostata correttamente nel file .env.")

# Inizializza il client OpenAI
client = OpenAI(api_key=openai_api_key)

def generate_content_from_prompt(prompt_or_state, max_tokens=4096):
    try:
        if isinstance(prompt_or_state, dict):
            prompt = prompt_or_state["prompt"]
        else:
            prompt = prompt_or_state

        # Suddividi il prompt in parti più piccole se necessario
        max_prompt_tokens = 4000  # Lascia spazio per la risposta
        prompt_parts = split_prompt(prompt, max_prompt_tokens)
        
        full_response = ""
        for part in prompt_parts:
            messages = [{"role": "user", "content": part}]
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=max_tokens,
            )
            full_response += response.choices[0].message.content + "\n\n"

        return full_response.strip()
    except Exception as e:
        st.error(f"Errore durante la generazione del contenuto: {e}")
        return ""

def split_prompt(prompt, max_tokens):
    words = prompt.split()
    parts = []
    current_part = []
    current_tokens = 0

    for word in words:
        word_tokens = len(word) // 4 + 1  # Stima approssimativa
        if current_tokens + word_tokens > max_tokens:
            parts.append(" ".join(current_part))
            current_part = [word]
            current_tokens = word_tokens
        else:
            current_part.append(word)
            current_tokens += word_tokens

    if current_part:
        parts.append(" ".join(current_part))

    return parts

def count_words(text):
    return len(text.split())

def generate_and_refine_content(initial_prompt, target_words=1000, tolerance=100):
    llm = ChatOpenAI(temperature=0.7)
    
    generate_prompt = ChatPromptTemplate.from_template(
        "Genera un contenuto di circa {target_words} parole sul seguente argomento:\n\n{topic}"
    )
    generate_chain = LLMChain(llm=llm, prompt=generate_prompt)
    
    refine_prompt = ChatPromptTemplate.from_template(
        "Il seguente contenuto ha {current_words} parole, ma dovrebbe averne circa {target_words}. "
        "Per favore, {action} il contenuto mantenendo le informazioni chiave:\n\n{content}"
    )
    refine_chain = LLMChain(llm=llm, prompt=refine_prompt)
    
    with get_openai_callback() as cb:
        content = generate_chain.run(topic=initial_prompt, target_words=target_words)
        word_count = count_words(content)
        
        iterations = 0
        max_iterations = 3  # Limita il numero di iterazioni per evitare loop infiniti
        
        while abs(word_count - target_words) > tolerance and iterations < max_iterations:
            action = "espandi" if word_count < target_words else "riduci"
            content = refine_chain.run(
                content=content, 
                current_words=word_count, 
                target_words=target_words, 
                action=action
            )
            word_count = count_words(content)
            iterations += 1
        
        print(f"Numero totale di token utilizzati: {cb.total_tokens}")
        print(f"Costo totale in USD: ${cb.total_cost}")
    
    return content, word_count

# Esempio di utilizzo
initial_prompt = "Scrivi un sommario esecutivo per un'azienda di tecnologia che si occupa di intelligenza artificiale"
content, final_word_count = generate_and_refine_content(initial_prompt)

print(f"\nContenuto generato ({final_word_count} parole):")
print(content)
