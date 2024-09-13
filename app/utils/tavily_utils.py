import os
from langchain_community.llms import OpenAI
from langchain_community.retrievers import TavilySearchAPIRetriever
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType
from langchain.tools import BaseTool
from pydantic import Field
from openai import OpenAI as OpenAIClient

# Carica le variabili ambiente dal file .env
load_dotenv()

# Configura l'API di OpenAI e Tavily
openai_api_key = os.getenv("OPENAI_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not openai_api_key or not tavily_api_key:
    raise ValueError("Le chiavi API di OpenAI e Tavily devono essere configurate correttamente.")

# Inizializzazione del client OpenAI
client = OpenAIClient(api_key=openai_api_key)

# Creazione del wrapper personalizzato per TavilySearchAPIRetriever
class TavilySearchTool(BaseTool):
    name = "Tavily Search"
    description = "Useful for searching the internet"
    retriever = TavilySearchAPIRetriever(api_key=tavily_api_key, k=3)
    single_input: bool = Field(True, alias="is_single_input")  # Utilizzo di un alias

    def _run(self, query: str) -> str:
        try:
            return self.retriever.get_relevant_documents(query)[0].page_content
        except IndexError:
            return "Nessun risultato trovato."

tavily_tool = TavilySearchTool()

# Inizializzazione di Chroma con gli embeddings di OpenAI
vectorstore = Chroma(embedding_function=OpenAIEmbeddings(), persist_directory="./chroma_db_oai")

# Inizializzazione del modello di Chat OpenAI
llm = ChatOpenAI(temperature=0)

# Verifica che il tool sia un'istanza valida
print("Tools:", [tavily_tool])

# Inizializza l'agente con il modello e il tool
agent = initialize_agent(
    tools=[tavily_tool],
    agent_type=AgentType.OPENAI_FUNCTIONS,
    llm=llm,
    verbose=True,
)

# Esegui una query tramite l'agente
def run_agent_query(query):
    try:
        result = agent.run(query)
        return result
    except Exception as e:
        raise RuntimeError(f"Errore durante l'esecuzione dell'agente: {str(e)}")

def search_and_scrape(query):
    try:
        results = tavily_tool._run(query)
        return results
    except Exception as e:
        raise RuntimeError(f"Errore durante il retrieval dei dati: {str(e)}")

# Esempio di utilizzo
if __name__ == "__main__":
    query = "What happened in the latest Burning Man floods?"
    result = run_agent_query(query)
    print(result)