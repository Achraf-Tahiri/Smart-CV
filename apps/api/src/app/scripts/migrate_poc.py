"""Migration des données du POC (SQLite dénormalisé) vers le schéma Postgres.

Réutilise le mapping `CVExtraction` + `ingestion.apply_extraction` : les données
déjà extraites par le POC (pas de LLM nécessaire) peuplent candidats + parcours +
compétences + langues + embeddings, et deviennent immédiatement recherchables.

Usage (POC monté en lecture seule) :
    docker compose run --rm --no-deps -T \\
      -v "/chemin/vers/Smart_CV/data:/poc:ro" \\
      api uv run --frozen python -m app.scripts.migrate_poc --sqlite /poc/cv_database.db

Idempotent : les lignes déjà migrées (marqueur `_poc_id`) sont ignorées.
Non destructif côté POC (lecture seule). Les fichiers binaires ne sont PAS
importés (souvent indisponibles) : aucun document rattaché aux candidats migrés.
"""

import argparse
import asyncio
import json
import sqlite3
import sys
import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.candidate import Candidate
from app.models.enums import CandidateStatus, Source
from app.providers.embeddings import get_embeddings
from app.schemas.extraction import CVExtraction
from app.services import ingestion

_STATUS_MAP = {
    "SUCCESS": CandidateStatus.success,
    "MANUAL_REVIEW": CandidateStatus.manual_review,
    "OCR_FAILED": CandidateStatus.failed,
}


def poc_status(value: str | None) -> CandidateStatus:
    return _STATUS_MAP.get((value or "").upper(), CandidateStatus.manual_review)


def poc_source(value: str | None) -> Source:
    return Source.google_drive if (value or "").lower() == "google_drive" else Source.local


def _split_csv(value: object) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def poc_row_to_extraction(row: dict) -> CVExtraction:
    """Transforme une ligne POC (dénormalisée) en `CVExtraction` structurée."""
    details: dict = {}
    if row.get("details_json"):
        try:
            details = json.loads(row["details_json"])
        except (json.JSONDecodeError, TypeError):
            details = {}
    return CVExtraction(
        prenom=row.get("prenom") or None,
        nom=row.get("nom") or None,
        email=row.get("email") or None,
        telephone=row.get("telephone") or None,
        ville=row.get("ville") or None,
        poste_actuel=row.get("poste_actuel") or None,
        secteur=row.get("secteur") or "Autre",  # coercé dans la taxonomie par le schéma
        specialite=row.get("specialite") or None,
        experiences=details.get("experiences") or [],
        activites_extra=details.get("activites_extra") or [],
        formations=details.get("formations") or [],
        hard_skills=_split_csv(row.get("hard_skills")),
        soft_skills=_split_csv(row.get("soft_skills")),
        langues=_split_csv(row.get("langues")),
    )


async def _existing_poc_ids(session) -> set:
    rows = (await session.execute(select(Candidate.raw_extraction))).scalars().all()
    return {r["_poc_id"] for r in rows if isinstance(r, dict) and "_poc_id" in r}


async def migrate(sqlite_path: str, limit: int | None = None) -> tuple[int, int, int]:
    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    poc_rows = [dict(r) for r in con.execute("SELECT * FROM candidats").fetchall()]
    con.close()
    if limit:
        poc_rows = poc_rows[:limit]

    embeddings = get_embeddings()
    created = skipped = errors = 0

    async with AsyncSessionLocal() as session:
        already = await _existing_poc_ids(session)
        for row in poc_rows:
            poc_id = row["id"]
            if poc_id in already:
                skipped += 1
                continue
            try:
                extraction = poc_row_to_extraction(row)
                candidate = Candidate(
                    id=uuid.uuid4(),
                    source=poc_source(row.get("source")),
                    status=poc_status(row.get("status")),
                    created_by_id=None,
                )
                session.add(candidate)
                await session.flush()
                await ingestion.apply_extraction(session, candidate, extraction, embeddings)
                candidate.raw_extraction = {**extraction.model_dump(), "_poc_id": poc_id}
                await session.commit()
                created += 1
            except Exception as exc:  # une ligne fautive ne bloque pas les autres
                await session.rollback()
                errors += 1
                print(f"  ⚠️ ligne POC {poc_id} ignorée : {exc}", file=sys.stderr)

    return created, skipped, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Migre les données du POC vers Postgres.")
    parser.add_argument("--sqlite", required=True, help="Chemin du fichier SQLite du POC.")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de lignes.")
    args = parser.parse_args()

    created, skipped, errors = asyncio.run(migrate(args.sqlite, args.limit))
    print(
        f"✅ Migration terminée : {created} créés, {skipped} déjà présents, {errors} erreurs.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
