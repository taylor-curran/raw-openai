import os
from openai import OpenAI
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")


def create_thread(client):
    thread = client.beta.threads.create()
    return thread


def add_message_to_thread(client, thread_id, content):
    message = client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=content
    )
    return message


class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)


if __name__ == "__main__":
    client = OpenAI(api_key=api_key)

    # Create a new thread
    thread = create_thread(client)
    print("Thread created:", thread)

    # Add a message to the thread
    content = "How do I specify the number of retries in a Prefect task? Does the task need to run in a prefect flow?"
    message = add_message_to_thread(client, thread.id, content)
    print("Message added to thread:", message)

    # Stream the response
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id="asst_EcMYxCg7MXM6lWfBQBTvDMQb",
        instructions="Please address the user as Jane Doe. The user has a premium account.",
        event_handler=EventHandler(),
    ) as stream:
        stream.until_done()
