from datetime import timedelta
from typing import List, Dict
from openai import OpenAI
from prefect import flow, task
from prefect.tasks import task_input_hash
from dotenv import load_dotenv
import os
from newsapi import NewsApiClient
import asyncio
import sys
import pandas as pd
import redis
from redis.commands.search.indexDefinition import (
    IndexDefinition,
    IndexType
)
from redis.commands.search.query import Query
from redis.commands.search.field import (
    TextField,
    VectorField
)

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client
client = OpenAI(api_key=api_key)


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
)
def fetch_news(api_key: str, query: str, num_articles: int) -> pd.DataFrame:
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
    try:
        # Connect to Redis
        redis_client = redis.Redis()

        # Try to ping the Redis server
        if redis_client.ping():
            print("Redis server is connected and responding with PONG.")
        else:
            raise Exception("Unexpected response from Redis server.")
    except redis.exceptions.ConnectionError:
        raise Exception("Could not connect to Redis server. Please check if the server is running and the connection settings are correct.\n"
                        "Make sure Redis is started using 'brew services start redis'.")


@flow(name="News Embedding Pipeline", log_prints=True)
async def news_embedding_pipeline():
    # Load environment variables from .env file
    load_dotenv()

    # Fetch financial news articles using NewsAPI
    news_api_key = os.getenv("NEWS_API_KEY")
    news_articles = fetch_news.submit(news_api_key, "technology", 60)

    check_redis_connection.submit()



if __name__ == "__main__":
    asyncio.run(news_embedding_pipeline())
