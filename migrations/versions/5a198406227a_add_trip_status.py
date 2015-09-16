"""add of status to trip_update

Revision ID: 5a198406227a
Revises: bb47e3fc587
Create Date: 2015-09-16 17:02:52.058237

"""

# revision identifiers, used by Alembic.
revision = '5a198406227a'
down_revision = '3565adec8c85'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('trip_update', sa.Column('status', sa.Enum('add', 'delete', 'update', 'none', name='modification_type'), nullable=False))


def downgrade():
    op.drop_column('trip_update', 'status')
