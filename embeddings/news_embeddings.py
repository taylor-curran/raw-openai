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
        redis_client = redis.Redis()

        # Try to ping the Redis server
        if redis_client.ping():
            print("Redis server is connected and responding with PONG.")
        else:
            raise Exception("Unexpected response from Redis server.")
    except redis.exceptions.ConnectionError:
        raise Exception(
            "Could not connect to Redis server. Please check if the server is running and the connection settings are correct.\n"
            "Make sure Redis is started using 'brew services start redis'."
        )
    return redis_client


@task
def create_redis_search_index(redis_client: redis.Redis):
    """
    Create a RediSearch index in Redis to store article metadata.

    Args:
        redis_client (redis.Redis): Redis client.
    """
    # Constants
    VECTOR_DIM = 1536  # Set an arbitrary dimension size for now # TODO - Update this value after we add the embeddings step
    VECTOR_NUMBER = 60  # Initial number of vectors, adjust as needed
    INDEX_NAME = "news-embeddings-index"  # Name of the search index
    PREFIX = "news-doc"  # Prefix for the document keys
    DISTANCE_METRIC = "COSINE"  # Distance metric for the vectors (e.g., COSINE, IP, L2)

    # Define RediSearch fields for each of the columns in the dataset
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

    # Check if index exists
    try:
        redis_client.ft(INDEX_NAME).info()
        print("Index already exists")
    except:
        # Create RediSearch Index
        redis_client.ft(INDEX_NAME).create_index(
            fields=fields,
            definition=IndexDefinition(prefix=[PREFIX], index_type=IndexType.HASH),
        )
        print("Index created successfully")


@flow(name="News Embedding Pipeline", log_prints=True)
async def news_embedding_pipeline():
    """
    Main flow to fetch news articles and create a Redis search index.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Fetch financial news articles using NewsAPI
    news_articles = fetch_news_articles.submit(news_api_key, "technology", 60)

    # Check Redis connection
    redis_client = check_redis_connection.submit()

    # Nate - can I pass the redis client? I think not
    # Create Redis search index
    create_redis_search_index.submit(redis_client)


if __name__ == "__main__":
    asyncio.run(news_embedding_pipeline())
