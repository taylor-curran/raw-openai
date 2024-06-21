import os
from openai import OpenAI
from dotenv import load_dotenv
from tools import TechNewsDBTool  # Import the custom tool

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client
client = OpenAI(api_key=api_key)

# Create the assistant with the custom tool
assistant = client.beta.assistants.create(
    name="Portfolio Manager Analyst Bot",
    instructions="""
    You are a portfolio manager/analyst assistant. Your main tasks are:
    - Researching and analyzing financial statements and reports
    - Staying updated with the latest market trends and news articles
    - Gathering and interpreting data from various financial resources and databases
    - Compiling detailed reports on companies and providing investment recommendations
    """,
    tools=[
        {"type": "web_browsing"},
        TechNewsDBTool(),  # Include the custom tool
    ],
    model="gpt-3.5-turbo",
)

# Example usage of the assistant with the custom tool
query_result = assistant.tools["tech_news_db_tool"].execute(
    query_texts=["Latest trends in AI investment"], n_results=5
)
print(query_result)
