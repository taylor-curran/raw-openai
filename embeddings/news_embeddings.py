from datetime import timedelta
from typing import List, Dict
from prefect import flow, task
from prefect.tasks import task_input_hash
from dotenv import load_dotenv
import os
from newsapi import NewsApiClient
import pandas as pd
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import sys
import asyncio

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
news_api_key = os.getenv("NEWS_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
)
def fetch_news_articles(api_key: str, query: str, num_articles: int) -> pd.DataFrame:
    """
    Fetch news articles using the NewsAPI client.

    Args:
        api_key (str): API key for NewsAPI.
        query (str): Query string for searching articles.
        num_articles (int): Number of articles to fetch.

    Returns:
        pd.DataFrame: DataFrame containing fetched articles.
    """
    if not api_key:
        raise ValueError("NEWS_API_KEY environment variable is not set")

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
    df = pd.DataFrame(data)
    return df


@task(cache_expiration=timedelta(days=1))
def create_chroma_collection():
    """
    Create a ChromaDB collection if it doesn't already exist.

    Returns:
        str: Name of the created or existing collection.
    """
    chroma_client = chromadb.Client()
    collection_name = "news_embeddings"

    try:
        chroma_client.get_collection(collection_name)
        print(f"Collection '{collection_name}' already exists.")
    except ValueError:
        chroma_client.create_collection(
            collection_name,
            {
                "title": "str",
                "url": "str",
                "content": "str",
                "title_vector": "vector(1536, cosine)",
                "content_vector": "vector(1536, cosine)",
            },
        )
        print(f"Collection '{collection_name}' created successfully.")

    return collection_name


@task
def store_embeddings_in_chroma(
    df: pd.DataFrame, collection_name: str, openai_api_key: str
):
    """
    Store embeddings of news article titles and content in a ChromaDB collection.

    Args:
        df (pd.DataFrame): DataFrame containing news articles.
        collection_name (str): Name of the ChromaDB collection.
        openai_api_key (str): API key for OpenAI to generate embeddings.
    """
    chroma_client = chromadb.Client()
    collection = chroma_client.get_collection(collection_name)

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key, model_name="text-embedding-ada-002"
    )

    df = df.drop_duplicates(subset=["url"])

    for _, row in df.iterrows():
        doc_id = row["url"]
        title = row["title"]
        content = row["content"]

        title_embedding = openai_ef.embed_with_retries([title])[0]
        content_embedding = openai_ef.embed_with_retries([content])[0]

        metadata = {"title": title, "url": row["url"], "content": content}

        # Upsert title embedding
        collection.upsert(
            ids=[f"{doc_id}_title"], embeddings=[title_embedding], metadatas=[metadata]
        )

        # Upsert content embedding
        collection.upsert(
            ids=[f"{doc_id}_content"],
            embeddings=[content_embedding],
            metadatas=[metadata],
        )

    print(f"Upserted {len(df)} documents to the collection '{collection_name}'.")


@flow(name="News Embedding Pipeline", log_prints=True)
async def news_embedding_pipeline():
    """
    Main flow to orchestrate fetching news articles, creating ChromaDB collection,
    and storing embeddings in the collection.
    """
    news_articles = fetch_news_articles.submit(news_api_key, "technology", 60)
    collection_name = create_chroma_collection.submit()
    store_embeddings_in_chroma.submit(news_articles, collection_name, openai_api_key)


if __name__ == "__main__":
    try:
        asyncio.run(news_embedding_pipeline())
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
