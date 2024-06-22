import os
import pandas as pd
from dotenv import load_dotenv
from newsapi import NewsApiClient
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from prefect import task, flow

@task
def load_environment_variables():
    """Load environment variables from .env file and return API keys."""
    load_dotenv()
    news_api_key = os.getenv("NEWS_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not news_api_key or not openai_api_key:
        raise ValueError("API keys are not set in the environment variables")
    return news_api_key, openai_api_key

@task
def fetch_news_articles(api_key: str, query: str, num_articles: int) -> pd.DataFrame:
    """Fetch news articles using the NewsAPI client."""
    newsapi = NewsApiClient(api_key=api_key)
    articles = newsapi.get_everything(q=query, language="en", page_size=num_articles)
    data = [
        {
            "title": article["title"],
            "description": article["description"],
            "author": article.get("author"),
            "url": article.get("url"),
            "urlToImage": article.get("urlToImage"),
            "publishedAt": article.get("publishedAt"),
            "content": article.get("content"),
        }
        for article in articles["articles"]
    ]
    return pd.DataFrame(data)

@task
def store_embeddings_in_chroma(df: pd.DataFrame, openai_api_key: str, chroma_db_path: str, embedding_model_name: str):
    """Store embeddings of news article titles and content in a ChromaDB collection."""
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key, model_name=embedding_model_name
    )
    collection = chroma_client.get_or_create_collection(
        "news_articles", embedding_function=openai_ef
    )
    df = df.drop_duplicates(subset=["url"])
    documents = df["content"].tolist()
    metadata = [
        {"title": title, "url": url} for title, url in zip(df["title"], df["url"])
    ]
    ids = [f"id{i}" for i in range(len(df))]
    collection.add(documents=documents, metadatas=metadata, ids=ids)
    print("------------------- peek -------------------")
    print(collection.peek(1))
    print("------------------- count -------------------")
    print(collection.count())

@flow
def news_embedding_pipeline(news_api_key: str, openai_api_key: str, query_string: str, num_articles: int, chroma_db_path: str, embedding_model_name: str):
    """Main function to orchestrate fetching news articles and storing embeddings."""
    news_articles = fetch_news_articles(news_api_key, query_string, num_articles)
    store_embeddings_in_chroma(news_articles, openai_api_key, chroma_db_path, embedding_model_name)

@flow
def main():
    """Entry point of the script."""
    # Constants
    QUERY_STRING = "technology"
    NUM_ARTICLES = 60
    CHROMA_DB_PATH = "./chroma_db"
    EMBEDDING_MODEL_NAME = "text-embedding-ada-002"

    # Load environment variables
    news_api_key, openai_api_key = load_environment_variables()

    # Run the pipeline
    news_embedding_pipeline(news_api_key, openai_api_key, QUERY_STRING, NUM_ARTICLES, CHROMA_DB_PATH, EMBEDDING_MODEL_NAME)

if __name__ == "__main__":
    main()