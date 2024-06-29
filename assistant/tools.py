# tools.py
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import os
import json


class ChromaNewsDatabase:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model_name = "text-embedding-ada-002"
        self.chroma_db_path = "./chroma_db"

        self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_path)
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key, model_name=self.embedding_model_name
        )
        self.collection = self.chroma_client.get_or_create_collection(
            "news_articles", embedding_function=self.openai_ef
        )

    def query_news(self, query_text, n_results=5):
        results = self.collection.query(query_texts=[query_text], n_results=n_results)
        return results


def query_tech_news(query: str, num_results: int = 5) -> str:
    news_db = ChromaNewsDatabase()
    results = news_db.query_news(query, n_results=num_results)

    # Format the results as a JSON string
    formatted_results = []
    for i, (doc, score) in enumerate(
        zip(results["documents"][0], results["distances"][0])
    ):
        formatted_results.append({"article": doc, "relevance_score": score})

    return json.dumps(formatted_results)
