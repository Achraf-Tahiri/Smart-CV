"""recherche hybride : search_text + tsvector genere + index GIN/HNSW

Revision ID: 0003_search
Revises: 0002_schema_initial
Create Date: 2026-08-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_search"
down_revision: str | None = "0002_schema_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Colonne texte de recherche (remplie à l'ingestion) + tsvector généré (indexé).
    op.add_column("candidates", sa.Column("search_text", sa.Text(), nullable=True))
    op.add_column(
        "candidates",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('french', coalesce(search_text, ''))", persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_candidates_search_vector",
        "candidates",
        ["search_vector"],
        postgresql_using="gin",
    )
    # Index vectoriel HNSW (distance cosinus) pour la recherche sémantique.
    op.create_index(
        "ix_candidate_embeddings_hnsw",
        "candidate_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_embeddings_hnsw", table_name="candidate_embeddings")
    op.drop_index("ix_candidates_search_vector", table_name="candidates")
    op.drop_column("candidates", "search_vector")
    op.drop_column("candidates", "search_text")
