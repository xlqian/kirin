"""empty message

Revision ID: 174583a01aea
Revises: 4d9df787c7a7
Create Date: 2018-11-28 14:58:50.362398

"""

# revision identifiers, used by Alembic.
revision = '174583a01aea'
down_revision = '4d9df787c7a7'

from alembic import op

def upgrade():
    op.execute("ALTER type modification_type ADD VALUE 'deleted_for_detour'")
    op.execute("ALTER type modification_type ADD VALUE 'added_for_detour'")

def downgrade():
    """
    Postgresql doesn't support the removal of a specific enum value
    """
    pass
