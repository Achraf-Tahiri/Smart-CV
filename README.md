# New Smart CV

Application de gestion et de recherche de CV pour le recrutement — réécriture **production** du POC *Smart CV*.

> **Statut : MVP complet ✅ + ingestion asynchrone.** Phases 0 à 2 (backend) + front + worker (Phase 3a). Auth JWT & rôles, CRUD candidats, upload + stockage MinIO, extraction IA structurée (cascade LLM), OCR, embeddings, **pipeline d'ingestion asynchrone** (worker Arq/Redis), recherche hybride (plein-texte + vecteurs), et un front Next.js complet (login, tableau de bord, recherche, fiche riche, création/édition, import). 94 tests back.

## Stack

- **Backend** : FastAPI (async) · Pydantic v2 · SQLAlchemy 2.0 async · Alembic
- **Base de données** : PostgreSQL + pgvector
- **Frontend** : Next.js (App Router) · TypeScript · Tailwind · shadcn/ui
- **Infra** : Docker Compose (Postgres, Redis, MinIO) · GitHub Actions
- **IA** (Phase 2) : LLM en cascade gratuite (Groq/Gemini/HF) derrière une abstraction · embeddings locaux (sentence-transformers) · OCR Tesseract
- **Outils** : uv (Python) · pnpm (Node) · ruff/black · structlog

## Arborescence

```
apps/
  api/                     API FastAPI
    src/app/
      core/                config, logging, sécurité
      db/                  session + base SQLAlchemy
      models/              tables ORM
      schemas/             DTO Pydantic v2
      api/routes/          endpoints HTTP (auth, candidates, documents)
      domain/              logique métier PURE portée du POC (dates, expérience, taxonomies, nettoyage)
      services/            orchestration (auth, candidats, documents, extraction, ingestion, recherche)
      providers/           abstractions : llm · embeddings · storage · drive
    alembic/               migrations
    tests/                 pytest
  web/                     front Next.js
infra/postgres/init/       init SQL (extension pgvector)
docker-compose.yml         stack locale
```

**Principe directeur** : chaque brique externe/remplaçable vit dans `providers/` derrière une interface → passer de gratuit/local à payant/cloud = changer une variable d'environnement, pas le code.

## Prérequis

- Docker + Docker Compose (obligatoire)
- `make` (raccourcis de commandes, optionnel) — `sudo apt-get install -y make`
- Optionnel, pour le développement hors conteneur : uv (Python) et pnpm (Node), installés en Phase 0.2/0.5.

## Démarrage rapide

```bash
cp .env.example .env                        # ajuster si besoin (ports, clés API)
docker compose build                        # api (OCR inclus) + web
docker compose up -d                        # postgres + minio + api + web

# Migrer la base et créer l'administrateur initial :
docker compose run --rm --no-deps -T api uv run --frozen alembic upgrade head
docker compose run --rm --no-deps -T api uv run --frozen \
  python -m app.scripts.create_admin --email admin@example.com --password 'password123'
```

- **Front** : http://localhost:3001 (login, recherche, fiche, import)
- **API / docs** : http://localhost:8001/docs
- **Console MinIO** : http://localhost:9001 (`minioadmin` / `minioadmin`)

> Les ports par défaut 3000 et 8000 étant souvent déjà pris, ce projet utilise
> `WEB_PORT=3001` et `API_PORT=8001` (configurables dans `.env`).

**Extraction IA réelle** : renseigner une clé `GROQ_API_KEY` (ou `GEMINI_API_KEY` /
`HF_API_TOKEN`) dans `.env`. Sans clé, l'import stocke le CV mais laisse le candidat
en statut `manual_review`. Embeddings sémantiques réels : `EMBEDDINGS_BACKEND=sentence-transformers`.

### Peupler avec les données du POC (optionnel)

Importe les CV déjà analysés par le POC (SQLite → Postgres, sans IA) :

```bash
docker compose run --rm --no-deps -T \
  -v "/chemin/vers/Smart_CV/data:/poc:ro" \
  api uv run --frozen python -m app.scripts.migrate_poc --sqlite /poc/cv_database.db
```

Idempotent (relançable sans doublon), lecture seule côté POC.

## Vérifications (dans Docker)

```bash
# Lint + format + tests (monter la source pour refléter le code courant) :
docker compose up -d postgres
docker compose run --rm --no-deps -T \
  -v "$PWD/apps/api/src:/app/src" -v "$PWD/apps/api/tests:/app/tests" \
  api uv run pytest
```

## Configuration

Toutes les variables sont documentées dans `.env.example`. Le fichier `.env` réel est **ignoré par git** ; ne commit jamais de secrets (clés API, `credentials.json` Google Drive).

## Feuille de route

| Phase | Contenu | Statut |
|-------|---------|--------|
| 0 | Fondations : mono-repo, Docker Compose, healthcheck, CI | ✅ |
| 1 | Modèle de données + migrations, auth + rôles, CRUD candidats, upload MinIO | ✅ |
| 2 | IA : extraction structurée, OCR, embeddings, recherche hybride | ✅ |
| — | Front MVP : login, recherche, fiche, import | ✅ |
| 3a | File de jobs async (worker Arq/Redis) — ingestion non bloquante | ✅ |
| 3b | Google Drive async, imports en masse | à venir |
| 4 | Produit : dashboard, édition, export, polish UI (shadcn/TanStack) | à venir |
| 5 | Sécurité & RGPD (rétention, effacement, durcissement) | à venir |
| 6 | Production : déploiement cloud, tests de charge, documentation client | à venir |
