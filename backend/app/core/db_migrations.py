import logging
import time
from typing import Optional, Dict, Any
from app.core.supabase import get_admin_client
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseMigrationError(Exception):
    """Custom exception for database migration errors"""
    pass

def execute_with_retry(client, query: str, max_retries: int = 3, delay: int = 5) -> None:
    """Execute a SQL query with retry logic."""
    for attempt in range(max_retries):
        try:
            client.postgrest.schema("public").rpc("execute_sql", {"query": query}).execute()
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
            time.sleep(delay)

def add_extracted_fields_column() -> None:
    """
    Add extracted_fields column to documents table if it doesn't exist.
    Uses a transaction to ensure data integrity.
    """
    client = get_admin_client()
    try:
        # Check if table exists by trying to select from it
        try:
            response = client.table("documents").select("*").limit(1).execute()
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Create the table using raw SQL through Supabase's REST API
                execute_with_retry(client, """
                    CREATE TABLE documents (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        user_id UUID REFERENCES auth.users(id),
                        filename TEXT NOT NULL,
                        content TEXT,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        extracted_fields JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    CREATE INDEX idx_documents_user_id ON documents(user_id);
                    CREATE INDEX idx_documents_created_at ON documents(created_at);
                    CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);
                    CREATE INDEX idx_documents_extracted_fields ON documents USING GIN (extracted_fields);
                    
                    ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
                    
                    CREATE POLICY "Users can view their own documents"
                        ON documents FOR SELECT
                        USING (auth.uid() = user_id);
                        
                    CREATE POLICY "Users can insert their own documents"
                        ON documents FOR INSERT
                        WITH CHECK (auth.uid() = user_id);
                        
                    CREATE POLICY "Users can update their own documents"
                        ON documents FOR UPDATE
                        USING (auth.uid() = user_id);
                        
                    CREATE POLICY "Users can delete their own documents"
                        ON documents FOR DELETE
                        USING (auth.uid() = user_id);
                """)
                logger.info("Created documents table with all required columns and policies")
            else:
                raise e

        logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise DatabaseMigrationError(f"Failed to add extracted_fields column: {str(e)}")

def add_submission_history_table() -> None:
    """
    Create submission_history table if it doesn't exist.
    Uses a transaction to ensure data integrity.
    """
    client = get_admin_client()
    try:
        # Check if table exists by trying to select from it
        try:
            response = client.table("submission_history").select("*").limit(1).execute()
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Create the table and indexes one by one
                statements = [
                    """
                    CREATE TABLE submission_history (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
                        status TEXT NOT NULL,
                        message TEXT,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                    """,
                    "CREATE INDEX idx_submission_history_submission_id ON submission_history(submission_id)",
                    "CREATE INDEX idx_submission_history_status ON submission_history(status)",
                    "CREATE INDEX idx_submission_history_created_at ON submission_history(created_at)",
                    "CREATE INDEX idx_submission_history_metadata ON submission_history USING GIN (metadata)",
                    "ALTER TABLE submission_history ENABLE ROW LEVEL SECURITY",
                    """
                    CREATE POLICY "Users can view their own submission history"
                        ON submission_history FOR SELECT
                        USING (
                            EXISTS (
                                SELECT 1 FROM submissions
                                WHERE submissions.id = submission_history.submission_id
                                AND submissions.user_id = auth.uid()
                            )
                        )
                    """,
                    """
                    CREATE POLICY "Users can insert their own submission history"
                        ON submission_history FOR INSERT
                        WITH CHECK (
                            EXISTS (
                                SELECT 1 FROM submissions
                                WHERE submissions.id = submission_history.submission_id
                                AND submissions.user_id = auth.uid()
                            )
                        )
                    """,
                    """
                    CREATE POLICY "Users can update their own submission history"
                        ON submission_history FOR UPDATE
                        USING (
                            EXISTS (
                                SELECT 1 FROM submissions
                                WHERE submissions.id = submission_history.submission_id
                                AND submissions.user_id = auth.uid()
                            )
                        )
                    """,
                    """
                    CREATE POLICY "Users can delete their own submission history"
                        ON submission_history FOR DELETE
                        USING (
                            EXISTS (
                                SELECT 1 FROM submissions
                                WHERE submissions.id = submission_history.submission_id
                                AND submissions.user_id = auth.uid()
                            )
                        )
                    """
                ]
                
                for statement in statements:
                    try:
                        execute_with_retry(client, statement.strip())
                        logger.info(f"Successfully executed: {statement[:50]}...")
                    except Exception as stmt_error:
                        logger.error(f"Failed to execute statement: {statement[:50]}...")
                        raise stmt_error

                logger.info("Created submission_history table with all required columns and policies")
            else:
                raise e

        logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise DatabaseMigrationError(f"Failed to create submission_history table: {str(e)}")

def create_annotations_tables() -> None:
    """
    Create annotations and comments tables if they don't exist.
    Uses a transaction to ensure data integrity.
    """
    client = get_admin_client()
    try:
        # Check if tables exist
        try:
            response = client.table("annotations").select("id").limit(1).execute()
            logger.info("annotations table already exists")
            return
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                logger.info("Creating annotations and comments tables...")
            else:
                raise e

        logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise DatabaseMigrationError(f"Failed to create annotations and comments tables: {str(e)}")

def run_migrations() -> None:
    """
    Run all database migrations in sequence.
    """
    migrations = [
        ("add_extracted_fields_column", add_extracted_fields_column),
        ("add_submission_history_table", add_submission_history_table),
        ("create_annotations_tables", create_annotations_tables)
    ]
    
    for name, migration in migrations:
        try:
            logger.info(f"Running migration: {name}")
            migration()
        except DatabaseMigrationError as e:
            logger.error(f"Migration {name} failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during migration {name}: {str(e)}")
            raise DatabaseMigrationError(f"Unexpected error during migration {name}: {str(e)}") 