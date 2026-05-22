FROM pgvector/pgvector:pg16
COPY backend/migrations/001_initial.sql /docker-entrypoint-initdb.d/001_initial.sql
