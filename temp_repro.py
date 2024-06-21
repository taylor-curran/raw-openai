from prefect import flow, task

from typing import Any

@task()
def salesforce_to_csv_file_extract():
    pass

@flow(log_prints=True)
def hello_world(name: str = "world", x: int = 1, y: int = 1) -> None:
    """

    Prefect workflow putting together all the tasks and managing the dependencies

    """

    csv_file_extract: Any = salesforce_to_csv_file_extract.submit(
        auth_output=salesforce_login,
        soql=config["query"],
        file_name=config["source_file_name"],
        load_type=job_configuration["BATCH_JOB_LOAD_TYPE_CODE"],
        logger=LOGGER,
        wait_for=[config, salesforce_login],
    )


if __name__ == "__main__":
    hello_world()
