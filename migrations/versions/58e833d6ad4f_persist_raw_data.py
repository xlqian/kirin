"""Add persist raw real time update data

Revision ID: 58e833d6ad4f
Revises: 434d1e68281b
Create Date: 2015-09-07 15:47:04.608884

"""

# revision identifiers, used by Alembic.
revision = '58e833d6ad4f'
down_revision = '434d1e68281b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():

    # https://bitbucket.org/zzzeek/alembic/issues/159/opdrop_column-never-ends-with-an-enum
    connector_type = sa.Enum('ire', 'gtfs-rt', name='connector_type')
    connector_type.create(bind=op.get_bind())
    rt_status = sa.Enum('OK', 'KO', 'pending', name='rt_status')
    rt_status.create(bind=op.get_bind())

    op.create_table('vj_update',
    sa.Column('id', postgresql.UUID(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('vj_id', postgresql.UUID(), nullable=False),
    sa.Column('real_time_update_id', postgresql.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['real_time_update_id'], ['real_time_update.id'], ),
    sa.ForeignKeyConstraint(['vj_id'], ['vehicle_journey.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_constraint(u'modification_real_time_update_id_fkey', 'modification', type_='foreignkey')
    op.create_foreign_key(None, 'modification', 'vj_update', ['real_time_update_id'], ['id'])
    op.add_column(u'real_time_update', sa.Column('connector', sa.Enum('ire', 'gtfs-rt', name='connector_type'), nullable=False))
    op.add_column(u'real_time_update', sa.Column('contributor', sa.Text(), nullable=True))
    op.add_column(u'real_time_update', sa.Column('error', sa.Text(), nullable=True))
    op.add_column(u'real_time_update', sa.Column('raw_data', sa.Text(), nullable=True))
    op.add_column(u'real_time_update', sa.Column('received_at', sa.DateTime(), nullable=False))
    op.add_column(u'real_time_update', sa.Column('status', sa.Enum('OK', 'KO', 'pending', name='rt_status'), nullable=True))
    op.alter_column(u'real_time_update', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.drop_constraint(u'real_time_update_vj_id_fkey', 'real_time_update', type_='foreignkey')
    op.drop_column(u'real_time_update', 'vj_id')


def downgrade():
    op.add_column(u'real_time_update', sa.Column('vj_id', postgresql.UUID(), autoincrement=False, nullable=False))
    op.create_foreign_key(u'real_time_update_vj_id_fkey', 'real_time_update', 'vehicle_journey', ['vj_id'], ['id'])
    op.alter_column(u'real_time_update', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.drop_column(u'real_time_update', 'status')
    op.drop_column(u'real_time_update', 'received_at')
    op.drop_column(u'real_time_update', 'raw_data')
    op.drop_column(u'real_time_update', 'error')
    op.drop_column(u'real_time_update', 'contributor')
    op.drop_column(u'real_time_update', 'connector')
    op.drop_constraint(None, 'modification', type_='foreignkey')
    op.create_foreign_key(u'modification_real_time_update_id_fkey', 'modification', 'real_time_update', ['real_time_update_id'], ['id'])
    op.drop_table('vj_update')

    #https://bitbucket.org/zzzeek/alembic/issues/159/opdrop_column-never-ends-with-an-enum
    sa.Enum(name='connector_type').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='rt_status').drop(op.get_bind(), checkfirst=False)