
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
    