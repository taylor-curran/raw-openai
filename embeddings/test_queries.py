import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL_NAME = "text-embedding-ada-002" 
CHROMA_DB_PATH = "./chroma_db" 

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Define the embedding function using OpenAI
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY, model_name=EMBEDDING_MODEL_NAME
)


collection = chroma_client.get_or_create_collection(
        "news_articles", embedding_function=openai_ef
    )

results = collection.query(
    query_texts=["Show me articles about smartphones"], # Chroma will embed this for you
    n_results=2 # how many results to return
)
print(results)
