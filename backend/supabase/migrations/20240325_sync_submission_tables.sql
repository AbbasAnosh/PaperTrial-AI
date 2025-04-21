-- Synchronize all submission-related tables with enhanced schema

-- Update submissions table to match form_submissions
DO $$
BEGIN
    -- Add missing columns if they don't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' 
        AND column_name = 'retry_count'
    ) THEN
        ALTER TABLE submissions 
        ADD COLUMN retry_count INTEGER DEFAULT 0,
        ADD COLUMN max_retries INTEGER DEFAULT 3,
        ADD COLUMN last_retry_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE,
        ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Update status enum to match form_submissions
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' 
        AND column_name = 'status'
    ) THEN
        -- Create temporary column
        ALTER TABLE submissions ADD COLUMN status_new TEXT;
        
        -- Update values with status mapping
        UPDATE submissions 
        SET status_new = CASE 
            WHEN status::TEXT = 'pending' THEN 'processing'
            WHEN status::TEXT = 'queued' THEN 'queued'
            WHEN status::TEXT = 'processing' THEN 'processing'
            WHEN status::TEXT = 'submitted' THEN 'submitted'
            WHEN status::TEXT = 'completed' THEN 'completed'
            WHEN status::TEXT = 'failed' THEN 'failed'
            WHEN status::TEXT = 'cancelled' THEN 'cancelled'
            ELSE 'processing' -- Default for any unknown status
        END;
        
        -- Drop old column
        ALTER TABLE submissions DROP COLUMN status;
        
        -- Create new enum type if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM pg_type 
            WHERE typname = 'submission_status'
        ) THEN
            CREATE TYPE submission_status AS ENUM (
                'queued', 'processing', 'submitted', 'completed', 'failed', 'cancelled'
            );
        END IF;
        
        -- Add new column with enum type
        ALTER TABLE submissions ADD COLUMN status submission_status;
        
        -- Update values
        UPDATE submissions SET status = status_new::submission_status;
        
        -- Drop temporary column
        ALTER TABLE submissions DROP COLUMN status_new;
    END IF;
END $$;

-- Update submission_history table
DO $$
BEGIN
    -- Add missing columns if they don't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_history' 
        AND column_name = 'retry_count'
    ) THEN
        ALTER TABLE submission_history 
        ADD COLUMN retry_count INTEGER DEFAULT 0,
        ADD COLUMN max_retries INTEGER DEFAULT 3,
        ADD COLUMN last_retry_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE,
        ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add check constraints
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_submission_history_retry_count'
    ) THEN
        ALTER TABLE submission_history
        ADD CONSTRAINT check_submission_history_retry_count 
        CHECK (retry_count >= 0 AND retry_count <= max_retries);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_submission_history_deleted_at'
    ) THEN
        ALTER TABLE submission_history
        ADD CONSTRAINT check_submission_history_deleted_at 
        CHECK ((is_deleted = FALSE AND deleted_at IS NULL) OR (is_deleted = TRUE AND deleted_at IS NOT NULL));
    END IF;
END $$;

-- Update RLS policies for submissions table
DO $$
BEGIN
    -- Drop existing policies
    DROP POLICY IF EXISTS "Users can view their own submissions" ON submissions;
    DROP POLICY IF EXISTS "Users can create their own submissions" ON submissions;
    DROP POLICY IF EXISTS "Users can update their own submissions" ON submissions;
    DROP POLICY IF EXISTS "Users can delete their own submissions" ON submissions;
    
    -- Create new policies with soft delete support
    CREATE POLICY "Users can view their own submissions" 
        ON submissions 
        FOR SELECT 
        USING (auth.uid() = user_id AND (is_deleted = FALSE OR deleted_at > NOW() - INTERVAL '30 days'));
        
    CREATE POLICY "Users can create their own submissions" 
        ON submissions 
        FOR INSERT 
        WITH CHECK (auth.uid() = user_id);
        
    CREATE POLICY "Users can update their own submissions" 
        ON submissions 
        FOR UPDATE 
        USING (auth.uid() = user_id AND (is_deleted = FALSE OR deleted_at > NOW() - INTERVAL '30 days'));
        
    CREATE POLICY "Users can delete their own submissions" 
        ON submissions 
        FOR DELETE 
        USING (auth.uid() = user_id);
END $$;

-- Add function to handle soft deletes for submissions
CREATE OR REPLACE FUNCTION handle_submissions_soft_delete()
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
    DROP TRIGGER IF EXISTS set_submissions_deleted_at ON submissions;
    
    CREATE TRIGGER set_submissions_deleted_at
        BEFORE UPDATE ON submissions
        FOR EACH ROW
        EXECUTE FUNCTION handle_submissions_soft_delete();
END $$;

-- Add indexes for new columns
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'submissions' 
        AND indexname = 'idx_submissions_retry_count'
    ) THEN
        CREATE INDEX idx_submissions_retry_count ON submissions(retry_count);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'submissions' 
        AND indexname = 'idx_submissions_is_deleted'
    ) THEN
        CREATE INDEX idx_submissions_is_deleted ON submissions(is_deleted);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'submission_history' 
        AND indexname = 'idx_submission_history_retry_count'
    ) THEN
        CREATE INDEX idx_submission_history_retry_count ON submission_history(retry_count);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'submission_history' 
        AND indexname = 'idx_submission_history_is_deleted'
    ) THEN
        CREATE INDEX idx_submission_history_is_deleted ON submission_history(is_deleted);
    END IF;
END $$; 