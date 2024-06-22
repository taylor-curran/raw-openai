from create_assistant import financial_analyst_assistant
from openai import OpenAI
from dotenv import load_dotenv
import os

# -- Create OpenAI client --

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client
client = OpenAI(api_key=api_key)

# -- Create Thread, Add Messages, and Run Assistant --

thread = client.beta.threads.create()

message = client.beta.threads.messages.create(
  thread_id=thread.id,
  role="user",
  content="Can you predict if Microsoft's stock price will increase tomorrow?"
)

message = client.beta.threads.messages.create(
  thread_id=thread.id,
  role="user",
  content="""Please gather the latest news articles related to Microsoft and analyze if this news will likely have a positive or negative effect on the stock price."""
)

run = client.beta.threads.runs.create_and_poll(
  thread_id=thread.id,
  assistant_id=financial_analyst_assistant.id,
  instructions="Please address the user as John Smith."
)

if run.status == 'completed': 
  messages = client.beta.threads.messages.list(
    thread_id=thread.id
  )
  print(messages)
else:
  print(run.status)
