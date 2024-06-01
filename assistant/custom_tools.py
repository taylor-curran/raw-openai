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

    # Build and run the Docker container
    client = docker.from_env()
    image, logs = client.images.build(path=".", tag="example_image")
    container = client.containers.run(image="example_image", detach=True)
    result = container.logs().decode("utf-8")
    container.stop()
    container.remove()

    return result

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
    "type": "function",
    "function": {
        "name": "execute_example_in_docker",
        "description": "Write example code for Prefect, install the library, run the code in a Docker container, and return the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "example_code": {
                    "type": "string",
                    "description": "The example code to run using Prefect",
                }
            },
            "required": ["example_code"],
        },
    },
}
