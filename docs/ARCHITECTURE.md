# SecureArchive AI — Architecture

## Overview

SecureArchive AI is a research-grade SaaS platform that implements the comparative compression methodology from the paper *Comparative Analysis of Compression Formats for OCR Preservation and Secure Data Embedding with Emphasis on DjVu*.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Next.js 15 │────▶│  FastAPI API │────▶│  Celery Workers │
│  Frontend   │     │  (REST/JWT)  │     │  (Pipeline)     │
└─────────────┘     └──────┬───────┘     └────────┬────────┘
                           │                       │
                    ┌──────┴───────┐        ┌──────┴──────┐
                    │ PostgreSQL   │        │ MinIO       │
                    │ Redis        │        │ (artifacts) │
                    └──────────────┘        └─────────────┘
```

## Processing Pipeline (Paper-Aligned)

1. **Preprocess** — greyscale normalization, Gaussian σ=0.5, deskew (Tesseract OSD)
2. **Resize** — 1000×1414 reference raster
3. **LSB embed** — 968-bit payload (UUID + timestamp + SHA-256), `p̃_k = (p_k & 0xFE) | b_k`
4. **Compress** — JPEG Q=75, PNG L6, TIFF LZW, PDF JPEG2000 ~10:1, WebP Q=75, DjVu `c44 -slice 74`
5. **Decompress** — decode to greyscale for metrics and payload extraction
6. **Metrics** — CR, MSE, PSNR, SSIM, OCR (CER), BER, payload recovery, encode/decode timing

## Repository Layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI, SQLAlchemy, Celery, MinIO integration |
| `frontend/` | Next.js 15 dashboard and analysis UI |
| `compression/` | Format encoders (paper parameters) |
| `metrics/` | CR, MSE, PSNR, SSIM, OCR, BER |
| `utils/` | Preprocessing, LSB steganography |
| `dataset/` | Demo images for research reproduction |
| `docker-compose.yml` | Full local stack |

## Security

- JWT authentication (OAuth2 password flow)
- RBAC: `admin`, `researcher`, `viewer`
- Upload extension and size validation
- SHA-256 checksums on uploads
- Audit log for auth and upload events

## AI Extensions (Beyond Paper)

Heuristic document-type classifier and pre-compression metric predictor in `backend/app/services/ai_extensions.py`.
