# API New Smart CV — image simple (Phase 0.2).
# Le contexte de build est apps/api/.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# uv : gestionnaire de paquets Python rapide (version figée = builds reproductibles).
RUN pip install --no-cache-dir uv==0.12.2

WORKDIR /app

# 1) Dépendances d'abord : couche mise en cache tant que pyproject/uv.lock ne changent pas.
#    `--frozen` installe EXACTEMENT les versions du lockfile (aucune résolution au build).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 2) Code applicatif + tests + migrations.
COPY src ./src
COPY tests ./tests
COPY alembic.ini ./
COPY alembic ./alembic

# 3) Installer le projet lui-même (le package `app`).
RUN uv sync --frozen

# Le venv créé par uv est ajouté au PATH : on lance uvicorn directement,
# sans repasser par `uv run` (démarrage instantané, pas de resync au boot).
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
