import os
from openai import OpenAI
from dotenv import load_dotenv
from openai import AssistantEventHandler

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client
client = OpenAI(api_key=api_key)

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
        {"type": "code_interpreter"},
        {"type": "web_browsing"},
        {"type": "document_summarizer"},
    ],
    model="gpt-3.5-turbo",
)
