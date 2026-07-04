"""institutions.upi_vpa + users login-lockout columns

- upi_vpa: the franchise's UPI ID for QR fee collection (Phase 1 UPI:
  student scans, pays, receptionist records the UTR — no gateway).
- failed_login_count / locked_until: DB-backed brute-force lockout on
  /api/auth/login (in-memory limiters do not survive serverless).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('institutions', sa.Column('upi_vpa', sa.String(), nullable=True))
    op.add_column('users', sa.Column('failed_login_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_count')
    op.drop_column('institutions', 'upi_vpa')
