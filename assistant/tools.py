import requests

chroma_db_url = "http://localhost:8000"  # Replace with your ChromaDB URL

# TODO: Add type hints


# Function to query ChromaDB
def query_chroma_db(
    query_texts=None,
    query_embeddings=None,
    n_results=10,
    where=None,
    where_document=None,
    include=None,
):
    payload = {
        "n_results": n_results,
    }

    if query_texts:
        payload["query_texts"] = query_texts
    if query_embeddings:
        payload["query_embeddings"] = query_embeddings
    if where:
        payload["where"] = where
    if where_document:
        payload["where_document"] = where_document
    if include:
        payload["include"] = include

    response = requests.post(f"{chroma_db_url}/query", json=payload)
    response.raise_for_status()
    return response.json()


# Custom tool definition
class TechNewsDBTool:
    def __init__(self):
        self.name = "tech_news_db_tool"
        self.description = (
            "Tool for querying the ChromaDB filled with technology news articles."
        )

    def execute(
        self,
        query_texts=None,
        query_embeddings=None,
        n_results=10,
        where=None,
        where_document=None,
        include=None,
    ):
        return query_chroma_db(
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
        )
