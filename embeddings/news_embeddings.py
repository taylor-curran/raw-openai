import os
import pandas as pd
from dotenv import load_dotenv
from newsapi import NewsApiClient
import chromadb
import chromadb.utils.embedding_functions as embedding_functions

# Load environment variables from .env file
load_dotenv()

# Get the API keys from environment variables
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Constants for the script
QUERY_STRING = "technology"  # The topic to search for in news articles
NUM_ARTICLES = 60  # Number of articles to fetch
CHROMA_DB_PATH = "./chroma_db"  # Path to store ChromaDB embeddings
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"  # Model used for generating embeddings

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

    # Initialize the NewsAPI client
    newsapi = NewsApiClient(api_key=api_key)
    
    # Fetch articles matching the query
    articles = newsapi.get_everything(q=query, language="en", page_size=num_articles)

    # Extract relevant fields from the articles
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

def store_embeddings_in_chroma(df: pd.DataFrame, openai_api_key: str):
    """
    Store embeddings of news article titles and content in a ChromaDB collection.

    Args:
        df (pd.DataFrame): DataFrame containing news articles.
        openai_api_key (str): API key for OpenAI to generate embeddings.
    """
    # Initialize ChromaDB client for storing embeddings
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Define the embedding function using OpenAI
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key, model_name=EMBEDDING_MODEL_NAME
    )

    # Create or get an existing collection in ChromaDB
    collection = chroma_client.get_or_create_collection(
        "news_articles", embedding_function=openai_ef
    )

    # Remove duplicate articles based on URL
    df = df.drop_duplicates(subset=["url"])

    # Prepare the data for embedding
    documents = df['content'].tolist()  # List of article contents
    metadata = [{'title': title, 'url': url} for title, url in zip(df['title'], df['url'])]  # Metadata
    ids = [f"id{i}" for i in range(len(df))]  # Unique IDs for each document

    # Add data to the collection
    collection.add(
        documents=documents,
        metadatas=metadata,
        ids=ids
    )

    # Print a peek and count for verification
    print("------------------- peek -------------------")
    print(collection.peek(1))  # Show a sample of one document
    print("------------------- count -------------------")
    print(collection.count())  # Show the total count of documents in the collection

def news_embedding_pipeline():
    """
    Main function to orchestrate fetching news articles, creating ChromaDB collection,
    and storing embeddings in the collection.
    """
    # Fetch news articles from NewsAPI
    news_articles = fetch_news_articles(NEWS_API_KEY, QUERY_STRING, NUM_ARTICLES)
    
    # Store the article embeddings in ChromaDB
    store_embeddings_in_chroma(news_articles, OPENAI_API_KEY)

# Entry point of the script
if __name__ == "__main__":
    news_embedding_pipeline()
