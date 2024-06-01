import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")


def create_assistant():
    client = OpenAI(api_key=api_key)

    assistant = client.beta.assistants.create(
        name="Prefect Assistant",
        instructions=(
            "You are an assistant specialized in Prefect. Reference Prefect documentation "
            "you must always 'pip install -U prefect' first then import it and write and run code to answer the question."
            "from a Chroma vector database to provide accurate information and write and run "
            "Prefect code until it works correctly."
        ),
        tools=[
            {"type": "code_interpreter"},
        ],
        model="gpt-3.5-turbo",
        # model="gpt-4o",
    )
    return assistant


if __name__ == "__main__":
    assistant = create_assistant()
    print("Assistant created:", assistant)
