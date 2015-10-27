""" Add an order to the stoptime in order to sort the stoptimes in the TripUpdate

Revision ID: 51d2d334dd4f
Revises: d6469f134d7
Create Date: 2015-10-23 17:04:11.216638

"""

# revision identifiers, used by Alembic.
revision = '51d2d334dd4f'
down_revision = 'd6469f134d7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('stop_time_update', sa.Column('order', sa.Integer(), nullable=False))


def downgrade():
    op.drop_column('stop_time_update', 'order')
