-- Enhance submission processing with improved retry logic and error tracking

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO postgres, authenticated, anon;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, authenticated, anon;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, authenticated, anon;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO postgres, authenticated, anon;

-- Add error category enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'error_category') THEN
        CREATE TYPE error_category AS ENUM (
            'network',
            'validation',
            'system',
            'external_service',
            'timeout',
            'unknown'
        );
    END IF;
END$$;

-- Add error tracking columns to form_submissions
ALTER TABLE IF EXISTS form_submissions
ADD COLUMN IF NOT EXISTS error_category error_category,
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
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_form_submissions_error_category') THEN
        CREATE INDEX idx_form_submissions_error_category ON form_submissions(error_category);
    END IF;
END$$;

-- Create index for retry scheduling
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_form_submissions_next_retry') THEN
        CREATE INDEX idx_form_submissions_next_retry ON form_submissions(next_retry_at) 
        WHERE status = 'failed' AND retry_count < max_retries;
    END IF;
END$$;

-- Create function to calculate next retry time with exponential backoff
CREATE OR REPLACE FUNCTION calculate_next_retry_time(
    retry_count INTEGER,
    base_backoff_seconds INTEGER DEFAULT 60
) RETURNS TIMESTAMP WITH TIME ZONE AS $$
BEGIN
    -- Exponential backoff with jitter: base * 2^retry_count * (0.5 + random)
    RETURN NOW() + 
           (base_backoff_seconds * POWER(2, retry_count) * (0.5 + random()))::INTEGER * 
           INTERVAL '1 second';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to update submission with processing metrics
CREATE OR REPLACE FUNCTION update_submission_processing_metrics(
    submission_id UUID,
    new_status submission_status,
    error_category error_category DEFAULT NULL,
    error_code VARCHAR DEFAULT NULL,
    error_details JSONB DEFAULT NULL,
    external_service_response JSONB DEFAULT NULL
) RETURNS form_submissions AS $$
DECLARE
    updated_submission form_submissions;
BEGIN
    UPDATE form_submissions
    SET 
        status = new_status,
        error_category = COALESCE(error_category, form_submissions.error_category),
        error_code = COALESCE(error_code, form_submissions.error_code),
        error_details = COALESCE(error_details, form_submissions.error_details),
        external_service_response = COALESCE(external_service_response, form_submissions.external_service_response),
        processing_completed_at = CASE 
            WHEN new_status IN ('completed', 'failed', 'cancelled') THEN NOW()
            ELSE processing_completed_at
        END,
        processing_duration_ms = CASE 
            WHEN new_status IN ('completed', 'failed', 'cancelled') AND processing_started_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (NOW() - processing_started_at)) * 1000
            ELSE processing_duration_ms
        END,
        next_retry_at = CASE 
            WHEN new_status = 'failed' AND retry_count < max_retries
            THEN calculate_next_retry_time(retry_count, retry_backoff_seconds)
            ELSE NULL
        END,
        updated_at = NOW()
    WHERE id = submission_id
    RETURNING * INTO updated_submission;
    
    RETURN updated_submission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create view for submission metrics
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'submission_metrics') THEN
        CREATE VIEW submission_metrics AS
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
        FROM form_submissions
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', created_at), status, error_category;
    END IF;
END$$;

-- Set up RLS for the view
ALTER VIEW IF EXISTS submission_metrics OWNER TO authenticated;

-- Create policy for the view
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can view their own submission metrics') THEN
        CREATE POLICY "Users can view their own submission metrics"
        ON submission_metrics
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM form_submissions fs
                WHERE fs.user_id = auth.uid()
                AND DATE_TRUNC('day', fs.created_at) = submission_metrics.submission_date
            )
        );
    END IF;
END$$; 