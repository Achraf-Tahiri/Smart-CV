"""Recalcule les embeddings de TOUS les candidats avec le backend courant.

À lancer après avoir basculé `EMBEDDINGS_BACKEND` (ex. `deterministic` →
`sentence-transformers`) : les anciens vecteurs stockés en base sont
incompatibles (espaces vectoriels différents) et doivent être régénérés,
sinon la recherche sémantique renvoie du bruit.

Cohérence stricte avec l'ingestion (`services/ingestion._persist_embedding`) :
- source : `candidate.search_text` (ou chaîne vide si nul) ;
- méthode : `embeddings.embed_documents([text])` (le provider e5 ajoute
  automatiquement le préfixe `passage: `).

Ne supprime AUCUN candidat. Idempotent (delete + insert par lot).

Usages (dans Docker) :
    # Aperçu (compte les candidats, ne modifie rien) :
    docker compose run --rm --no-deps -T \\
      -v "$PWD/apps/api/src:/app/src" \\
      -e EMBEDDINGS_BACKEND=sentence-transformers \\
      api uv run --no-sync python -m app.scripts.reembed_candidates --dry-run

    # Réel :
    docker compose run --rm --no-deps -T \\
      -v "$PWD/apps/api/src:/app/src" \\
      -e EMBEDDINGS_BACKEND=sentence-transformers \\
      api uv run --no-sync python -m app.scripts.reembed_candidates
"""

import argparse
import asyncio
import sys

import structlog
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models.candidate import Candidate
from app.models.embedding import CandidateEmbedding
from app.providers.embeddings import get_embeddings

log = structlog.get_logger(__name__)


async def _run(batch_size: int, dry_run: bool) -> int:
    embeddings = get_embeddings()
    model_name = embeddings.__class__.__name__

    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count()).select_from(Candidate))).scalar_one()
        if dry_run:
            print(
                f"[DRY-RUN] {total} candidat(s) à ré-embedder avec {model_name} "
                f"(dim={embeddings.dimension}). Aucune modification.",
                file=sys.stderr,
            )
            return total

        if total == 0:
            print("Aucun candidat en base — rien à faire.", file=sys.stderr)
            return 0

        processed = 0
        offset = 0
        while True:
            rows = (
                await session.execute(
                    select(Candidate.id, Candidate.search_text)
                    .order_by(Candidate.id)
                    .offset(offset)
                    .limit(batch_size)
                )
            ).all()
            if not rows:
                break

            texts = [(row.search_text or "") for row in rows]
            vectors = await embeddings.embed_documents(texts)

            ids = [row.id for row in rows]
            await session.execute(
                delete(CandidateEmbedding).where(CandidateEmbedding.candidate_id.in_(ids))
            )
            for candidate_id, vector in zip(ids, vectors, strict=True):
                session.add(
                    CandidateEmbedding(
                        candidate_id=candidate_id,
                        embedding=vector,
                        model_name=model_name,
                    )
                )
            await session.commit()

            processed += len(rows)
            offset += batch_size
            log.info(
                "reembed.batch",
                processed=processed,
                total=total,
                model=model_name,
            )
            print(f"  … {processed}/{total}", file=sys.stderr)

        print(
            f"✅ Ré-embedding terminé : {processed} candidat(s) traité(s) avec {model_name}.",
            file=sys.stderr,
        )
        return processed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalcule les embeddings de tous les candidats (backend courant)."
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Taille de lot (défaut 50).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne fait rien, compte seulement les candidats concernés.",
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size doit être >= 1")

    asyncio.run(_run(args.batch_size, args.dry_run))


if __name__ == "__main__":
    main()
