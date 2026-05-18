"""initial schema

Revision ID: 20260518_01
Revises:
Create Date: 2026-05-18 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260518_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'config',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('namespace', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('namespace', 'key', name='uq_config_namespace_key'),
    )
    op.create_index(op.f('ix_config_namespace'), 'config', ['namespace'], unique=False)

    op.create_table(
        'flights',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('origin', sa.String(), nullable=False),
        sa.Column('destination', sa.String(), nullable=False),
        sa.Column('flight_date', sa.Date(), nullable=False),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('notification_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'flight_fare_snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('flight_id', sa.String(), nullable=False),
        sa.Column('fare', sa.Float(), nullable=True),
        sa.Column('flight_number', sa.String(), nullable=True),
        sa.Column('departure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrival_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scrape_status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('flight_fare_snapshots')
    op.drop_table('flights')
    op.drop_index(op.f('ix_config_namespace'), table_name='config')
    op.drop_table('config')
