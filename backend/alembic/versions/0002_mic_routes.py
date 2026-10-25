"""Persist scoped microphone routes and channel venue zones."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('channels',sa.Column('zone',sa.String(80),nullable=False,server_default='main'))
    op.create_table('hypeman_routes',
        sa.Column('event_id',sa.String(36),sa.ForeignKey('events.id'),primary_key=True),
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('zone',sa.String(80),nullable=False),
        sa.Column('channel_ids',sa.Text(),nullable=False),
        sa.Column('muted',sa.Boolean(),nullable=False),
        sa.Column('push_to_talk',sa.Boolean(),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False),
        sa.Column('gain',sa.Float(),nullable=False),
        sa.Column('broadcast_all',sa.Boolean(),nullable=False),
        sa.Column('allow_broadcast_all',sa.Boolean(),nullable=False))
def downgrade():
    op.drop_table('hypeman_routes')
    op.drop_column('channels','zone')
