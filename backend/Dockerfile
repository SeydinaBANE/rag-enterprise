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

# Spacy model for PII detection (en_core_web_sm ≈ 12 MB)
# For French support: docker build --build-arg PII_LANG=fr
ARG PII_LANG=en
RUN python -m spacy download en_core_web_sm \
    && if [ "$PII_LANG" = "fr" ]; then python -m spacy download fr_core_news_md; fi

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
