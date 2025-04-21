-- Enhance form_submissions table with new columns and constraints

-- Add new columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'retry_count'
    ) THEN
        ALTER TABLE form_submissions 
        ADD COLUMN retry_count INTEGER DEFAULT 0,
        ADD COLUMN max_retries INTEGER DEFAULT 3,
        ADD COLUMN last_retry_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE,
        ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN document_id UUID,
        ADD COLUMN response_data JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- Update status enum to include new values
DO $$
DECLARE
    enum_exists BOOLEAN;
    column_exists BOOLEAN;
    current_type TEXT;
BEGIN
    -- Check if the enum type exists
    SELECT EXISTS (
        SELECT 1 FROM pg_type 
        WHERE typname = 'submission_status'
    ) INTO enum_exists;
    
    -- Check if the status column exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'status'
    ) INTO column_exists;
    
    -- Get the current data type of the status column if it exists
    IF column_exists THEN
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'status'
        INTO current_type;
    END IF;
    
    -- Handle the case where the column exists but is not the right type
    IF column_exists AND current_type != 'USER-DEFINED' THEN
        -- Create a temporary column with the new type
        ALTER TABLE form_submissions ADD COLUMN status_new TEXT;
        
        -- Update the temporary column with the current values
        UPDATE form_submissions SET status_new = status::TEXT;
        
        -- Drop the old column
        ALTER TABLE form_submissions DROP COLUMN status;
        
        -- Create the new enum type if it doesn't exist
        IF NOT enum_exists THEN
            CREATE TYPE submission_status AS ENUM (
                'queued', 'processing', 'submitted', 'completed', 'failed', 'cancelled'
            );
        END IF;
        
        -- Update the temporary column to the new enum type
        ALTER TABLE form_submissions 
        ALTER COLUMN status_new TYPE submission_status 
        USING status_new::submission_status;
        
        -- Rename the new column
        ALTER TABLE form_submissions RENAME COLUMN status_new TO status;
    -- Handle the case where the column exists and is already the right type
    ELSIF column_exists AND current_type = 'USER-DEFINED' THEN
        -- Check if we need to update the enum type
        IF NOT enum_exists THEN
            -- Create the enum type
            CREATE TYPE submission_status AS ENUM (
                'queued', 'processing', 'submitted', 'completed', 'failed', 'cancelled'
            );
            
            -- We can't directly alter the column type, so we need to recreate it
            ALTER TABLE form_submissions ADD COLUMN status_new submission_status;
            UPDATE form_submissions SET status_new = status::TEXT::submission_status;
            ALTER TABLE form_submissions DROP COLUMN status;
            ALTER TABLE form_submissions RENAME COLUMN status_new TO status;
        END IF;
    -- Handle the case where the column doesn't exist
    ELSIF NOT column_exists THEN
        -- Create the enum type if it doesn't exist
        IF NOT enum_exists THEN
            CREATE TYPE submission_status AS ENUM (
                'queued', 'processing', 'submitted', 'completed', 'failed', 'cancelled'
            );
        END IF;
        
        -- Add the column with the new enum type
        ALTER TABLE form_submissions 
        ADD COLUMN status submission_status DEFAULT 'queued';
    END IF;
END $$;

-- Create new indexes if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_retry_count'
    ) THEN
        CREATE INDEX idx_form_submissions_retry_count ON form_submissions(retry_count);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_is_deleted'
    ) THEN
        CREATE INDEX idx_form_submissions_is_deleted ON form_submissions(is_deleted);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_document_id'
    ) THEN
        CREATE INDEX idx_form_submissions_document_id ON form_submissions(document_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_response_data'
    ) THEN
        CREATE INDEX idx_form_submissions_response_data ON form_submissions USING GIN (response_data);
    END IF;
END $$;

-- Add check constraints
DO $$
BEGIN
    -- Check if constraints already exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_retry_count'
    ) THEN
        ALTER TABLE form_submissions
        ADD CONSTRAINT check_retry_count 
        CHECK (retry_count >= 0 AND retry_count <= max_retries);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_deleted_at'
    ) THEN
        ALTER TABLE form_submissions
        ADD CONSTRAINT check_deleted_at 
        CHECK ((is_deleted = FALSE AND deleted_at IS NULL) OR (is_deleted = TRUE AND deleted_at IS NOT NULL));
    END IF;
END $$;

-- Update RLS policies to handle soft delete
DO $$
BEGIN
    -- Drop existing policy if it exists
    DROP POLICY IF EXISTS "Users can view their own submissions" ON form_submissions;
    
    -- Create new policy
    CREATE POLICY "Users can view their own submissions" 
        ON form_submissions 
        FOR SELECT 
        USING (auth.uid() = user_id AND (is_deleted = FALSE OR deleted_at > NOW() - INTERVAL '30 days'));
END $$;

-- Add function to handle soft deletes
CREATE OR REPLACE FUNCTION handle_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_deleted = TRUE AND OLD.is_deleted = FALSE THEN
        NEW.deleted_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for soft delete if it doesn't exist
DO $$
BEGIN
    DROP TRIGGER IF EXISTS set_form_submissions_deleted_at ON form_submissions;
    
    CREATE TRIGGER set_form_submissions_deleted_at
        BEFORE UPDATE ON form_submissions
        FOR EACH ROW
        EXECUTE FUNCTION handle_soft_delete();
END $$; 