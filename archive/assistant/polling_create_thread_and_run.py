from create_assistant import analyst_assistant
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
    content="I need to know if Apple's stock price will go up tomorrow.",
)

message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="""Can you look up the latest news that is relevant to Apple and let me know if this information will impact the stock price for better or worse?""",
)

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=analyst_assistant.id,
    instructions="Please address the user as Jane Doe.",
)

if run.status == "completed":
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print(messages)
else:
    print(run.status)
