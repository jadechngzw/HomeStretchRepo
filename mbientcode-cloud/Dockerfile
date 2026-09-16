FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY isolation_forest.pkl .
COPY scaler.pkl .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 main:app