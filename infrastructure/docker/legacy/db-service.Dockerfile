FROM python:3.13-slim  

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


COPY services/db-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/db-service /app

COPY libs /app/libs

EXPOSE 80  

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
