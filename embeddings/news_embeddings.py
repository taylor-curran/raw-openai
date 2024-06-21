import os
import pandas as pd
from dotenv import load_dotenv
from newsapi import NewsApiClient
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import sys

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
news_api_key = os.getenv("NEWS_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")


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


def store_embeddings_in_chroma(
    df: pd.DataFrame, openai_api_key: str
):
    """
    Store embeddings of news article titles and content in a ChromaDB collection.

    Args:
        df (pd.DataFrame): DataFrame containing news articles.
        openai_api_key (str): API key for OpenAI to generate embeddings.
    """
    chroma_client = chromadb.PersistentClient(path="./chroma")
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key, model_name="text-embedding-ada-002"
    )

    collection = chroma_client.get_or_create_collection(
            "news_articles", embedding_function=openai_ef
        )

    df = df.drop_duplicates(subset=["url"])

    # Prepare the data
    documents = df['content'].tolist()
    metadata = [{'title': title, 'url': url} for title, url in zip(df['title'], df['url'])]
    ids = [f"id{i}" for i in range(len(df))]

    # Add data to the collection
    collection.add(
        documents=documents,
        metadatas=metadata,
        ids=ids
    )

    print("------------------- peek -------------------")
    print(collection.peek(1))
    print("------------------- count -------------------")
    print(collection.count())


def news_embedding_pipeline():
    """
    Main function to orchestrate fetching news articles, creating ChromaDB collection,
    and storing embeddings in the collection.
    """
    news_articles = fetch_news_articles(news_api_key, "technology", 60)
    store_embeddings_in_chroma(news_articles, openai_api_key)


if __name__ == "__main__":
    news_embedding_pipeline()


