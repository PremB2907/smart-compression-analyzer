# Project Audit: Smart Compression Analyzer

**Audit Date:** October 11, 2026  
**Auditor:** Senior Cloud & DevOps Engineer (Automated Technical Audit)  
**Repository Path:** `/home/prem/Prem Projects/smart-compression-analyzer-main`  
**Git Remote:** `https://github.com/PremB2907/smart-compression-analyzer`  
**Current Branch:** `main` (clean working tree aligned with `origin/main`)  

---

## 1. Executive Summary

**Smart Compression Analyzer** (internally titled *SecureArchive AI*) is a research-grade document compression and preservation analysis platform. The application is built around the empirical methodology of comparative document compression (evaluating JPEG, PNG, TIFF, PDF, WebP, and DjVu) combined with LSB steganographic watermark preservation and Optical Character Recognition (OCR) error-rate metrics.

The platform provides a dual-interface architecture:
1. **Next.js 15 Frontend Dashboard:** User-facing analytics, upload management, format comparison, and visualization.
2. **FastAPI & Celery Backend:** Asynchronous processing pipeline, mathematical metric calculation, storage abstraction, and RESTful API endpoints.
3. **Batch CLI (`batch_process.py`):** Standalone research tool for running the pipeline across local image collections.

---

## 2. Git & Repository Status

- **Working Directory:** `/home/prem/Prem Projects/smart-compression-analyzer-main`
- **Remote Configuration:**
  - `origin` -> `https://github.com/PremB2907/smart-compression-analyzer` (fetch & push)
- **Active Branch:** `main` tracking `origin/main`
- **Recent Commit Log:**
  - `fb37cab`: `chore: update local development database schema and seed data`
  - `537536e`: `feat: implement file serving for local storage and integrate presigned URLs into analysis API and comparison UI.`
  - `614ce8e`: `fix: ignore infinite and NaN values when calculating dashboard averages`
  - `a769841`: `fix: align initial upload status with processing flow and improve celery state resolution logic`
  - `f5d7e48`: `feat: add authentication check to document upload page`

---

## 3. Architecture & Technology Stack

### 3.1 Backend
- **Language / Runtime:** Python 3.11+ (verified running on Python 3.14.4 virtual environment `.venv`)
- **Framework:** FastAPI (`fastapi>=0.111.0`, `uvicorn>=0.30.0`, `pydantic>=2.7.0`)
- **Database ORM:** SQLAlchemy 2.0 with SQLite (`sqlite:///./dev.db`) in local development and PostgreSQL 16 supported in Docker
- **Task Queue & Broker:** Celery 5.4 with Redis (`redis://localhost:6379`). Supports synchronous local execution via `CELERY_TASK_ALWAYS_EAGER=true`
- **Storage Layer (`backend/app/services/storage.py`):**
  - MinIO / S3 object store client with automated probe and retry logic (`minio` SDK).
  - Local filesystem fallback mechanism targeting `uploads/_local_storage` when MinIO is unreachable.
- **Image Processing & Scientific Compute:** NumPy, Pillow, OpenCV (headless), scikit-image, tifffile, img2pdf, pikepdf, pytesseract

### 3.2 Frontend
- **Framework:** Next.js 15.3.0 (React 19, TypeScript)
- **Styling:** Tailwind CSS, Radix UI primitives, Lucide icons
- **Data Visualization:** Recharts
- **Pages / Routes:**
  - `/` (Home landing page)
  - `/login` (Authentication)
  - `/dashboard` (Aggregated analytics & format leaderboards)
  - `/upload` (Document upload & processing pipeline trigger)
  - `/compare` (Side-by-side format inspection & metric diffs)
  - `/djvu` (DjVu-specific analysis)
  - `/research` (Research tables & exports)

### 3.3 CI/CD & Automation
- Pre-commit hooks configured (`.pre-commit-config.yaml` with Ruff)
- No GitHub Actions workflows currently exist under `.github/workflows/`

---

## 4. Compression Codecs & Integrity Metrics

### 4.1 Supported Formats & Implementations
| Format | Codec / Library | Configuration Parameters |
|---|---|---|
| **JPEG** | Pillow (`PIL.Image`) | Quality = 75, Standard DCT |
| **PNG** | Pillow (`PIL.Image`) | Compression level = 6, Optimize = True |
| **TIFF** | `tifffile` / Pillow | Compression = LZW / Deflate |
| **PDF** | `img2pdf` / `pikepdf` | JPEG2000 / Lossless embedding raster |
| **WebP** | Pillow (`PIL.Image`) | Quality = 75 |
| **DjVu** | Subprocess `c44` (DjVuLibre) | `-slice 74` (fallback gracefully handled if binary missing) |

### 4.2 Pipeline Workflow (`backend/app/services/pipeline.py`)
1. **Preprocessing:** Greyscale normalization, Gaussian smoothing ($\sigma=0.5$), and deskewing via Tesseract OSD.
2. **Standardization:** Resizing to reference raster ($1000 \times 1414$ pixels).
3. **Steganographic Embedding:** Injects 968-bit binary payload (32-char UUID + 25-char ISO timestamp + 64-char SHA-256 checksum) into least significant bits (LSB).
4. **Multi-Format Compression:** Encodes raster into all 6 formats, recording compression duration.
5. **Decompression & Analysis:** Decodes formats to greyscale rasters, measuring:
   - **Compression Ratio (CR):** $S_{original} / S_{compressed}$
   - **Mean Squared Error (MSE) & PSNR:** Reconstruction fidelity against uncompressed reference
   - **SSIM:** Structural similarity index
   - **OCR Character Error Rate (CER):** Levenshtein distance between OCR output on compressed image vs ground truth text
   - **Bit Error Rate (BER):** Fraction of corrupted bits extracted from LSB payload after lossy/lossless compression

---

## 5. Security & Risk Analysis

- **File Upload Protection:**
  - Filename and extension whitelisting (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.pdf`).
  - Size limitation enforced at application level (`max_upload_size_mb = 50 MB`).
  - SHA-256 checksum computation on upload.
- **Path Traversal Defense:** Temporary files created using `tempfile.NamedTemporaryFile` with random safe prefixes; file keys generated using UUID4 identifiers.
- **Resource Exhaustion & Concurrency:** Concurrency limits on Celery worker (`CELERY_WORKER_CONCURRENCY=1`, `CELERY_TASK_TIME_LIMIT_SEC=600`).
- **Secrets Management:** Environment variables loaded via Pydantic `Settings`. Secret key validation checks for production defaults.

---

## 6. Current Test Suite Status

Running `pytest -v` via the active Python 3.14 virtual environment:
- **Total Tests:** 50 tests executed
- **Pass Rate:** 100% (50 passed, 0 failed, 1 deprecation warning)
- **Duration:** 2.52 seconds
- **Test Categories:**
  - `tests/test_bug_conditions.py`: Edge cases, zero divisions, extreme compression values.
  - `tests/test_preservation.py`: Codec stability, metric preservation, payload roundtrips.
  - `tests/test_properties.py`: Hypothesis property-based testing of image normalization and stego algorithms.
  - `backend/tests/test_api.py`: FastAPI route execution, token handling, upload validation.
  - `backend/tests/test_pipeline.py`: End-to-end pipeline execution on demo test pages.

---

## 7. Cloud Integration Feasibility (Floci)

- **Target Emulator:** Floci (`https://github.com/floci-io/floci`), an open-source, AWS-compatible local cloud service emulator exposing standard AWS APIs on port `4566`.
- **Planned Cloud Mapping:**
  1. **Storage (Amazon S3 compatible):** Transition `StorageService` to interact with Floci S3 endpoints (`http://localhost:4566`) using `boto3`, retaining the local fallback mode.
  2. **Job & Run Metadata (Amazon DynamoDB compatible):** Store job status, compression run metrics, and analysis summaries in a DynamoDB table (`smart-compression-jobs`).
  3. **Task Queue (Amazon SQS compatible):** Dispatch compression jobs to an SQS queue (`smart-compression-tasks`) processed by a worker service.
  4. **Multi-Mode Support:** Configurable `CLOUD_MODE`: `floci` (active AWS emulator) vs `local` (in-memory/SQLite + local directory).
