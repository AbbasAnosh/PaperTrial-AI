import logging
from typing import Optional, Dict, Any
from app.core.supabase_client import get_admin_client
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseMigrationError(Exception):
    """Custom exception for database migration errors"""
    pass

async def add_extracted_fields_column() -> None:
    """
    Add extracted_fields column to documents table if it doesn't exist.
    Uses a transaction to ensure data integrity.
    """
    client = get_admin_client()
    try:
        # Check if column exists
        response = await client.table("documents").select("extracted_fields").limit(1).execute()
        if response.data and "extracted_fields" in response.data[0]:
            logger.info("extracted_fields column already exists")
            return

        logger.info("Starting migration: Adding extracted_fields column")
        
        # Start transaction
        async with client.transaction() as txn:
            # Create new table with desired schema
            await txn.execute("""
                CREATE TABLE documents_new (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES auth.users(id),
                    filename TEXT NOT NULL,
                    content TEXT,
                    metadata JSONB,
                    extracted_fields JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Copy data from old table
            await txn.execute("""
                INSERT INTO documents_new (id, user_id, filename, content, metadata, created_at, updated_at)
                SELECT id, user_id, filename, content, metadata, created_at, updated_at
                FROM documents
            """)
            
            # Drop old table and rename new one
            await txn.execute("DROP TABLE documents")
            await txn.execute("ALTER TABLE documents_new RENAME TO documents")
            
            # Create indexes
            await txn.execute("""
                CREATE INDEX idx_documents_user_id ON documents(user_id);
                CREATE INDEX idx_documents_created_at ON documents(created_at);
                CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);
                CREATE INDEX idx_documents_extracted_fields ON documents USING GIN (extracted_fields);
            """)
            
            logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise DatabaseMigrationError(f"Failed to add extracted_fields column: {str(e)}")

async def add_submission_history_table() -> None:
    """
    Create submission_history table if it doesn't exist.
    Uses a transaction to ensure data integrity.
    """
    client = get_admin_client()
    try:
        # Check if table exists
        response = await client.table("submission_history").select("id").limit(1).execute()
        if response.data:
            logger.info("submission_history table already exists")
            return

        logger.info("Starting migration: Creating submission_history table")
        
        # Start transaction
        async with client.transaction() as txn:
            # Create table
            await txn.execute("""
                CREATE TABLE submission_history (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    message TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create indexes
            await txn.execute("""
                CREATE INDEX idx_submission_history_submission_id ON submission_history(submission_id);
                CREATE INDEX idx_submission_history_status ON submission_history(status);
                CREATE INDEX idx_submission_history_created_at ON submission_history(created_at);
                CREATE INDEX idx_submission_history_metadata ON submission_history USING GIN (metadata);
            """)
            
            logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise DatabaseMigrationError(f"Failed to create submission_history table: {str(e)}")

async def run_migrations() -> None:
    """
    Run all database migrations in sequence.
    """
    migrations = [
        ("add_extracted_fields_column", add_extracted_fields_column),
        ("add_submission_history_table", add_submission_history_table)
    ]
    
    for name, migration in migrations:
        try:
            logger.info(f"Running migration: {name}")
            await migration()
        except DatabaseMigrationError as e:
            logger.error(f"Migration {name} failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during migration {name}: {str(e)}")
            raise DatabaseMigrationError(f"Unexpected error during migration {name}: {str(e)}") 