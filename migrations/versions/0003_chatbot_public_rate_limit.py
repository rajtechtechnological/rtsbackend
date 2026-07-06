"""chatbot_rate_limits table

DB-backed per-IP throttle for the new public (unauthenticated) chatbot
endpoints — same reasoning as the 0002 login lockout: in-memory limiters
do not survive Vercel's stateless serverless functions.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-05

"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chatbot_rate_limits',
        sa.Column('ip_hash', sa.String(), nullable=False),
        sa.Column('minute_bucket', sa.BigInteger(), nullable=False),
        sa.Column('minute_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('day_bucket', sa.Date(), nullable=False),
        sa.Column('day_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('ip_hash'),
    )


def downgrade() -> None:
    op.drop_table('chatbot_rate_limits')
