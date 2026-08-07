"""Bootstrap du compte administrateur initial.

Usage (dans Docker) :
    docker compose run --rm api uv run python -m app.scripts.create_admin \\
        --email admin@example.com --password 'un-mot-de-passe-fort'

Les valeurs peuvent aussi venir des variables d'environnement
ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_FULL_NAME.

Idempotent : si le compte existe déjà, son mot de passe est réinitialisé et le
rôle `admin` (+ compte actif) est garanti — pratique pour reprendre la main.
"""

import argparse
import asyncio
import os
import sys

from pydantic import ValidationError

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate
from app.services import users as users_service


async def _upsert_admin(email: str, password: str, full_name: str | None) -> tuple[str, User]:
    """Crée ou met à jour l'admin. Retourne ('created'|'updated', user)."""
    async with AsyncSessionLocal() as session:
        existing = await users_service.get_by_email(session, email)
        if existing is not None:
            existing.hashed_password = hash_password(password)
            existing.role = UserRole.admin
            existing.is_active = True
            if full_name:
                existing.full_name = full_name
            await session.commit()
            return "updated", existing

        user = await users_service.create_user(
            session,
            UserCreate(email=email, password=password, full_name=full_name, role=UserRole.admin),
        )
        await session.commit()
        return "created", user


def main() -> None:
    parser = argparse.ArgumentParser(description="Crée/met à jour l'administrateur initial.")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    parser.add_argument("--full-name", default=os.getenv("ADMIN_FULL_NAME"))
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error(
            "email et mot de passe requis (--email/--password ou ADMIN_EMAIL/ADMIN_PASSWORD)."
        )

    # Valide format email + longueur du mot de passe avant de toucher la base.
    try:
        UserCreate(email=args.email, password=args.password, role=UserRole.admin)
    except ValidationError as exc:
        parser.error(f"données invalides : {exc}")

    action, user = asyncio.run(_upsert_admin(args.email, args.password, args.full_name))
    verb = "créé" if action == "created" else "mis à jour"
    print(f"✅ Administrateur {verb} : {user.email} (id={user.id})", file=sys.stderr)


if __name__ == "__main__":
    main()
