# SecureArchive AI

[![CI](https://github.com/YOUR_USER/smart-compression-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USER/smart-compression-analyzer/actions/workflows/ci.yml)

**Compression. OCR. Integrity. All Verified.**

Research-grade SaaS platform implementing the comparative compression methodology for scanned documents — evaluating JPEG, PNG, TIFF, PDF, WebP, and DjVu on storage efficiency, OCR preservation, hidden metadata survival, and archival suitability.

> Replace `YOUR_USER` in the CI badge URL with your GitHub username or organization after the first push.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, React, TypeScript, Tailwind, Recharts |
| Backend | FastAPI, Python 3.11, Celery |
| Data | PostgreSQL, Redis, MinIO |
| Processing | OpenCV, Pillow, Tesseract v5, DjVuLibre (`c44 -slice 74`) |

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY, POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, NEXTAUTH_SECRET
docker compose up --build
```

- App: http://localhost:3000  
- API: http://localhost:8000/api/v1/docs  

Requires Docker Desktop plus system tools in the worker image (Tesseract, DjVuLibre, Poppler).

### Local Python (tests & batch CLI)

```bash
py -3 -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install --upgrade pip
pip install -r requirements-dev.txt

ruff check .
mypy --explicit-package-bases backend/app compression metrics utils
python -m pytest
```

**Verified locally:** 50 tests passed · ruff clean · mypy clean.

Property tests may trigger a harmless PSNR `divide-by-zero` warning when comparing identical images (infinite PSNR); this is filtered in `pyproject.toml`.

Optional: [pre-commit](https://pre-commit.com/) — `pre-commit install`

Celery workers default to **concurrency=1** to avoid CPU contention during OCR/compression. Override with `CELERY_WORKER_CONCURRENCY` in `.env`.

### Manual (without Docker)

```bash
# Terminal 1 — API
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2 — Celery
celery -A app.celery_app worker --loglevel=info --concurrency=1

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

Register at http://localhost:3000/login, then upload at http://localhost:3000/upload.

## Paper Pipeline

1. Preprocess → 1000×1414 greyscale reference  
2. LSB embed 968-bit payload (UUID + timestamp + SHA-256)  
3. Compress six formats with paper parameters  
4. Decode, measure CR / PSNR / SSIM / OCR / BER  

## Project Structure

```
├── backend/          # FastAPI + Celery + SQLAlchemy
├── frontend/         # Next.js dashboard
├── compression/      # Format encoders
├── metrics/          # Evaluation metrics
├── utils/            # Preprocessing & LSB steganography
├── docs/             # Architecture, schema, deployment, CI
├── dataset/          # Demo benchmark images
└── docker-compose.yml
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database Schema](docs/schema.sql)
- [Deployment](docs/DEPLOYMENT.md)
- [CI & secrets](docs/CI.md)

## Research reference

Paper table screenshots (if any) belong under `docs/paper-screenshots/`. Add your PDF to `docs/` when available.

# SecureArchive AI

Compression. OCR. Integrity. All Verified.

SecureArchive AI is a research-focused platform that implements and reproduces a comparative document compression methodology. The system evaluates multiple archival formats (JPEG, PNG, TIFF, PDF, WebP, DjVu) for storage efficiency, OCR preservation, hidden payload survival, and archival suitability.

This repository contains a full-stack reference implementation: a Next.js dashboard, a FastAPI backend with Celery workers, and a collection of format encoders/metrics used in the paper pipeline.

**Repository:** https://github.com/PremB2907/smart-compression-analyzer

---

## Highlights

- Multi-format compression pipeline with deterministic parameters used in the study
- LSB steganography embedding for payload survival (UUID + timestamp + SHA-256)
- Evaluation metrics: compression ratio, MSE, PSNR, SSIM, OCR accuracy (CER), BER
- Asynchronous processing via Celery + Redis, object storage via MinIO
- CI: `ruff`, `mypy`, and `pytest` integrated (see `.github/workflows/ci.yml`)

---

## Table of Contents

1. [Architecture](#architecture)
2. [Quick Start (Docker)](#quick-start-docker-recommended)
3. [Local Development](#local-development)
4. [Running Tests & Linters](#running-tests--linters)
5. [Configuration & Secrets](#configuration--secrets)
6. [Developer Notes](#developer-notes)
7. [CI / Release](#ci--release)
8. [Contributing](#contributing)

---

## Architecture

High level:

- Frontend: Next.js application providing login, upload, and result dashboards.
- Backend: FastAPI app exposing `/api/v1` endpoints for uploads, analysis, and reports.
- Workers: Celery tasks perform file conversions, compression runs, OCR, and metric extraction.
- Storage: MinIO for object storage; PostgreSQL for metadata and results; Redis for Celery broker/result backend.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full details.

---

## Quick Start (Docker, recommended)

1. Copy the example env file and set secrets (do not commit `.env`):

```bash
cp .env.example .env
# Edit .env and set at minimum:
#   SECRET_KEY=$(openssl rand -hex 32)
#   POSTGRES_PASSWORD=...  
#   MINIO_ROOT_PASSWORD=... 
#   NEXTAUTH_SECRET=$(openssl rand -hex 32)

docker compose up --build
```

The API will be available at `http://localhost:8000/api/v1` and the frontend at `http://localhost:3000`.

Smoke test checklist (after containers are healthy):

- Visit the frontend and register/login
- Upload a single scanned image via the UI
- Wait for the Celery worker to finish and verify the analysis page shows metrics
