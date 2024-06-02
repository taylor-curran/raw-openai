import os
from openai import OpenAI
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler
from custom_tools import run_prefect_code_tool, run_prefect_code

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client
client = OpenAI(api_key=api_key)


def create_assistant(client):
    assistant = client.beta.assistants.create(
        name="Prefect Assistant",
        instructions=(
            "You only answer questions after verifying the code works. Use the `run_prefect_code` tool to execute Prefect code."
            "You are an assistant specialized in Prefect. Reference Prefect documentation."
            "Always run the code in a Docker container until it runs without error. Use the `run_prefect_code` tool to execute Prefect code."
            "Don't give an answer unless you are able to verify your answer works by running the code in a docker container."
            "Always respond with the code example AND importantly the version of prefect that was used to run the code."
            "If the code fails, try up to 5 times with different versions. Stop after 5 tries."
            "If you cannot run the code, apologize and indicate you could not verify the answer."
        ),
        tools=[run_prefect_code_tool],
        model="gpt-4o",
    )
    return assistant


def create_thread(client):
    thread = client.beta.threads.create()
    return thread


def add_message_to_thread(client, thread_id, content):
    message = client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=content
    )
    return message


class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.function_call_arguments = ""

    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > {text}")

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}")

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "function":
            if delta.function.arguments:
                self.function_call_arguments += delta.function.arguments
            if delta.function.output:
                print(f"\n\noutput > {delta.function.output}", flush=True)


if __name__ == "__main__":
    # Create the assistant
    assistant = create_assistant(client)
    print("Assistant created:", assistant)

    # Create a new thread
    thread = create_thread(client)
    print("Thread created:", thread)

    # Add a message to the thread
    content = "How do I specify the number of retries in a Prefect task? Does the task need to run in a Prefect flow? Please run an example Prefect code for me."
    message = add_message_to_thread(client, thread.id, content)
    print("Message added to thread:", message)

    # Stream the response with run-specific instructions
    event_handler = EventHandler()
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,  # Use the created assistant's ID
        instructions="Please address the user as Jane Doe. The user has a premium account.",
        event_handler=event_handler,
    ) as stream:
        stream.until_done()
    print(
        f"\nComplete function call arguments: {event_handler.function_call_arguments}"
    )

    # Execute the captured function call arguments
    result = run_prefect_code({"example_code": event_handler.function_call_arguments})
    print("Execution Result:")
    print(result)
    print("Library Version:")
    print(result)
