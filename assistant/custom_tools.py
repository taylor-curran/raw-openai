import docker
import os

def create_dockerfile():
    dockerfile_content = """
    FROM python:3.9-slim

    RUN pip install prefect

    WORKDIR /usr/src/app

    COPY example.py .

    CMD ["python", "example.py"]
    """
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)

def run_in_docker(example_code):
    # Create Dockerfile
    create_dockerfile()

    # Write example code to a file
    with open("example.py", "w") as f:
        f.write(example_code)

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

        # Capture container logs
        print("Capturing container logs...")
        logs = container.logs(stdout=True, stderr=True, stream=True)
        result = "".join(log.decode("utf-8") for log in logs)

        container.stop()
        container.remove()
        return result
    except docker.errors.APIError as e:
        return f"API error: {e}"
    except docker.errors.BuildError as e:
        return f"Build error: {e}"
    except docker.errors.ContainerError as e:
        return f"Container error: {e}"
    except Exception as e:
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
        }
    }
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
    print(output["result"])
    print("Library Version:")
    print(output["library_version"])
