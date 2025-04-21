-- Add events array to processed_documents table
ALTER TABLE processed_documents ADD COLUMN IF NOT EXISTS events JSONB[] DEFAULT '{}';

-- Create a custom type for submission status if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'submission_status') THEN
        CREATE TYPE submission_status AS ENUM ('queued', 'in_progress', 'completed', 'failed');
    END IF;
END$$;

-- Update the status column to use the custom enum type
ALTER TABLE processed_documents 
    ALTER COLUMN status TYPE submission_status 
    USING status::submission_status;

-- Add a default value for the status column
ALTER TABLE processed_documents 
    ALTER COLUMN status SET DEFAULT 'queued'::submission_status;

-- Add a message column
ALTER TABLE processed_documents ADD COLUMN IF NOT EXISTS message TEXT;

-- Create an index on the events column
CREATE INDEX IF NOT EXISTS idx_processed_documents_events ON processed_documents USING GIN (events); 