-- Enhance submission processing with improved retry logic and error tracking
-- This is a minimal version that focuses only on the essential changes

-- Add error tracking columns to form_submissions
ALTER TABLE IF EXISTS public.form_submissions
ADD COLUMN IF NOT EXISTS error_category TEXT,
ADD COLUMN IF NOT EXISTS error_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS error_details JSONB,
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_duration_ms INTEGER,
ADD COLUMN IF NOT EXISTS retry_backoff_seconds INTEGER DEFAULT 60,
ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS external_service_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS external_service_response JSONB;

-- Create index for error tracking
CREATE INDEX IF NOT EXISTS idx_form_submissions_error_category 
ON public.form_submissions(error_category);

-- Create index for retry scheduling
CREATE INDEX IF NOT EXISTS idx_form_submissions_next_retry 
ON public.form_submissions(next_retry_at) 
WHERE status = 'failed' AND retry_count < max_retries; 