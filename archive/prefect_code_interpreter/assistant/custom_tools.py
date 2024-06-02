import docker
import os


def create_dockerfile():
    dockerfile_content = """
    FROM python:3.9-slim

    RUN pip install -U prefect

    WORKDIR /usr/src/app

    COPY example.py .

    CMD ["python", "example.py"]
    """
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)


def run_in_docker(example_code: str):
    # Create Dockerfile
    create_dockerfile()

    # Write example code to a file
    print("Writing the following code to example.py:")
    print(example_code)

    with open("example.py", "w") as f:
        f.write(example_code)

    # Check if the file was written correctly
    with open("example.py", "r") as f:
        written_content = f.read()
        print("Content of example.py:")
        print(written_content)

    try:
        # Set Docker environment variable
        os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"

        # Reinitialize Docker client after setting environment variable
        client = docker.from_env()

        # Build the Docker image
        print("Building Docker image...")
        image, logs = client.images.build(path=".", tag="example_image")
        for log in logs:
            stream = log.get("stream")
            if stream:
                print(stream.strip())

        # Run the Docker container
        print("Running Docker container...")
        container = client.containers.run(image="example_image", detach=True)

        # Wait for the container to finish
        print("Waiting for container to finish...")
        result = container.wait()
        print(f"Container finished with status: {result['StatusCode']}")

        # Capture container logs
        print("Capturing container logs...")
        logs = container.logs(stdout=True, stderr=True).decode("utf-8")
        print("Container logs captured successfully.")
        print("Container logs:\n", logs)

        container.remove()
        return logs
    except docker.errors.APIError as e:
        print(f"API error: {e}")
        return f"API error: {e}"
    except docker.errors.BuildError as e:
        print(f"Build error: {e}")
        return f"Build error: {e}"
    except docker.errors.ContainerError as e:
        print(f"Container error: {e}")
        return f"Container error: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"


def execute_example_in_docker(example_code):
    try:
        # Run example code in Docker
        result = run_in_docker(example_code)
        # Get library version
        version_command = "pip show prefect | grep Version"
        version_result = os.popen(version_command).read().strip()
        return {
            "example_code": example_code,
            "result": result,
            "library_version": version_result,
        }
    except Exception as e:
        return {"error": str(e)}


def run_prefect_code(params):
    example_code = params.get("example_code")
    print("This is Params: ", params)
    print("This is example_code: ", example_code)
    if not example_code:
        return {"error": "No code provided"}

    retries = 5
    for attempt in range(retries):
        result = execute_example_in_docker(example_code)
        if not result.get("error"):
            return result
        example_code = update_example_code(example_code, attempt + 1)

    return {"error": "Failed to run the code successfully after 5 attempts"}


def update_example_code(example_code, attempt):
    # Modify the example code based on the attempt number
    # This is a placeholder function; you'll need to implement the logic to modify the code.
    return example_code


run_prefect_code_tool = {
    "type": "function",
    "function": {
        "name": "run_prefect_code",
        "description": "Run Prefect code in a Docker container",
        "parameters": {
            "type": "object",
            "properties": {
                "example_code": {
                    "type": "string",
                    "description": "The Prefect code to run",
                },
            },
            "required": ["example_code"],
        },
    },
}

if __name__ == "__main__":
    example_code = """
from prefect import flow, task

@task
def hello_task():
    print("Task started")
    result = "Hello, Prefect!"
    print(f"Task result: {result}")
    return result

@flow(log_prints=True)
def hello_flow():
    result = hello_task()
    print(f"Flow result: {result}")
    print("Hello Flow Completing!")

hello_flow()
    """
    output = execute_example_in_docker(example_code)
    print("Execution Result:")
    print(output.get("result", "No result"))
    print("Prefect Library Version:")
    print(output.get("library_version", "No library version"))
