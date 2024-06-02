{
  "example_code": "from prefect import task, Flow\nfrom datetime import timedelta\n\n@task(retries=3, retry_delay=timedelta(seconds=10))\ndef example_task():\n    print(\"Running task\")\n    raise ValueError(\"An error occurred!\")\n\nwith Flow(\"retry-example\") as flow:\n    example_task()\n\nif __name__ == \"__main__\":\n    flow.run()\n"
}