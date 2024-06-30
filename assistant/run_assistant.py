from create_assistant import analyst_assistant
from prefect.task_runners import ThreadPoolTaskRunner
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing_extensions import override
from openai import AssistantEventHandler
from prefect import task, flow
from tools import query_tech_news
import json
import time


def load_and_get_client():
    """Load environment variables and create an OpenAI client."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


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
        print(f"\nassistant > Text created", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(f"Text delta: {delta.value}", end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > Tool call created: {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        print(f"\nassistant > Tool call delta: {delta.type}\n", flush=True)
        if delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                print(f"Code input: {delta.code_interpreter.input}", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\nCode output >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)
        elif delta.type == "function":
            if delta.function.name == "query_tech_news":
                print(
                    f"Calling query_tech_news with arguments: {delta.function.arguments}",
                    flush=True,
                )
                result = query_tech_news(**json.loads(delta.function.arguments))
                print(f"query_tech_news result: {result}", flush=True)

    def on_exception(self, exception):
        print(f"Exception in event handler: {exception}", flush=True)

    def on_end(self):
        print("Event stream ended", flush=True)


# TODO this still isn't working
def run_assistant_with_event_handler(client, thread_id):
    """Run the assistant with event handling."""
    try:
        print(f"Starting assistant run for thread {thread_id}")

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=analyst_assistant.id,
            instructions="Please address the user as Jane Doe. Use the query_tech_news function to find relevant articles when needed.",
        )
        print(f"Run created with ID: {run.id}")

        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            print(f"Run status: {run.status}")

            if run.status == "completed":
                print("Run completed successfully")
                break
            elif run.status == "requires_action":
                print("Run requires action")
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    if function_name == "query_tech_news":
                        output = query_tech_news(**function_args)
                        tool_outputs.append(
                            {
                                "tool_call_id": tool_call.id,
                                "output": output,
                            }
                        )
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
                )
            elif run.status in ["failed", "cancelled", "expired"]:
                print(f"Run ended with status: {run.status}")
                break
            else:
                time.sleep(1)  # Wait for 1 second before checking again

        print("Run completed, now streaming results")

        # Now that the run is complete, we can stream the results
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=analyst_assistant.id,
            event_handler=EventHandler(),
        ) as stream:
            print("Streaming started")
            stream.until_done()

        print("Streaming completed")

        # Fetch and print the messages after the run
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for message in messages:
            print(f"Message: {message.role} - {message.content[0].text.value}")

    except Exception as e:
        print(f"Error in run_assistant_with_event_handler: {e}")


def main():
    try:
        print("Starting main function")
        client = load_and_get_client()
        print("Client created")
        thread_id = create_thread_with_messages(client)
        print(f"Thread created with ID: {thread_id}")
        run_assistant_with_event_handler(client, thread_id)
        print("Assistant run completed")
    except Exception as e:
        print(f"An error occurred in main: {e}")


if __name__ == "__main__":
    main()
