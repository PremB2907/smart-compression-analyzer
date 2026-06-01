# Continuous Integration

## Workflow

GitHub Actions runs on every push/PR to `main` or `master`:

1. **lint** — `ruff check .` and `mypy --explicit-package-bases backend/app compression metrics utils`
2. **backend-tests** — `pytest` with ephemeral Postgres (credentials are CI-only, not production secrets)
3. **frontend-build** — `npm run build` in `frontend/`

## Repository secrets (optional)

CI uses built-in test credentials for Postgres. For deployments or stricter CI, set these in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `SECRET_KEY` | JWT signing (min 32 chars) |
| `POSTGRES_PASSWORD` | Database password |
| `MINIO_ROOT_PASSWORD` | Object storage |
| `NEXTAUTH_SECRET` | Next.js session encryption |

Local development values live in [`.env.example`](../.env.example). Never commit `.env`.

## Badge

After pushing to GitHub, replace `YOUR_USER` and `YOUR_REPO` in `README.md`:

```markdown
[![CI](https://github.com/YOUR_USER/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USER/YOUR_REPO/actions/workflows/ci.yml)
```
