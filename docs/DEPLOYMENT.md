# SecureArchive AI — Deployment Guide

## Local (Docker Compose)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API docs | http://localhost:8000/api/v1/docs |
| MinIO console | http://localhost:9001 |

## AWS

1. **RDS** — PostgreSQL 16; set `DATABASE_URL`
2. **ElastiCache** — Redis for Celery broker/result
3. **S3** — Replace MinIO with `MINIO_*` pointed at S3-compatible endpoint
4. **ECS/Fargate** — Deploy `api` and `worker` tasks from `backend/Dockerfile`
5. **Amplify or Vercel** — Deploy `frontend/` with `NEXT_PUBLIC_API_URL`

## GCP

- Cloud SQL (PostgreSQL), Memorystore (Redis), Cloud Storage (MinIO replacement), Cloud Run for API/worker.

## Azure

- Azure Database for PostgreSQL, Azure Cache for Redis, Blob Storage, Container Apps.

## System Dependencies (Workers)

Install on worker images:

- Tesseract OCR 5.x
- DjVuLibre (`c44`, `ddjvu`)
- Poppler (`pdftoppm`)

## Environment Variables

1. Copy `.env.example` → `.env` (repo root for Docker Compose).
2. Generate secrets: `openssl rand -hex 32`
3. Set `ENVIRONMENT=production`, `SECRET_KEY`, and rotate all database/MinIO credentials.
4. Production startup validates `SECRET_KEY` length and rejects default MinIO passwords when `ENVIRONMENT=production`.
