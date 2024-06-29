import os
from openai import OpenAI
from dotenv import load_dotenv
from tools import query_tech_news

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client
client = OpenAI(api_key=api_key)

# Create the assistant with the custom tool
analyst_assistant = client.beta.assistants.create(
    name="Portfolio Manager Analyst Bot",
    instructions="""
    You are a portfolio manager/analyst assistant. Your main tasks are:
    - Researching and analyzing financial statements and reports
    - Staying updated with the latest market trends and news articles
    - Gathering and interpreting data from various financial resources and databases
    - Compiling detailed reports on companies and providing investment recommendations
    You can use the query_tech_news function to retrieve relevant news articles.
    """,
    tools=[
        {"type": "code_interpreter"},
        {
            "type": "function",
            "function": {
                "name": "query_tech_news",
                "description": "Query the tech news database for relevant articles",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for news articles",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "The number of results to return (default: 5)",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    ],
    model="gpt-3.5-turbo",
)
