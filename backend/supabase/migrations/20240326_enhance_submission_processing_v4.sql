-- Enhance submission processing with improved retry logic and error tracking
-- This version uses the correct syntax for view policies in Supabase

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

-- Create a simple function to update submission status
CREATE OR REPLACE FUNCTION public.update_submission_status(
    submission_id UUID,
    new_status TEXT,
    error_message TEXT DEFAULT NULL,
    error_category TEXT DEFAULT NULL,
    error_code TEXT DEFAULT NULL,
    error_details JSONB DEFAULT NULL,
    response_data JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE public.form_submissions
    SET 
        status = new_status,
        error_message = COALESCE(error_message, form_submissions.error_message),
        error_category = COALESCE(error_category, form_submissions.error_category),
        error_code = COALESCE(error_code, form_submissions.error_code),
        error_details = COALESCE(error_details, form_submissions.error_details),
        response_data = COALESCE(response_data, form_submissions.response_data),
        updated_at = NOW()
    WHERE id = submission_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a simple view for submission metrics
CREATE OR REPLACE VIEW public.submission_metrics AS
SELECT 
    DATE_TRUNC('day', created_at) AS submission_date,
    status,
    error_category,
    COUNT(*) AS submission_count,
    AVG(processing_duration_ms) AS avg_processing_time_ms,
    MAX(processing_duration_ms) AS max_processing_time_ms,
    MIN(processing_duration_ms) AS min_processing_time_ms,
    AVG(retry_count) AS avg_retry_count,
    COUNT(CASE WHEN retry_count > 0 THEN 1 END) AS retried_submissions_count
FROM public.form_submissions
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), status, error_category;

-- Grant permissions to authenticated users
GRANT SELECT ON public.submission_metrics TO authenticated;

-- For views, we need to use a different approach for RLS
-- Instead of creating a policy, we'll modify the view to include the user_id check
DROP VIEW IF EXISTS public.submission_metrics;
CREATE OR REPLACE VIEW public.submission_metrics AS
SELECT 
    DATE_TRUNC('day', created_at) AS submission_date,
    status,
    error_category,
    COUNT(*) AS submission_count,
    AVG(processing_duration_ms) AS avg_processing_time_ms,
    MAX(processing_duration_ms) AS max_processing_time_ms,
    MIN(processing_duration_ms) AS min_processing_time_ms,
    AVG(retry_count) AS avg_retry_count,
    COUNT(CASE WHEN retry_count > 0 THEN 1 END) AS retried_submissions_count
FROM public.form_submissions
WHERE created_at >= NOW() - INTERVAL '30 days'
AND user_id = auth.uid()  -- This ensures users can only see their own data
GROUP BY DATE_TRUNC('day', created_at), status, error_category; 