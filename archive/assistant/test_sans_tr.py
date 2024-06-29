from create_assistant import analyst_assistant
from prefect.task_runners import ThreadPoolTaskRunner
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing_extensions import override
from openai import AssistantEventHandler
from prefect import task, flow


@task
def load_and_get_client():
    raise NotImplementedError("This task is not implemented yet.")
    """Load environment variables and create an OpenAI client."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


@task
def create_thread_with_messages(client):
    """Create a thread and add initial messages."""
    thread = client.beta.threads.create()
    messages = [
        "Can you predict if Apple's stock price will increase tomorrow?",
        "Please gather the latest news articles related to Apple and analyze if this news will likely have a positive or negative effect on the stock price.",
    ]
    for message in messages:
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message,
        )
    return thread.id


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


@task
def run_assistant_with_event_handler(client, thread_id):
    """Run the assistant with event handling."""
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=analyst_assistant.id,
        instructions="Please address the user as Jane Doe.",
        event_handler=EventHandler(),
    ) as stream:
        stream.until_done()


@flow()
def main():
    client = load_and_get_client()
    thread_id = create_thread_with_messages(client)
    run = run_assistant_with_event_handler(client, thread_id)


if __name__ == "__main__":
    main()
