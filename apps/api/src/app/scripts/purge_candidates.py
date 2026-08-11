"""Déclenchement manuel de la purge RGPD par rétention (Phase 5).

⚠️ La suppression est IRRÉVERSIBLE et EN CASCADE. Par sécurité, ce script est en
mode APERÇU (dry-run) PAR DÉFAUT : il n'efface RIEN tant qu'on ne passe pas
explicitement `--apply --yes`. Les CV migrés du POC (marqueur `_poc_id`) sont
toujours exclus par le service.

Exemples (POC de dev, conteneur `api`) :

    # Aperçu de ce qui SERAIT purgé avec la rétention configurée (RETENTION_DAYS) :
    docker compose run --rm --no-deps -T \\
      -v "$PWD/apps/api/src:/app/src" \\
      api uv run --no-sync python -m app.scripts.purge_candidates

    # Aperçu avec une rétention forcée (sans toucher au .env) :
    docker compose run --rm --no-deps -T -v "$PWD/apps/api/src:/app/src" \\
      api uv run --no-sync python -m app.scripts.purge_candidates --retention-days 365

    # Purge RÉELLE (confirmation explicite obligatoire) :
    docker compose run --rm --no-deps -T -v "$PWD/apps/api/src:/app/src" \\
      api uv run --no-sync python -m app.scripts.purge_candidates \\
        --retention-days 365 --apply --yes
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services import gdpr


async def _run(retention_days: int, batch_limit: int, apply: bool) -> int:
    async with AsyncSessionLocal() as session:
        if not apply:
            preview = await gdpr.preview_purge(
                session, retention_days=retention_days, batch_limit=batch_limit
            )
            if not preview.enabled:
                print(
                    "Purge DÉSACTIVÉE (RETENTION_DAYS <= 0). Rien à faire.",
                    file=sys.stderr,
                )
                return 0
            print(
                f"[DRY-RUN] {preview.total} candidat(s) éligible(s) "
                f"(> {retention_days} j, seuil {preview.cutoff:%Y-%m-%d}). "
                f"Affichage borné à {batch_limit} :",
                file=sys.stderr,
            )
            for item in preview.items:
                print(
                    f"  - {item.id}  {item.prenom or ''} {item.nom or ''}"
                    f"  (créé le {item.created_at:%Y-%m-%d}, {item.age_days} j)",
                    file=sys.stderr,
                )
            print(
                "\nAucune suppression effectuée. Ajoute `--apply --yes` pour purger.",
                file=sys.stderr,
            )
            return preview.total

        # Mode réel : suppression effective.
        purged = await gdpr.purge_expired_candidates(
            session, retention_days=retention_days, batch_limit=batch_limit
        )
        await session.commit()
        print(f"✅ Purge terminée : {len(purged)} candidat(s) supprimé(s).", file=sys.stderr)
        return len(purged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge RGPD par rétention (dry-run par défaut).")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=settings.retention_days,
        help="Ancienneté (jours) au-delà de laquelle purger. Défaut : RETENTION_DAYS du .env.",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=settings.retention_purge_batch_limit,
        help="Nombre max supprimé par exécution. Défaut : RETENTION_PURGE_BATCH_LIMIT.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Effectue la suppression réelle (sinon : aperçu seul).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirme explicitement la suppression IRRÉVERSIBLE (requis avec --apply).",
    )
    args = parser.parse_args()

    if args.apply and not args.yes:
        parser.error("Suppression IRRÉVERSIBLE : ajoute `--yes` pour confirmer `--apply`.")
    if args.apply and args.retention_days <= 0:
        parser.error("Rétention <= 0 : purge désactivée. Précise `--retention-days N` (N > 0).")

    asyncio.run(_run(args.retention_days, args.batch_limit, args.apply))


if __name__ == "__main__":
    main()
