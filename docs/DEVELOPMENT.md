# Development guide

## Full application setup

### 1. Configure the environment

Install Docker with the Docker Compose plugin, then clone the repository:

```bash
git clone https://github.com/Achraf-Tahiri/Smart-CV.git
cd Smart-CV
cp .env.example .env
```

Edit `.env` before starting. Set your own `JWT_SECRET_KEY` and replace the example database and storage credentials. Add a provider API key if you want to enable structured CV extraction.

### 2. Build and start the services

```bash
docker compose build
docker compose up -d postgres redis minio
docker compose run --rm -T api uv run --frozen alembic upgrade head
docker compose run --rm -T api uv run --frozen \
  python -m app.scripts.create_admin \
  --email admin@example.com \
  --password 'replace-with-a-strong-password'
docker compose up -d api worker web
```

The first build can take time because the backend includes OCR tools and CPU PyTorch. Re-running the admin command for an existing account resets its password and restores its administrator role.

With the supplied `.env.example` defaults:

| Service | Address |
| --- | --- |
| Web application | http://localhost:3000 |
| Interactive API documentation | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |

Log in with the administrator credentials you set above. Create a candidate manually or upload a CV to start processing it.

If ports 3000 or 8000 are already in use, change `WEB_PORT` and `API_PORT` in `.env`. Keep `CORS_ORIGINS` aligned with the frontend URL and rebuild the web image after changing the API port, since its API URL is embedded at build time.

## Configuration

See [`.env.example`](../.env.example) for the available settings. Keep real credentials in your local `.env`, which is excluded from Git.

| Setting | Purpose |
| --- | --- |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `HF_API_TOKEN` | Credentials for structured extraction and natural-language search providers |
| `LLM_PROVIDER_ORDER` | Provider fallback order; defaults to `groq,gemini,hf` |
| `GROQ_MODEL`, `GEMINI_MODEL`, `HF_MODEL` | Model identifiers for the configured providers |
| `EMBEDDINGS_BACKEND` | `deterministic` for local testing or `sentence-transformers` for semantic search |
| `EMBEDDINGS_MODEL` | Embedding model; defaults to `intfloat/multilingual-e5-base` |
| `S3_PUBLIC_ENDPOINT_URL` | Browser-accessible storage URL used for signed downloads |
| `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON` | Base64-encoded Google service account JSON for Drive imports |
| `GOOGLE_DRIVE_FOLDER_ID` | Default Drive folder to import |
| `RETENTION_DAYS` | Candidate retention period; `0` disables automatic deletion |

Without a configured extraction provider, documents can still be uploaded and stored, but processing falls back to manual review. Provider availability depends on your account and the configured model identifiers.

The default deterministic embedding backend does **not** provide semantic similarity. Set `EMBEDDINGS_BACKEND=sentence-transformers` to enable semantic embeddings; the model is downloaded on first use and cached in the `hf-cache` Docker volume. After switching backends, rebuild existing candidate embeddings:

```bash
docker compose run --rm -T api uv run --frozen \
  python -m app.scripts.reembed_candidates --dry-run
docker compose run --rm -T api uv run --frozen \
  python -m app.scripts.reembed_candidates
```

## Development and verification

### Backend

With the Docker images built and PostgreSQL running:

```bash
docker compose run --rm -T api uv run --frozen ruff check src tests
docker compose run --rm -T api uv run --frozen black --check src tests
docker compose run --rm -T api uv run --frozen pytest
```

Integration tests create and reset a dedicated database named `<database>_test`. Rebuild the API image after source changes when testing the container image.

### Frontend

For local frontend development, install Node.js 24 and pnpm 9, then run:

```bash
cd apps/web
cp .env.local.example .env.local
pnpm install
pnpm dev
```

Keep `NEXT_PUBLIC_API_URL` in `.env.local` aligned with your running API. Stop the Compose web service first if you want the local development server to use the same port.

```bash
pnpm test
pnpm build
```

The Playwright smoke test requires a running application, an administrator account, and at least one candidate:

```bash
pnpm exec playwright install chromium
E2E_BASE_URL=http://localhost:3000 \
E2E_ADMIN_EMAIL=admin@example.com \
E2E_ADMIN_PASSWORD='your-test-account-password' \
  pnpm test:e2e
```

GitHub Actions is configured to run backend linting, formatting checks, and tests, plus a frontend production build.


## Legacy prototype import

The optional `app.scripts.migrate_poc` utility imports a compatible SQLite
prototype database into PostgreSQL. Source data is never part of this repository.
Use synthetic records when testing the importer; do not publish source databases
or exports.
