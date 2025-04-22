"""Initial database migration

Revision ID: 20240318_initial
Revises: 
Create Date: 2024-03-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240318_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create form_templates table
    op.create_table(
        'form_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fields', postgresql.JSONB(), nullable=False),
        sa.Column('validation_rules', postgresql.JSONB(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create form_submissions table
    op.create_table(
        'form_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('form_templates.id')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_category', sa.String(50), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create field_mappings table
    op.create_table(
        'field_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('form_templates.id')),
        sa.Column('source_field', sa.String(255), nullable=False),
        sa.Column('target_field', sa.String(255), nullable=False),
        sa.Column('transformation_rules', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create pdf_documents table
    op.create_table(
        'pdf_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('storage_path', sa.String(512), nullable=False),
        sa.Column('extracted_data', postgresql.JSONB(), nullable=True),
        sa.Column('processing_status', sa.String(50), nullable=False),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_form_templates_user_id', 'form_templates', ['user_id'])
    op.create_index('ix_form_submissions_template_id', 'form_submissions', ['template_id'])
    op.create_index('ix_form_submissions_user_id', 'form_submissions', ['user_id'])
    op.create_index('ix_form_submissions_status', 'form_submissions', ['status'])
    op.create_index('ix_field_mappings_template_id', 'field_mappings', ['template_id'])
    op.create_index('ix_pdf_documents_user_id', 'pdf_documents', ['user_id'])

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('pdf_documents')
    op.drop_table('field_mappings')
    op.drop_table('form_submissions')
    op.drop_table('form_templates')
    op.drop_table('users') 