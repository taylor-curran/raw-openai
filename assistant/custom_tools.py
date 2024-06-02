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
            print(log.get("stream", "").strip())

        # Run the Docker container
        print("Running Docker container...")
        container = client.containers.run(image="example_image", detach=True)

        # Capture container logs
        print("Capturing container logs...")
        logs = container.logs(stdout=True, stderr=True, stream=True)
        result = ""
        for log in logs:
            result += log.decode("utf-8")

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


run_prefect_code = {
# add tool here
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
