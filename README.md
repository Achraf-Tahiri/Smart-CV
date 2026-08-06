# New Smart CV

Application de gestion et de recherche de CV pour le recrutement — réécriture **production** du POC *Smart CV*.

> **Statut : Phase 0 (fondations) — en cours.** L'arborescence est en place ; l'API, la base de données et le front sont câblés incrément par incrément (0.2 → 0.6).

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
      models/              tables ORM (Phase 1)
      schemas/             DTO Pydantic v2
      api/routes/          endpoints HTTP
      services/            metier porte du POC (dates, experience, taxonomies)
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
cp .env.example .env      # puis renseigner les valeurs
make up                   # disponible à partir de la Phase 0.3
```

`make help` liste les raccourcis.

## Configuration

Toutes les variables sont documentées dans `.env.example`. Le fichier `.env` réel est **ignoré par git** ; ne commit jamais de secrets (clés API, `credentials.json` Google Drive).

## Feuille de route

| Phase | Contenu |
|-------|---------|
| 0 | Fondations : mono-repo, Docker Compose, healthcheck, CI |
| 1 | Modèle de données + migrations, auth + rôles, CRUD candidats, upload MinIO |
| 2 | IA : extraction structurée, embeddings, recherche hybride |
| 3 | Intégrations & jobs : Google Drive async, imports en masse |
| 4 | Produit : dashboard, fiche candidat, édition, export |
| 5 | Sécurité & RGPD |
| 6 | Production : déploiement cloud, tests de charge, documentation |
