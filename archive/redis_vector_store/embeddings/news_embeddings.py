from datetime import timedelta
from typing import List, Dict
from prefect import flow, task
from prefect.tasks import task_input_hash
from dotenv import load_dotenv
import os
from newsapi import NewsApiClient
import asyncio
import pandas as pd
import redis
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import TextField, VectorField
import subprocess  # TODO remove
import json

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


@task
def check_redis_connection():
    """
    Check connection to the Redis server.

    Returns:
        redis.Redis: Redis client if connection is successful.
    """
    try:
        # Connect to Redis
        redis_client = redis.Redis(host="localhost", port=6379)

        # Try to ping the Redis server
        if redis_client.ping():
            print("Redis server is connected and responding with PONG.")
        else:
            raise Exception("Unexpected response from Redis server.")
    except redis.exceptions.ConnectionError:
        raise Exception(
            "Could not connect to Redis server. Please check if the server is running and the connection settings are correct.\n"
            "Make sure Redis is started using 'docker-compose up -d'."
        )
    return redis_client


@task
def create_redis_search_index(redis_client: redis.Redis):
    VECTOR_DIM = 1536
    VECTOR_NUMBER = 60
    INDEX_NAME = "news-embeddings-index"
    PREFIX = "news-doc"
    DISTANCE_METRIC = "COSINE"

    title = TextField(name="title")
    url = TextField(name="url")
    text = TextField(name="text")
    title_embedding = VectorField(
        "title_vector",
        "FLAT",
        {
            "TYPE": "FLOAT32",
            "DIM": VECTOR_DIM,
            "DISTANCE_METRIC": DISTANCE_METRIC,
            "INITIAL_CAP": VECTOR_NUMBER,
        },
    )
    content_embedding = VectorField(
        "content_vector",
        "FLAT",
        {
            "TYPE": "FLOAT32",
            "DIM": VECTOR_DIM,
            "DISTANCE_METRIC": DISTANCE_METRIC,
            "INITIAL_CAP": VECTOR_NUMBER,
        },
    )
    fields = [title, url, text, title_embedding, content_embedding]

    try:
        redis_client.ft(INDEX_NAME).info()
        print("Index already exists")
    except redis.exceptions.ResponseError as e:
        if "unknown command 'FT.INFO'" in str(e):
            raise Exception(
                "RediSearch commands are not recognized by the Redis server. Ensure RediSearch is properly installed and loaded."
            )
        elif "Unknown Index name" in str(e):
            try:
                redis_client.ft(INDEX_NAME).create_index(
                    fields=fields,
                    definition=IndexDefinition(
                        prefix=[PREFIX], index_type=IndexType.HASH
                    ),
                )
                print("Index created successfully")
            except redis.exceptions.ResponseError as e:
                raise Exception(f"Failed to create index: {str(e)}")
        else:
            raise


@flow(name="News Embedding Pipeline", log_prints=True)
async def news_embedding_pipeline():
    """
    Main flow to fetch news articles and create a Redis search index.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Fetch financial news articles using NewsAPI
    news_articles = fetch_news_articles(news_api_key, "technology", 60)

    # Check Redis connection
    redis_client = check_redis_connection()

    # Create Redis search index
    create_redis_search_index(redis_client)


if __name__ == "__main__":
    asyncio.run(news_embedding_pipeline())
