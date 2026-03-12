FROM python:3.13-slim

WORKDIR /code

COPY services/db-service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/db-service /code