
    FROM python:3.9-slim

    RUN pip install prefect

    WORKDIR /usr/src/app

    COPY example.py .

    CMD ["python", "example.py"]
    