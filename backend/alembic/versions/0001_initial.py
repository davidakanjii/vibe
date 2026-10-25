"""Initial transactional platform schema (frozen revision metadata)."""
from pathlib import Path
from runpy import run_path
from alembic import op
revision='0001'
down_revision=None
branch_labels=None
depends_on=None
def metadata():
    return run_path(str(Path(__file__).resolve().parents[1] / 'initial_schema.py'))['Base'].metadata
def upgrade(): metadata().create_all(op.get_bind())
def downgrade(): metadata().drop_all(op.get_bind())
