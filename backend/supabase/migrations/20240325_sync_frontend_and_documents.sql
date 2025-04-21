-- Synchronize frontend types and processed_documents with enhanced submission status

-- Update processed_documents table status enum
DO $$
BEGIN
    -- Create temporary column
    ALTER TABLE processed_documents ADD COLUMN status_new TEXT;
    
    -- Update values with status mapping
    UPDATE processed_documents 
    SET status_new = CASE 
        WHEN status::TEXT = 'queued' THEN 'queued'
        WHEN status::TEXT = 'in_progress' THEN 'processing'
        WHEN status::TEXT = 'completed' THEN 'completed'
        WHEN status::TEXT = 'failed' THEN 'failed'
        ELSE 'processing' -- Default for any unknown status
    END;
    
    -- Drop old column
    ALTER TABLE processed_documents DROP COLUMN status;
    
    -- Add new column with enum type
    ALTER TABLE processed_documents ADD COLUMN status submission_status;
    
    -- Update values
    UPDATE processed_documents SET status = status_new::submission_status;
    
    -- Drop temporary column
    ALTER TABLE processed_documents DROP COLUMN status_new;
    
    -- Add default value
    ALTER TABLE processed_documents 
        ALTER COLUMN status SET DEFAULT 'queued'::submission_status;
END $$;

-- Add missing columns to form_submissions if they don't exist
DO $$
BEGIN
    -- Add confirmation_number column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'confirmation_number'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN confirmation_number TEXT;
    END IF;
    
    -- Add error column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'error'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN error TEXT;
    END IF;
    
    -- Add response_data column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'response_data'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN response_data JSONB DEFAULT '{}';
    END IF;
    
    -- Add retry_count column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'retry_count'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN retry_count INTEGER DEFAULT 0;
    END IF;
    
    -- Add max_retries column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'max_retries'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN max_retries INTEGER DEFAULT 3;
    END IF;
    
    -- Add last_retry_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'last_retry_at'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN last_retry_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Add is_deleted column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'is_deleted'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add deleted_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE form_submissions ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- Ensure RLS is enabled on the form_submissions table
ALTER TABLE form_submissions ENABLE ROW LEVEL SECURITY;

-- Create or update RLS policies for form_submissions
DO $$
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Users can view their own submissions" ON form_submissions;
    DROP POLICY IF EXISTS "Users can create their own submissions" ON form_submissions;
    DROP POLICY IF EXISTS "Users can update their own submissions" ON form_submissions;
    DROP POLICY IF EXISTS "Users can delete their own submissions" ON form_submissions;
    
    -- Create new policies with soft delete support
    CREATE POLICY "Users can view their own submissions" 
        ON form_submissions 
        FOR SELECT 
        USING (auth.uid() = user_id AND (is_deleted = FALSE OR deleted_at > NOW() - INTERVAL '30 days'));
        
    CREATE POLICY "Users can create their own submissions" 
        ON form_submissions 
        FOR INSERT 
        WITH CHECK (auth.uid() = user_id);
        
    CREATE POLICY "Users can update their own submissions" 
        ON form_submissions 
        FOR UPDATE 
        USING (auth.uid() = user_id AND (is_deleted = FALSE OR deleted_at > NOW() - INTERVAL '30 days'));
        
    CREATE POLICY "Users can delete their own submissions" 
        ON form_submissions 
        FOR DELETE 
        USING (auth.uid() = user_id);
END $$;

-- Create a view for frontend compatibility
CREATE OR REPLACE VIEW submission_status_view AS
SELECT 
    id,
    user_id,
    form_id,
    form_data,
    screenshots,
    CASE 
        WHEN status = 'queued' THEN 'pending'
        WHEN status = 'processing' THEN 'processing'
        WHEN status = 'submitted' THEN 'submitted'
        WHEN status = 'completed' THEN 'completed'
        WHEN status = 'failed' THEN 'failed'
        WHEN status = 'cancelled' THEN 'failed'
        ELSE 'processing'
    END as frontend_status,
    confirmation_number,
    error,
    created_at,
    updated_at,
    metadata,
    document_id,
    response_data,
    retry_count,
    max_retries,
    last_retry_at,
    is_deleted,
    deleted_at
FROM form_submissions;

-- Create a function to update submission status with frontend compatibility
CREATE OR REPLACE FUNCTION update_submission_status(
    submission_id UUID,
    new_status TEXT,
    message TEXT DEFAULT NULL
)
RETURNS SETOF submission_status_view
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    mapped_status submission_status;
BEGIN
    -- Map frontend status to enum
    mapped_status := CASE new_status
        WHEN 'pending' THEN 'queued'::submission_status
        WHEN 'processing' THEN 'processing'::submission_status
        WHEN 'submitted' THEN 'submitted'::submission_status
        WHEN 'completed' THEN 'completed'::submission_status
        WHEN 'failed' THEN 'failed'::submission_status
        ELSE 'processing'::submission_status
    END;
    
    -- Update the submission
    UPDATE form_submissions
    SET 
        status = mapped_status,
        message = COALESCE(message, form_submissions.message),
        updated_at = NOW()
    WHERE id = submission_id;
    
    -- Return the updated record through the view
    RETURN QUERY
    SELECT * FROM submission_status_view
    WHERE id = submission_id;
END;
$$; 