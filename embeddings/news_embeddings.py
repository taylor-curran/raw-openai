from datetime import timedelta
from typing import List, Dict
from prefect import flow, task
from prefect.tasks import task_input_hash
from dotenv import load_dotenv
import os
from newsapi import NewsApiClient
import asyncio
import pandas as pd
import chromadb
import chromadb.utils.embedding_functions as embedding_functions


# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
news_api_key = os.getenv("NEWS_API_KEY")


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
)
def fetch_news_articles(api_key: str, query: str, num_articles: int) -> pd.DataFrame:
    """
    Fetch news articles using the NewsAPI.

    Args:
        api_key (str): The NewsAPI key.
        query (str): The search query.
        num_articles (int): Number of articles to fetch.

    Returns:
        pd.DataFrame: DataFrame containing the fetched articles.
    """
    # Check if the News API key is loaded correctly
    if not api_key:
        raise ValueError("NEWS_API_KEY environment variable is not set")

    newsapi = NewsApiClient(api_key=api_key)
    articles = newsapi.get_everything(q=query, language="en", page_size=num_articles)

    # Convert articles to DataFrame
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
    chroma_client = chromadb.Client()
    collection_name = "news_embeddings"

    try:
        # Check if the collection already exists
        chroma_client.get_collection(collection_name)
        print(f"Collection '{collection_name}' already exists.")
    except ValueError:
        # Create the schema in Chroma DB if collection does not exist
        chroma_client.create_collection(collection_name, {
            "title": "str",
            "url": "str",
            "content": "str",
            "title_vector": "vector(1536, cosine)",
            "content_vector": "vector(1536, cosine)"
        })
        print(f"Collection '{collection_name}' created successfully.")

    return collection_name

@task
def store_embeddings_in_chroma(df: pd.DataFrame, collection_name: str):
    chroma_client = chromadb.Client()
    collection = chroma_client.get_collection(collection_name)
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(api_key=openai_api_key, model_name="text-embedding-ada-002")

    ids = []
    metadata = []
    title_vectors = []
    content_vectors = []

    for _, row in df.iterrows():
        doc_id = row['url']
        ids.append(doc_id)
        
        title = row['title']
        content = row['content']

        title_embedding = openai_ef.embed_with_retries([title])[0]
        content_embedding = openai_ef.embed_with_retries([content])[0]

        metadata.append({
            "title": title,
            "url": row['url'],
            "content": content
        })
        title_vectors.append(title_embedding)
        content_vectors.append(content_embedding)

    collection.upsert(
        ids=ids,
        embeddings=[title_vectors, content_vectors],
        metadatas=metadata
    )

@flow(name="News Embedding Pipeline", log_prints=True)
async def news_embedding_pipeline():
    """
    Main flow to fetch news articles stores them in a Chroma DB.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Fetch financial news articles using NewsAPI
    news_articles = fetch_news_articles.submit(news_api_key, "technology", 60)

    collection_name = create_chroma_collection.submit()

    store_embeddings_in_chroma.submit(news_articles, collection_name)



if __name__ == "__main__":
    asyncio.run(news_embedding_pipeline())
