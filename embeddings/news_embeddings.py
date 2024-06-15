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

# Increase recursion limit to help diagnose the issue
sys.setrecursionlimit(2000)

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
    chroma_client = chromadb.Client()
    collection_name = "news_embeddings"

    try:
        chroma_client.get_collection(collection_name)
        print(f"Collection '{collection_name}' already exists.")
    except ValueError:
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
def store_embeddings_in_chroma(df: pd.DataFrame, collection_name: str, openai_api_key: str):
    chroma_client = chromadb.Client()
    collection = chroma_client.get_collection(collection_name)
    
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(api_key=openai_api_key, model_name="text-embedding-ada-002")

    df = df.drop_duplicates(subset=['url'])

    ids = []
    metadata = []
    embeddings = []

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
        embeddings.append(title_embedding)
        embeddings.append(content_embedding)

    # Check dimensions and log before upsert
    print(f"IDs: {ids}")
    print(f"Metadata: {metadata}")
    print(f"Embeddings shape: {len(embeddings)}")

    # Ensure embeddings are correctly shaped
    assert all(len(vec) == 1536 for vec in embeddings), "Embeddings are not of length 1536"

    # Format the data for upsert
    for i in range(len(ids)):
        collection.upsert(
            ids=[ids[i]],
            embeddings=[embeddings[i*2], embeddings[i*2+1]],
            metadatas=[metadata[i]]
        )


@flow(name="News Embedding Pipeline", log_prints=True)
async def news_embedding_pipeline():
    news_articles = fetch_news_articles.submit(news_api_key, "technology", 60)
    collection_name = create_chroma_collection.submit()
    store_embeddings_in_chroma.submit(news_articles, collection_name, openai_api_key)


if __name__ == "__main__":
    try:
        asyncio.run(news_embedding_pipeline())
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
