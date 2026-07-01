FROM python:3.12.4-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=8000

WORKDIR /app

# Instalar dependencias do SO
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn psycopg2-binary

COPY . .

CMD python manage.py migrate && \
    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT \
    --workers 3 --threads 2 --timeout 60 --keep-alive 5 \
    --max-requests 1000 --max-requests-jitter 50
