FROM python:3.11-slim

WORKDIR /app

# Seules dépendances système strictement nécessaires :
# - gcc + libpq-dev  : compilation asyncpg / psycopg2
# - libgomp1         : OpenMP requis par fastembed (ONNX Runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
