"""add an unique index one VehicleJourney(navitia_id, circulation_date)

Revision ID: 3565adec8c85
Revises: bb47e3fc587
Create Date: 2015-09-15 17:14:31.001863

"""

# revision identifiers, used by Alembic.
revision = '3565adec8c85'
down_revision = 'bb47e3fc587'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_unique_constraint('vehicle_journey_navitia_id_circulation_date_idx', 'vehicle_journey', ['navitia_id', 'circulation_date'])


def downgrade():
    op.drop_constraint('vehicle_journey_navitia_id_circulation_date_idx', 'vehicle_journey', type_='unique')
