"""
Add an attribut validity of type boolean which will contain the validity of inserted gtfs-rt

Revision ID: 3a12525235bf
Revises: 2763a0e3f0bf
Create Date: 2017-12-28 14:56:25.238546

"""

# revision identifiers, used by Alembic.
revision = '3a12525235bf'
down_revision = '2763a0e3f0bf'

from alembic import op
import sqlalchemy as sa

rt_validity = sa.Enum('valid', 'empty', 'invalid', name='rt_validity')


def upgrade():
    rt_validity.create(op.get_bind())
    op.add_column('real_time_update', sa.Column('validity', rt_validity, nullable=True))
    op.execute("UPDATE real_time_update SET validity = 'valid' WHERE validity IS NULL")
    op.alter_column('real_time_update', 'validity', nullable=False)
    op.create_index('ix_rt_validity', 'real_time_update', ['validity'], unique=False)


def downgrade():
    op.drop_index('ix_rt_validity', 'real_time_update')
    op.drop_column('real_time_update', 'validity')
    rt_validity.drop(op.get_bind())
