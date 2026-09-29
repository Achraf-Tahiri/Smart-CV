# Smart CV

A full-stack recruitment application that turns CV documents into searchable candidate profiles. Smart CV combines document parsing, OCR, structured information extraction, and hybrid search in a FastAPI backend with a Next.js interface.

**Status:** working MVP under active development. The application interface is currently in French.

## Features

- **Candidate management:** create, edit, browse, and delete profiles with work experience, education, skills, languages, and attached documents.
- **Document ingestion:** upload CVs, detect duplicate files by content hash, store originals in MinIO, and process them asynchronously through an Arq/Redis worker.
- **Text extraction and OCR:** extract text from PDF and DOCX files, with Tesseract support for scanned PDFs and images in French and English.
- **Structured CV extraction:** validate extracted information with Pydantic and use a configurable fallback chain of Groq, Gemini, and Hugging Face providers.
- **Search:** filter candidates by name, city, sector, and experience; combine PostgreSQL full-text search with pgvector similarity search. A natural-language search endpoint is also available through the API.
- **Dashboard:** view candidate totals and breakdowns by processing status, seniority, and sector.
- **Authentication and permissions:** JWT access tokens, rotating refresh tokens, login rate limiting, and administrator, recruiter, and reader roles.
- **Google Drive integration:** queue folder imports through administrator API endpoints, with duplicate detection and retry handling.
- **Audit and data management:** audit logs, per-candidate data export, and configurable retention with a preview mode. Automatic deletion is disabled by default.

## Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Radix UI |
| API | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 async |
| Database | PostgreSQL 16, pgvector, Alembic |
| Background jobs | Arq, Redis |
| Document storage | MinIO / S3-compatible storage |
| Extraction | pdfplumber, python-docx, Tesseract, configurable LLM providers |
| Embeddings | sentence-transformers, multilingual-e5-base, CPU PyTorch |
| Testing | pytest, Vitest, Testing Library, Playwright |
| Tooling | Docker Compose, uv, pnpm, Ruff, Black, GitHub Actions |

## Architecture

The frontend calls the FastAPI API for authentication, candidate management, search, and document uploads. Original documents are stored in MinIO; candidate records and search indexes live in PostgreSQL.

Document processing runs outside the HTTP request cycle. The API queues a job in Redis, and an Arq worker extracts text, parses the CV into structured data, normalizes the profile, and stores its search embedding. The frontend follows the candidate's processing status.

External integrations are grouped behind provider interfaces for language models, embeddings, storage, and Google Drive. Tests use local substitutes for these services where appropriate.

```text
apps/
  api/
    src/app/
      api/routes/       HTTP endpoints
      core/             Configuration, logging, security, and job queue
      db/               Database sessions and model base
      domain/           Date normalization, experience calculation, taxonomies
      models/           SQLAlchemy models
      schemas/          Pydantic request and response schemas
      providers/        Language models, embeddings, storage, and Google Drive
      services/         Candidate, ingestion, search, and data management logic
      scripts/          Admin setup, migration, retention, and re-embedding
      worker.py         Background jobs and scheduled retention task
    alembic/            Database migrations
    tests/              Backend tests
  web/
    src/                Next.js pages, components, and API client
    e2e/                Playwright smoke test
infra/postgres/init/     PostgreSQL extension initialization
docs/                   Domain migration notes and design tokens
docker-compose.yml      Local application stack
```

## Quick start

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

See [`.env.example`](.env.example) for the available settings. Keep real credentials in your local `.env`, which is excluded from Git.

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

## Migrating data from the original prototype

An optional import script migrates already extracted candidate data from the original SQLite prototype into PostgreSQL:

```bash
docker compose run --rm -T \
  -v "/path/to/Smart_CV/data:/poc:ro" \
  api uv run --frozen python -m app.scripts.migrate_poc \
  --sqlite /poc/cv_database.db
```

The import reads the source database without modifying it and can be re-run without creating duplicate candidates.

## Next steps

- Expand end-to-end test coverage for imports and candidate editing.
- Improve bulk import controls and visibility into background jobs.
- Add an English application interface.
- Prepare deployment documentation, performance checks, and further production hardening.
