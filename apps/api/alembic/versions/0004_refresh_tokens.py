"""refresh tokens (Phase 5c)

Revision ID: 0004_refresh_tokens
Revises: 0003_search
Create Date: 2026-08-10

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# Identifiants de révision utilisés par Alembic.
revision: str = '0004_refresh_tokens'
down_revision: str | None = '0003_search'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('refresh_tokens',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('replaced_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
