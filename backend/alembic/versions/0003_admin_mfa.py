"""Encrypted privileged identity and replay-resistant MFA sessions."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('users',sa.Column('username',sa.String(40),nullable=True))
    op.create_index('ix_users_username_unique','users',['username'],unique=True)
    op.create_index('ix_users_username_lower_unique','users',[sa.text('lower(username)')],unique=True)
    op.add_column('users',sa.Column('mfa_secret_encrypted',sa.Text(),nullable=True))
    op.add_column('users',sa.Column('mfa_last_step',sa.Integer(),nullable=False,server_default='-1'))
    op.add_column('users',sa.Column('mfa_confirmed',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column('sessions',sa.Column('mfa_verified',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_table('mfa_enrollments',sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_mfa_enrollments_user_id','mfa_enrollments',['user_id'])
def downgrade():
    op.drop_index('ix_mfa_enrollments_user_id',table_name='mfa_enrollments'); op.drop_table('mfa_enrollments')
    op.drop_column('sessions','mfa_verified')
    op.drop_column('users','mfa_confirmed'); op.drop_column('users','mfa_last_step'); op.drop_column('users','mfa_secret_encrypted')
    op.drop_index('ix_users_username_lower_unique',table_name='users')
    op.drop_index('ix_users_username_unique',table_name='users'); op.drop_column('users','username')
