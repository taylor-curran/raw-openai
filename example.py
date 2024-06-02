{
  "example_code": "from prefect import task, Flow\nfrom datetime import timedelta\n\n@task(retries=3, retry_delay_seconds=10)\ndef unreliable_task():\n    print(\"Running task...\")\n    raise ValueError(\"An error occurred\")\n\nwith Flow(\"retry example\") as flow:\n    unreliable_task()\n\n# Execute the flow\nif __name__ == \"__main__\":\n    flow.run()"
}